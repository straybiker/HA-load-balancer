# HA-load-balancer
Power load balancer for Home Assistant tailered to Belgium energy regulation.

## Introduction
This is not an integration (yet), just home assistant yaml files to use in automations and scripts.

This load balancer checkes the current power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power. The total power to use, household + EV charger, is limited by a parameter.
This load balancer uses 3 phase power and a max current of 16A.
The current script also checks the accu state of a BMW. When forecasted accu state doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. 

## Installation
- Create a new automation and paste the yaml code of LoadbalanceEVCharger.yamlinto it
- Create a new script and past the the yaml code of the SetChargerParams.yaml in it

## Prerequisites
- Home Assistant HACS Alfen Wallbox integration: https://github.com/leeyuentuen/alfen_wallbox
- Home Assistant BMW Connected drive integration: https://www.home-assistant.io/integrations/bmw_connected_drive
- Helpers:
  - Input number: maximum total power limit
  - Input number: overcharge limit for when the minimum car charge is not reached
  - Input select to select looad balacing mode [Off, Minimal 1.4kW, Minimal 4kW, Eco, Fast]
  - Input number: Alfen charger efficiency
  - Input number: Car accu capacity
  - Input number: Minimum target car charge
  - Date time: to set the time the minimum car charge should be reached
- Sensor: Current household power consumption. Since I don't have a digital meter yet, but this is a test to prepare for the digital meter, I use a Shelly Pro3EM to measure household power consumption.

## Tips
Since household power consumption can be scattery, best to pass it first trough a low pass filter.
My filter looks like this in the configuration.yaml:
```
  - platform: filter
    name: "Netto verbruik huis LP"
    unique_id: netto_verbruik_huis_lp
    entity_id: sensor.netto_verbruik_huis
    filters:
      - filter: outlier
        window_size: 4
        radius: 500.0
      - filter: lowpass
        time_constant: 12
        precision: 2
```

## Details
This load balancer checkes every 10 seconds the current power consumption and sets the Alfen Wallbox charging parameters according to the remaining available power. The total power to use, household + EV charger, is defined in an input helper parameter.
This load balancer uses 3 phase power and a max current of 16A.
The current script also checks the accu state of a BMW. When forecasted accu state doesn't reach a minimum charge by a set time, the charger can override the maximum power to a second limit. If the threshold is reached, charging will just continue until the car stops the session.

When the remaining power is not enough to reach 1 phae, 6A, charging stops. There is a risk with this that the car is not charged for a prolonged period if household power consumption is high.

The loading behavior can be adjust by in input select:
- Off: No not load
- Minimal 1.4kW: Always load 1 phase 6A
- Minimal 4kW: Always load 3 phases 6A
- Eco: load balance based on the available rest power
- Fast: Always load at 3 phases, 16A
