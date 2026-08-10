"""Sensor platform for prometheus_sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_QUERIES,
    CONF_QUERY,
    CONF_STATE_CLASS,
    DISCOVERY_COORDINATOR,
    DOMAIN,
    LOGGER,
    query_id_from_name,
)
from .coordinator import PrometheusDataUpdateCoordinator

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
        AddEntitiesCallback,
    )
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

    from .data import PrometheusSensorsConfigEntry


async def async_setup_platform(
    _hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Prometheus sensors from domain-level YAML discovery."""
    if discovery_info is None:
        LOGGER.error(
            "YAML platform config under sensor is not supported. Use %s instead",
            DOMAIN,
        )
        return

    config = discovery_info
    queries = [_sensor_query_config(query) for query in config[CONF_QUERIES]]
    coordinator = config[DISCOVERY_COORDINATOR]
    device_info = DeviceInfo(
        name=config[CONF_NAME],
        identifiers={(DOMAIN, config[CONF_HOST])},
        entry_type=DeviceEntryType.SERVICE,
    )
    async_add_entities(
        [
            PrometheusSensor(
                coordinator=coordinator,
                entity_description=_entity_description_from_query(query),
                attribution=query[CONF_QUERY],
                device_info=device_info,
            )
            for query in queries
        ],
        update_before_add=True,
    )


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    for subentry in entry.subentries.values():
        if subentry.data.get(CONF_PLATFORM, Platform.SENSOR) != Platform.SENSOR:
            continue

        sensor = PrometheusSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=_entity_description_from_query(subentry.data),
            attribution=subentry.data[CONF_QUERY],
            device_info=DeviceInfo(
                name=entry.data[CONF_NAME],
                identifiers={
                    (
                        entry.domain,
                        entry.entry_id,
                    ),
                },
                entry_type=DeviceEntryType.SERVICE,
            ),
        )
        async_add_entities([sensor], update_before_add=True)


class PrometheusSensor(
    CoordinatorEntity[PrometheusDataUpdateCoordinator], SensorEntity
):
    """Sensor class."""

    def __init__(
        self,
        coordinator: PrometheusDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        attribution: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_attribution = attribution
        self._attr_unique_id = entity_description.key
        self._attr_device_info = device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        value = self.coordinator.data[self.entity_description.key]
        self._attr_available = value is not None
        self._attr_native_value = value
        self.async_write_ha_state()


def _entity_description_from_query(query: Mapping[str, Any]) -> SensorEntityDescription:
    """Create a sensor entity description from a query definition."""
    return SensorEntityDescription(
        key=query[CONF_ID],
        name=query[CONF_NAME],
        icon=query.get(CONF_ICON),
        state_class=query.get(CONF_STATE_CLASS),
        device_class=query.get(CONF_DEVICE_CLASS),
        native_unit_of_measurement=query.get(CONF_UNIT_OF_MEASUREMENT),
    )


def _sensor_query_config(query: dict) -> dict:
    """Normalize a YAML sensor query config."""
    return {
        CONF_ID: query_id_from_name(query[CONF_NAME]),
        CONF_NAME: query[CONF_NAME],
        CONF_QUERY: query[CONF_QUERY],
        CONF_ICON: query.get(CONF_ICON),
        CONF_DEVICE_CLASS: query.get(CONF_DEVICE_CLASS),
        CONF_UNIT_OF_MEASUREMENT: query.get(CONF_UNIT_OF_MEASUREMENT) or None,
        CONF_STATE_CLASS: query.get(CONF_STATE_CLASS, SensorStateClass.MEASUREMENT),
    }
