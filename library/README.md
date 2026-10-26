# PSE&G NJ MyMeter client

An experimental, unofficial client for PSE&G New Jersey's MyMeter portal.
Author: **brylee123**. License: **MIT**. Requires Python 3.13 or newer.
This project is not affiliated with or endorsed by PSE&G.

Install with `python -m pip install pseg-nj-mymeter`.

An independent asynchronous Python library. It has no Home Assistant imports.
It accepts an injected `aiohttp.ClientSession`, reads the current export form,
maps displayed meters to internal IDs, and downloads Hourly consumption CSV.
The data module validates exports and constructs hourly cumulative statistics.
It supports an existing user session; password login and MFA are not implemented.

```python
from aiohttp import ClientSession, CookieJar
from pseg_mymeter.client import PsegClient

async with ClientSession(cookie_jar=CookieJar()) as session:
    client = PsegClient(session, cookie_header, meter_number)
    await client.async_validate_session()
    csv_text = await client.async_usage()
```

Build locally with `python -m build library` from the repository root.
Use `python -m pip install -e library` for development. A public source repository,
issue tracker, release tags and automated publishing are still prerequisites
before this library is ready to become a Home Assistant core dependency.

The current custom integration bundles an exact copy under
`_vendor/pseg_mymeter`; `scripts/sync_vendor.py --check` verifies it against this
canonical source. The bundle is a temporary custom-integration accommodation,
not the final core dependency architecture.
