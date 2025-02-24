# Prometheus Sensors Integration for Home Assistant
This custom integration allows to add Prometheus metrics into Home Assistant.
Uses configuration subentries to add multple PromQL queries as sensors.

## Installation
1. Add the integration via HACS.
2. Configure the integration from the UI.

## Configuration
- **Host**: The URL of your Prometheus server.
- **Verify SSL**: Whether to verify SSL certificates.

## Credits
- https://github.com/ludeeus/integration_blueprint
- https://github.com/mweinelt/ha-prometheus-sensor