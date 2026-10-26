"""Durable usage ledger and Home Assistant recorder adapter."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util.unit_conversion import EnergyConverter
from pseg_mymeter.data import (
    HourLedger,
    ImportReport,
    build_statistics,
    parse_csv,
)
from pseg_mymeter.exceptions import InvalidUsage

from .const import DOMAIN, MAX_IMPORT_BYTES


class StoredLedger(TypedDict):
    """Storage format compatible with the v0.1 ledger."""

    hours: HourLedger


class ImportResult(ImportReport):
    """Counts returned by the import action."""

    hours_changed: int
    ledger_hours: int


def read_import(root: Path, filename: str) -> str:
    """Read a CSV directly inside the configured import directory."""
    root = root.resolve()
    path = (root / filename).resolve()
    if (
        Path(filename).name != filename
        or path.parent != root
        or path.suffix.lower() != ".csv"
    ):
        raise InvalidUsage("invalid_filename")
    if path.stat().st_size > MAX_IMPORT_BYTES:
        raise InvalidUsage("file_too_large")
    return path.read_text(encoding="utf-8-sig")


class PsegStatistics:
    """Serialize imports, persist validated hours, and queue recorder writes."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, label: str, meter: str
    ) -> None:
        """Initialize without I/O."""
        self.hass = hass
        self.label = label
        self.meter = meter
        self.store = Store[StoredLedger](hass, 1, f"{DOMAIN}_{entry_id}")
        self.hours: HourLedger = {}
        self.last_import: datetime | None = None
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Replay the saved ledger after any interrupted recorder writes."""
        saved = await self.store.async_load()
        self.hours = saved["hours"] if saved else {}
        self.async_publish()

    @callback
    def async_publish(self) -> None:
        """Queue hourly statistics with explicit metadata."""
        rows = build_statistics(self.hours)
        if not rows:
            return
        metadata: StatisticMetaData = {
            "statistic_id": f"{DOMAIN}:{self.label}_energy",
            "source": DOMAIN,
            "name": f"PSE&G NJ {self.label} electricity",
            "has_sum": True,
            "mean_type": StatisticMeanType.NONE,
            "unit_class": EnergyConverter.UNIT_CLASS,
            "unit_of_measurement": "kWh",
        }
        async_add_external_statistics(
            self.hass, metadata, cast(list[StatisticData], rows)
        )

    async def async_import(self, text: str) -> ImportResult:
        """Validate a complete hourly export before changing saved data."""
        hours, report = await self.hass.async_add_executor_job(
            parse_csv, text, self.meter
        )
        async with self._lock:
            changed = sum(self.hours.get(key) != value for key, value in hours.items())
            if changed:
                merged = self.hours | hours
                await self.store.async_save({"hours": merged})
                self.hours = merged
            # Replay unchanged imports too: an earlier queued DB write may have
            # failed, or a previously open hour may now have finished.
            self.async_publish()
            self.last_import = datetime.now(UTC)
            return cast(
                ImportResult,
                report | {"hours_changed": changed, "ledger_hours": len(self.hours)},
            )
