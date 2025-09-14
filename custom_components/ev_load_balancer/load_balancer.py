"""Core load balancing logic for EV Load Balancer."""
from datetime import datetime as dt, timedelta
from enum import Enum
import logging
from typing import Any, Optional

from .const import DEFAULT_PHASE_SWITCHING_DELAY

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    UnitOfPower,
    UnitOfElectricCurrent,
)

from .const import (
    ATTR_ACTIVE_POWER,
    ATTR_CURRENT,
    ATTR_PHASES,
    ATTR_POWER_AVAILABLE,
    DEFAULT_MIN_CURRENT,
    DEFAULT_MAX_CURRENT,
    DEFAULT_NOMINAL_VOLTAGE,
)

_LOGGER = logging.getLogger(__name__)

class ChargingMode(str, Enum):
    """Charging modes."""
    OFF = "Off"
    MINIMAL_1PHASE = "Minimal 1.4kW"
    MINIMAL_3PHASE = "Minimal 4kW"
    ECO = "Eco"
    FAST = "Fast"
    SOLAR = "Solar"

class LoadBalancer:
    """Load balancer implementation."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the load balancer."""
        self.hass = hass
        self._mode = ChargingMode.OFF
        self._power_limit = 0
        self._power_limit_extended = 0
        self._car_aware = False
        self._pv_prioritized = False
        self._nominal_voltage = DEFAULT_NOMINAL_VOLTAGE
        self._phase_switching_ends = None
        self._in_error_state = False

    def calculate_efficiency(
        self,
        current: float,
        power: float,
        phases: int,
    ) -> float:
        """Calculate charger efficiency."""
        if current > 0 and power > 1000.0:
            return power / (current * self._nominal_voltage * phases)
        return 1.0

    def validate_sensors(self, sensors: dict[str, Any]) -> bool:
        """Validate sensor states for charging."""
        required = ["house_power", "active_power", "current_input", "phases_input"]
        car_sensors = ["battery_percentage"]
        
        # Check basic sensors
        for sensor in required:
            if sensor not in sensors or sensors[sensor] in ["unavailable", "unknown", None]:
                return False
                
        # Check car sensors if car-aware
        if self._car_aware:
            for sensor in car_sensors:
                if sensor not in sensors or sensors[sensor] in ["unavailable", "unknown", None]:
                    return False

        return True

    def handle_error_state(self, connection_state: str) -> None:
        """Handle charger error state."""
        was_in_error = self._in_error_state
        self._in_error_state = connection_state == "Error"
        
        if self._in_error_state and not was_in_error:
            _LOGGER.error("Charger entered error state")
            self.set_mode(ChargingMode.OFF)

    def calculate_available_power(
        self,
        household_power: float,
        pv_power: Optional[float],
        charger_efficiency: float,
        min_current: float = DEFAULT_MIN_CURRENT,
    ) -> float:
        """Calculate available power based on mode and conditions."""
        if self._mode == ChargingMode.OFF:
            return 0

        if self._mode == ChargingMode.SOLAR:
            if household_power > 0:
                return 0
            power_left = (-household_power + (self._nominal_voltage * 1)) / charger_efficiency
            return max(power_left, 0)

        if self._mode == ChargingMode.ECO:
            min_power_threshold = -(self._nominal_voltage * min_current)
            if self._pv_prioritized and household_power < min_power_threshold and pv_power:
                return max(pv_power / charger_efficiency, 0)
            power_left = (self._power_limit - household_power) / charger_efficiency
            return max(power_left, 0)

        if self._mode == ChargingMode.MINIMAL_1PHASE:
            return self._nominal_voltage * DEFAULT_MIN_CURRENT

        if self._mode == ChargingMode.MINIMAL_3PHASE:
            return self._nominal_voltage * DEFAULT_MIN_CURRENT * 3

        if self._mode == ChargingMode.FAST:
            return self._nominal_voltage * DEFAULT_MAX_CURRENT * 3

        return 0

    def calculate_phase_selection(
        self,
        available_power: float,
        min_current: float = DEFAULT_MIN_CURRENT,
        current_phases: int = 1,
    ) -> int:
        """Calculate optimal phase selection."""
        desired_phases = 3 if available_power >= (self._nominal_voltage * min_current * 3) else 1
        
        # Don't increase phases if cooldown is active
        if desired_phases > current_phases and self.phase_switching_active:
            return current_phases
            
        return desired_phases

    def calculate_current_limit(
        self,
        available_power: float,
        phases: int,
        min_current: float = DEFAULT_MIN_CURRENT,
        max_current: float = DEFAULT_MAX_CURRENT,
    ) -> float:
        """Calculate current limit based on available power."""
        current = (available_power / (self._nominal_voltage * phases))
        
        if current < min_current:
            return 0
        if current > max_current:
            return max_current
            
        return current

    def calculate_estimated_battery_percentage(
        self,
        current_battery_percentage: float,
        battery_capacity_wh: float,
        charging_power: float,
        time_until_target: float,
    ) -> float:
        """Calculate estimated battery percentage at target time."""
        charging_power_w = charging_power
        added_energy = charging_power_w * time_until_target
        current_energy = (battery_capacity_wh * current_battery_percentage / 100)
        estimated_energy = current_energy + added_energy
        return (estimated_energy / battery_capacity_wh) * 100

    def adjust_for_car_aware(
        self,
        power_limit: float,
        battery_percentage: float,
        soc_threshold: float,
        battery_capacity_wh: float,
        charging_power: float,
        time_until_target: float,
    ) -> float:
        """Adjust power limit for car-aware mode."""
        if not self._car_aware or self._power_limit_extended <= 0:
            return power_limit

        estimated_percentage = self.calculate_estimated_battery_percentage(
            battery_percentage,
            battery_capacity_wh,
            charging_power,
            time_until_target,
        )

        if estimated_percentage < soc_threshold:
            return self._power_limit_extended
        return power_limit

    def set_mode(self, mode: ChargingMode) -> None:
        """Set charging mode."""
        self._mode = mode

    def set_car_aware(self, enabled: bool) -> None:
        """Enable/disable car-aware mode."""
        self._car_aware = enabled

    def set_pv_prioritized(self, enabled: bool) -> None:
        """Enable/disable PV prioritization."""
        self._pv_prioritized = enabled

    def set_power_limits(self, normal: float, extended: Optional[float] = None) -> None:
        """Set power limits."""
        self._power_limit = normal
        if extended is not None:
            self._power_limit_extended = extended

    def start_phase_switching_timer(self) -> None:
        """Start phase switching cooldown timer."""
        self._phase_switching_ends = dt.now() + timedelta(seconds=DEFAULT_PHASE_SWITCHING_DELAY)

    @property
    def phase_switching_active(self) -> bool:
        """Check if phase switching cooldown is active."""
        if self._phase_switching_ends is None:
            return False
        return dt.now() < self._phase_switching_ends