"""Sensor platform for prometheus_sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_QUERY, CONF_STATE_CLASS
from .coordinator import PrometheusDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import PrometheusSensorsConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    for subentry_id, subentry in entry.subentries.items():
        device_class = subentry.data.get(CONF_DEVICE_CLASS)
        state_class = subentry.data.get(CONF_STATE_CLASS)
        unit_of_measurement = subentry.data.get(CONF_UNIT_OF_MEASUREMENT)
        sensor = PrometheusSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=SensorEntityDescription(
                key=subentry.data[CONF_ID],
                name=subentry.data[CONF_NAME],
                icon=subentry.data.get(CONF_ICON, None),
                state_class=state_class,
                device_class=device_class,
                native_unit_of_measurement=unit_of_measurement,
            ),
            attribution=subentry.data[CONF_QUERY],
        )
        async_add_entities(
            [sensor], update_before_add=True, config_subentry_id=subentry_id
        )


class PrometheusSensor(
    CoordinatorEntity[PrometheusDataUpdateCoordinator], SensorEntity
):
    """Sensor class."""

    def __init__(
        self,
        coordinator: PrometheusDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
        attribution: str,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_attribution = attribution
        self._attr_unique_id = entity_description.key
        self._attr_device_info = DeviceInfo(
            name=coordinator.config_entry.data[CONF_NAME],
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            entry_type=DeviceEntryType.SERVICE,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        value = self.coordinator.data[self.entity_description.key]
        self._attr_available = value is not None
        self._attr_native_value = value
        self.async_write_ha_state()
