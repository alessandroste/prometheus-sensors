"""Constants for prometheus_sensors."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "prometheus_sensors"

SCAN_INTERVAL = timedelta(seconds=15)

CONF_HEADERS = "headers"
CONF_BINARY_SENSORS = "binary_sensors"
CONF_QUERY = "query"
CONF_QUERIES = "queries"
CONF_SENSORS = "sensors"
CONF_STATE_CLASS = "state_class"
DISCOVERY_COORDINATOR = "coordinator"

SCHEMA_HINT_QUERY = (
    'sum(rate(node_cpu_seconds_total{mode!="idle"}[1m]))'
    " / sum(rate(node_cpu_seconds_total[1m])) * 100"
)

SCHEMA_HINT_HOST = "http://prometheus:9090"
SCHEMA_HINT_NAME = "My Prometheus Server"
SCHEMA_HINT_QUERY_NAME = "My Query"
SCHEMA_HINT_ICON = "mdi:chart-line"


def query_id_from_name(name: str) -> str:
    """Create a query id from a query name."""
    return name.lower().replace(" ", "_")
