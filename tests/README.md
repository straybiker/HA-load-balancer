# Testing Setup for EV Load Balancer

This directory contains mock entities and scenario helpers for exercising the
EV Load Balancer package without a real charger or car.

## Files
- `mock_sensors.yaml` — mock sensors and writable charger output entities. Their
  entity IDs match the ones referenced in
  `packages/ev_loadbalancer_user_config.yaml`, so the unmodified package runs
  against them.
- `configuration.yaml` — scenario helper scripts that put the mocks into a known
  state.

## Usage
1. Copy the `tests/` folder into your Home Assistant config directory (alongside
   `packages/`).
2. Load the mocks and scenarios as packages in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages:
       evlb_core: !include packages/ev_loadbalancer.yaml
       evlb_user: !include packages/ev_loadbalancer_user_config.yaml
       evlb_mocks: !include tests/mock_sensors.yaml
       evlb_tests: !include tests/configuration.yaml
   ```
   > The mock sensors provide the raw `sensor.alfen_eve_*`, `sensor.sma_power_w`,
   > and car SOC entities that the user config reads, so no changes to the user
   > config are needed. Do not load the test packages on a production install —
   > they redefine those entity IDs.
3. Restart Home Assistant.
4. Drive a scenario in one of two ways:
   - Manually set the `input_number.mock_*` and `input_select.mock_*` helpers in
     Developer Tools > States, or
   - Run one of the `script.test_scenario_*` scripts (see below).
5. Watch the result in Developer Tools > States (`sensor.ev_load_balancer*`,
   `number.alfen_eve_max_current_limit_s1`, `select.alfen_eve_usable_phases1`) or
   the EV Load Balancer Logic dashboard.

## Mock control helpers
| Helper | Purpose |
|---|---|
| `input_number.mock_house_power` | Net household power (W); negative = solar export |
| `input_number.mock_pv_power` | PV generation (W) |
| `input_number.mock_charger_power` | Charger measured active power (W) |
| `input_number.mock_charger_max_current` | Charger hardware max current (A) |
| `input_number.mock_car_battery` | Car SOC (%) |
| `input_select.mock_charger_state` | IEC-61851 Mode 3 state (`A`, `B1`, `C2`, `F`, …) |

The charger outputs the package writes to (`number.alfen_eve_max_current_limit_s1`
and `select.alfen_eve_usable_phases1`) are mock template entities backed by
`input_number.mock_current_store` and `input_select.mock_charger_phases_store`.

## Scenario scripts
| Script | Scenario |
|---|---|
| `test_scenario_normal_load` | 2000 W house, no PV, car connected |
| `test_scenario_pv_excess` | −3000 W house, 5000 W PV, car connected |
| `test_scenario_car_low_battery` | Car at 15 %, car connected |
| `test_scenario_phase_switching` | 500 W house — single-phase headroom |
| `test_scenario_grid_overload` | 9000 W house — power limiting |
| `test_scenario_error_state` | Charger in error (Mode 3 = F) |
| `test_scenario_full_battery` | Car at 100 % — charging stop |
| `test_scenario_disconnected` | Car disconnected (Mode 3 = A) |

> [!NOTE]
> These mocks let you observe the logic, but they do not simulate the real
> charger's reporting lag. The setter script's wait loops resolve immediately
> because the mock `current_input` mirrors the output store.
