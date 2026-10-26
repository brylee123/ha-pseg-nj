"""Library transport tests without network calls."""

import json
import unittest
from types import SimpleNamespace

from aiohttp import ClientConnectionError
from pseg_mymeter.client import PsegClient
from pseg_mymeter.exceptions import CannotConnect, InvalidResponse, SessionExpired
from test_data import form


class Response:
    """Minimal asynchronous HTTP response test double."""

    def __init__(self, body, status=200, mime="text/plain"):
        self.body, self.status = body, status
        self.headers = {"Content-Type": mime}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return self.body


class TransportTests(unittest.IsolatedAsyncioTestCase):
    """Validate HTTP boundaries and safe exception types."""

    def client(self, responses):
        requests = []

        class Session:
            cookie_jar = SimpleNamespace(update_cookies=lambda *args, **kwargs: None)
            closed = False

            def request(self, *args, **kwargs):
                requests.append((args, kwargs))
                response = responses.pop(0)
                if isinstance(response, Exception):
                    raise response
                return response

            async def close(self):
                self.closed = True

        return PsegClient(Session(), "session=synthetic-only", "00123"), requests

    async def test_hourly_download_uses_no_redirects(self):
        client, requests = self.client(
            [Response(json.dumps(form())), Response("Start,kWh\n", mime="text/csv")]
        )
        self.assertEqual(await client.async_usage(), "Start,kWh\n")
        self.assertTrue(requests[1][0][1].endswith("/Usage/Download"))
        self.assertTrue(
            all(request[1]["allow_redirects"] is False for request in requests)
        )
        self.assertEqual(dict(requests[1][1]["data"])["SelectedInterval"], "5")

    async def test_validation_is_read_only_and_close_releases_session(self):
        client, requests = self.client([Response(json.dumps(form()))])
        await client.async_validate_session()
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0][0], "GET")
        await client.async_close()
        self.assertTrue(client.session.closed)

    async def test_expired_redirect_forbidden_and_html(self):
        for response in [
            Response("", 302),
            Response("", 403),
            Response("Login", mime="text/html"),
        ]:
            client, _ = self.client([response])
            with self.assertRaises(SessionExpired):
                await client.async_usage()

    async def test_connection_server_rate_limit_and_invalid_payload(self):
        for response in [
            Response("", 500),
            Response("", 429),
            ClientConnectionError("secret server body"),
        ]:
            client, _ = self.client([response])
            with self.assertRaises(CannotConnect) as caught:
                await client.async_usage()
            self.assertNotIn("secret", str(caught.exception))
        for payload in ("garbage", "[]", '{"AjaxResults": null}'):
            client, _ = self.client([Response(payload)])
            with self.assertRaises(InvalidResponse):
                await client.async_usage()

    async def test_missing_form_does_not_submit(self):
        client, requests = self.client([Response('{"AjaxResults": []}')])
        with self.assertRaises(SessionExpired):
            await client.async_usage()
        self.assertEqual(len(requests), 1)

    async def test_cookie_header_injection_rejected(self):
        with self.assertRaises(SessionExpired):
            PsegClient(None, "session=x\r\nHost: attacker.invalid", "00123")
