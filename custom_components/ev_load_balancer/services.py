"""Services for EV Load Balancer."""
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_SET_CHARGING,
    SERVICE_SET_MODE,
    DEFAULT_PHASE_SWITCHING_DELAY,
)
from .load_balancer import ChargingMode

_LOGGER = logging.getLogger(__name__)

async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for EV Load Balancer."""
    async def set_charging(call: ServiceCall) -> None:
        """Set charging parameters."""
        coordinator = hass.data[DOMAIN]
        current = call.data.get("current")
        phases = call.data.get("phases")

        if phases != coordinator.current_phases:
            # Start internal phase switching timer
            coordinator.load_balancer.start_phase_switching_timer()

        # Update charging parameters
        # Implementation specific to your charger control

    async def set_mode(call: ServiceCall) -> None:
        """Set charging mode."""
        coordinator = hass.data[DOMAIN]
        mode = call.data.get("mode")
        try:
            charging_mode = ChargingMode(mode)
            coordinator.load_balancer.set_mode(charging_mode)
        except ValueError as err:
            _LOGGER.error("Invalid charging mode: %s", err)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CHARGING,
        set_charging,
        vol.Schema({
            vol.Required("current"): vol.All(vol.Coerce(int), vol.Range(min=6, max=16)),
            vol.Required("phases"): vol.All(vol.Coerce(int), vol.In([1, 3])),
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MODE,
        set_mode,
        vol.Schema({
            vol.Required("mode"): vol.In([mode.value for mode in ChargingMode]),
        }),
    )