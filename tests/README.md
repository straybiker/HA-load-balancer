# Testing Setup for EV Load Balancer

This directory c8. **Oscillating Load**
   - Simulates morning load pattern:
     * House power cycles: 4500W → 1500W → 3000W
     * PV power ramps up: 1000W → 2000W → 3000W
   - 10-second intervals, 6 cycles
   - Tests adaptation to varying loads

9. **State Change Verification**
   - Verifies output states are actually set
   - Tests safe phase switching sequence
   - Includes timeouts and retry handling

10. **Error Recovery**
   - Tests error state detection
   - Verifies charging stops in error
   - Tests automatic recovery

11. **Concurrent Updates**
   - Tests update lock mechanism
   - Verifies only one update processes
   - Checks state stability

Run all scenarios automatically using the `script.test_all_scenarios` service.configuration files for testing the EV Load Balancer integration.

## Files
- `mock_sensors.yaml`: Mock sensors and entities that simulate a real setup
- `configuration.yaml`: Test scenarios and automations

## Usage
1. Copy both files to your Home Assistant config directory
2. Include them in your main configuration.yaml:
   ```yaml
   homeassistant:
     packages:
       test_evlb: !include tests/configuration.yaml
   ```
3. Restart Home Assistant
4. Use the mock input helpers to simulate different scenarios
5. Or trigger pre-defined test scenarios using these events:
   - `test_normal_load`
   - `test_pv_excess`
   - `test_car_low_battery`

## Test Scenarios
1. **Normal Load**
   - House power: 2000W
   - PV: 0W
   - Car connected

2. **PV Excess**
   - House power: -3000W
   - PV: 5000W
   - Car connected

3. **Car Low Battery**
   - Car battery: 20%
   - Car connected

4. **Phase Switching**
   - House power: 500W
   - Force 1 phase operation
   - Car connected

5. **Grid Overload**
   - House power: 9000W
   - Charger power: 11000W
   - Tests power limiting

6. **Error State**
   - Charger in error state (STATE_F)
   - Tests error handling

7. **Full Battery**
   - Car battery at 100%
   - Tests charging stop condition

8. **Oscillating Load**
   - Simulates morning load pattern:
     * House power cycles: 4500W → 1500W → 3000W
     * PV power ramps up: 1000W → 2000W → 3000W
   - 10-second intervals, 6 cycles
   - Tests adaptation to varying loads with PV

Run all scenarios automatically using the `script.test_all_scenarios` service.