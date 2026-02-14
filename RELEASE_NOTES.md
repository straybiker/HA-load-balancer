# Release Notes

## Update: Generic EMS Budgeting & Solar Turbo

This release introduces a significant overhaul of the EMS (Energy Management System) integration, moving from a standard binary "On/Off" control to a flexible **Power Budget** model.

### 🚀 New Features
-   **Generic EMS Budgeting**: The load balancer now accepts a **Watt value** (`ems_signal`) from your EMS.
    -   The charger will limit its **Grid Usage** to this budget.
    -   This allows for precise control by external optimizers (e.g., EMHASS).
-   **Solar Turbo**: Solar surplus is now added **on top** of the EMS budget.
    -   *Example*: If EMS says "0W Grid" (don't buy), but you have 2000W Solar -> We charge at 2000W.
    -   *Example*: If EMS says "1500W Grid" (buy cheap) and you have 500W Solar -> We charge at 2000W.
-   **Emergency Guard**: Added `input_number.ev_load_balancer_emergency_soc`.
    -   If the car's battery is below this level (default 20%), **all** EMS and Price constraints are ignored to ensure the car is not left stranded.
-   **Max Charging Cost**: Added `input_number.ev_max_charging_cost`.
    -   Simple price cap for grid charging.

### ⚠️ Breaking Changes / Configuration Required
1.  **EMS Signal Definition**:
    -   The `ems_signal_entity` string parameter has been replaced by an `ems_signal` attribute in the `ev_loadbalancer_user_config.yaml`.
    -   **Action**: Update your `ev_loadbalancer_user_config.yaml` to define `ems_signal`. It must return a float (Watts).
    -   *Example*: `ems_signal: "{{ states('sensor.my_ems_power_allocation') | float(0) }}"`

2.  **EMS Logic Change**:
    -   If you were relying on the old binary "On/Off" logic, ensure your generic EMS signal returns `0` for Off and a high value (e.g., `11000`) for On.

### 🧹 Cleanups
-   Removed unused `ev_average_charging_speed` input.
