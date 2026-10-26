"""Exercise ledger adapter behavior with explicit HA interface test doubles.

These tests are not a substitute for running the native tests/ha suite.
"""

import importlib
import sys
import tempfile
from enum import IntEnum
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from test_data import export


def load_adapter():
    """Load only statistics.py against small, explicit recorder/storage doubles."""
    modules = {}
    for name in (
        "homeassistant",
        "homeassistant.components",
        "homeassistant.components.recorder",
        "homeassistant.components.recorder.models",
        "homeassistant.components.recorder.statistics",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.storage",
        "homeassistant.util",
        "homeassistant.util.unit_conversion",
    ):
        module = ModuleType(name)
        module.__path__ = []
        modules[name] = module

    class MeanType(IntEnum):
        NONE = 0

    class Store:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, *args):
            self.saved = None
            self.fail = False

        async def async_load(self):
            return self.saved

        async def async_save(self, data):
            if self.fail:
                raise OSError("simulated disk full")
            self.saved = data

    recorder = modules["homeassistant.components.recorder.models"]
    recorder.StatisticData = dict
    recorder.StatisticMetaData = dict
    recorder.StatisticMeanType = MeanType
    calls = []
    modules[
        "homeassistant.components.recorder.statistics"
    ].async_add_external_statistics = lambda *args: calls.append(args)
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.core"].callback = lambda function: function
    modules["homeassistant.helpers.storage"].Store = Store
    modules["homeassistant.util.unit_conversion"].EnergyConverter = SimpleNamespace(
        UNIT_CLASS="energy"
    )
    package = ModuleType("adapter_test")
    package.__path__ = [
        str(Path(__file__).resolve().parents[2] / "custom_components/pseg_nj")
    ]
    modules["adapter_test"] = package
    with patch.dict(sys.modules, modules):
        adapter = importlib.import_module("adapter_test.statistics")
    return adapter, calls


class AdapterTests(IsolatedAsyncioTestCase):
    """Check atomicity, replay and import path boundaries."""

    @classmethod
    def setUpClass(cls):
        cls.adapter, cls.calls = load_adapter()

    def setUp(self):
        self.calls.clear()

    async def asyncSetUp(self):
        async def executor(function, *args):
            return function(*args)

        self.ledger = self.adapter.PsegStatistics(
            SimpleNamespace(async_add_executor_job=executor),
            "synthetic",
            "electricity",
            "00123",
        )
        self.text = export([("10/01/2025 1:00:00 AM", 1), ("10/01/2025 2:00:00 AM", 2)])

    async def test_repeat_is_idempotent_but_replays_recorder(self):
        first = await self.ledger.async_import(self.text)
        repeat = await self.ledger.async_import(self.text)
        self.assertEqual(first["hours_changed"], 2)
        self.assertEqual(repeat["hours_changed"], 0)
        self.assertEqual(self.calls[0][2], self.calls[1][2])
        self.assertEqual(self.calls[-1][1]["unit_class"], "energy")
        self.assertEqual(self.calls[-1][2][-1]["sum"], 3)

    async def test_disk_failure_does_not_mutate_or_publish(self):
        self.ledger.store.fail = True
        with self.assertRaises(OSError):
            await self.ledger.async_import(self.text)
        self.assertEqual(self.ledger.hours, {})
        self.assertEqual(self.calls, [])

    async def test_restart_replays_durable_ledger(self):
        await self.ledger.async_import(self.text)
        expected = self.calls[-1][2]
        self.ledger.hours = {}
        await self.ledger.async_load()
        self.assertEqual(self.calls[-1][2], expected)

    async def test_bad_export_is_atomic(self):
        await self.ledger.async_import(self.text)
        before = dict(self.ledger.hours)
        with self.assertRaises(ValueError):
            await self.ledger.async_import("End,kWh\n10/01/2025,100")
        self.assertEqual(self.ledger.hours, before)
        self.assertEqual(len(self.calls), 1)

    def test_file_paths_are_confined_to_import_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "usage.csv").write_text(self.text)
            self.assertEqual(self.adapter.read_import(root, "usage.csv"), self.text)
            for name in ("../usage.csv", "nested/usage.csv", "usage.txt"):
                with self.assertRaises(ValueError):
                    self.adapter.read_import(root, name)
