"""Coordinate utility polling and expose local ledger status."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import override

from aiohttp import CookieJar
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pseg_mymeter.client import PsegClient
from pseg_mymeter.exceptions import (
    CannotConnect,
    InvalidResponse,
    InvalidUsage,
    MeterNotFound,
    SessionExpired,
)

from .const import CONF_COOKIE, CONF_LABEL, CONF_METER, DOMAIN, UPDATE_INTERVAL
from .statistics import PsegStatistics

_LOGGER = logging.getLogger(__name__)

type PsegConfigEntry = ConfigEntry[PsegCoordinator]


@dataclass(frozen=True)
class PsegStatus:
    """Non-sensitive coordinator data for entities."""

    imported_hours: int
    last_import: datetime | None


class PsegCoordinator(DataUpdateCoordinator[PsegStatus]):
    """Poll at a fixed interval only when a session is configured."""

    config_entry: PsegConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PsegConfigEntry) -> None:
        """Initialize typed runtime objects without I/O."""
        cookie = entry.data.get(CONF_COOKIE, "")
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL if cookie else None,
            always_update=False,
        )
        self.statistics = PsegStatistics(
            hass, entry.entry_id, entry.data[CONF_LABEL], entry.data[CONF_METER]
        )
        self.client: PsegClient | None = None

    @override
    async def _async_setup(self) -> None:
        """Load saved state once before the first refresh."""
        await self.statistics.async_load()
        if cookie := self.config_entry.data.get(CONF_COOKIE, ""):
            session = async_create_clientsession(self.hass, cookie_jar=CookieJar())
            try:
                self.client = PsegClient(
                    session, cookie, self.config_entry.data[CONF_METER]
                )
            except SessionExpired as err:
                await session.close()
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN, translation_key="session_expired"
                ) from err

    def status(self) -> PsegStatus:
        """Return a status snapshot from the authoritative ledger."""
        return PsegStatus(len(self.statistics.hours), self.statistics.last_import)

    @override
    async def _async_update_data(self) -> PsegStatus:
        """Download hourly usage or return status in CSV-only mode."""
        if self.client is not None:
            try:
                text = await self.client.async_usage()
                await self.statistics.async_import(text)
            except SessionExpired as err:
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN, translation_key="session_expired"
                ) from err
            except CannotConnect as err:
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="cannot_connect"
                ) from err
            except (InvalidResponse, InvalidUsage, MeterNotFound) as err:
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="invalid_response"
                ) from err
            except OSError as err:
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="storage_failed"
                ) from err
        return self.status()

    @override
    async def async_shutdown(self) -> None:
        """Cancel polling and close this entry's isolated session."""
        await super().async_shutdown()
        if self.client is not None:
            await self.client.async_close()
