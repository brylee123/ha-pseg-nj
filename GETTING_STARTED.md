# Home Assistant Getting Started alignment

This audit follows all five pages in [Getting Started](https://contributors.home-assistant.io/core/integrations/). It separates completed code changes from publication and live tests that have not been performed.

## 1. How an integration fits in

Completed: the HA adapter translates a library into config entries, entities and statistics. `pseg_nj` remains the permanent domain. One config entry represents one meter. The implementation uses one sensor platform for diagnostic values, plus external hourly recorder statistics for actual utility history. Delayed usage is imported at its measurement time; a current sensor reading is not used to impersonate historical measurements.

## 2. Tutorial

Implemented the tutorial's main architecture:

* Config flow with unique meter IDs and optional session validation before entry creation. CSV-only mode intentionally has no remote prerequisite.
* Typed `ConfigEntry[PsegCoordinator]` and `entry.runtime_data`; no integration runtime objects under `hass.data`.
* `DataUpdateCoordinator` in `coordinator.py`, `_async_setup`, first refresh before platform setup, a fixed 12-hour cloud interval, and native `UpdateFailed`/`ConfigEntryAuthFailed` behavior.
* `entity.py` base class, service-device grouping, `CoordinatorEntity`, stable entity IDs, entity descriptions, translation keys and lifecycle-managed subscriptions.
* Translated service errors, credential reauthentication/reconfiguration flows, diagnostics that whitelist only non-sensitive counts, and explicit session cleanup.
* Actions registered once in `async_setup` via `services.py`; statistics persistence and import logic live in `statistics.py`.
* A v1→v2 config migration retains existing entry/meter/statistic IDs and the v0.1 ledger.
* Local library tests, Ruff checks, source compilation, release verification, a CI workflow, and native HA test cases for setup, unloading, migration, configuration and duplicate/auth failures.

Not claimed: a Bronze/Silver quality tier, full integration test coverage, running HAOS verification, or core acceptance. `quality_scale.yaml` is a self-audit with remaining work marked todo.

## 3. Build a Python library

Completed: independent `library/` project with `pyproject.toml`, typed async session injection, safe domain errors, form parsing, meter identity checks, Hourly CSV models, standalone tests, and wheel/source-distribution builds. No Home Assistant imports exist in the library.

Published: `pseg-nj-mymeter==0.2.0` is available on PyPI under MIT, authored by `brylee123`. The integration manifest pins that version and all HA adapters import `pseg_mymeter` directly. The vendor bundle and sync script have been removed. The local suite tests the installed distribution. The source repository and issue tracker are configured at https://github.com/brylee123/ha-pseg-nj. Release tags and automated publishing remain pending for full Core dependency readiness.

## 4. Create an integration

Completed: maintain custom-integration scope while the portal behavior is being tested; keep one platform; implement the normal setup/flow/coordinator/entity boundaries and preserve the domain.

The official scaffold creates a *new* integration in a Home Assistant Core checkout. This workspace already contained the custom integration. I refactored the existing code into that scaffold's structure rather than generating a second domain or replacing functionality with placeholders. The scaffold is not rerun for the existing domain. Native HA tests now pass on Linux; official tooling attempts and results are recorded in VALIDATION.md. No Core development container has been run. The earlier package-index check used Python 3.13 and therefore filtered out HA 2026.10, which requires Python >=3.14.2. A dedicated Linux Python 3.14.2 environment and the exact HA 2026.10.0 source checkout are now available; see VALIDATION.md for the actual tooling/test results.

## 5. File structure

Completed: required `manifest.json`/`__init__.py`, `const.py`, `config_flow.py`, `coordinator.py`, `entity.py`, `sensor.py`, `services.py`/`services.yaml`, `statistics.py`, `diagnostics.py`, `strings.json`, `translations/en.json`, `icons.json` and `quality_scale.yaml`. The standalone client is outside the HA adapter's source boundary and installed from PyPI through the manifest requirement.

## Core contribution and live verification checklist

1. Use the matching Core development environment and install the independently published library (or an editable local checkout for development).
2. Adapt `custom_components/pseg_nj` to `homeassistant/components/pseg_nj`; retain the existing direct `pseg_mymeter` imports and exact manifest requirement.
3. Fill actual owner/documentation/issue-tracker/release metadata. Add approved brand assets.
4. Run the real scaffold only if generating a fresh integration; retain and review the implemented code rather than duplicating its domain.
5. Completed official hassfest on the custom integration path: zero invalid integrations and no warnings. A future Core contribution needs its own full Core checks.
6. Completed `python -m script.translations develop --integration pseg_nj`: generated English translations match.
7. Nine native HA tests pass, including reauthentication, service replay, diagnostics and Recorder database writes. Broader network recovery coverage remains.
8. Run HA, configure CSV mode, import a short Hourly sample twice, and compare a complete day's Energy total with the portal. Then test a current session, expiry and reconnection.

The source/ZIP includes no production credentials or raw usage exports. The standalone library has been published on PyPI. The GitHub repository hosts the custom integration for HACS installation. It has not been installed on the user's Raspberry Pi.

## Historical granularity

HA's short-term statistics are five-minute summaries; long-term statistics are hourly. For external utility backfill, the supported `async_add_external_statistics` route explicitly requires timestamps at the top of an hour and writes hourly statistics. There is no supported public 15-minute external-backfill route in the checked HA 2026.10 recorder API. This integration therefore downloads/imports Hourly exports. It does not write private recorder tables or replay old usage as live states.

Sources: [statistics overview](https://contributors.home-assistant.io/data/reference/statistics/), [HA 2026.10 import implementation](https://github.com/home-assistant/core/blob/2026.10.0/homeassistant/components/recorder/statistics.py).
