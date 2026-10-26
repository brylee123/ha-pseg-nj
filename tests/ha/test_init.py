"""Native setup/unload/migration contracts for the target HA environment."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pseg_nj import async_migrate_entry
from custom_components.pseg_nj.const import CONF_COOKIE, CONF_LABEL, CONF_METER, DOMAIN


async def test_csv_setup_and_unload(hass):
    """Typed runtime data and entities should unload cleanly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="00123",
        data={CONF_LABEL: "electricity", CONF_METER: "00123", CONF_COOKIE: ""},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.runtime_data.statistics.hours == {}
    assert entry.runtime_data.update_interval is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_v1_migration_keeps_identity_and_moves_cookie(hass):
    """Upgrade the released config schema without changing statistic IDs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="00123",
        data={CONF_LABEL: "electricity", CONF_METER: "00123"},
        options={CONF_COOKIE: "session=synthetic"},
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.unique_id == "00123"
    assert entry.data[CONF_COOKIE] == "session=synthetic"
    assert CONF_COOKIE not in entry.options
