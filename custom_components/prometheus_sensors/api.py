"""Sample API Client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .api_client.prometheus_client import PrometheusClient

if TYPE_CHECKING:
    import aiohttp


class PrometheusApiClientError(Exception):
    """Exception to indicate a general API error."""

    error_code: str = "unknown"


class PrometheusApiClientCommunicationError(
    PrometheusApiClientError,
):
    """Exception to indicate a communication error."""

    error_code = "connection"


class PrometheusApiClientAuthenticationError(
    PrometheusApiClientError,
):
    """Exception to indicate an authentication error."""

    error_code = "auth"


class PrometheusApiClient:
    """A wrapper around prometheus-api-client."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._host = host
        self._connection = PrometheusClient(url=self._host, session=session)

    async def async_get_metrics(self) -> list[str]:
        """Get all the defined metrics from Prometheus."""
        try:
            return await self._connection.all_metrics()
        except Exception as exception:
            msg = f"Error fetching metrics: {exception}"
            raise PrometheusApiClientError(
                msg,
            ) from exception

    async def async_query(self, query: str) -> float | None:
        """Query Prometheus with a given query."""
        try:
            result = await self._connection.custom_query(query)
            return float(result[0]["value"][1]) if result else None
        except Exception as exception:
            msg = f"Error querying Prometheus: {exception}"
            raise PrometheusApiClientError(
                msg,
            ) from exception

    async def async_get_query_labels(self, query: str) -> list[str]:
        """Query Prometheus and return the list of label names."""
        try:
            result = await self._connection.custom_query(query)
            return list(result[0]["metric"].keys()) if result else []
        except Exception as exception:
            msg = f"Error querying Prometheus labels: {exception}"
            raise PrometheusApiClientError(
                msg,
            ) from exception

    async def async_test_query_result_size(self, query: str) -> bool:
        """Query Prometheus and return the list of label names."""
        try:
            result = await self._connection.custom_query(query)
            return len(result) == 1
        except Exception as exception:
            msg = f"Error querying Prometheus labels: {exception}"
            raise PrometheusApiClientError(
                msg,
            ) from exception
