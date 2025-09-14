"""EV Load Balancer devices."""
from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import DOMAIN
from .entities import (
    ChargerPowerSensor,
    ChargerCurrentSensor,
    ChargerPhaseSelect,
    ChargerCurrentNumber,
)

class EVLoadBalancerDeviceBase:
    """Base class for EV Load Balancer devices."""

    def __init__(self, hass, config_entry_id: str) -> None:
        """Initialize the device."""
        self.hass = hass
        self.entry_id = config_entry_id
        self._entities = []

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        raise NotImplementedError

    def register_entity(self, entity: Any) -> None:
        """Register an entity with this device."""
        self._entities.append(entity)

    @callback
    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update device state from a dictionary."""
        for entity in self._entities:
            if entity.entity_description.key in data:
                entity.update_state(data[entity.entity_description.key])

class EVLoadBalancerDevice(EVLoadBalancerDeviceBase):
    """Main EV Load Balancer device."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{self.entry_id}_main")},
            name="EV Load Balancer",
            manufacturer="straybiker",
            model="Load Balancer",
            sw_version="1.0.0",
        )

class EVLoadBalancerChargerDevice(EVLoadBalancerDeviceBase):
    """EV Charger device."""

    def __init__(self, hass, config_entry_id: str) -> None:
        """Initialize the device."""
        super().__init__(hass, config_entry_id)
        
        # Create entities
        self.power_sensor = ChargerPowerSensor(self)
        self.current_sensor = ChargerCurrentSensor(self)
        self.phase_select = ChargerPhaseSelect(self)
        self.current_number = ChargerCurrentNumber(self)
        
        # Register entities with device
        self.register_entity(self.power_sensor)
        self.register_entity(self.current_sensor)
        self.register_entity(self.phase_select)
        self.register_entity(self.current_number)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{self.entry_id}_charger")},
            name="EV Load Balancer Charger",
            manufacturer="Alfen",
            model="Eve Pro Single",
            sw_version="1.0.0",
        )

    async def set_phases(self, phases: str) -> None:
        """Set the number of phases."""
        # Implement the actual phase switching logic here
        pass

    async def set_current(self, current: float) -> None:
        """Set the charging current."""
        # Implement the actual current setting logic here
        pass

class EVLoadBalancerCarDevice(EVLoadBalancerDeviceBase):
    """Car device."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{self.entry_id}_car")},
            name="EV Load Balancer Car",
            manufacturer="BMW",
            model="iX3",
            sw_version="1.0.0",
            via_device=(DOMAIN, f"{self.entry_id}_main"),
        )