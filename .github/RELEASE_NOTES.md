Experimental PSE&G NJ MyMeter electricity integration for Home Assistant 2026.10+.

- Installs the published `pseg-nj-mymeter==0.2.0` dependency; removes vendored protocol code.
- Backfills Hourly exports into Energy statistics and optionally polls with an existing session.
- Includes config flows, reauthentication, diagnostics and persistent import replay.
- Validated with standalone tests, nine native HA 2026.10.4 tests including a Recorder round trip, and official HA tooling.

Install through HACS as a custom repository. For manual installation, extract `pseg_nj.zip` into `/config/custom_components/pseg_nj/`, restart HA and add PSE&G NJ Energy. See the repository README for configuration and CSV import instructions.

This is a prerelease: live HAOS/portal acceptance is still pending. Password/MFA login and automatic session renewal are not implemented. External historical statistics use hourly intervals. Back up HA and Recorder before installing.
