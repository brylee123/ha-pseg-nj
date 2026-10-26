"""Config, reconfigure and reauthentication flows for PSE&G NJ."""

import re
from typing import Any

import probatio as vol
from aiohttp import CookieJar
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from pseg_mymeter.client import PsegClient
from pseg_mymeter.data import meter_id
from pseg_mymeter.exceptions import (
    CannotConnect,
    InvalidResponse,
    MeterNotFound,
    SessionExpired,
)

from .const import CONF_COOKIE, CONF_LABEL, CONF_METER, DOMAIN


def _cookie_field() -> selector.TextSelector:
    """Mask credentials in the form."""
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )


class PsegConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a unique meter and validate optional session credentials."""

    VERSION = 2

    async def _async_validate_cookie(self, cookie: str, meter: str) -> str | None:
        """Read the export form to validate credentials, then close the session."""
        if not cookie:
            return None  # Offline CSV mode intentionally has no remote prerequisite.
        session = async_create_clientsession(self.hass, cookie_jar=CookieJar())
        try:
            client = PsegClient(session, cookie, meter)
            await client.async_validate_session()
        except SessionExpired:
            return "invalid_auth"
        except CannotConnect:
            return "cannot_connect"
        except MeterNotFound:
            return "meter_not_found"
        except InvalidResponse:
            return "invalid_response"
        finally:
            await session.close()
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial user setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            label = user_input[CONF_LABEL].strip().lower()
            meter = meter_id(user_input[CONF_METER])
            cookie = user_input.get(CONF_COOKIE, "").strip()
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", label):
                errors[CONF_LABEL] = "invalid_label"
            elif not meter:
                errors[CONF_METER] = "invalid_meter"
            else:
                await self.async_set_unique_id(meter)
                self._abort_if_unique_id_configured()
                if any(
                    entry.data[CONF_LABEL] == label
                    for entry in self._async_current_entries()
                ):
                    errors[CONF_LABEL] = "label_used"
                elif error := await self._async_validate_cookie(cookie, meter):
                    errors["base"] = error
                else:
                    return self.async_create_entry(
                        title=f"PSE&G NJ {label}",
                        data={
                            CONF_LABEL: label,
                            CONF_METER: meter,
                            CONF_COOKIE: cookie,
                        },
                    )
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LABEL, default="electricity"): str,
                    vol.Required(CONF_METER): str,
                    vol.Optional(CONF_COOKIE, default=""): _cookie_field(),
                }
            ),
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication for an expired session."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate a replacement session or explicitly select CSV-only mode."""
        return await self._async_credentials("reauth_confirm", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change credentials without changing meter/statistic identity."""
        return await self._async_credentials("reconfigure", user_input)

    async def _async_credentials(
        self, step: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Share credential validation and reload behavior."""
        entry = (
            self._get_reauth_entry()
            if step == "reauth_confirm"
            else self._get_reconfigure_entry()
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            cookie = user_input.get(CONF_COOKIE, "").strip()
            if error := await self._async_validate_cookie(
                cookie, entry.data[CONF_METER]
            ):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_COOKIE: cookie}
                )
        return self.async_show_form(
            step_id=step,
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_COOKIE, default=""): _cookie_field(),
                }
            ),
        )
