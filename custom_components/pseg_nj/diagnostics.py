"""Whitelisted diagnostics without credentials, meter IDs or usage history."""

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import PsegConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PsegConfigEntry
) -> dict[str, Any]:
    """Return operational counts, never the config-entry data/options."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        return {"config_version": entry.version, "loaded": False}
    status = coordinator.status()
    return {
        "config_version": entry.version,
        "mode": "session" if coordinator.client is not None else "csv",
        "last_update_success": coordinator.last_update_success,
        "imported_hours": status.imported_hours,
        "last_import": status.last_import.isoformat() if status.last_import else None,
    }
