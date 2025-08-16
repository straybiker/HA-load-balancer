"""Config flow for EV Load Balancer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN
from .models import (
    LoadBalancerConfig,
    RequiredSensors,
    ControlEntities,
    OptionalSensors,
    LoadBalancerOptions,
    CarSensors,
    validate_config,
)

_LOGGER = logging.getLogger(__name__)

def get_config_schema(car_aware: bool = False, pv_prioritized: bool = False) -> vol.Schema:
    """Get schema based on options."""
    schema = {
        # Required sensors
        vol.Required("house_power_sensor"): str,
        vol.Required("charger_power_sensor"): str,
        vol.Required("current_input_sensor"): str,
        vol.Required("phases_input_sensor"): str,
        vol.Required("connection_state_sensor"): str,
        
        # Control entities
        vol.Required("current_output_entity"): str,
        vol.Required("phases_output_entity"): str,
        
        # Options
        vol.Required("car_aware", default=False): bool,
        vol.Required("pv_prioritized", default=False): bool,
        
        # Configuration
        vol.Required("max_power_limit", default=1500): int,
    }
    
    # Add car sensors if car_aware is enabled
    if car_aware:
        schema.update({
            vol.Required("battery_percentage_sensor"): str,
            vol.Required("power_limit_extended"): int,
        })

    # Add PV sensors if pv_prioritized is enabled
    if pv_prioritized:
        schema.update({
            vol.Required("pv_power_sensor"): str,
        })

    return vol.Schema(schema)

STEP_USER_DATA_SCHEMA = get_config_schema()

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    try:
        config = LoadBalancerConfig(
            required=RequiredSensors(
                house_power=data["house_power_sensor"],
                active_power=data["charger_power_sensor"],
                current_input=data["current_input_sensor"],
                phases_input=data["phases_input_sensor"],
                connection_state=data["connection_state_sensor"],
            ),
            control=ControlEntities(
                current_output=data["current_output_entity"],
                phases_output=data["phases_output_entity"],
            ),
            optional=OptionalSensors(
                pv_power=data.get("pv_power_sensor"),
            ),
            options=LoadBalancerOptions(
                car_aware=data.get("car_aware", False),
                pv_prioritized=data.get("pv_prioritized", False),
            ),
            car=CarSensors(
                battery_percentage=data["battery_percentage_sensor"],
            ) if data.get("car_aware") else None,
            max_power_limit=data["max_power_limit"],
            power_limit_extended=data.get("power_limit_extended"),
        )
        
        validate_config(hass, config)
        return {"title": "EV Load Balancer"}
    except ValueError as err:
        raise InvalidSensor from err

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EV Load Balancer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        # Get current options from user input
        car_aware = user_input.get("car_aware", False) if user_input else False
        pv_prioritized = user_input.get("pv_prioritized", False) if user_input else False
        
        # Get schema based on current options
        schema = get_config_schema(car_aware=car_aware, pv_prioritized=pv_prioritized)
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidSensor:
                errors["base"] = "invalid_sensor"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

class InvalidSensor(HomeAssistantError):
    """Error to indicate there is an invalid sensor."""