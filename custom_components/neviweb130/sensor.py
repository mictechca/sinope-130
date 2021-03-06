"""
Support for Neviweb sensors connected via GT130 ZigBee.
model xxx = VA4201WZ, sedna valve 1 inch
model xxx = VA4200WZ, sedna valve 3/4 inch
model 5051 = WL4200, water leak detector
model xxx = WL4200S, water leak detector with sensor
model 4110 = LM4110-ZB, level monitor
For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""

import logging

import voluptuous as vol
import time

import custom_components.neviweb130 as neviweb130
from . import (SCAN_INTERVAL)

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (DEVICE_CLASS_BATTERY, DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT, STATE_OK, ATTR_VOLTAGE)
from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from .const import (DOMAIN, ATTR_ROOM_TEMPERATURE, ATTR_WATER_LEAK_STATUS, ATTR_LEVEL_STATUS, ATTR_BATTERY_VOLTAGE, MODE_OFF, STATE_WATER_LEAK)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neviweb130 sensor'

UPDATE_ATTRIBUTES = [ATTR_ROOM_TEMPERATURE, ATTR_WATER_LEAK_STATUS, ATTR_BATTERY_VOLTAGE]

IMPLEMENTED_TANK_MONITOR = [4110]
IMPLEMENTED_SENSOR_MODEL = [5051]
IMPLEMENTED_DEVICE_MODEL = IMPLEMENTED_SENSOR_MODEL + IMPLEMENTED_TANK_MONITOR

SENSOR_TYPES = [
    ["temperature", TEMP_CELSIUS, "mdi:thermometer"],
    ["leak status", None, "mdi:water-percent"],
    ["level status", "%", "mdi:water-percent"],
    ["battery", "v", "mdi:battery-50"],
]

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Neviweb sensor."""
    data = hass.data[DOMAIN]
    
    devices = []
    for device_info in data.neviweb130_client.gateway_data:
        if "signature" in device_info and \
            "model" in device_info["signature"] and \
            device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL:
            device_name = '{} {}'.format(DEFAULT_NAME, device_info["name"])
            devices.append(Neviweb130Sensor(data, device_info, device_name))

    async_add_entities(devices, True)

class Neviweb130Sensor(Entity):
    """Implementation of a Neviweb sensor."""

    def __init__(self, data, device_info, name):
        """Initialize."""
        self._name = name
        self._client = data.neviweb130_client
        self._id = device_info["id"]
        self._cur_temp = None
        self._leak_status = None
        self._battery_voltage = None
        self._is_monitor = device_info["signature"]["model"] in \
            IMPLEMENTED_TANK_MONITOR
        self._level_status = None
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        if self._is_monitor:
            MONITOR_ATTRIBUTE = [ATTR_LEVEL_STATUS]
        else:
            MONITOR_ATTRIBUTE = []
        """Get the latest data from Neviweb and update the state."""
        start = time.time()
        device_data = self._client.get_device_attributes(self._id,
            UPDATE_ATTRIBUTES + MONITOR_ATTRIBUTE)
        device_daily_stats = self._client.get_device_daily_stats(self._id)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_data)
        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._cur_temp = device_data[ATTR_ROOM_TEMPERATURE]      
                self._leak_status = STATE_WATER_LEAK if \
                    device_data[ATTR_WATER_LEAK_STATUS] == STATE_WATER_LEAK else "ok"
                if self._is_monitor:
                    self._level_status = device_data[ATTR_LEVEL_STATUS]
#                self._operation_mode = device_data[ATTR_POWER_MODE] if \
#                    device_data[ATTR_POWER_MODE] is not None else MODE_MANUAL
                self._battery_voltage = device_data[ATTR_BATTERY_VOLTAGE]
                return
            _LOGGER.warning("Error in reading device %s: (%s)", self._name, device_data)
            return
        _LOGGER.warning("Cannot update %s: %s", self._name, device_data)     

    @property
    def unique_id(self):
        """Return unique ID based on Neviweb device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    
    @property
    def current_temperature(self):
        """Return the current sensor temperature."""
        return self._cur_temp
    
    @property  
    def leak_status(self):
        """Return current sensor leak status: 'water' or 'ok' """
        return self._leak_status != None
    
    @property  
    def level_status(self):
        """Return current sensor liquid level status in % """
        return self._level_status != None
    
    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {'Battery': self._battery_voltage,
                'leak': self._leak_status,
#                'temperature': self._cur_temp,
#                'level': self._level_status,
                'id': self._id}

    @property
    def battery_voltage(self):
        """Return the current battery voltage."""
        return self._battery_voltage
