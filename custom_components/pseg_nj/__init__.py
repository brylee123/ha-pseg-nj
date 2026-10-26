"""The PSE&G NJ electricity integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_COOKIE, DOMAIN
from .coordinator import PsegConfigEntry, PsegCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register actions once, independently of loaded entries."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PsegConfigEntry) -> bool:
    """Restore and refresh before forwarding the sensor platform."""
    coordinator = PsegCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await coordinator.async_shutdown()
        raise
    entry.runtime_data = coordinator
    if coordinator.client is not None:
        # Recorder backfill must continue even if all diagnostic entities are disabled.
        entry.async_on_unload(coordinator.async_add_listener(lambda: None))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PsegConfigEntry) -> bool:
    """Unload entities and stop polling and the isolated HTTP session."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_shutdown()
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Move v1 cookie options to v2 data, preserving IDs and ledger."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        data = dict(entry.data)
        data[CONF_COOKIE] = entry.options.get(CONF_COOKIE, "")
        options = {
            key: value for key, value in entry.options.items() if key != CONF_COOKIE
        }
        hass.config_entries.async_update_entry(
            entry, data=data, options=options, version=2
        )
    return True
