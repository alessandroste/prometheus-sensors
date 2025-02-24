"""A Class for collection of metrics from a Prometheus Host."""

from datetime import datetime
from http import HTTPStatus
from typing import Any

import aiohttp

from .exceptions import PrometheusApiClientError


class PrometheusClient:
    """Class to retrieve data from a Prometheus server."""

    def __init__(
        self,
        url: str,
        session: aiohttp.ClientSession,
        timeout: aiohttp.ClientTimeout | None = None,
    ) -> None:
        """Initialize the Prometheus API client."""
        if url is None:
            raise ValueError

        self._url = url
        self._session = session
        self._timeout = timeout or aiohttp.ClientTimeout(total=10)

    async def check_connection(self, params: dict | None = None) -> bool:
        """Validate the connection to the server."""
        response = await self._session.get(
            f"{self._url}/",
            params=params,
            timeout=self._timeout,
        )
        return response.ok

    async def all_metrics(self, params: dict | None = None) -> list[str]:
        """Return a list of the available metrics."""
        self._all_metrics = await self.get_label_values(
            label_name="__name__", params=params
        )
        return self._all_metrics

    async def get_label_names(self, params: dict | None = None) -> list[str]:
        """Return a list of the available labels."""
        params = params or {}
        response = await self._session.get(
            f"{self._url}/api/v1/labels",
            params=params,
            timeout=self._timeout,
        )

        if response.status == HTTPStatus.OK:
            labels = (await response.json())["data"]
        else:
            raise PrometheusApiClientError(response.status, response.content)
        return labels

    async def get_label_values(
        self, label_name: str, params: dict | None = None
    ) -> list[str]:
        """Return a list of the label values."""
        params = params or {}
        response = await self._session.get(
            f"{self._url}/api/v1/label/{label_name}/values",
            params=params,
            timeout=self._timeout,
        )

        if response.status == HTTPStatus.OK:
            labels = (await response.json())["data"]
        else:
            raise PrometheusApiClientError(response.status, response.content)
        return labels

    async def custom_query(
        self,
        query: str,
        params: dict | None = None,
    ) -> Any:
        """Evaluate a custom query."""
        params = params or {}
        data = None
        query = str(query)
        # using the query API to get raw data
        response = await self._session.get(
            f"{self._url}/api/v1/query",
            params={"query": query, **params},
            timeout=self._timeout,
        )
        if response.status == HTTPStatus.OK:
            data = (await response.json())["data"]["result"]
        else:
            raise PrometheusApiClientError(response.status, response.content)

        return data

    async def custom_query_range(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        step: str,
        params: dict | None = None,
    ) -> Any:
        """Evaluate a custom query with time range."""
        start = round(start_time.timestamp())
        end = round(end_time.timestamp())
        params = params or {}
        data = None
        query = str(query)
        # using the query_range API to get raw data
        response = await self._session.get(
            f"{self._url}/api/v1/query_range",
            params={
                "query": query,
                "start": start,
                "end": end,
                "step": step,
                **params,
            },
            timeout=self._timeout,
        )
        if response.status == HTTPStatus.OK:
            data = (await response.json())["data"]["result"]
        else:
            raise PrometheusApiClientError(response.status, response.content)
        return data
