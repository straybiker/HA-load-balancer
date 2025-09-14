"""Models and validation for EV Load Balancer."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class RequiredSensors:
    """Required sensors for the load balancer."""
    house_power: str  # netto_verbruik_huis_lp
    active_power: str  # alfen_eve_active_power_total_socket_1
    current_input: str  # alfen_eve_main_active_max_current_socket_1
    phases_input: str  # alfen_eve_connector_1_max_allowed_of_phases
    connection_state: str  # alfen_eve_mode3_state_socket_1

@dataclass
class CarSensors:
    """Car-specific sensors."""
    battery_percentage: str  # ix3_m_sport_remaining_battery_percent

@dataclass
class ControlEntities:
    """Control entities for the load balancer."""
    current_output: str  # number.alfen_eve_power_connector_max_current_socket_1
    phases_output: str  # select.alfen_eve_installation_max_allowed_phases

@dataclass
class OptionalSensors:
    """Optional sensors for the load balancer."""
    pv_power: Optional[str] = None  # sma_power_w

@dataclass
class LoadBalancerOptions:
    """Load balancer options."""
    car_aware: bool = False
    pv_prioritized: bool = False

@dataclass
class LoadBalancerConfig:
    """Configuration for the load balancer."""
    required: RequiredSensors
    control: ControlEntities
    optional: OptionalSensors
    options: LoadBalancerOptions
    car: Optional[CarSensors] = None
    max_power_limit: int = 1500
    power_limit_extended: Optional[int] = None

def validate_config(hass, config: LoadBalancerConfig) -> bool:
    """Validate that all required entities exist and are accessible."""
    # Check required sensors
    for field_name, entity_id in vars(config.required).items():
        if not hass.states.get(entity_id):
            raise ValueError(f"Required sensor {field_name} ({entity_id}) not found")

    # Check control entities
    for field_name, entity_id in vars(config.control).items():
        if not hass.states.get(entity_id):
            raise ValueError(f"Control entity {field_name} ({entity_id}) not found")

    # Check car sensors if car_aware is enabled
    if config.options.car_aware:
        if not config.car:
            raise ValueError("Car sensors are required when car_aware is enabled")
        for field_name, entity_id in vars(config.car).items():
            if not hass.states.get(entity_id):
                raise ValueError(f"Car sensor {field_name} ({entity_id}) not found")

    # Check PV sensors if pv_prioritized is enabled
    if config.options.pv_prioritized:
        if not config.optional.pv_power:
            raise ValueError("PV power sensor is required when pv_prioritized is enabled")
        if not hass.states.get(config.optional.pv_power):
            raise ValueError(f"PV power sensor {config.optional.pv_power} not found")

    return True