# HA-load-balancer
Power load balancer for Home Assistant tailered to Belgian energy regulation (Capaciteitstarief).

## Introduction
This is not an integration (yet), just home assistant yaml files to use in automations and scripts.

> [!Note]
> These scripts are based on my own needs, such as an integration with my car. Future developments may make it more generic. 

This load balancer checkes the current power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power. The total power to use, household + EV charger, is limited by a parameter.
This load balancer uses 3 phase power and a max current of 16A.
The current script also checks the accu state of a BMW. When forecasted accu state doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. 

## Installation
- Create a new automation and paste the yaml code of LoadbalanceEVCharger.yamlinto it
- Create a new script and past the the yaml code of the SetChargerParams.yaml in it

## Prerequisites
- Home Assistant HACS Alfen Wallbox integration: https://github.com/leeyuentuen/alfen_wallbox
- Home Assistant BMW Connected drive integration: https://www.home-assistant.io/integrations/bmw_connected_drive
- Helpers (See :
  - Input number: maximum total power limit
  - Input number: overcharge limit for when the minimum car charge is not reached
  - Input select to select looad balacing mode [Off, Minimal 1.4kW, Minimal 4kW, Eco, Fast]
  - Input number: Alfen charger efficiency
  - Input number: Car accu capacity
  - Input number: Minimum target car charge
  - Date time: to set the time the minimum car charge should be reached
- Sensor: Current household power consumption. Since I don't have a digital meter yet, but this is a test to prepare for the digital meter, I use a Shelly Pro3EM to measure household power consumption.

>[!Tip] 
>Since household power consumption can be scattery, best to pass it first trough a low pass filter. https://www.home-assistant.io/integrations/filter/#low-pass .My filter looks like this in the configuration.yaml:
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
>sensor.netto_verbruik_huis is the raw household power consuption, netto_verbruik_huis_lp is used by the load balancer.

## Details
This load balancer checkes every 10 seconds the current power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power. The total power to use, household + EV charger, is defined in an input helper parameter.
This load balancer uses 3 phase power and a max current of 16A.

![Power consuption](https://github.com/straybiker/HA-load-balancer/blob/main/doc/powerconsumption.png)
Red line shows the total power consumption, which is kept steady at 6kW overnight. The small drops are periods that there isn't enough capacity to charge.

The current script also checks the accu state of a BMW. When forecasted accu state doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. If the threshold is reached, charging will just continue until the car stops the session. For example, I want my car to be 80% charged by 8:00 in the morning. If it cannot reach 80%, some additional power can be consumed. Set both power parameters equal to disable the extra power consumption

When the remaining power is not enough to reach 1 phae, 6A, charging stops. There is a risk with this that the car is not charged for a prolonged period if household power consumption is high.
>[!Tip]
> Create a script to set the charger parameters to a disered phase and current when you disconnect the cable from the car. This way you shouldn't end up with a charger that is set to 0A when home assistant is not available. There is still a risk if home assistant becomes unavailable during charging with the charger set at 0A. Then you need the alfen app or ACE Service Installer to reset the charger.

The loading behavior can be adjust by in input select:
- Off: No not load
- Minimal 1.4kW: Always load 1 phase 6A
- Minimal 4kW: Always load 3 phases 6A
- Eco: load balance based on the available rest power
- Fast: Always load at 3 phases, 16A

## Configuration
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
| charger_efficiency | % | input number helper | sometimes the charger output is less then the theoretical output. This value can compensate this loss. Note: this output efficiency seems to vary so using this push your power consumption over max_combined_power and extended_power_limit |
| target_time | date time | datetime input helper | Time at which soc_threshold should be reached. Not this is not a variable but in the calculation of time_until_target_time |


## Future developments
Testing: adjust the power limit dynamically with the monthly capacity peak. If you went over your inital setting, you may just as well consume this amount of power the rest of the month.
Todo: make dependency on the car batttery percentage optional, so others when another car charges, it is not depending on my car. 

Maybe: option to limit to 1 phase in Eco mode
