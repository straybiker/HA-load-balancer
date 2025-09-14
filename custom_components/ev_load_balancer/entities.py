"""EV Load Balancer entities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.select import SelectEntity
from homeassistant.const import (
    UnitOfPower,
    UnitOfElectricCurrent,
    PERCENTAGE,
    ELECTRIC_POTENTIAL_VOLT,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_ACTIVE_POWER,
    ATTR_CURRENT_INPUT,
    ATTR_CURRENT_OUTPUT,
    ATTR_PHASES_INPUT,
    ATTR_PHASES_OUTPUT,
)

@dataclass
class EVLBBaseEntityDescription:
    """Base entity description for EV Load Balancer."""
    key: str
    name: str
    entity_category: EntityCategory | None = None

@dataclass
class EVLBSensorDescription(EVLBBaseEntityDescription):
    """Sensor entity description for EV Load Balancer."""
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    native_unit_of_measurement: str | None = None

class EVLBBaseEntity:
    """Base entity for EV Load Balancer."""

    def __init__(self, device, description: EVLBBaseEntityDescription) -> None:
        """Initialize the entity."""
        self._device = device
        self._attr_name = description.name
        self._attr_unique_id = f"{device.entry_id}_{description.key}"
        self._attr_device_info = device.device_info
        self._attr_entity_category = description.entity_category
        self._attr_has_entity_name = True

class EVLBSensor(EVLBBaseEntity, SensorEntity):
    """Sensor entity for EV Load Balancer."""

    def __init__(self, device, description: EVLBSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(device, description)
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._state: StateType = None

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self._state

    def update_state(self, state: StateType) -> None:
        """Update the state."""
        self._state = state

class ChargerPowerSensor(EVLBSensor):
    """Active power sensor for charger."""
    def __init__(self, device) -> None:
        """Initialize the sensor."""
        super().__init__(
            device,
            EVLBSensorDescription(
                key=ATTR_ACTIVE_POWER,
                name="Active Power",
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.WATT,
            ),
        )

class ChargerCurrentSensor(EVLBSensor):
    """Current sensor for charger."""
    def __init__(self, device) -> None:
        """Initialize the sensor."""
        super().__init__(
            device,
            EVLBSensorDescription(
                key=ATTR_CURRENT_INPUT,
                name="Current",
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            ),
        )

class ChargerPhaseSelect(EVLBBaseEntity, SelectEntity):
    """Phase selection for charger."""
    def __init__(self, device) -> None:
        """Initialize the select entity."""
        super().__init__(
            device,
            EVLBBaseEntityDescription(
                key=ATTR_PHASES_OUTPUT,
                name="Phases",
                entity_category=EntityCategory.CONFIG,
            ),
        )
        self._attr_options = ["1 Phase", "3 Phases"]
        self._current_option = "3 Phases"

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Update the current option."""
        self._current_option = option
        await self._device.set_phases(option)

class ChargerCurrentNumber(EVLBBaseEntity, NumberEntity):
    """Current setting for charger."""
    def __init__(self, device) -> None:
        """Initialize the number entity."""
        super().__init__(
            device,
            EVLBBaseEntityDescription(
                key=ATTR_CURRENT_OUTPUT,
                name="Current Setting",
                entity_category=EntityCategory.CONFIG,
            ),
        )
        self._attr_native_min_value = 6
        self._attr_native_max_value = 16
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._value = 16

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._value = value
        await self._device.set_current(value)