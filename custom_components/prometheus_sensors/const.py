"""Constants for prometheus_sensors."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "prometheus_sensors"

CONF_QUERY = "query"
CONF_STATE_CLASS = "state_class"

SCHEMA_HINT_QUERY = (
    'sum(rate(node_cpu_seconds_total{mode!="idle"}[1m]))'
    " / sum(rate(node_cpu_seconds_total[1m])) * 100"
)

SCHEMA_HINT_HOST = "http://prometheus:9090"
SCHEMA_HINT_NAME = "My Prometheus Server"
SCHEMA_HINT_QUERY_NAME = "My Query"
SCHEMA_HINT_ICON = "mdi:chart-line"
