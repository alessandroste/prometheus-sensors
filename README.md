# Prometheus Sensors Integration for Home Assistant
This custom integration allows to add Prometheus metrics into Home Assistant.
Uses configuration subentries to add multiple PromQL queries as sensors.

## Installation
1. Add the integration via HACS.
2. Configure the integration from the UI.

## Configuration
### UI
- **Host**: The URL of your Prometheus server.
- **Verify SSL**: Whether to verify SSL certificates.

### YAML
The integration can also be configured from `configuration.yaml` under the
`prometheus_sensors` domain.

```yaml
prometheus_sensors:
  - name: My Prometheus Server
    host: http://localhost:9090
    verify_ssl: true
    scan_interval: 15
    headers:
      X-Scope-OrgID: my-tenant
    sensors:
      - name: Energy usage
        query: energy_usage_wh / 1000
        unit_of_measurement: kWh
        device_class: energy
        state_class: total_increasing
      - name: CPU usage
        query: sum(rate(node_cpu_seconds_total{mode!="idle"}[1m])) / sum(rate(node_cpu_seconds_total[1m])) * 100
        unit_of_measurement: "%"
        icon: mdi:cpu-64-bit
    binary_sensors:
      - name: Front Door
        query: front_door_open
        value_template: "{{ value == 1 }}"
        device_class: door
```

Supported platform options:
- **name**: Friendly name for the Prometheus server device.
- **host**: Prometheus-compatible API base URL.
- **verify_ssl**: Whether to verify SSL certificates. Defaults to `true`.
- **scan_interval**: Polling interval. Defaults to 15 seconds.
- **headers**: Optional mapping of HTTP headers sent with every request.
- **sensors**: Optional list of PromQL queries to expose as sensor entities.
- **binary_sensors**: Optional list of PromQL queries to expose as binary sensor entities.

Sensor query options:
- **name**: Friendly entity name.
- **query**: PromQL expression.
- **icon**: Optional Material Design icon.
- **unit_of_measurement**: Optional native unit.
- **device_class**: Optional Home Assistant sensor device class.
- **state_class**: Optional Home Assistant sensor state class.

Binary sensor query options:
- **name**: Friendly entity name.
- **query**: PromQL expression.
- **icon**: Optional Material Design icon.
- **device_class**: Optional Home Assistant binary sensor device class.
- **value_template**: Optional template rendered with `value` set to the query result.
  Without a template, the binary sensor is off for `0` and on for any other value.

## Credits
- https://github.com/ludeeus/integration_blueprint
- https://github.com/mweinelt/ha-prometheus-sensor