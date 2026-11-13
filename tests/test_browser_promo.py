"""«Кабинет есть и в браузере»: the link in the chat, the low-balance button and the «кабинет в браузере» broadcast."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin, balance, broadcast_media, cabinet_login, db, runtime, web
from app.balance_notifications import balance_keyboard
from app.handlers import cabinet_login as handlers

SITE = SimpleNamespace(webapp_public_url="https://lk.example.ru/")


class SiteLinkTest(unittest.IsolatedAsyncioTestCase):
    async def test_sends_the_plain_address_with_a_button(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch.object(cabinet_login, "get_settings", return_value=SITE):
            self.assertTrue(await cabinet_login.send_site_link(bot, 7))
        args, kwargs = bot.send_message.await_args
        self.assertEqual(args[0], 7)
        self.assertIn("https://lk.example.ru", args[1])
        self.assertEqual(kwargs["reply_markup"].inline_keyboard[0][0].url, "https://lk.example.ru")

    async def test_no_https_address_means_no_link(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch.object(cabinet_login, "get_settings", return_value=SimpleNamespace(webapp_public_url="")), \
                patch.object(runtime, "webapp_url", "http://127.0.0.1:8080"):
            self.assertFalse(await cabinet_login.send_site_link(bot, 7))
            self.assertEqual(cabinet_login.site_url(), "")
        bot.send_message.assert_not_awaited()


class FakeRequest(SimpleNamespace):
    async def json(self):
        return {}


class BrowserLinkApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        web._cabinet_login_hits.clear()

    async def test_sends_and_then_stops_after_three(self):
        send = AsyncMock(return_value=True)
        request = FakeRequest(app={"bot": object()}, headers={}, remote="10.0.0.1")
        with patch.object(web, "_require_tg", AsyncMock(return_value=(7, None))), patch.object(web, "send_site_link", send):
            codes = [(await web.api_browser_link(request)).status for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])
        self.assertEqual(send.await_count, 3)

    async def test_says_so_when_the_link_cannot_be_sent(self):
        request = FakeRequest(app={"bot": object()}, headers={}, remote="10.0.0.1")
        with patch.object(web, "_require_tg", AsyncMock(return_value=(7, None))), \
                patch.object(web, "send_site_link", AsyncMock(side_effect=RuntimeError("blocked"))):
            res = await web.api_browser_link(request)
        self.assertEqual(res.status, 400)
        self.assertFalse(json.loads(res.text)["ok"])


class LowBalanceTest(unittest.IsolatedAsyncioTestCase):
    def test_button_sits_above_the_main_menu(self):
        rows = balance_keyboard(browser=True).inline_keyboard
        self.assertEqual(rows[-2][0].callback_data, "brw:link")
        self.assertEqual(rows[-1][0].callback_data, "profile")
        self.assertNotIn("brw:link", [b.callback_data for row in balance_keyboard().inline_keyboard for b in row])

    async def test_offered_only_to_someone_without_a_browser_login(self):
        with patch.object(cabinet_login, "get_settings", return_value=SITE):
            with patch.object(db, "has_cabinet_session", AsyncMock(return_value=False)):
                self.assertTrue(await balance._offer_browser(7))
            with patch.object(db, "has_cabinet_session", AsyncMock(return_value=True)):
                self.assertFalse(await balance._offer_browser(7))
        with patch.object(cabinet_login, "get_settings", return_value=SimpleNamespace(webapp_public_url="")), \
                patch.object(runtime, "webapp_url", ""), patch.object(db, "has_cabinet_session", AsyncMock()) as has:
            self.assertFalse(await balance._offer_browser(7))
            has.assert_not_awaited()

    async def test_button_sends_the_link(self):
        callback = SimpleNamespace(from_user=SimpleNamespace(id=7), bot=object())
        send = AsyncMock(return_value=True)
        with patch.object(handlers, "send_site_link", send), patch.object(handlers, "ack", AsyncMock()) as ack:
            await handlers.browser_link(callback)
        send.assert_awaited_once_with(callback.bot, 7)
        ack.assert_awaited_once_with(callback, None)


class BroadcastTest(unittest.TestCase):
    def test_goes_to_people_without_a_browser_login_and_takes_a_video(self):
        video = {"id": "abc.mp4", "kind": "video"}
        with patch.object(cabinet_login, "get_settings", return_value=SITE), \
                patch.object(broadcast_media, "check", return_value=(video, None)):
            spec, error = admin._check_broadcast({"template": "browser", "media": video})
            self.assertIsNone(error)
            self.assertEqual(spec["audience"], "no_browser")
            self.assertEqual(spec["media"], video)
            self.assertIn("только к своему", admin._check_broadcast({"template": "unused", "media": video})[1])

    def test_needs_the_site(self):
        with patch.object(cabinet_login, "get_settings", return_value=SimpleNamespace(webapp_public_url="")), \
                patch.object(runtime, "webapp_url", ""):
            self.assertIn("https", admin._check_broadcast({"template": "browser"})[1])

    def test_message_has_the_site_and_the_steps(self):
        with patch.object(cabinet_login, "get_settings", return_value=SITE), \
                patch("app.keyboards.mini_app_url", return_value="https://lk.example.ru/"):
            body, markup = admin._broadcast_payload("browser", "", 7, "Иван", SITE)
        self.assertIn("в браузере", body)
        site, how = markup.inline_keyboard
        self.assertEqual(site[0].url, "https://lk.example.ru")
        self.assertEqual(how[0].web_app.url, "https://lk.example.ru/?screen=browser")
        self.assertEqual(admin._broadcast_title("browser"), "Рассылка: кабинет в браузере")

    def test_segment_is_active_vpn_without_a_browser_login(self):
        sql = db.BROADCAST_SEGMENTS["no_browser"]
        self.assertIn("30 days", sql)
        self.assertIn("NOT EXISTS (SELECT 1 FROM cabinet_tokens", sql)


if __name__ == "__main__":
    unittest.main()
