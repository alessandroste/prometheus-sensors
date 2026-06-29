"""
Custom integration to integrate Prometheus metrics as sensors into Home Assistant.

For more details about this integration, please refer to
https://github.com/alessandroste/prometheus-sensors
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import PrometheusApiClient
from .const import (
    CONF_BINARY_SENSORS,
    CONF_HEADERS,
    CONF_QUERIES,
    CONF_QUERY,
    CONF_SENSORS,
    CONF_STATE_CLASS,
    DISCOVERY_COORDINATOR,
    DOMAIN,
    LOGGER,
    SCAN_INTERVAL,
    SCHEMA_HINT_HOST,
    SCHEMA_HINT_NAME,
    query_id_from_name,
)
from .coordinator import PrometheusDataUpdateCoordinator
from .data import PrometheusSensorsData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .data import PrometheusSensorsConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

_SENSOR_QUERY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_QUERY): cv.string,
        vol.Optional(CONF_ICON): cv.icon,
        vol.Optional(CONF_DEVICE_CLASS): vol.Coerce(SensorDeviceClass),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_STATE_CLASS): vol.Coerce(SensorStateClass),
    }
)

_BINARY_SENSOR_QUERY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_QUERY): cv.string,
        vol.Optional(CONF_ICON): cv.icon,
        vol.Optional(CONF_DEVICE_CLASS): vol.Coerce(BinarySensorDeviceClass),
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    }
)


def _has_platform_queries(config: dict) -> dict:
    if not config[CONF_SENSORS] and not config[CONF_BINARY_SENSORS]:
        msg = f"At least one of {CONF_SENSORS} or {CONF_BINARY_SENSORS} is required"
        raise vol.Invalid(msg)
    query_ids = [
        query_id_from_name(query[CONF_NAME])
        for query in [*config[CONF_SENSORS], *config[CONF_BINARY_SENSORS]]
    ]
    if len(set(query_ids)) != len(query_ids):
        msg = "Query names must be unique per Prometheus server"
        raise vol.Invalid(msg)
    return config


_SERVER_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(CONF_NAME, default=SCHEMA_HINT_NAME): cv.string,
            vol.Required(CONF_HOST, default=SCHEMA_HINT_HOST): cv.string,
            vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
            vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            vol.Optional(CONF_HEADERS): vol.Schema({cv.string: cv.string}),
            vol.Optional(CONF_SENSORS, default=[]): [_SENSOR_QUERY_SCHEMA],
            vol.Optional(CONF_BINARY_SENSORS, default=[]): [
                _BINARY_SENSOR_QUERY_SCHEMA
            ],
        }
    ),
    _has_platform_queries,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [_SERVER_SCHEMA])}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up YAML-configured Prometheus sensors."""
    for server_config in config.get(DOMAIN, []):
        client = PrometheusApiClient(
            host=server_config[CONF_HOST],
            session=async_get_clientsession(
                hass, verify_ssl=server_config[CONF_VERIFY_SSL]
            ),
            headers=server_config.get(CONF_HEADERS),
        )
        coordinator = PrometheusDataUpdateCoordinator(
            hass=hass,
            logger=LOGGER,
            client=client,
            queries={
                query_id_from_name(query[CONF_NAME]): query[CONF_QUERY]
                for query in [
                    *server_config[CONF_SENSORS],
                    *server_config[CONF_BINARY_SENSORS],
                ]
            },
            name=DOMAIN,
            update_interval=server_config[CONF_SCAN_INTERVAL],
        )
        await coordinator.async_refresh()

        common_config = {
            CONF_NAME: server_config[CONF_NAME],
            CONF_HOST: server_config[CONF_HOST],
            DISCOVERY_COORDINATOR: coordinator,
        }

        if server_config[CONF_SENSORS]:
            await discovery.async_load_platform(
                hass,
                Platform.SENSOR,
                DOMAIN,
                {**common_config, CONF_QUERIES: server_config[CONF_SENSORS]},
                config,
            )
        if server_config[CONF_BINARY_SENSORS]:
            await discovery.async_load_platform(
                hass,
                Platform.BINARY_SENSOR,
                DOMAIN,
                {
                    **common_config,
                    CONF_QUERIES: server_config[CONF_BINARY_SENSORS],
                },
                config,
            )

    return True


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrometheusSensorsConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    client = PrometheusApiClient(
        host=entry.data[CONF_HOST],
        session=async_get_clientsession(hass, verify_ssl=entry.data[CONF_VERIFY_SSL]),
    )
    coordinator = PrometheusDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        client=client,
        queries={
            subentry.data[CONF_ID]: subentry.data[CONF_QUERY]
            for subentry in entry.subentries.values()
        },
        config_entry=entry,
        name=DOMAIN,
        update_interval=timedelta(**entry.data[CONF_SCAN_INTERVAL])
        if CONF_SCAN_INTERVAL in entry.data
        else timedelta(seconds=1),
    )
    entry.runtime_data = PrometheusSensorsData(
        client=client,
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
