# Validation — v0.2.1

## Completed locally

* Nine native HA 2026.10.4 tests pass on Linux Python 3.14.7, using
  pytest-homeassistant-custom-component 0.13.375. Configuration, setup/unload,
  migration, reauthentication, service replay, diagnostics and a real Recorder
  database round trip are covered. Repeated imports retain the expected total.
  Python 3.14.2 encountered an upstream mock annotation error during fixture
  setup; the supported newer patch runtime resolves it.

* 21 standalone library/transport and ledger-adapter tests, plus 10 value-case
  subtests. Adapter tests explicitly use HA interface doubles;
  they do not establish native HA runtime compatibility.
* Ruff lint/format checks; Python source compilation; JSON/YAML parsing;
  English translation parity; published dependency resolution; ZIP integrity.
* Independent MIT-licensed library wheel and source distribution published on PyPI as pseg-nj-mymeter 0.2.0; exact hashes and installation verified. Integration imports that installed version directly, with no vendored source.
* Hourly parsing, DST ambiguity handling, repeated imports and cumulative
  statistics verified. Private customer exports remain local and are excluded
  from the repository and release archives.
* Billing and sub-hourly exports rejected. Recorded NJ initialization response
  parsed correctly: 68 prepared form fields, exactly one selected meter via
  display-label-to-internal-ID mapping, current token, Hourly consumption.
* Typed runtime/coordinator/session/recorder interfaces checked against the
  referenced Home Assistant 2026.10 source. Native execution and official validation are reported separately below.

## Pending

* Complete config/reauth/network recovery coverage and target type checking.
* Live HA 2026.10/HAOS installation, Energy display and server acceptance of
  reconstructed requests using a current user-entered session.
* MFA/password login and session renewal (not implemented).
* Repository: https://github.com/brylee123/ha-pseg-nj (issue tracker configured).
  Local custom integration brand assets are included. HACS validation and automated future PyPI releases remain. Library author, MIT license and initial PyPI upload are complete.

No quality tier is claimed. `quality_scale.yaml` identifies pending criteria;
`GETTING_STARTED.md` maps every Getting Started page to completed/pending work.

## First runtime check

Back up HA; install/restart; configure with cookie blank. Import a short Hourly
sample twice and confirm the second result has `hours_changed: 0`. Check
`pseg_nj:<label>_energy` in Statistics, choose it in Energy, and compare a complete
day against the portal. Then import the full Hourly history and test session
polling/expiry/reconnection. Nothing has been installed on the user's Pi.

## Official Home Assistant tools

* HA Core 2026.10.0 checkout: `python -m script.hassfest --integration-path .../custom_components/pseg_nj` completed with **1 integration, 0 invalid integrations**, with no remaining warnings.
* `python -m script.translations develop --integration pseg_nj` completed in a temporary Core-checkout copy. Its generated English JSON matches the shipped translation exactly.
* The scaffold is not rerun because this domain already exists. No Core contribution or quality tier is claimed.
