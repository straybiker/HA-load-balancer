# EV Load Balancer Home Assistant Integration

This integration provides dynamic load balancing for EV charging, supporting car-aware and PV-prioritized modes.

## Features
- Dynamic load balancing for EV charging
- Car-aware charging (optional)
- PV-prioritized charging (optional)
- Configurable via Home Assistant UI

## Installation
1. Copy the `ev_load_balancer` folder to your `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the UI and follow the setup wizard.

## Configuration
- Sensors and entities must be available in Home Assistant before setup.
- Car and PV options are shown only if enabled during setup.

## Platforms Supported
- Sensor
- Number
- Select
- Switch

## Troubleshooting
- Ensure all required sensors/entities exist before setup.
- Check Home Assistant logs for errors.

## License
MIT
