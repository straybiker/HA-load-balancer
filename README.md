# Home Assistant car charging load balancer automation 
Car charging load balancer for Home Assistant tailered to Belgian energy regulation (Capaciteitstarief).

## Introduction
This is not an integration (yet), just home assistant yaml files to use in automations and scripts.

> [!Note]
> These scripts are based on my own needs, such as an integration with my car. Future developments may make it more generic. 

This load balancer checks the current power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power. The total power to use, household + EV charger, is limited by a parameter. 
This load balancer uses 3 phases power and a maximum current of 16A.
The current script also checks the battery state of a BMW. When forecasted battery charge doesn't reach a minimum desired level by a set time, the charger can override the maximum power to a second limit. 

## Installation
- Create a new automation for the load balancer and paste the yaml code of LoadbalanceEVCharger.yamlinto it
- Create a new script to update the charger and paste the yaml code of the SetChargerParams.yaml in it
- [Optional] Create a new automation to reset the charger parameters when the car is disconnected and paste the yaml code of resetCharger.yaml in it

## Prerequisites
The load balancer is currently built to used in combination with an Alfen Eve Pro and BMW EV, but it can be easily adjusted to use with another charger or car.  

- Home Assistant HACS Alfen Wallbox integration: https://github.com/leeyuentuen/alfen_wallbox
- Home Assistant BMW Connected drive integration: https://www.home-assistant.io/integrations/bmw_connected_drive
- Helpers. See [Configuration](https://github.com/straybiker/HA-load-balancer/blob/main/README.md#configuration) for more details on how to use these:
  - Input number: maximum total power limit
  - Input number: overcharge limit for when the minimum car charge is not reached
  - Input select to select load balancing mode [Off, Minimal 1.4kW, Minimal 4kW, Eco, Fast]
  - Input number: Alfen charger efficiency
  - Input number: Car battery capacity
  - Input number: Minimum target car charge
  - Date time: to set the time the minimum car charge should be reached
- Sensor: Current household power consumption. Since I don't have a digital meter yet, but this is a test to prepare for the digital meter. I use a Shelly Pro3EM to measure household power consumption.
- Template sensor to determine the socket connection state. Add this to your `configuration.yaml` file.
```
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

I assume active load balancing needs to be switched off on the Alfen charger to avoid conflicts. I don't have a license, so running this load balancer in combination with the one from Alfen is untested.

>[!Tip] 
>Since household power consumption can be scattery; best to pass it first trough a low pass filter. https://www.home-assistant.io/integrations/filter/#low-pass .My filter looks like this in the configuration.yaml:
>```
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
>sensor.netto_verbruik_huis is the raw household power consumption, netto_verbruik_huis_lp is used by the load balancer. This sensor can become negative if PV panels provide more power then being used by the household.

## Details
This load balancer checks every 10 seconds the current power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power. The total power to use, household + EV charger, is defined in an input helper parameter.
This load balancer uses 3 phases power and a max current of 16A.

![Power consumption](https://github.com/straybiker/HA-load-balancer/blob/main/doc/powerconsumption.png)
Red line shows the total power consumption, which is kept steady at 6kW overnight. The small drops are periods that there isn't enough capacity to charge.

The current script also checks the battery state of a BMW. When forecasted battery state doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. If the threshold is reached, charging will just continue until the car stops the session. For example, I want my car to be 80% charged by 8:00 in the morning. If it cannot reach 80%, some additional power can be consumed. Set both power parameters equal to disable the extra power consumption. 

If there is not enough power to charge at 3 phases, 6A, the charger is switched to 1 phase. When the remaining power is not enough to reach 1 phase, 6A, charging stops by setting the maximum socket current to 0A. There is a risk with this that the car is not charged for a prolonged period if household power consumption is high.

>[!NOTE]
>There is a built in delay in the script when the charger parameters are changed. Since this automation runs every 10 seconds, a warning in the HA log will appear that the automation is already running.

Use the script to set the charger parameters to a desired phase and current when you disconnect the cable from the car. This way you shouldn't end up with a charger that is set to 0A when home assistant is not available.

> [!WARNING]
> There is still a risk if home assistant becomes unavailable during charging with the charger set at 0A. Then you need the [Eve Connect](https://alfen.com/en-be/eve-connect) app or ACE Service Installer to set the values of the charger.

The loading behavior can be adjust by in input select:
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
| charger_efficiency | % | input number helper | sometimes the charger output is less then the theoretical output. This value can compensate this loss. Note: this output efficiency seems to vary so using this pushes your power consumption over max_combined_power and extended_power_limit |
| target_time | date time | datetime input helper | Time at which soc_threshold should be reached. Not this is not a variable but in the calculation of time_until_target_time |

![Image](https://github.com/user-attachments/assets/9ebd9154-5a44-45b6-ae89-c8545ebcd0fa)

![Image](https://github.com/user-attachments/assets/2717a963-ad2c-469a-9077-8368c776afb6)

![Image](https://github.com/user-attachments/assets/b347021d-229c-4a7d-8682-5a99f5f9c4f6)

![Image](https://github.com/user-attachments/assets/e263175f-1407-45e9-b684-dfdd1172b7c7)

![Image](https://github.com/user-attachments/assets/73853bbc-1ff1-494f-b80a-216cd31b3291)

![Image](https://github.com/user-attachments/assets/93a0863c-7ad4-4ee5-bc11-36dc61b7e0e3)

![Image](https://github.com/user-attachments/assets/cf492018-cf80-4fbe-bc1d-b0f54fee5580)


## Future developments
Testing: adjust the power limit dynamically with the monthly capacity peak. If you went over your initial setting, you may just as well consume this amount of power the rest of the month.
Todo: make dependency on the car battery percentage optional, so others when another car charges, it is not depending on my car. This is also needed when another car is charging at my charger. 
Todo: optimize for dynamic energy contracts
Todo: provide this in an Home Assistant package. 

Maybe: option to limit to 1 phase in Eco mode
Maybe: a minimum charge power instead of switching the charger off. 
Maybe: make it an HA integration


## Disclaimer
The use of this automation is at your own risk! I take no responsibility for the outcome of the power consumption, the amount the car is charged or any damages that may come from using this automation.
