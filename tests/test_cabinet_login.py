"""Browser login: «Войти через Telegram» without a nickname, «Да, это я» with the device, and «завершить сеанс»."""
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import cabinet_login, db, web
from app.handlers import cabinet_login as handlers


class DeviceLabelTest(unittest.TestCase):
    def test_common_browsers(self):
        win = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
        iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
        yandex = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/128.0 YaBrowser/24.10 Mobile Safari/537.36"
        mac_ff = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:131.0) Gecko/20100101 Firefox/131.0"
        self.assertEqual(cabinet_login.device_label(win), "Chrome на Windows")
        self.assertEqual(cabinet_login.device_label(iphone), "Safari на iPhone")
        self.assertEqual(cabinet_login.device_label(yandex), "Яндекс Браузер на Android")
        self.assertEqual(cabinet_login.device_label(mac_ff), "Firefox на Mac")

    def test_unknown_or_hostile_header_gives_only_fixed_words(self):
        self.assertEqual(cabinet_login.device_label(None), "Браузер")
        self.assertEqual(cabinet_login.device_label("<b>evil</b>"), "Браузер")


class StartPayloadTest(unittest.TestCase):
    def test_login_payload(self):
        self.assertEqual(cabinet_login.start_challenge_id("lk_AbC-123_xyzQWERTYu"), "AbC-123_xyzQWERTYu")

    def test_other_payloads_are_not_logins(self):
        for payload in (None, "", "ref_42", "ad_promo", "lk_", "lk_short", "lk_" + "a" * 60, "lk_bad id here!!!!"):
            self.assertEqual(cabinet_login.start_challenge_id(payload), "", payload)


class RequestTextTest(unittest.TestCase):
    def test_shows_device_and_time(self):
        at = datetime(2026, 11, 13, 18, 40, tzinfo=timezone.utc)
        text = cabinet_login.request_text("Chrome на Windows", at)
        self.assertIn("Chrome на Windows", text)
        self.assertIn("21:40 МСК", text)
        self.assertIn("Это не я", text)


class FakeRequest(SimpleNamespace):
    async def json(self):
        return self.body


def _request(body, ua="Mozilla/5.0 (Windows NT 10.0) Chrome/130.0 Safari/537.36", bot=None):
    return FakeRequest(body=body, headers={"User-Agent": ua}, remote="10.0.0.1", app={"bot": bot})


class LoginApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        web._cabinet_login_hits.clear()

    async def test_telegram_button_needs_no_nickname(self):
        create = AsyncMock(return_value="ABCDEFGHIJKLMNOPQRSTUV")
        with patch.object(db, "flag_on", AsyncMock(return_value=False)), patch.object(db, "create_cabinet_login_challenge", create), \
                patch.object(web, "get_settings", return_value=SimpleNamespace(bot_username="frog_bot")):
            res = await web.api_cabinet_login(_request({"via": "tg"}))
        data = json.loads(res.text)
        self.assertEqual(data["wait"], "ABCDEFGHIJKLMNOPQRSTUV")
        self.assertEqual(data["link"], "https://t.me/frog_bot?start=lk_ABCDEFGHIJKLMNOPQRSTUV")
        create.assert_awaited_once_with(None, "10.0.0.1", "Chrome на Windows")

    async def test_telegram_button_has_a_looser_limit_of_its_own(self):
        create = AsyncMock(return_value="ABCDEFGHIJKLMNOPQRSTUV")
        with patch.object(db, "flag_on", AsyncMock(return_value=False)), patch.object(db, "create_cabinet_login_challenge", create), \
                patch.object(web, "get_settings", return_value=SimpleNamespace(bot_username="frog_bot")):
            for _ in range(13):
                await web.api_cabinet_login(_request({"via": "tg"}))
        self.assertEqual(create.await_count, 13)

    async def test_nickname_login_asks_with_the_device(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch.object(db, "flag_on", AsyncMock(return_value=False)), \
                patch.object(db, "get_user_by_username", AsyncMock(return_value={"telegram_id": 7})), \
                patch.object(db, "create_cabinet_login_challenge", AsyncMock(return_value="ABCDEFGHIJKLMNOPQRSTUV")):
            res = await web.api_cabinet_login(_request({"username": "@ivan_petrov"}, bot=bot))
        self.assertEqual(json.loads(res.text)["wait"], "ABCDEFGHIJKLMNOPQRSTUV")
        args, kwargs = bot.send_message.await_args
        self.assertEqual(args[0], 7)
        self.assertIn("Chrome на Windows", args[1])
        buttons = kwargs["reply_markup"].inline_keyboard[0]
        self.assertEqual([b.text for b in buttons], ["Да, это я", "Это не я"])


class BotTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_link_binds_the_request_and_asks(self):
        message = SimpleNamespace(from_user=SimpleNamespace(id=7), answer=AsyncMock())
        row = {"device": "Safari на iPhone", "created_at": datetime.now(timezone.utc)}
        with patch.object(db, "user_is_blocked", AsyncMock(return_value=False)), \
                patch.object(db, "bind_cabinet_login_challenge", AsyncMock(return_value=row)) as bind:
            await handlers.open_from_start(message, "ABCDEFGHIJKLMNOPQRSTUV")
        bind.assert_awaited_once_with("ABCDEFGHIJKLMNOPQRSTUV", 7)
        text = message.answer.await_args.args[0]
        self.assertIn("Safari на iPhone", text)
        self.assertEqual(message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data, "lk:y:ABCDEFGHIJKLMNOPQRSTUV")

    async def test_stale_or_someone_elses_link_says_so(self):
        message = SimpleNamespace(from_user=SimpleNamespace(id=7), answer=AsyncMock())
        with patch.object(db, "user_is_blocked", AsyncMock(return_value=False)), \
                patch.object(db, "bind_cabinet_login_challenge", AsyncMock(return_value=None)):
            await handlers.open_from_start(message, "ABCDEFGHIJKLMNOPQRSTUV")
        self.assertNotIn("reply_markup", message.answer.await_args.kwargs)

    async def test_blocked_person_cannot_log_in(self):
        message = SimpleNamespace(from_user=SimpleNamespace(id=7), answer=AsyncMock())
        bind = AsyncMock()
        with patch.object(db, "user_is_blocked", AsyncMock(return_value=True)), patch.object(db, "bind_cabinet_login_challenge", bind):
            await handlers.open_from_start(message, "ABCDEFGHIJKLMNOPQRSTUV")
        bind.assert_not_awaited()

    async def test_yes_offers_to_end_the_session(self):
        callback = SimpleNamespace(data="lk:y:ABCDEFGHIJKLMNOPQRSTUV", from_user=SimpleNamespace(id=7),
                                   message=SimpleNamespace(edit_text=AsyncMock()), answer=AsyncMock())
        with patch.object(db, "approve_cabinet_login_challenge", AsyncMock(return_value="raw-token")), \
                patch.object(db, "get_cabinet_login_challenge", AsyncMock(return_value={"device": "Chrome на Windows"})), \
                patch.object(handlers, "ack", AsyncMock()):
            await handlers.cabinet_login_yes(callback)
        text = callback.message.edit_text.await_args.args[0]
        self.assertIn("Chrome на Windows", text)
        button = callback.message.edit_text.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(button.callback_data, "lk:x:" + db.cabinet_token_ref("raw-token"))
        self.assertLessEqual(len(button.callback_data.encode()), 64)

    async def test_end_session_logs_that_browser_out(self):
        callback = SimpleNamespace(data="lk:x:0123456789abcdef", from_user=SimpleNamespace(id=7),
                                   message=SimpleNamespace(edit_text=AsyncMock()), answer=AsyncMock())
        end = AsyncMock(return_value=True)
        with patch.object(db, "end_cabinet_session", end), patch.object(handlers, "ack", AsyncMock()):
            await handlers.cabinet_session_end(callback)
        end.assert_awaited_once_with(7, "0123456789abcdef")
        self.assertIn("Сеанс завершён", callback.message.edit_text.await_args.args[0])


class QueryTest(unittest.IsolatedAsyncioTestCase):
    async def test_bind_only_takes_a_free_or_own_live_request(self):
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value=None))
        with patch.object(db, "_pool_req", return_value=pool):
            self.assertIsNone(await db.bind_cabinet_login_challenge("abc", 7))
        sql = pool.fetchrow.await_args.args[0]
        self.assertIn("status = 'pending'", sql)
        self.assertIn("telegram_id IS NULL OR telegram_id = $2", sql)
        self.assertIn("expires_at > timezone('utc', now())", sql)

    async def test_end_session_is_limited_to_the_owner(self):
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value={"token_hash": "x"}))
        with patch.object(db, "_pool_req", return_value=pool):
            self.assertTrue(await db.end_cabinet_session(7, "0123456789ABCDEF"))
            self.assertFalse(await db.end_cabinet_session(7, "not-hex-at-all!!"))
        sql, *args = pool.fetchrow.await_args.args
        self.assertIn("telegram_id = $1", sql)
        self.assertEqual(args, [7, "0123456789abcdef"])
        self.assertEqual(pool.fetchrow.await_count, 1)


if __name__ == "__main__":
    unittest.main()
