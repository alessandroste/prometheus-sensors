"""
Custom integration to integrate Prometheus metrics as sensors into Home Assistant.

For more details about this integration, please refer to
https://github.com/alessandroste/prometheus-sensors
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, CONF_VERIFY_SSL, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import PrometheusApiClient
from .const import DOMAIN, LOGGER
from .coordinator import PrometheusDataUpdateCoordinator
from .data import PrometheusSensorsData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .data import PrometheusSensorsConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = PrometheusDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_interval=timedelta(**entry.data[CONF_SCAN_INTERVAL])
        if CONF_SCAN_INTERVAL in entry.data
        else timedelta(seconds=1),
    )
    entry.runtime_data = PrometheusSensorsData(
        client=PrometheusApiClient(
            host=entry.data[CONF_HOST],
            session=async_get_clientsession(
                hass, verify_ssl=entry.data[CONF_VERIFY_SSL]
            ),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle update."""
    await hass.config_entries.async_reload(entry.entry_id)
