"""DataUpdateCoordinator for prometheus_sensors."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_ID
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.prometheus_sensors.const import CONF_QUERY

from .api import (
    PrometheusApiClientAuthenticationError,
    PrometheusApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine
    from datetime import timedelta
    from logging import Logger

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.debounce import Debouncer
    from homeassistant.helpers.typing import StateType

    from .data import PrometheusSensorsConfigEntry

type PrometheusResult = dict[str, StateType | date | datetime | Decimal | None]


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class PrometheusDataUpdateCoordinator(DataUpdateCoordinator[PrometheusResult]):
    """Class to manage fetching data from the API."""

    config_entry: PrometheusSensorsConfigEntry

    def __init__(  # noqa: D107, PLR0913
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        config_entry: PrometheusSensorsConfigEntry,
        name: str,
        update_interval: timedelta | None = None,
        update_method: Callable[[], Awaitable[PrometheusResult]] | None = None,
        setup_method: Callable[[], Awaitable[None]] | None = None,
        request_refresh_debouncer: Debouncer[Coroutine[Any, Any, None]] | None = None,
        always_update: bool = True,
    ) -> None:
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            name=name,
            update_interval=update_interval,
            update_method=update_method,
            setup_method=setup_method,
            request_refresh_debouncer=request_refresh_debouncer,
            always_update=always_update,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            return {
                subentry_config.data[
                    CONF_ID
                ]: await self.config_entry.runtime_data.client.async_query(
                    subentry_config.data[CONF_QUERY]
                )
                for _, subentry_config in self.config_entry.subentries.items()
            }
        except PrometheusApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except PrometheusApiClientError as exception:
            raise UpdateFailed(exception) from exception
