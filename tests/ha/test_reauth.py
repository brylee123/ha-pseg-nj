"""Native reauthentication and reconfiguration flows."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pseg_nj.const import CONF_COOKIE, CONF_LABEL, CONF_METER, DOMAIN


async def test_reauth_can_disable_cloud_without_changing_identity(
    hass: HomeAssistant,
) -> None:
    """CSV-only recovery keeps the same entry and meter/statistic identifiers."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="00123",
        data={
            CONF_LABEL: "electricity",
            CONF_METER: "00123",
            CONF_COOKIE: "session=old",
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"
    with patch("custom_components.pseg_nj.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_COOKIE: ""}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_COOKIE] == ""
    assert entry.unique_id == "00123"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
