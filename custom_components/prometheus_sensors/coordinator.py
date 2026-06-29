"""DataUpdateCoordinator for prometheus_sensors."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    PrometheusApiClient,
    PrometheusApiClientAuthenticationError,
    PrometheusApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import timedelta
    from logging import Logger

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import StateType

    from .data import PrometheusSensorsConfigEntry

type PrometheusResult = dict[str, StateType | date | datetime | Decimal | None]


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class PrometheusDataUpdateCoordinator(DataUpdateCoordinator[PrometheusResult]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        client: PrometheusApiClient,
        queries: Mapping[str, str],
        config_entry: PrometheusSensorsConfigEntry | None = None,
        name: str,
        update_interval: timedelta | None = None,
    ) -> None:
        self.client = client
        self.queries = queries
        coordinator_kwargs = {}
        if config_entry is not None:
            coordinator_kwargs["config_entry"] = config_entry

        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
            **coordinator_kwargs,
        )

    async def _async_update_data(self) -> PrometheusResult:
        """Update data via library."""
        try:
            return {
                query_id: await self.client.async_query(query)
                for query_id, query in self.queries.items()
            }
        except PrometheusApiClientAuthenticationError as exception:
            if getattr(self, "config_entry", None) is not None:
                raise ConfigEntryAuthFailed(exception) from exception
            raise UpdateFailed(exception) from exception
        except PrometheusApiClientError as exception:
            raise UpdateFailed(exception) from exception
