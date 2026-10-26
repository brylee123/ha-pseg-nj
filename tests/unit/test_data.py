"""Standalone data tests; no Home Assistant or account fixtures."""

import unittest
from datetime import UTC, date, datetime

from pseg_mymeter.client import download_fields
from pseg_mymeter.data import build_statistics, parse_csv
from pseg_mymeter.exceptions import InvalidUsage, MeterNotFound, SessionExpired


def export(rows: list[tuple[str, str | int]], meter: bool = True) -> str:
    """Build a synthetic hourly export."""
    header = "Start,kWh,Meter\n" if meter else "Start,kWh\n"
    return header + "\n".join(
        f'"{stamp}",{value}' + (",Meter #00123" if meter else "")
        for stamp, value in rows
    )


def form() -> dict:
    """Create an export form with internal IDs different from meter numbers."""
    return {
        "AjaxResults": [
            {
                "Value": """<form id="downloadOptions">
    <input name="__RequestVerificationToken" value="synthetic-token">
    <input name="Meters[0].Value" value="9876543">
    <label for="Meters_0__Selected">Meter #00123 (Residential Service (RS))</label>
    <input type="checkbox" name="Meters[0].Selected" checked value="true">
    <input type="hidden" name="Meters[0].Selected" value="false">
    <input name="Meters[1].Value" value="1111111">
    <label for="Meters_1__Selected">Meter #00999 (Residential Service (RS))</label>
    <input type="checkbox" name="Meters[1].Selected" checked value="true">
    <select name="SelectedInterval"><option value="3">15-Minute</option><option selected value="5">Hourly</option></select>
    </form>"""
            }
        ]
    }


class DataTests(unittest.TestCase):
    """Validate time placement, import behavior and resolution."""

    def test_hourly_values_keep_original_utc_hour(self):
        hours, report = parse_csv(
            "\ufeff"
            + export(
                [("10/01/2026 1:00:00 AM", ".3"), ("10/01/2026 2:00:00 AM", ".4")]
            ),
            "00123",
        )
        self.assertEqual(hours["2026-10-01T05:00:00+00:00"], "0.3")
        self.assertEqual(report["hours"], 2)

    def test_subhourly_daily_and_billing_exports_rejected(self):
        for text in [
            export([("10/01/2026 1:00:00 AM", 1), ("10/01/2026 1:15:00 AM", 1)]),
            export([("10/01/2026 1:00:00 AM", 1), ("10/01/2026 1:30:00 AM", 1)]),
            export([("10/01/2026 12:00:00 AM", 20), ("10/02/2026 12:00:00 AM", 30)]),
            "End,kWh\n10/01/2026,100",
        ]:
            with self.subTest(text=text), self.assertRaises(InvalidUsage):
                parse_csv(text, "00123")

    def test_repeat_correction_and_earlier_backfill(self):
        hours, _ = parse_csv(
            export([("10/01/2026 1:00:00 AM", 1), ("10/01/2026 2:00:00 AM", 2)]),
            "00123",
        )
        fix = {"2026-10-01T05:00:00+00:00": "3"}
        now = datetime(2027, 1, 1, tzinfo=UTC)
        self.assertEqual(
            build_statistics(hours, now), build_statistics(hours | hours, now)
        )
        self.assertEqual(
            [row["sum"] for row in build_statistics(hours | fix, now)], [0, 3, 5]
        )
        older = {"2026-10-01T04:00:00+00:00": "4"}
        self.assertEqual(
            [row["sum"] for row in build_statistics(hours | fix | older, now)],
            [0, 4, 7, 9],
        )

    def test_gap_anchor_remains_monotonic_after_earlier_backfill(self):
        now = datetime(2027, 1, 1, tzinfo=UTC)
        hours = {"2026-10-01T07:00:00+00:00": "2"}
        anchor = build_statistics(hours, now)[0]["start"]
        revised = build_statistics(hours | {"2026-10-01T04:00:00+00:00": "3"}, now)
        self.assertEqual(
            next(row["sum"] for row in revised if row["start"] == anchor), 3
        )
        self.assertEqual([row["sum"] for row in revised], [0, 3, 3, 5])

    def test_dst_times_are_skipped_without_guessing(self):
        for ambiguous in ("11/01/2026 1:00:00 AM", "03/08/2026 2:00:00 AM"):
            hours, report = parse_csv(
                export(
                    [
                        (ambiguous, 10),
                        ("10/01/2026 1:00:00 AM", 1),
                        ("10/01/2026 2:00:00 AM", 2),
                    ]
                ),
                "00123",
            )
            self.assertEqual(report["dst_rows_skipped"], 1)
            self.assertEqual(sum(float(v) for v in hours.values()), 3)

    def test_malformed_duplicate_and_nonfinite_values_rejected(self):
        for value in ("NaN", "Infinity", "-1", "garbage", "", "1e999"):
            with self.subTest(value=value), self.assertRaises(InvalidUsage):
                parse_csv(export([("10/01/2026 1:00:00 AM", value)]), "00123")
        for text in [
            export([("10/01/2026 1:00:00 AM", 1)] * 2),
            "Start,kWh,kWh\nx,1,2",
        ]:
            with self.assertRaises(InvalidUsage):
                parse_csv(text, "00123")

    def test_meter_filter_and_optional_identity_columns(self):
        text = export([("10/01/2026 1:00:00 AM", 1), ("10/01/2026 2:00:00 AM", 2)])
        text += '\n"10/01/2026 1:00:00 AM",5,Meter #00999'
        hours, report = parse_csv(text, "00123")
        self.assertEqual(report["other_meter_rows"], 1)
        self.assertEqual(sum(float(v) for v in hours.values()), 3)
        self.assertEqual(
            len(
                parse_csv(
                    export(
                        [("10/01/2026 1:00:00 AM", 1), ("10/01/2026 2:00:00 AM", 2)],
                        False,
                    ),
                    "00123",
                )[0]
            ),
            2,
        )

    def test_open_hours_not_published(self):
        hours = {"2026-10-01T05:00:00+00:00": "1"}
        self.assertEqual(
            build_statistics(hours, datetime(2026, 10, 1, 5, 30, tzinfo=UTC)), []
        )


class FormTests(unittest.TestCase):
    """Verify meter identity, current tokens and fixed hourly resolution."""

    def test_one_selected_meter_hourly_and_dates(self):
        fields = download_fields(form(), "00123", date(2026, 10, 1), date(2026, 10, 7))
        self.assertEqual(
            [x for x in fields if x[0].endswith(".Selected")],
            [("Meters[0].Selected", "true")],
        )
        values = dict(fields)
        self.assertEqual(values["SelectedInterval"], "5")
        self.assertEqual(values["SelectedUsageType"], "1")
        self.assertEqual(values["Start"], "2026-10-01")
        self.assertEqual(values["__RequestVerificationToken"], "synthetic-token")

    def test_wrong_meter_and_missing_auth_form(self):
        with self.assertRaises(SessionExpired):
            download_fields({}, "00123", date.today(), date.today())
        with self.assertRaises(MeterNotFound):
            download_fields(form(), "00888", date.today(), date.today())
