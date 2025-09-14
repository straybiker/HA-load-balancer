"""DataUpdateCoordinator for the EV Load Balancer integration."""
from __future__ import annotations

import asyncio
from datetime import datetime as dt, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from .models import LoadBalancerConfig

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_NOMINAL_VOLTAGE,
)
from .load_balancer import LoadBalancer

_LOGGER = logging.getLogger(__name__)

class EVLoadBalancerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching EV Load Balancer data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: LoadBalancerConfig,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self._config = config
        self._devices = {}
        self._entities = {}
        self._update_lock = asyncio.Lock()
        self.load_balancer = LoadBalancer(hass)
        self.load_balancer.set_power_limits(
            config.max_power_limit,
            config.power_limit_extended
        )
        self.load_balancer.set_car_aware(config.options.car_aware)
        self.load_balancer.set_pv_prioritized(config.options.pv_prioritized)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        if hasattr(self, '_update_in_progress'):
            return self.data or {}

        try:
            setattr(self, '_update_in_progress', True)
            async with self._update_lock:
                data = {}
            
            # Get required sensor states
            for field_name, entity_id in vars(self._config.required).items():
                state = self.hass.states.get(entity_id)
                if not state:
                    raise UpdateFailed(f"Required sensor {field_name} not available")
                try:
                    data[field_name] = float(state.state)
                except ValueError:
                    data[field_name] = state.state

            # Validate sensors and handle errors
            if not self.load_balancer.validate_sensors(data):
                _LOGGER.error("Required sensors unavailable")
                return data

            # Handle charger state
            self.load_balancer.handle_error_state(data.get("connection_state", ""))
            if self.load_balancer._in_error_state:
                return data

            # Calculate efficiency
            current_phases = 3 if data.get("phases_input") == "3 Phases" else 1
            efficiency = self.load_balancer.calculate_efficiency(
                data.get("current_input", 0),
                data.get("active_power", 0),
                current_phases,
            )

            # Get PV sensor state if pv_prioritized is enabled
            pv_power = None
            if self._config.options.pv_prioritized:
                pv_state = self.hass.states.get(self._config.optional.pv_power)
                if pv_state:
                    try:
                        pv_power = float(pv_state.state)
                    except ValueError:
                        _LOGGER.warning("Invalid PV power value")

            # Calculate available power
            available_power = self.load_balancer.calculate_available_power(
                data.get("house_power", 0),
                pv_power,
                efficiency,
            )

            # Adjust for car-aware mode if enabled
            if self._config.options.car_aware and self._config.car:
                try:
                    # Calculate time until target
                    now = dt.now()
                    target_time = self._config.car.soc_time.split(":")
                    target_hour = int(target_time[0])
                    target_minute = int(target_time[1])
                    target_datetime = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                    if target_datetime < now:
                        target_datetime = target_datetime + timedelta(days=1)
                    time_until_target = (target_datetime - now).total_seconds() / 3600

                    # Get battery percentage
                    battery_state = self.hass.states.get(self._config.car.battery_percentage)
                    if battery_state:
                        battery_percentage = float(battery_state.state)
                        # Calculate charging power for estimation
                        charging_power = current_limit * DEFAULT_NOMINAL_VOLTAGE * phase_selection
                        
                        available_power = self.load_balancer.adjust_for_car_aware(
                            available_power,
                            battery_percentage,
                            self._config.soc_threshold or 0,
                            self._config.car.battery_capacity_wh,
                            charging_power,
                            time_until_target,
                        )
                except (ValueError, TypeError) as err:
                    _LOGGER.warning("Error in car-aware calculations: %s", err)

            # Calculate phase selection
            phase_selection = self.load_balancer.calculate_phase_selection(
                available_power,
                current_phases=current_phases,
            )

            # Calculate current limit
            current_limit = self.load_balancer.calculate_current_limit(
                available_power,
                phase_selection,
            )

            # Update data with calculations
            data.update({
                "available_power": available_power,
                "phase_selection": phase_selection,
                "current_limit": current_limit,
            })

            # Update charger output
            if data.get("current_limit") != data.get("current_input") or \
               data.get("phase_selection") != current_phases:
                try:
                    # Handle phase changes first
                    if data.get("phase_selection") != current_phases:
                        _LOGGER.info(
                            "Phase switch initiated: %s -> %s. Stopping charging for safety.",
                            current_phases,
                            data.get("phase_selection")
                        )
                        try:
                            # Stop charging by setting current to 0
                            await self.hass.services.async_call(
                                "number",
                                "set_value",
                                {
                                    "entity_id": self._config.control.current_output,
                                    "value": 0
                                },
                            )
                            if not await self.wait_for_state_change(
                                self._config.control.current_output,
                                0,
                                timeout=5
                            ):
                                raise ValueError("Failed to stop charging before phase switch")
                            
                            _LOGGER.debug("Charging stopped, proceeding with phase change")
                            await asyncio.sleep(2)  # Allow contactors to fully open
                            
                            # Change phases
                            await self.hass.services.async_call(
                                "select",
                                "select_option",
                                {
                                    "entity_id": self._config.control.phases_output,
                                    "option": "3 Phases" if data["phase_selection"] == 3 else "1 Phase"
                                },
                            )
                            phases_state = await self.wait_for_state_change(
                                self._config.control.phases_output,
                                "3 Phases" if data["phase_selection"] == 3 else "1 Phase",
                                timeout=5
                            )
                            if not phases_state:
                                raise ValueError("Phase change failed")
                                
                            # Wait for contactors to settle after phase change
                            await asyncio.sleep(2)
                            _LOGGER.debug("Phase change complete, restarting charging")
                                
                            _LOGGER.info("Phase switch completed successfully")
                            
                        except Exception as err:
                            _LOGGER.error("Phase switching failed: %s", err)
                            raise

                    # Set target current
                    await self.hass.services.async_call(
                        "number",
                        "set_value",
                        {
                            "entity_id": self._config.control.current_output,
                            "value": data["current_limit"]
                        },
                    )
                    current_state = await self.wait_for_state_change(
                        self._config.control.current_output,
                        data["current_limit"],
                        timeout=5
                    )
                    
                    if not current_state or not phases_state:
                        raise ValueError("Output values not set correctly")
                        
                except Exception as err:
                    _LOGGER.error("Failed to update charger: %s", err)
                    return self.data or {}

            # Update device data
            for device in self._devices.values():
                if hasattr(device, 'update_from_dict'):
                    device.update_from_dict(data)

            return data
            
        except UpdateFailed:
            raise
        except Exception as exception:
            raise UpdateFailed(f"Unexpected error: {exception}") from exception
        finally:
            if hasattr(self, '_update_in_progress'):
                delattr(self, '_update_in_progress')

    async def wait_for_state_change(self, entity_id: str, target_state: Any, timeout: int = 5) -> bool:
        """Wait for entity to reach target state."""
        done = asyncio.Event()
        target = str(target_state)

        @callback
        def state_checker(event):
            """Check if state matches target."""
            if event.data.get("entity_id") != entity_id:
                return
                
            new_state = event.data.get("new_state")
            try:
                if new_state and str(new_state.state) == target:
                    self.hass.loop.call_soon_threadsafe(done.set)
            except Exception as err:
                _LOGGER.error("Error in state checker: %s", err)

        # Check current state first in a non-blocking way
        try:
            current = self.hass.states.get(entity_id)
            if current and str(current.state) == target:
                return True
        except Exception as err:
            _LOGGER.error("Error checking current state: %s", err)
            return False

        # Listen for state changes
        unsub = self.hass.bus.async_listen("state_changed", state_checker)
        try:
            # Wait for state change or timeout
            await asyncio.wait_for(done.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            unsub()

    @callback
    def async_update_device(self, device_id: str, data: dict[str, Any]) -> None:
        """Update device data."""
        if device_id in self._devices:
            self._devices[device_id].update_from_dict(data)
            self.async_update()