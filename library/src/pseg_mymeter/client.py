"""Session-only MyMeter export client. Never logs cookies or response bodies."""

import json
import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from http.cookies import CookieError, SimpleCookie
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientSession, ClientTimeout
from yarl import URL

from .data import meter_id
from .exceptions import CannotConnect, InvalidResponse, MeterNotFound, SessionExpired

BASE = "https://mysmartenergy.nj.pseg.com"


class ExportForm(HTMLParser):
    """Extract successful input/select fields from the recorded export form."""

    def __init__(self) -> None:
        """Initialize a form-only parser."""
        super().__init__(convert_charrefs=True)
        self.active = False
        self.fields: list[tuple[str, str]] = []
        self.select: str | None = None
        self.options: list[tuple[str, bool]] = []
        self.label: str | None = None
        self.labels: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect successful form controls and meter labels."""
        a = dict(attrs)
        if tag == "form":
            self.active = a.get("id") == "downloadOptions"
        if not self.active:
            return
        if tag == "input" and a.get("name") and "disabled" not in a:
            kind = a.get("type", "text")
            if kind in ("submit", "button", "file"):
                return
            if kind in ("checkbox", "radio") and "checked" not in a:
                return
            self.fields.append((a["name"], a.get("value") or ""))
        elif tag == "select" and a.get("name"):
            self.select, self.options = a["name"], []
        elif tag == "option" and self.select:
            self.options.append((a.get("value") or "", "selected" in a))
        elif tag == "label" and a.get("for"):
            self.label = a["for"]
            self.labels[self.label] = ""

    def handle_data(self, data: str) -> None:
        """Retain label text to map displayed meters to internal IDs."""
        if self.label:
            self.labels[self.label] += data

    def handle_endtag(self, tag: str) -> None:
        """Finish select controls and labels."""
        if tag == "label":
            self.label = None
        elif tag == "select" and self.select:
            selected = next(
                (x for x in self.options if x[1]),
                self.options[0] if self.options else None,
            )
            if selected:
                self.fields.append((self.select, selected[0]))
            self.select = None
        elif tag == "form":
            self.active = False


def download_fields(
    payload: dict[str, Any], meter: str, start: date, end: date
) -> list[tuple[str, str]]:
    """Use current server selectors/token; override only export-specific fields."""
    parser = ExportForm()
    for item in payload.get("AjaxResults", []):
        if not isinstance(item, dict):
            raise InvalidResponse
        if (
            isinstance(item.get("Value"), str)
            and 'id="downloadOptions"' in item["Value"]
        ):
            parser.feed(item["Value"])
    fields = parser.fields
    if not any(k == "__RequestVerificationToken" and v for k, v in fields):
        raise SessionExpired("Export form unavailable; reconnect your session")
    meter_indices = []
    for key, value in fields:
        match = re.fullmatch(r"Meters\[(\d+)\]\.Value", key)
        if match:
            label = parser.labels.get(f"Meters_{match[1]}__Selected", "")
            displayed = re.search(r"Meter\s*#\s*([0-9]+)", label, re.IGNORECASE)
            if displayed and displayed[1] == meter_id(meter):
                meter_indices.append(match[1])
    if len(meter_indices) != 1:
        raise MeterNotFound
    updates = {
        "FileFormat": "download-usage-csv",
        "SelectedFormat": "2",
        "SelectedServiceType": "1",
        "SelectedInterval": "5",
        "SelectedUsageType": "1",
        "Start": start.isoformat(),
        "End": end.isoformat(),
    }
    result = [
        (k, v)
        for k, v in fields
        if k not in updates and not re.fullmatch(r"Meters\[\d+\]\.Selected", k)
    ]
    result.extend(updates.items())
    result.append((f"Meters[{meter_indices[0]}].Selected", "true"))
    return result


class PsegClient:
    """An asynchronous, session-injected client without Home Assistant imports."""

    def __init__(self, session: ClientSession, cookie: str, meter: str) -> None:
        """Initialize an isolated cookie jar with an existing session."""
        if "\n" in cookie or "\r" in cookie:
            raise SessionExpired
        parsed = SimpleCookie()
        try:
            parsed.load(cookie)
        except CookieError:
            raise SessionExpired from None
        if not parsed:
            raise SessionExpired
        self.session, self.meter = session, meter
        self.session.cookie_jar.update_cookies(parsed, response_url=URL(BASE))

    async def _async_request(
        self, method: str, path: str, *, data: list[tuple[str, str]] | None = None
    ) -> str:
        """Read a response without redirects or leaking server error text."""
        try:
            async with self.session.request(
                method,
                BASE + path,
                headers={
                    "Referer": BASE + "/Dashboard",
                    "X-Requested-With": "XMLHttpRequest",
                },
                allow_redirects=False,
                timeout=ClientTimeout(total=90),
                data=data,
            ) as response:
                if response.status in (301, 302, 303, 307, 308, 401, 403):
                    raise SessionExpired
                if response.status == 429 or response.status >= 500:
                    raise CannotConnect
                if response.status != 200:
                    raise InvalidResponse
                if "text/html" in response.headers.get("Content-Type", "").lower():
                    raise SessionExpired
                body = await response.text()
                if len(body) > 25_000_000:
                    raise InvalidResponse
                return body
        except (ClientError, TimeoutError):
            raise CannotConnect from None

    async def _async_form(self) -> dict[str, Any]:
        """Retrieve fresh form controls and verification token."""
        text = await self._async_request("GET", "/Usage/InitializeDownloadSettings")
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            raise InvalidResponse from None
        if not isinstance(payload, dict) or not isinstance(
            payload.get("AjaxResults"), list
        ):
            raise InvalidResponse
        return payload

    async def async_validate_session(self) -> None:
        """Validate authentication and meter membership without downloading."""
        today = datetime.now(ZoneInfo("America/New_York")).date()
        download_fields(await self._async_form(), self.meter, today, today)

    async def async_usage(self) -> str:
        """Download Hourly electricity for the previous seven days."""
        end = datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=1)
        fields = download_fields(
            await self._async_form(), self.meter, end - timedelta(days=6), end
        )
        return await self._async_request("POST", "/Usage/Download", data=fields)

    async def async_close(self) -> None:
        """Close the caller-owned isolated session on teardown."""
        await self.session.close()
