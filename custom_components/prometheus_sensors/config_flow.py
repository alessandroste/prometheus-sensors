"""Adds config flow for Blueprint."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import (
    ConfigSubentryFlow,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from custom_components.prometheus_sensors.data import QueryDefinition

from .api import (
    PrometheusApiClient,
    PrometheusApiClientAuthenticationError,
    PrometheusApiClientCommunicationError,
    PrometheusApiClientError,
)
from .const import (
    CONF_QUERY,
    CONF_STATE_CLASS,
    DOMAIN,
    LOGGER,
    SCHEMA_HINT_HOST,
    SCHEMA_HINT_ICON,
    SCHEMA_HINT_NAME,
    SCHEMA_HINT_QUERY,
    SCHEMA_HINT_QUERY_NAME,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiohttp import ClientSession
    from homeassistant.config_entries import (
        ConfigEntry,
        ConfigFlowResult,
        SubentryFlowResult,
    )


SCHEMA_CONNECTION = vol.Schema(
    {
        vol.Required(CONF_NAME, default=SCHEMA_HINT_NAME): selector.TextSelector(),
        vol.Required(CONF_HOST, default=SCHEMA_HINT_HOST): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        ),
        vol.Required(CONF_VERIFY_SSL, default=True): selector.BooleanSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): selector.DurationSelector(
            selector.DurationSelectorConfig(
                enable_day=False, enable_millisecond=False, allow_negative=False
            )
        ),
    },
)

SCHEMA_QUERY = vol.Schema(
    {
        vol.Required(
            CONF_NAME, default=SCHEMA_HINT_QUERY_NAME
        ): selector.TextSelector(),
        vol.Required(CONF_QUERY, default=SCHEMA_HINT_QUERY): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT, multiline=True
            )
        ),
        vol.Required(CONF_ICON, default=SCHEMA_HINT_ICON): selector.IconSelector(),
        vol.Required(
            CONF_STATE_CLASS, default=SensorStateClass.MEASUREMENT
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=state_class, label=state_class)
                    for state_class in SensorStateClass
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(CONF_DEVICE_CLASS, default=""): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    *[
                        selector.SelectOptionDict(
                            value=device_class, label=device_class
                        )
                        for device_class in SensorDeviceClass
                    ],
                    selector.SelectOptionDict(value="", label=""),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=""): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
    }
)


class PrometheusConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Prometheus Sensors."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, _config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this handler."""
        return {"entity": SubentryFlowHandler}

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    host=user_input[CONF_HOST],
                    session=async_create_clientsession(
                        self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]
                    ),
                )
            except PrometheusApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except PrometheusApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except PrometheusApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self._async_handle_discovery_without_unique_id()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=SCHEMA_CONNECTION,
            errors=_errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        reconfigure_entry = self._get_reconfigure_entry()
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA_CONNECTION,
                reconfigure_entry.data,
            ),
        )

    async def _test_credentials(self, host: str, session: ClientSession) -> None:
        """Validate credentials."""
        client = PrometheusApiClient(
            host=host,
            session=session,
        )
        await client.async_get_metrics()

    async def _get_query_labels(
        self, host: str, session: ClientSession, query: str
    ) -> list[str]:
        """Validate query."""
        client = PrometheusApiClient(
            host=host,
            session=session,
        )
        return await client.async_get_query_labels(query)


class SubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow."""

    async def async_step_user(
        self, _user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to create a query subentry."""
        return await self.async_step_add_query()

    async def async_step_add_query(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a new sensor."""
        server_config: ConfigEntry | None = self.hass.config_entries.async_get_entry(
            self.handler[0]
        )
        if server_config is None:
            return self.async_abort(reason="server_not_configured")
        _errors = {}
        if user_input is not None:
            valid = await _client_call_wrapper(
                lambda: self._async_test_query(
                    host=server_config.data[CONF_HOST],
                    query=user_input[CONF_QUERY],
                    session=async_create_clientsession(
                        self.hass, verify_ssl=server_config.data[CONF_VERIFY_SSL]
                    ),
                )
            )

            if valid and valid.result:
                query = QueryDefinition(
                    name=user_input[CONF_NAME],
                    query=user_input[CONF_QUERY],
                    icon=user_input.get(CONF_ICON),
                    device_class=user_input.get(CONF_DEVICE_CLASS),
                    unit_of_measurement=user_input.get(CONF_UNIT_OF_MEASUREMENT),
                    state_class=user_input[CONF_STATE_CLASS],
                )
                return self.async_create_entry(
                    data=asdict(query), title=user_input[CONF_NAME]
                )
            if valid:
                _errors["base"] = "invalid_query"
            else:
                _errors["base"] = valid.error_code

        return self.async_show_form(
            step_id="add_query", data_schema=SCHEMA_QUERY, errors=_errors
        )

    async def async_step_reconfigure(
        self, _user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure a sensor subentry."""
        return await self.async_step_reconfigure_sensor()

    async def async_step_reconfigure_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure a sensor."""
        _errors = {}
        reconfigure_data = self._get_reconfigure_subentry()
        server_config = self._get_entry()
        if user_input is not None:
            valid = await _client_call_wrapper(
                lambda: self._async_test_query(
                    host=server_config.data[CONF_HOST],
                    query=user_input[CONF_QUERY],
                    session=async_create_clientsession(
                        self.hass, verify_ssl=server_config.data[CONF_VERIFY_SSL]
                    ),
                )
            )

            if valid and valid.result:
                query = QueryDefinition(
                    name=user_input[CONF_NAME],
                    query=user_input[CONF_QUERY],
                    icon=user_input.get(CONF_ICON),
                    device_class=user_input.get(CONF_DEVICE_CLASS),
                    unit_of_measurement=user_input.get(CONF_UNIT_OF_MEASUREMENT),
                    state_class=user_input[CONF_STATE_CLASS],
                )
                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    data=asdict(query),
                    title=user_input[CONF_NAME],
                )
            if valid:
                _errors["base"] = "invalid_query"
            else:
                _errors["base"] = valid.error_code

        return self.async_show_form(
            step_id="reconfigure_sensor",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA_QUERY, reconfigure_data.data
            ),
            errors=_errors,
        )

    async def _async_test_query(
        self, host: str, session: ClientSession, query: str
    ) -> bool:
        client = PrometheusApiClient(host=host, session=session)
        return await client.async_test_query_result_size(query)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Prometheus Sensors."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_menu(
            menu_options=["none"],
        )

    async def async_step_none(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        return self.async_abort(reason="none")


T = TypeVar("T")


@dataclass
class _ResultOrError(Generic[T]):
    result: T | None = None
    error_code: str | None = None

    def __init__(self, error_code: str | None = None, result: T | None = None) -> None:
        self.error_code = error_code
        self.result = result

    def __bool__(self) -> bool:
        return self.error_code is None


async def _client_call_wrapper(
    func: Callable[[], Awaitable[Any]],
) -> _ResultOrError:
    """Wrap client calls to handle exceptions."""
    try:
        return _ResultOrError(result=await func())
    except PrometheusApiClientError as err:
        return _ResultOrError(error_code=err.error_code)
