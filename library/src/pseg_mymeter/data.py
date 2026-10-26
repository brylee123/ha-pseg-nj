"""Parse hourly MyMeter exports without depending on Home Assistant."""

import csv
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import TypedDict
from zoneinfo import ZoneInfo

from .exceptions import InvalidUsage

type HourLedger = dict[str, str]


class ImportReport(TypedDict):
    """Aggregate import counts without personal data."""

    rows: int
    other_meter_rows: int
    dst_rows_skipped: int
    hours: int


def meter_id(value: str) -> str:
    """Normalize a displayed meter number, preserving leading zeroes."""
    return re.sub(r"[^0-9]", "", value)


def parse_csv(text: str, meter: str) -> tuple[HourLedger, ImportReport]:
    """Parse Hourly exports; reject sub-hourly, daily and billing data."""
    reader = csv.DictReader(StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames or not {"Start", "kWh"} <= set(reader.fieldnames):
        raise InvalidUsage("invalid_columns")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise InvalidUsage("invalid_columns")
    expected_meter = meter_id(meter)
    if not expected_meter:
        raise InvalidUsage("invalid_meter")
    zone = ZoneInfo("America/New_York")
    hours: HourLedger = {}
    seen: set[datetime] = set()
    report: ImportReport = {
        "rows": 0,
        "other_meter_rows": 0,
        "dst_rows_skipped": 0,
        "hours": 0,
    }
    for row in reader:
        report["rows"] += 1
        if None in row or any(value is None for value in row.values()):
            raise InvalidUsage("invalid_row")
        if "Meter" in row and meter_id(row["Meter"]) != expected_meter:
            report["other_meter_rows"] += 1
            continue
        try:
            local = datetime.strptime(row["Start"].strip(), "%m/%d/%Y %I:%M:%S %p")
            value = Decimal(row["kWh"].replace(",", "").strip())
        except (ValueError, InvalidOperation) as err:
            raise InvalidUsage("invalid_row") from err
        if not value.is_finite() or not 0 <= value <= Decimal("1000000000"):
            raise InvalidUsage("invalid_value")
        if local.second or local.minute:
            raise InvalidUsage("hourly_required")
        if local in seen:
            raise InvalidUsage("duplicate_time")
        seen.add(local)
        candidates: set[datetime] = set()
        for fold in (0, 1):
            candidate = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            if candidate.astimezone(zone).replace(tzinfo=None) == local:
                candidates.add(candidate)
        if len(candidates) != 1:
            report["dst_rows_skipped"] += 1
            continue
        hours[candidates.pop().isoformat()] = str(value)
    starts = sorted(datetime.fromisoformat(key) for key in hours)
    if not starts:
        raise InvalidUsage("no_hours")
    # Headers alone do not distinguish daily/monthly exports. Require an hourly
    # pair to establish resolution while allowing gaps elsewhere in the file.
    if not any(b - a == timedelta(hours=1) for a, b in zip(starts, starts[1:])):
        raise InvalidUsage("hourly_required")
    report["hours"] = len(hours)
    return hours, report


class HourStatistic(TypedDict, total=False):
    """Standalone recorder payload before the Home Assistant adapter."""

    start: datetime
    state: float
    sum: float


def build_statistics(
    hours: HourLedger, now: datetime | None = None
) -> list[HourStatistic]:
    """Build stable sums with baseline markers before contiguous segments."""
    now = now or datetime.now(UTC)
    total = Decimal(0)
    previous: datetime | None = None
    result: list[HourStatistic] = []
    for timestamp in sorted(hours):
        start = datetime.fromisoformat(timestamp)
        if start + timedelta(hours=1) > now:
            continue
        if previous is None or previous + timedelta(hours=1) != start:
            result.append({"start": start - timedelta(hours=1), "sum": float(total)})
        value = Decimal(hours[timestamp])
        total += value
        result.append({"start": start, "state": float(value), "sum": float(total)})
        previous = start
    return result
