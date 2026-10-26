"""Common coordinator entity for the PSE&G NJ service."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LABEL, DOMAIN
from .coordinator import PsegCoordinator


class PsegEntity(CoordinatorEntity[PsegCoordinator]):
    """Group entities under one service device per meter entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PsegCoordinator) -> None:
        """Initialize shared device identity and coordinator subscription."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"PSE&G NJ {entry.data[CONF_LABEL]}",
            manufacturer="PSE&G",
            model="MyMeter electricity usage",
            entry_type=DeviceEntryType.SERVICE,
        )
