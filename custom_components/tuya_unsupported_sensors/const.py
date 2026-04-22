"""Constants for the Tuya Unsupported Sensors integration."""

DOMAIN = "tuya_unsupported_sensors"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_REGION = "region"
CONF_DEVICES = "devices"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_LAST_ERROR = "last_error"

DEFAULT_UPDATE_INTERVAL = 60
MIN_UPDATE_INTERVAL = 1
MAX_UPDATE_INTERVAL = 1800

# IOT CORE TRIAL PLAN limits
TRIAL_MAX_DEVICES = 50
TRIAL_MAX_CONTROLLABLE_DEVICES = 10
TRIAL_MAX_API_CALLS_PER_MONTH = 26000
TRIAL_MAX_MESSAGES_PER_MONTH = 68000
# Approximate seconds in a month (30 days)
SECONDS_PER_MONTH = 30 * 24 * 60 * 60  # 2,592,000
# Estimated messages per API call (based on 68k messages / 26k API calls ≈ 2.6)
MESSAGES_PER_API_CALL = 2.6

REGIONS = {
    "us": "https://openapi.tuyaus.com",
    "us_east": "https://openapi-ueaz.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "eu_west": "https://openapi-weaz.tuyaeu.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
    "sg": "https://openapi-sg.iotbing.com",
    "jp": "https://openapi.tuyajp.com",
}

LOGIN_URL = "/v1.0/token?grant_type=1"
DEVICE_LIST_URL = "/v2.0/cloud/thing/device"
PROPERTIES_URL = "/v2.0/cloud/thing/{device_id}/shadow/properties"
MODEL_URL = "/v2.0/cloud/thing/{device_id}/model"

EMPTY_BODY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

ISSUE_ID_API_AUTH_FAILED = "api_auth_failed"
ISSUE_ID_DISCOVERY_FAILED = "discovery_failed_datacenter_or_subscription"
DISCOVERY_HELP_URL = "https://github.com/kattcrazy/tuya_unsupported_sensors#discovery_failed-error"
IOT_CORE_URL = "https://www.tuya.com/vas/commodity/IOT_CORE_V2"

SENSOR_PROPERTY_CODES = {
    "temperature": ["temp", "temperature", "va_temperature", "temp_current"],
    "humidity": ["humidity", "va_humidity", "humidity_value"],
    "battery": ["battery", "battery_percentage", "battery_state", "residual_electricity"],
    "battery_value": ["battery_value"],
    "illuminance": ["illuminance_value", "illuminance", "illumination"],
    "alarm": ["temp_alarm", "hum_alarm"],
    # Smart lock telemetry/status
    "lock_status": ["alarm_lock", "beep_volume"],
    # Electric meter (ZX-7500 and similar)
    "voltage": ["voltagea", "voltageb", "voltagec"],
    "current": ["currenta", "currentb", "currentc", "current"],
    "power": ["activepowera", "activepowerb", "activepowerc", "activepower"],
    "energy": [
        "energyconsumeda", "energyconsumedb", "energyconsumedc", "energyconsumed"
    ],
    "frequency": ["frequency"],
    "reactive_power": [
        "reactivepowera", "reactivepowerb", "reactivepowerc", "reactivepower"
    ],
    "power_factor": ["powerfactora", "powerfactorb", "powerfactorc"],
    "device_status": ["devicestatus"],
    "voltage_phase_seq": ["voltage_phase_seq"],
}

# Config/setting properties that use temp unit (maxtemp_set etc.) - need temp_unit_convert
TEMP_UNIT_PROPERTIES = [
    "maxtemp_set", "minitemp_set", "temp_sensitivity",
]
# Config properties with fixed units
PROPERTY_UNIT_MAP = {
    "maxhum_set": "%",
    "minihum_set": "%",
    "hum_sensitivity": "%",
    "temp_periodic_report": "min",
    "hum_periodic_report": "min",
    # Electric meter
    "voltagea": "V",
    "voltageb": "V",
    "voltagec": "V",
    "currenta": "A",
    "currentb": "A",
    "currentc": "A",
    "current": "A",
    "activepowera": "W",
    "activepowerb": "W",
    "activepowerc": "W",
    "activepower": "W",
    "reactivepowera": "var",
    "reactivepowerb": "var",
    "reactivepowerc": "var",
    "reactivepower": "var",
    "powerfactora": "",
    "powerfactorb": "",
    "powerfactorc": "",
    "energyconsumeda": "kWh",
    "energyconsumedb": "kWh",
    "energyconsumedc": "kWh",
    "energyconsumed": "kWh",
    "frequency": "Hz",
}

BINARY_SENSOR_PROPERTY_CODES = {
    "contact": ["contact", "doorcontact_state", "door_sensor_state"],
    "motion": ["motion", "pir", "pir_state"],
    "occupancy": ["presence_state", "presence"],
    "online": ["online"],
}

BINARY_SENSOR_VALUE_MAP = {
    "on": ["true", "1", "open", "pir", "presence"],
    "off": ["false", "0", "close", "none", "absence"],
}

