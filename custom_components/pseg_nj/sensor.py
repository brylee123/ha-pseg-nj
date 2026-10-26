"""Diagnostic sensor platform for imported electricity history."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PsegConfigEntry, PsegCoordinator
from .entity import PsegEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PsegSensorDescription(SensorEntityDescription):
    """Describe a diagnostic value from the coordinator."""

    value_fn: Callable[[PsegCoordinator], str | int | datetime | None]
    always_available: bool = False


SENSORS: tuple[PsegSensorDescription, ...] = (
    PsegSensorDescription(
        key="import_entry_id",
        translation_key="import_entry_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        always_available=True,
        value_fn=lambda coordinator: coordinator.config_entry.entry_id,
    ),
    PsegSensorDescription(
        key="imported_hours",
        translation_key="imported_hours",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.data.imported_hours,
    ),
    PsegSensorDescription(
        key="last_import",
        translation_key="last_import",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.data.last_import,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PsegConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add diagnostic entities from typed runtime data."""
    async_add_entities(
        PsegSensor(entry.runtime_data, description) for description in SENSORS
    )


class PsegSensor(PsegEntity, SensorEntity):
    """A translated, coordinator-backed diagnostic sensor."""

    entity_description: PsegSensorDescription

    def __init__(
        self, coordinator: PsegCoordinator, description: PsegSensorDescription
    ) -> None:
        """Initialize stable entity IDs, retaining the original entry-ID sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    @override
    def native_value(self) -> str | int | datetime | None:
        """Return the current diagnostic value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    @override
    def available(self) -> bool:
        """Keep the static action ID accessible during a cloud failure."""
        return self.entity_description.always_available or super().available
