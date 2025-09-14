"""Constants for the EV Load Balancer integration."""

DOMAIN = "ev_load_balancer"

# Entity attributes
ATTR_ACTIVE_POWER = "active_power"
ATTR_CURRENT = "current"
ATTR_PHASES = "phases"
ATTR_CONNECTION_STATE = "connection_state"
ATTR_BATTERY_PERCENTAGE = "battery_percentage"
ATTR_POWER_AVAILABLE = "power_available"

# Configuration options
CONF_HOUSE_POWER_SENSOR = "house_power_sensor"
CONF_CHARGER_POWER_SENSOR = "charger_power_sensor"
CONF_PV_POWER_SENSOR = "pv_power_sensor"
CONF_CURRENT_CONTROL = "current_output_entity"
CONF_PHASES_CONTROL = "phases_output_entity"
CONF_MAX_POWER_LIMIT = "max_power_limit"

# Service constants
SERVICE_SET_CHARGING = "set_charging"
SERVICE_SET_MODE = "set_mode"

# Default values
DEFAULT_UPDATE_INTERVAL = 10  # seconds
DEFAULT_MIN_CURRENT = 6
DEFAULT_MAX_CURRENT = 16
DEFAULT_NOMINAL_VOLTAGE = 230
DEFAULT_PHASE_SWITCHING_DELAY = 300  # seconds