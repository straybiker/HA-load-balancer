"""Support for EV Load Balancer sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .coordinator import EVLoadBalancerCoordinator
from .device import EVLoadBalancerChargerDevice
from .models import (
    LoadBalancerConfig,
    RequiredSensors,
    ControlEntities,
    OptionalSensors,
    LoadBalancerOptions,
    CarSensors,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EV Load Balancer sensors."""
    # Convert config entry data to LoadBalancerConfig
    config = LoadBalancerConfig(
        required=RequiredSensors(
            house_power=config_entry.data["house_power_sensor"],
            active_power=config_entry.data["charger_power_sensor"],
            current_input=config_entry.data["current_input_sensor"],
            phases_input=config_entry.data["phases_input_sensor"],
            connection_state=config_entry.data["connection_state_sensor"],
        ),
        control=ControlEntities(
            current_output=config_entry.data["current_output_entity"],
            phases_output=config_entry.data["phases_output_entity"],
        ),
        optional=OptionalSensors(
            pv_power=config_entry.data.get("pv_power_sensor"),
        ),
        options=LoadBalancerOptions(
            car_aware=config_entry.data.get("car_aware", False),
            pv_prioritized=config_entry.data.get("pv_prioritized", False),
        ),
        car=CarSensors(
            battery_percentage=config_entry.data["battery_percentage_sensor"],
        ) if config_entry.data.get("car_aware") else None,
        max_power_limit=config_entry.data["max_power_limit"],
        power_limit_extended=config_entry.data.get("power_limit_extended"),
    )
    
    coordinator = EVLoadBalancerCoordinator(hass, config)
    
    # Create devices
    charger = EVLoadBalancerChargerDevice(hass, config_entry.entry_id)
    
    # Add all entities from devices
    async_add_entities(charger._entities)