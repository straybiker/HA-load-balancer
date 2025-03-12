# Home Assistant car charging load balancer automation 
Car charging load balancer for Home Assistant tailored to Belgian energy regulation (Capaciteitstarief).



## Table of Contents
- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Option 1: Individual file installation](#option-1-individual-file-installation)
  - [Option 2: Package installation](#option-2-package-installation)
- [Details](#details)
- [Configuration and helpers](#configuration-and-helpers)
- [Future developments](#future-developments)
- [Disclaimer](#disclaimer)
- [License](#license)
- [Contributing](#contributing)
- [Contact](#contact)

## Introduction
This Home Assistant automation provides intelligent load balancing for EV charging, designed to minimize energy costs and avoid exceeding your maximum power limit (capaciteitspiek) under Belgian energy regulations. By dynamically adjusting the charging current based on your household's power consumption, this system helps you charge your EV efficiently without overloading your electrical grid.

This project is ideal for users with an Alfen Wallbox and can be adapted for other EV chargers and power monitoring solutions.  While the current version includes specific integration with BMW vehicles for battery state monitoring, this dependency can be made optional.

This is not a fully-fledged Home Assistant integration (yet), but rather a set of YAML files for automations and scripts that you can easily integrate into your existing Home Assistant setup.

This load balancer checks the current household power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power by setting the allowed phases and current.
The current script also checks the battery state of a BMW. When forecasted battery charge doesn't reach a minimum desired level by a set time, the charger can override the maximum power to a second limit. 

There are 2 versions of the scripts available, one with individual YAML files, one as a package. The version in the package is a simplified version without integration to BMW and charger efficiency.

## Prerequisites
- 3 Phases electrical installation
- Home Assistant HACS Alfen Wallbox integration: [Alfen Wallbox Integration](https://github.com/leeyuentuen/alfen_wallbox). I assume active load balancing needs to be switched off on the Alfen charger to avoid conflicts. I don't have a license, so running this load balancer in combination with the one from Alfen is untested. Minimum version 2.9.4
- Sensor: Current household power consumption measured, excluding the charger power consumption. Since I don't have a digital meter yet, but this is a test to prepare for the digital meter. I use a Shelly Pro3EM to measure household power consumption.

## Installation
These scripts can be installed in 2 ways, by creating individual entities, automations and scripts, or via a package.

###  Option 1: Individual file installation
#### Step 1
Install Home Assistant BMW Connected drive integration: [BMW Connected Drive Integration](https://www.home-assistant.io/integrations/bmw_connected_drive)

#### Step 2: Create helpers
See [Configuration](#configuration-and-helpers) for more details on how to use these.
- Input number: maximum total power limit
- Input number: overcharge limit for when the minimum car charge is not reached
- Input select to select load balancing mode [Off, Minimal 1.4kW, Minimal 4kW, Eco, Fast]
- Input number: Car battery capacity
- Input number: Minimum target car charge
- Date time: to set the time the minimum car charge should be reached
- Template sensor to determine the socket connection state. Add this to your `configuration.yaml` file.
```yaml
template:
  - sensor:
      - name: Alfen Eve Connection State
        unique_id: alfen_eve_connection_state
        state: >
          {% set m3 = states('sensor.alfen_eve_mode3_state_socket_1') %}
          {% if m3 in ['STATE_A', 'STATE_E'] %} Disconnected
          {% elif m3 in ['STATE_B1', 'STATE_B2', 'STATE_C1', 'STATE_D1', 'STATE_C2', 'STATE_D2'] %} Connected
          {% elif m3 in ['STATE_F'] %} Error
          {% else %} unavailable
          {% endif %}
```

>[!Tip] 
>Since household power consumption can be noisy, it's best to pass it through a low pass filter. See [Home Assistant Low Pass Filter](https://www.home-assistant.io/integrations/filter/#low-pass) documentation. The filter helps smooth out spikes in power measurements as shown below:
>```yaml
>platform: filter
>name: "Netto verbruik huis LP"
>unique_id: netto_verbruik_huis_lp
>entity_id: sensor.netto_verbruik_huis
>filters:
>  - filter: outlier
>    window_size: 4
>    radius: 500.0
>  - filter: lowpass
>    time_constant: 12
>    precision: 2
>```
>Note: `sensor.netto_verbruik_huis` represents raw household power consumption, while `netto_verbruik_huis_lp` is the filtered value used by the load balancer. This sensor can show negative values when PV panels generate more power than the household consumes.

#### Step 3: Create Scripts
1. Load Balancer Automation
   - Create a new automation in Home Assistant
   - Paste the contents of `LoadbalanceEVCharger.yaml` into it
   - Save and enable the automation

2. Charger Parameters Script
   - Create a new script in Home Assistant  
   - Paste the contents of `SetChargerParams.yaml` into it
   - Save the script

3. Optional: Reset Parameters Automation
   - Create a new automation in Home Assistant
   - Paste the contents of `resetCharger.yaml` into it 
   - Save and enable the automation

### Option 2: Package installation
See https://www.home-assistant.io/docs/configuration/packages/ for details about packages
The package file is located in the package folder.
>[!WARNING]
>The package version is untested!

## Details
This load balancer checks every 10 seconds the current household power consumption and sets the Alfen Wallbox charging parameters, phase and current, according to the remaining available power. The total allowed power to use (capaciteitspiek), household + EV charger, is defined in an input helper parameter.
The loadbalancer also takes charger efficiency into account by comparing the calculated power output with the actual power output.

> [!Note]
> The maximum current can still be limited by the settings of the car. This setting can be checked by the external socket max current sensor. 

>[!IMPORTANT]
> This load balancer switches between 3 phases power and a max current of 16A. 1 phase only is not supported.

![image](https://github.com/user-attachments/assets/bf4685fa-3eef-4814-b577-23d8f777e9c8)
Here, during charging, the power is kept stable around 6000W, although major changes in the household power consumption. At 18h, the car was disconnected for a while. The spikes are measurement errors.

The current script also checks the battery state of a BMW. When forecasted battery percentage doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. If the threshold is reached, charging will just continue until the car stops the session. For example, I want my car to be 80% charged by 8:00 in the morning. If it cannot reach 80%, some additional power can be consumed. Set both power parameters equal to disable the extra power consumption. 

If there is not enough power to charge at 3 phases, 6A, the charger is switched to 1 phase. When the remaining power is not enough to reach 1 phase, 6A, charging stops by setting the maximum socket current to 0A. There is a risk with this that the car is not charged for a prolonged period if household power consumption is high.

>[!NOTE]
>There is a built in delay in the script when the charger parameters are changed. Since this automation runs every 10 seconds, a warning in the HA log will appear that the automation is already running.

Use the script `resetCharger.yaml` to set the charger parameters to a desired phase and current when you disconnect the cable from the car. This way you shouldn't end up with a charger that is set to 0A when Home Assistant is not available.

> [!WARNING]
> There is still a risk if Home Assistant becomes unavailable during charging with the charger set at 0A. Then you need the [Eve Connect](https://alfen.com/en-be/eve-connect) app or ACE Service Installer to set the values of the charger.

The loading behavior can be adjusted by an input select:
- Off: Do not charge
- Minimal 1.4kW: Always charge at 1 phase, 6A
- Minimal 4kW: Always charge at 3 phases, 6A
- Eco: Load balance based on the available rest power
- Fast: Always load at 3 phases, 16A

## Configuration and helpers
Update the following variables in the script with your own helpers and sensors

| Variable | Unit | Type | Description |
| -------- | ---- | ---- | ----------- |
| home_power | W | sensor | The (smoothed) household power consumption excluding the charger |
| max_combined_power | W | input number helper | Maximum power consumption limit incling charging |
| extended_power_limit | W | input number helper | Maximum overcharge limit to reach the minimum car SOC threshold |
| max_current | A | fixed value | Update to the maximum charger or car current in your system |
| battery_percentage | % | sensor | Linked car current battery percentage |
| battery_capacity_wh | Wh | input number helper | Linked car battery capacity |
| soc_threshold | % | input number helper | Required battery % to reach at a set time. If not, overcharge to extended_power_limit |
| target_time | date time | datetime input helper | Time at which soc_threshold should be reached. Not this is not a variable but in the calculation of time_until_target_time |

![Image](https://github.com/user-attachments/assets/2717a963-ad2c-469a-9077-8368c776afb6)

![Image](https://github.com/user-attachments/assets/b347021d-229c-4a7d-8682-5a99f5f9c4f6)

![Image](https://github.com/user-attachments/assets/e263175f-1407-45e9-b684-dfdd1172b7c7)

![Image](https://github.com/user-attachments/assets/73853bbc-1ff1-494f-b80a-216cd31b3291)

![Image](https://github.com/user-attachments/assets/93a0863c-7ad4-4ee5-bc11-36dc61b7e0e3)

![Image](https://github.com/user-attachments/assets/cf492018-cf80-4fbe-bc1d-b0f54fee5580)


>[!Tip]
>Once the monthly peak consumption passes the set power limit of the loadbalancer, you can increase this limit to the new monthly peak via an automation. Do not forget to reset this at the beginning of the month.

## Future developments
- [ ] Testing: adjust the power limit dynamically with the monthly capacity peak. If you went over your initial setting, you may just as well consume this amount of power the rest of the month.
- [x] Testing: Autocalculate charger efficiency
- [ ] Make dependency on the car battery percentage optional, so others when another car charges, it is not depending on my car. This is also needed when another car is charging at my charger. 
- [ ] Optimize for dynamic energy contracts
- [ ] Provide this in a Home Assistant package. 

- [ ] Option to limit to 1 phase in Eco mode
- [ ] A minimum charge power instead of switching the charger off. 
- [ ] Convert to an HA integration


## Disclaimer
The use of this automation is at your own risk. The author assumes no responsibility for any consequences arising from the use of this automation, including but not limited to power consumption, the state of charge of the vehicle, or any damages that may result from its use. Users are advised to thoroughly test and verify the automation in their own environment before relying on it for critical operations.