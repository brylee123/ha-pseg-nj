"""Home Assistant action registration and validation."""

from pathlib import Path
from typing import cast

import probatio as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from pseg_mymeter.exceptions import InvalidUsage

from .const import DOMAIN, SERVICE_IMPORT_CSV
from .coordinator import PsegConfigEntry
from .statistics import read_import

IMPORT_SCHEMA = vol.Schema(
    {vol.Required("entry_id"): cv.string, vol.Required("filename"): cv.string}
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the action once at integration setup."""

    async def async_import_csv(call: ServiceCall) -> ServiceResponse:
        """Import a local Hourly export into a loaded entry."""
        entry = hass.config_entries.async_get_entry(call.data["entry_id"])
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_loaded"
            )
        coordinator = cast(PsegConfigEntry, entry).runtime_data
        try:
            text = await hass.async_add_executor_job(
                read_import, Path(hass.config.path(DOMAIN)), call.data["filename"]
            )
            result = await coordinator.statistics.async_import(text)
        except InvalidUsage as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=err.translation_key
            ) from err
        except (OSError, UnicodeError) as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="read_failed"
            ) from err
        # Offline imports must not reset cloud authentication/availability errors.
        coordinator.data = coordinator.status()
        coordinator.async_update_listeners()
        return dict(result)

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_CSV,
        async_import_csv,
        schema=IMPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
