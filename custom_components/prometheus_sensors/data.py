"""Custom types for prometheus_sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import (
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
)

from .const import CONF_QUERY, CONF_STATE_CLASS

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import PrometheusApiClient
    from .coordinator import PrometheusDataUpdateCoordinator


type PrometheusSensorsConfigEntry = ConfigEntry[PrometheusSensorsData]


@dataclass
class QueryDefinition:
    """Definition of a Prometheus query."""

    __annotations__ = {
        CONF_NAME: str,
        CONF_QUERY: str,
        CONF_ID: str,
        CONF_ICON: str,
        CONF_DEVICE_CLASS: str | None,
        CONF_UNIT_OF_MEASUREMENT: str | None,
        CONF_STATE_CLASS: str | None,
    }

    def __init__(
        self,
        name: str,
        query: str,
        icon: str | None = None,
        device_class: str | None = None,
        unit_of_measurement: str | None = None,
        state_class: str | None = None,
    ) -> None:
        """Initialize a QueryDefinition object."""
        setattr(self, CONF_NAME, name)
        setattr(self, CONF_QUERY, query)
        setattr(self, CONF_ID, name.lower().replace(" ", "_"))
        setattr(self, CONF_ICON, icon or "mdi:chart-line")
        setattr(
            self,
            CONF_DEVICE_CLASS,
            None if device_class == "" else SensorDeviceClass(device_class),
        )
        setattr(
            self,
            CONF_UNIT_OF_MEASUREMENT,
            None if unit_of_measurement == "" else unit_of_measurement,
        )
        setattr(self, CONF_STATE_CLASS, SensorStateClass(state_class))


@dataclass
class PrometheusSensorsData:
    """Data for the Prometheus Sensors integration."""

    client: PrometheusApiClient
    coordinator: PrometheusDataUpdateCoordinator
    integration: Integration
