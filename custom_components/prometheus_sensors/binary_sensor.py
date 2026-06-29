"""Binary sensor platform for prometheus_sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_VALUE_TEMPLATE,
    Platform,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_QUERIES,
    CONF_QUERY,
    DISCOVERY_COORDINATOR,
    DOMAIN,
    LOGGER,
    query_id_from_name,
)
from .coordinator import PrometheusDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
        AddEntitiesCallback,
    )
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

    from .data import PrometheusSensorsConfigEntry


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Prometheus binary sensors from domain-level YAML discovery."""
    if discovery_info is None:
        LOGGER.error(
            "YAML platform config under binary_sensor is not supported. Use %s instead",
            DOMAIN,
        )
        return

    config = discovery_info
    queries = [_binary_query_config(query, hass) for query in config[CONF_QUERIES]]
    coordinator = config[DISCOVERY_COORDINATOR]
    device_info = DeviceInfo(
        name=config[CONF_NAME],
        identifiers={(DOMAIN, config[CONF_HOST])},
        entry_type=DeviceEntryType.SERVICE,
    )
    async_add_entities(
        [
            PrometheusBinarySensor(
                coordinator=coordinator,
                entity_description=_entity_description_from_query(query),
                attribution=query[CONF_QUERY],
                device_info=device_info,
                value_template=query.get(CONF_VALUE_TEMPLATE),
            )
            for query in queries
        ],
        update_before_add=True,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    for subentry_id, subentry in entry.subentries.items():
        if subentry.data.get(CONF_PLATFORM, Platform.SENSOR) != Platform.BINARY_SENSOR:
            continue

        query = _binary_query_config(dict(subentry.data), hass)
        binary_sensor = PrometheusBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=_entity_description_from_query(query),
            attribution=query[CONF_QUERY],
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
            value_template=query.get(CONF_VALUE_TEMPLATE),
        )
        async_add_entities(
            [binary_sensor], update_before_add=True, config_subentry_id=subentry_id
        )


class PrometheusBinarySensor(
    CoordinatorEntity[PrometheusDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor class."""

    def __init__(
        self,
        coordinator: PrometheusDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
        attribution: str,
        device_info: DeviceInfo,
        value_template: Template | None,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._value_template = value_template
        self._attr_attribution = attribution
        self._attr_unique_id = entity_description.key
        self._attr_device_info = device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        value = self.coordinator.data[self.entity_description.key]
        self._attr_available = value is not None
        if value is None:
            self._attr_is_on = None
        elif self._value_template is None:
            self._attr_is_on = bool(value)
        else:
            self._attr_is_on = _render_binary_value(self._value_template, value)
        self.async_write_ha_state()


def _binary_query_config(query: dict, hass: HomeAssistant) -> dict:
    """Normalize a YAML binary sensor query config."""
    query_config = {
        CONF_ID: query_id_from_name(query[CONF_NAME]),
        CONF_NAME: query[CONF_NAME],
        CONF_QUERY: query[CONF_QUERY],
        CONF_ICON: query.get(CONF_ICON),
        CONF_DEVICE_CLASS: query.get(CONF_DEVICE_CLASS),
        CONF_VALUE_TEMPLATE: query.get(CONF_VALUE_TEMPLATE),
    }
    value_template = query_config[CONF_VALUE_TEMPLATE]
    if value_template is not None:
        if isinstance(value_template, str):
            value_template = Template(value_template, hass)
            query_config[CONF_VALUE_TEMPLATE] = value_template
        else:
            value_template.hass = hass
    return query_config


def _entity_description_from_query(query: dict) -> BinarySensorEntityDescription:
    """Create a binary sensor entity description from a query definition."""
    return BinarySensorEntityDescription(
        key=query[CONF_ID],
        name=query[CONF_NAME],
        icon=query.get(CONF_ICON),
        device_class=query.get(CONF_DEVICE_CLASS),
    )


def _render_binary_value(value_template: Template, value: object) -> bool | None:
    """Render a binary sensor template into a boolean value."""
    rendered = value_template.async_render(variables={"value": value})
    if rendered is None:
        return None
    try:
        return cv.boolean(rendered)
    except vol.Invalid:
        return bool(rendered)
