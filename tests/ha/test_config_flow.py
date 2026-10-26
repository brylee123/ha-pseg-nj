"""Native config-flow tests, pending a target-version HA test environment."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pseg_mymeter.exceptions import SessionExpired
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pseg_nj.const import CONF_COOKIE, CONF_LABEL, CONF_METER, DOMAIN


async def test_csv_only_config_flow(hass):
    """Offline setup should not require a portal request."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.pseg_nj.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_LABEL: "electricity",
                CONF_METER: "00123",
                CONF_COOKIE: "",
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_METER] == "00123"


async def test_invalid_session_shows_form_error(hass):
    """Rejected sessions must not create an entry."""
    with patch(
        "custom_components.pseg_nj.config_flow.PsegClient.async_validate_session",
        new=AsyncMock(side_effect=SessionExpired),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_LABEL: "electricity",
                CONF_METER: "00123",
                CONF_COOKIE: "session=synthetic",
            },
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_duplicate_meter_aborts(hass):
    """A second entry must not write the same meter statistics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="00123",
        version=2,
        data={CONF_LABEL: "electricity", CONF_METER: "00123", CONF_COOKIE: ""},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_LABEL: "another",
            CONF_METER: "00123",
            CONF_COOKIE: "",
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
