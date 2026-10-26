# Changelog

## 0.2.1

* Depend on published `pseg-nj-mymeter==0.2.0` through the HA manifest.
* Import the library directly and remove the bundled protocol source and vendor-sync script.
* Run local tests against the installed distribution instead of shadowing it with library source.
* Add native HA tests for service imports, repeat imports, diagnostics and reauthentication recovery.
* Keep domain, config schema version, entity IDs, statistic IDs and saved ledger unchanged.

## 0.2.0

* Introduce the typed coordinator, entity, service/statistics adapters, diagnostics and reauthentication.
* Use Hourly exports for supported external historical statistics.
* Publish independent `pseg-nj-mymeter` v0.2.0 under MIT on PyPI.
