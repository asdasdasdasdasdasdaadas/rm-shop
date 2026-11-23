"""The /connect page: a signed one-device token in the #fragment, the key over a header, the bot's links."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import connect_link, db, nudge, web


def _req(token="", body=None):
    return SimpleNamespace(headers={"X-Connect-Token": token} if token else {},
                           json=AsyncMock(return_value=body or {}))


class TokenTest(unittest.TestCase):
    def test_round_trip_tamper_and_expiry(self):
        t = connect_link.make_token(123, 45, now=1000)
        self.assertEqual(connect_link.read_token(t, now=1001), (123, 45))
        self.assertIsNone(connect_link.read_token(t, now=1000 + 31 * 86400))
        forged = t.replace(f"{45:x}.", f"{46:x}.", 1)
        self.assertIsNone(connect_link.read_token(forged, now=1001))
        for bad in ("", "x", "a.b.c.d", t + "x", "." * 200):
            self.assertIsNone(connect_link.read_token(bad, now=1001))

    def test_url_keeps_the_token_out_of_the_query(self):
        url = connect_link.connect_url("https://shop.example/", 1, 2, "happ")
        self.assertTrue(url.startswith("https://shop.example/connect#t="))
        self.assertNotIn("?", url)
        self.assertTrue(url.endswith("&a=happ"))
        self.assertEqual(connect_link.connect_url("", 1, 2), "")


class ApiTest(unittest.IsolatedAsyncioTestCase):
    real_record = staticmethod(db.record_onboarding_event)

    def setUp(self):
        self.patches = [patch.object(db, "flag_on", AsyncMock(return_value=False)),
                        patch.object(db, "user_is_blocked", AsyncMock(return_value=False)),
                        patch.object(db, "record_onboarding_event", AsyncMock())]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    async def test_gives_only_the_token_device_key(self):
        device = {"id": 7, "telegram_id": 5, "title": "Мой iPhone", "platform": "ios", "client": "happ",
                  "subscription_url": "https://sub.example/abc"}
        with patch.object(db, "get_device", AsyncMock(return_value=device)) as get:
            resp = await web.api_connect(_req(connect_link.make_token(5, 7)))
        get.assert_awaited_once_with(5, 7)
        self.assertEqual(resp.status, 200)
        self.assertIn(b'"key": "https://sub.example/abc"', resp.body)
        self.assertEqual(resp.headers["Referrer-Policy"], "no-referrer")
        self.assertIn("no-store", resp.headers["Cache-Control"])

    async def test_rejects_missing_forged_and_foreign_tokens(self):
        with patch.object(db, "get_device", AsyncMock(return_value=None)):
            self.assertEqual((await web.api_connect(_req())).status, 401)
            self.assertEqual((await web.api_connect(_req("1.2.3.zz"))).status, 401)
            self.assertEqual((await web.api_connect(_req(connect_link.make_token(5, 8)))).status, 404)

    async def test_blocked_user_gets_nothing(self):
        db.user_is_blocked.return_value = True
        with patch.object(db, "get_device", AsyncMock()) as get:
            self.assertEqual((await web.api_connect(_req(connect_link.make_token(5, 7)))).status, 403)
        get.assert_not_awaited()

    async def test_events_map_to_onboarding_stages(self):
        device = {"id": 7, "subscription_url": "k"}
        with patch.object(db, "get_device", AsyncMock(return_value=device)):
            ok = await web.api_connect_event(_req(connect_link.make_token(5, 7), {"kind": "copy"}))
            bad = await web.api_connect_event(_req(connect_link.make_token(5, 7), {"kind": "wizard_1"}))
        self.assertEqual((ok.status, bad.status), (200, 400))
        db.record_onboarding_event.assert_awaited_once_with(5, "connect_copy")

    async def test_connect_stages_are_allowed_in_the_db(self):
        pool = SimpleNamespace(execute=AsyncMock())
        with patch.object(db, "_pool_req", return_value=pool):
            for stage in web._CONNECT_STAGES.values():
                await self.real_record(1, stage)
        self.assertEqual(pool.execute.await_count, len(web._CONNECT_STAGES))


class BotMessageTest(unittest.IsolatedAsyncioTestCase):
    async def test_first_device_message_has_key_link_and_copy(self):
        devices = [{"id": 3, "subscription_url": "https://sub.example/old", "platform": "ios"},
                   {"id": 9, "subscription_url": "https://sub.example/new&x", "platform": "android"},
                   {"id": 11, "subscription_url": "https://sub.example/r", "kind": "router"}]
        with patch.object(db, "list_devices", AsyncMock(return_value=devices)), \
             patch("app.keyboards.mini_app_url", return_value="https://shop.example"):
            body, markup = await nudge._first_device_message(42)
        self.assertIn("<code>https://sub.example/new&amp;x</code>", body)
        buttons = [b for row in markup.inline_keyboard for b in row]
        link = next(b for b in buttons if b.url)
        self.assertTrue(link.url.startswith("https://shop.example/connect#t="))
        self.assertEqual(connect_link.read_token(link.url.split("#t=")[1]), (42, 9))
        self.assertEqual(next(b for b in buttons if b.copy_text).copy_text.text, "https://sub.example/new&x")

    async def test_without_devices_keeps_the_old_message(self):
        with patch.object(db, "list_devices", AsyncMock(return_value=[])):
            body, markup = await nudge._first_device_message(42)
        self.assertNotIn("<code>", body)
        self.assertFalse(any(b.copy_text for row in markup.inline_keyboard for b in row))


if __name__ == "__main__":
    unittest.main()
