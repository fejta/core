"""Support the sensor of a BloomSky weather station."""
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS,

    # Units of measurement
    VOLT,

    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,

    LENGTH_MILLIMETERS,
    LENGTH_INCHES,

    PRESSURE_INHG,
    PRESSURE_MBAR,

    AREA_SQUARE_METERS,

    UV_INDEX,

    PERCENTAGE,

    PRECIPITATION_MILLIMETERS_PER_HOUR,

    SPEED_INCHES_PER_HOUR,
    SPEED_MILES_PER_HOUR,
    SPEED_METERS_PER_SECOND,
)
import homeassistant.helpers.config_validation as cv

from . import DOMAIN

# See http://weatherlution.com/bloomsky-api/
# http://weatherlution.com/wp-content/uploads/2016/01/v1.6BloomskyDeviceOwnerAPIDocumentationforBusinessOwners.pdf

# These are the available sensors
SENSOR_TYPES = [
    # SKY
    "Temperature",
    "Humidity",
    "Pressure",
    "Luminance",
    "UVIndex", # Also on storm
    "Voltage",

    # Storm
    "WindDirection", # NW, etc
    "RainDaily", # 12a-1159p
    "WindGust",
    "SustainedWindSpeed",
    "RainRate", # last 10m
    "24hRain", # last 24hs
]

# Sensor units - these do not currently align with the API documentation
SENSOR_UNITS_IMPERIAL = {
    "Temperature": TEMP_FAHRENHEIT,
    "Humidity": PERCENTAGE,
    "Pressure": PRESSURE_INHG,
    "Luminance": f"cd/{AREA_SQUARE_METERS}",
    "Voltage": f"m{VOLT}",

    "RainDaily": LENGTH_INCHES,
    "WindGust": SPEED_MILES_PER_HOUR,
    "SustainedWindSpeed": SPEED_MILES_PER_HOUR,
    "RainRate": SPEED_INCHES_PER_HOUR,
    "24hRain": LENGTH_INCHES,
}

# Metric units
SENSOR_UNITS_METRIC = {
    "Temperature": TEMP_CELSIUS,
    "Humidity": PERCENTAGE,
    "Pressure": PRESSURE_MBAR,
    "Luminance": f"cd/{AREA_SQUARE_METERS}",
    "Voltage": f"m{VOLT}",

    # "WindDirection"
    "RainDaily": LENGTH_MILLIMETERS,
    "WindGust": SPEED_METERS_PER_SECOND,
    "SustainedWindSpeed": SPEED_METERS_PER_SECOND,
    "RainRate": PRECIPITATION_MILLIMETERS_PER_HOUR,
    "24hRain": LENGTH_MILLIMETERS,
}

# Which sensors to format numerically
FORMAT_NUMBERS = [
        "Temperature",
        "Pressure",
        "Voltage",

        "RainDaily",
        "WindGust",
        "SustainedWindSpeed",
        "RainRate",
        "24hRain",
]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_MONITORED_CONDITIONS, default=SENSOR_TYPES): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        )
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the available BloomSky weather sensors."""
    # Default needed in case of discovery
    if discovery_info is not None:
        return

    sensors = config[CONF_MONITORED_CONDITIONS]
    bloomsky = hass.data[DOMAIN]

    for device in bloomsky.devices.values():
        for variable in sensors:
            add_entities([BloomSkySensor(bloomsky, device, variable)], True)


class BloomSkySensor(SensorEntity):
    """Representation of a single sensor in a BloomSky device."""

    def __init__(self, bs, device, sensor_name):
        """Initialize a BloomSky sensor."""
        self._bloomsky = bs
        self._device_id = device["DeviceID"]
        self._sensor_name = sensor_name
        self._name = f"{device['DeviceName']} {sensor_name}"
        self._state = None
        self._unique_id = f"{self._device_id}-{self._sensor_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the BloomSky device and this sensor."""
        return self._name

    @property
    def state(self):
        """Return the current state, eg. value, of this sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the sensor units."""
        if self._bloomsky.is_metric:
            return SENSOR_UNITS_METRIC.get(self._sensor_name, None)
        return SENSOR_UNITS_IMPERIAL.get(self._sensor_name, None)

    def update(self):
        """Request an update from the BloomSky API."""
        self._bloomsky.refresh_devices()

        data = self._bloomsky.devices[self._device_id].get("Data", {})
        # Storm supersedes sky data.
        data.update(self._bloomsky.devices[self._device_id].get("Storm", {}))
        state = data[self._sensor_name]

        if self._sensor_name in FORMAT_NUMBERS:
            self._state = f"{state:.2f}"
        else:
            self._state = state
