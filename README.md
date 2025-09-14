# Home Assistant Car Charging Load Balancer Automation 
[![Version](https://img.shields.io/github/v/release/straybiker/HA-load-balancer)](https://github.com/straybiker/HA-load-balancer/releases)
[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-orange)](https://github.com/custom-components/hacs)
[![Home Assistant: Core](https://img.shields.io/badge/Home%20Assistant-Core-blue)](https://www.home-assistant.io/)

A car charging load balancer for Home Assistant tailored to Belgian energy regulation (Capaciteitstarief).

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Details](#details)
- [Configuration and Helpers](#configuration-and-helpers)
- [Future Developments](#future-developments)
- [Disclaimer](#disclaimer)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Introduction
This Home Assistant automation provides intelligent load balancing for EV charging, designed to minimize energy costs and avoid exceeding your maximum power limit (capaciteitspiek) under Belgian energy regulations. By dynamically adjusting the charging phases and current based on your household's power consumption, this system helps you charge your EV efficiently without exceeding a set peak power (capaciteitstarief).

This project is ideal for users with an EV charger that can switch phases and adjust current, such as the Alfen Eve Pro wallbox. The load balancer can also be made car-aware, where the current SOC is taken into account to reach a minimum SOC at a set time.

This is not a fully-fledged Home Assistant integration (yet), but a [package](https://www.home-assistant.io/docs/configuration/packages/) that can easily be integrated into your existing Home Assistant setup. 

> [!IMPORTANT]
> The separate YAML files are deprecated and archived in the archive folder.

## Features
- Dynamically adjusts EV charging based on household power consumption.
- Supports 3-phase electrical installations.
- Car-aware functionality to meet minimum SOC targets by a set time.
- Configurable modes: Off, Fixed (1.4kW or 4kW), Limited, and Fast.
- Handles charger efficiency and measurement noise with filtering.
- Phase switching protection to prevent frequent switching between 1 and 3 phases on days with alternating sun and clouds.

## Prerequisites
- **3-phase electrical installation**: 1-phase only is not yet supported.
- **EV charger integration**: Only 1 socket is currently supported.
  - For the Alfen Eve Pro, install the Home Assistant HACS Alfen Wallbox integration: [Alfen Wallbox Integration](https://github.com/leeyuentuen/alfen_wallbox). Ensure active load balancing is disabled on the Alfen charger to avoid conflicts. Minimum version: 2.9.4.
- **Household power consumption sensor** excluding charger power consumption. 
> [!TIP]
> If you can't measure the household power consumption seperately, create helpers to calculate the to subtract the charger power from the total power consumption

## Installation
### Step 1: Package Installation
Follow the [Home Assistant package documentation](https://www.home-assistant.io/docs/configuration/packages/) for installation details. The package file is located in the `package` folder.

### Step 2: Configuration
Update the configuration section to your specific setup and check the configuration from the developer YAML section.
If you don't need Car Aware functionality, the settings in the car configuration can be emptied

> [!TIP]
> Use a low-pass filter to smooth noisy household power consumption data. Example configuration:
> ```yaml
> platform: filter
> name: "Netto verbruik huis LP"
> unique_id: netto_verbruik_huis_lp
> entity_id: sensor.netto_verbruik_huis
> filters:
>   - filter: outlier
>     window_size: 4
>     radius: 500.0
>   - filter: lowpass
>     time_constant: 12
>     precision: 2
> ```
> Here, `sensor.netto_verbruik_huis` is the raw household power consumption, and `netto_verbruik_huis_lp` is the filtered value used by the load balancer.

> [!TIP]
> For PV-aware charging, use a low-pass filter to prevent excessive switching by cloud coverage. Example configuration:
> ```yaml
> platform: filter
> name: "PV Power LP"
> unique_id: pv_power_lp
> entity_id: sensor.sma_power_w
> filters:
>   - filter: outlier
>     window_size: 3
>     radius: 1000.0
>   - filter: lowpass
>     time_constant: 5
>     precision: 0
> ```

### Step 3: Update script
The script to set the charger parameters currently supports the Alfen Eve Pro Single charger. Update the script to the outputs according to your charger.
> [!Note]
> The charger connection states are based on the [IEC-61851 standard](https://en.wikipedia.org/wiki/IEC_61851). If your charger is not compliant to this standard, you need to update the state mapping.

### Step 4: Reload
Restart Home Assistant

### Step 5: Set parameters
Set the helpers that are now available in the UI to the desired values.

## Details
This load balancer checks every 10 seconds the current household power consumption and sets the charger output parameters, phase and current, according to the remaining available power. The total allowed power to use (capaciteitspiek), household + EV charger, is defined in an input helper parameter.
The load balancer also takes charger efficiency into account by comparing the calculated power output with the actual power output.

> [!Note]
> The maximum current can still be limited by the settings of the car. This setting can be checked by the external socket max current sensor. 

>[!IMPORTANT]
> This load balancer switches between 3 phases power and a max current of 16A. 1 phase only is not supported.

![image](https://github.com/user-attachments/assets/bf4685fa-3eef-4814-b577-23d8f777e9c8)
Here, during charging, the power is kept stable around 6000W, although major changes in the household power consumption. At 18h, the car was disconnected for a while. The spikes are measurement errors.

The current script also checks the battery state of a car. When forecasted battery percentage doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. If the threshold is reached, charging will just continue until the car stops the session. For example, I want my car to be 80% charged by 8:00 in the morning. If it cannot reach 80%, some additional power can be consumed. Set both power parameters equal to disable the extra power consumption. 

If there is not enough power to charge at 3 phases, 6A, the charger is switched to 1 phase. When the remaining power is not enough to reach 1 phase, 6A, charging stops by setting the maximum socket current to 0A. There is a risk with this that the car is not charged for a prolonged period if household power consumption is high.

>[!NOTE]
>There is a built in dynamic delay in the script when the charger parameters are changed. There will be no update sent to the charger until the setting is updated or a time-out in the script occurs.

When the charger is disconnected, the charger phases and current are set to a default value. This way you shouldn't end up with a charger that is set to 0A when Home Assistant is not available.

> [!WARNING]
> There is still a risk if Home Assistant becomes unavailable during charging with the charger set at 0A. Then you need to configure the charger directly on the charger such as [Eve Connect](https://alfen.com/en-be/eve-connect) app or ACE Service Installer for the Alfen Eve Pro. Check your charger's manufacturer manual.

## Charge Modes
The available charge modes are:
- Off: Charging disabled
- Fixed 1.4kW: Single phase charging at 6A (1.4kW)
- Fixed 4kW: Three phase charging at 6A (4kW)
- Limited: Dynamic power limiting based on household consumption
- Fast: Full speed charging at maximum current
- Solar: Dynamic power based on solar production

## Configuration and helpers
Update the following variables in the script with your own sensors and parameters. The parameters can be hard coded or set with a helper variable if you want to control it from the UI

### Load balancer
| Variable              | Unit | Type                | Description                                                                |
|-----------------------|------|---------------------|----------------------------------------------------------------------------|
| `state`               | string | Parameter.        | Load balancer mode [Off, Fixed 1.4kW, Fixed 4kW, Fast, Limited, Solar]     |
| `car_aware`           | bool | Parameter.          | Enable car aware functionality [true, false]                               |
| `power_limit`         | W    | Parameter           | Maximum power consumption limit including charging.                        |
| `power_limit_extended`| W    | Parameter           | [Optional] Maximum power allowed overcharge to reach SOC                   |
| `pv_prioritized`      | bool | Parameter           | Enable to make maximum use of solar power                                  |
| `single_phase_only`   | bool | Parameter           | Limit to phase output to 1 phase only                                      |

### Charger
| Variable              | Unit | Type                | Description                                                                |
|-----------------------|------|---------------------|----------------------------------------------------------------------------|
| `active_power`        | W    | Sensor              | Current active power of the charger to calculate charger efficiency.       |
| `connection_state`    |      | Sensor              | Connection state of the changer. [Disconnected, Connected]                 |
| `current_input`       | A    | Sensor              | Active current of the charger.                                             |
| `current_output`      | A    | Output entity       | Current setting of the charger.                                            |
| `default_current`     | A    | Parameter           | Default current to reset the charger of diconnecting.                      |
| `default_phases`      |      | Parameter           | Default phase selection to reset the charger after disconnecting. Charger dependant         |
| `max_current`         | A    | Parameter           | Maximum supported current of the charger.                                  |
| `min_current`         | A    | Parameter           | Minimum supported current of the charger.                                  |
| `nominal_voltage`     | V    | Parameter           | Nominal operating voltage of the charger.                                  |
| `phases_input`        |      | Sensor              | Active selected phases of the charger. Charger dependat                    |
| `phases_output`       |      | Output entity       | Phases setting of the charger. Charger dependant                           |

### Household
| Variable              | Unit | Type                | Description                                                                |
|-----------------------|------|---------------------|----------------------------------------------------------------------------|
| `household_power`     | W    | Sensor              | Smoothed household power consumption excluding the charger.                |
| `pv_power`            | W    | Sensor              | [Optional] Smoothed PV generated power.                                    |

### Car
Car configuration is optional and only needed when car_aware is enabled in the load balancer
| Variable              | Unit | Type                | Description                                                                |
|-----------------------|------|---------------------|----------------------------------------------------------------------------|
| `min_current`         | A    | Parameter           | Minimum supported car current.                                             |
| `max_current`         | A    | Parameter           | Maximum supported car current.                                             |
| `battery_percentage`  | %    | Sensor              | Current battery percentage of the car. [0%-100%]                           |
| `battery_capacity_wh` | Wh   | Parameter           | Battery capacity of the car.                                               |
| `soc_threshold`       | %    | Parameter           | Required battery percentage to reach by a set time. [0%-100%]              |
| `target_time`         | Time [HH:SS] | Parameter   | Time by which the SOC threshold should be reached.                         |

>[!Tip]
>Once the monthly peak consumption passes the set power limit of the loadbalancer, you can increase this limit to the new monthly peak via an automation. Do not forget to reset this at the beginning of the month.

## Features

### PV optimalization
 - pv_prioritized is only applicable to Limited mode and when enabled, the car will charge purely on solar power if the remaining solar power, not consumed by household consumption, is enough to charge the car. If there is not enough solar power, power from the grid will be used to charge up to power_limit. This combination is usefull to use as much solar power as possible but make sure the car is charged in the end.
 - With Solar charging, only remaining solar power is used. If this is not enough to charge the car, loading stops. This is useful if only need to be charged a little or the charger can be connected for 2 days or longer, such as in the weekend.

### Efficiency Handling
The system accounts for charger efficiency in all power calculations, by comparing the theoretical output with the real output:
- Available power is adjusted using measured charger efficiency
- Phase selection considers efficiency losses
- Current calculations include efficiency compensation
- Efficiency is calculated dynamically based on actual power measurements
- Fallback to 100% efficiency when no valid measurements available

### Car-aware Mode Behavior
When car-aware mode is enabled (`car_aware: true`), the system checks for required car sensors:
- battery_percentage
- battery_capacity_wh
- soc_time
- soc_threshold

If any of these sensors are unavailable the system continues operating as were car_aware=false

The current and phase limits are determined as follows:
- With car_aware=true: Uses minimum of car and charger max current
- With car_aware=false: Uses charger defaults
- With unavailable car sensors: Falls back to charger defaults

### Single Phase Operation
The load balancer can be configured to operate in single phase mode only:
- Toggle `Single Phase Only` in the configuration to force single phase operation
- When enabled:
  - All modes will operate in single phase regardless of power availability
  - Fast mode will still use maximum current but only on single phase. This is the same as Fixed 4kW mode.
  - Fixed 4kW mode will be limited to single phase operation. This is the same as Fast mode.
  - Limited and Solar modes will calculate optimal current for single phase
- Use this option if:
  - Your installation only supports single phase charging
  - You want to minimize the impact on phase balancing
  - You prefer consistent single phase operation

### Frequent Phase Switching Protection
The load balancer includes a phase switching protection mechanism to prevent frequent switches between 1 and 3 phases:

- When switching from 3 phases to 1 phase in Limied or Solar mode, a timer is started. Default 5 minutes.
- During this period, the charger will not switch back to 3 phases even if more power becomes available. However, the utilization of the current is maximized on 1 phase. 
- This protection does not apply to manual mode changes (e.g., switching to "Fixed 1.4kW" or "Fixed 4kW")
- The timer duration can be adjusted in the `timer.ev_load_balancer_phase_switching_timer` configuration

### Robust Sensor Validity Check and Fallback
If any required sensor or attribute for the selected charge mode is unavailable, unknown, none, or non-numeric, the automation will:
- Log an error to Home Assistant's system log: `[EV Load Balancer] Fallback to default charger values due to missing or invalid sensor data.`
- Set the charger to its default current and phase, skipping all further logic.

## Future Developments
- [x] Autocalculate charger efficiency.
- [x] Make car awareness optional.
- [x] Option to prioritize PV consumption.
- [x] Phase switching protection
- [ ] Optimize for dynamic energy contracts.
- [x] Provide as generic a Home Assistant package.
- [x] Option to limit to 1 phase only.
- [ ] Implement a minimum charge power instead of switching off the charger.
- [ ] Convert to a full Home Assistant integration.

## Disclaimer
The use of this automation is at your own risk. The author assumes no responsibility for any consequences arising from its use, including power consumption, vehicle SOC, or damages. Test thoroughly in your environment before relying on it for critical operations.

## Troubleshooting

### Common Issues

1. **Missing or Invalid Sensor Data**
   - If any required sensor becomes unavailable, the charger falls back to default values
   - Check Home Assistant logs for "[EV Load Balancer] Fallback" messages
   - Verify all required sensors are properly configured and responding

2. **Phase Switching Issues**
   - The timer prevents rapid phase switching
   - Check if the phase switching timer is working correctly
   - Verify charger's phase switching capability

3. **Car Awareness Not Working**
   - Ensure car_aware is enabled
   - Verify all car-related sensors are available and providing valid data
   - Check if target time and SOC threshold are properly set

### Debug Logging
To enable debug logging, add the following to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.ev_load_balancer: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
