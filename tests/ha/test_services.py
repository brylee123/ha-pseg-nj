"""Native action/statistics and diagnostics tests."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pseg_nj.const import CONF_COOKIE, CONF_LABEL, CONF_METER, DOMAIN
from custom_components.pseg_nj.diagnostics import async_get_config_entry_diagnostics

CSV = 'Start,kWh,Meter\n"10/01/2025 1:00:00 AM",1.25,Meter #00123\n"10/01/2025 2:00:00 AM",2.50,Meter #00123\n'


async def test_import_replay_and_diagnostics(hass: HomeAssistant) -> None:
    """Repeated imports replace statistics and diagnostics omit credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="00123",
        data={CONF_LABEL: "electricity", CONF_METER: "00123", CONF_COOKIE: ""},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    with (
        patch("custom_components.pseg_nj.services.read_import", return_value=CSV),
        patch(
            "custom_components.pseg_nj.statistics.async_add_external_statistics"
        ) as recorder,
    ):
        first = await hass.services.async_call(
            DOMAIN,
            "import_csv",
            {"entry_id": entry.entry_id, "filename": "usage.csv"},
            blocking=True,
            return_response=True,
        )
        repeated = await hass.services.async_call(
            DOMAIN,
            "import_csv",
            {"entry_id": entry.entry_id, "filename": "usage.csv"},
            blocking=True,
            return_response=True,
        )
    assert first["hours_changed"] == 2
    assert repeated["hours_changed"] == 0
    assert recorder.call_count == 2
    metadata, rows = recorder.call_args.args[1:]
    assert metadata["statistic_id"] == "pseg_nj:electricity_energy"
    assert rows[-1]["sum"] == 3.75
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["imported_hours"] == 2
    assert CONF_COOKIE not in diagnostics
    assert CONF_METER not in diagnostics
    assert "hours" not in diagnostics


async def test_unloaded_entry_action_error(hass: HomeAssistant) -> None:
    """Actions cannot import into an unloaded meter entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="00123",
        data={CONF_LABEL: "electricity", CONF_METER: "00123", CONF_COOKIE: ""},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "import_csv",
            {"entry_id": entry.entry_id, "filename": "usage.csv"},
            blocking=True,
            return_response=True,
        )


async def test_recorder_round_trip(hass: HomeAssistant) -> None:
    """The public recorder API retains measured totals after a repeated import."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="00123",
        data={CONF_LABEL: "electricity", CONF_METER: "00123", CONF_COOKIE: ""},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    with patch("custom_components.pseg_nj.services.read_import", return_value=CSV):
        for _ in range(2):
            await hass.services.async_call(
                DOMAIN,
                "import_csv",
                {"entry_id": entry.entry_id, "filename": "usage.csv"},
                blocking=True,
                return_response=True,
            )
            await get_instance(hass).async_block_till_done()
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        datetime(2025, 10, 1, tzinfo=UTC),
        datetime(2025, 10, 2, tzinfo=UTC),
        {"pseg_nj:electricity_energy"},
        "hour",
        None,
        {"sum"},
    )
    rows = result["pseg_nj:electricity_energy"]
    assert [row["sum"] for row in rows] == [0.0, 1.25, 3.75]
