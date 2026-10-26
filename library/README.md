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
Use `python -m pip install -e library` for development.
Source and issues: https://github.com/brylee123/ha-pseg-nj.

The custom integration pins the published PyPI distribution in its manifest
and imports `pseg_mymeter` directly. No vendored library is shipped in the
component. Automated library publishing and broader live testing remain
before proposing this dependency for Home Assistant Core.

The files here support future library development. The existing PyPI 0.2.0
artifacts are immutable; library changes must use a new version when published.
