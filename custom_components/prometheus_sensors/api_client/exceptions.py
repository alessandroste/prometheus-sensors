"""Exceptions for Prometheus API client."""

from aiohttp import StreamReader


class PrometheusApiClientError(Exception):
    """Exception to indicate a general API error."""

    def __init__(self, status: int, content: StreamReader) -> None:
        """Initialize the exception."""
        super().__init__(f"HTTP Status Code {status} ({content!r})")
