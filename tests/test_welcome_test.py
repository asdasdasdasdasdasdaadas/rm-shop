"""The first-message A/B test: who gets the card, what it says, and how the verdict reads."""
import asyncio
import os
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, welcome, welcome_test


def settings(**kw):
    return SimpleNamespace(**{"brand_name": "Лягушка VPN", "referral_program_enabled": False, "trial_days": 3,
                              "welcome_tariff_enabled": True, "required_channel_enabled": False, "max_devices": 5,
                              "vpn_day_price_rub": 6, "balance_topup_min": 50, "legal_offer_url": "o",
                              "legal_privacy_url": "p", **kw})


class CardTest(unittest.IsolatedAsyncioTestCase):
    async def intro(self, arm, *, granted=None, cached="", **kw):
        from app import auto_gift, keyboards
        photo = SimpleNamespace(photo=[SimpleNamespace(file_id="small"), SimpleNamespace(file_id="big")])
        message = SimpleNamespace(bot=object(), from_user=SimpleNamespace(id=1, first_name="Иван"),
                                  chat=SimpleNamespace(id=1), answer=AsyncMock(), answer_photo=AsyncMock(return_value=photo))
        with ExitStack() as st:
            st.enter_context(patch.object(welcome, "get_settings", return_value=settings(**kw)))
            st.enter_context(patch.object(keyboards, "get_settings", return_value=settings(webapp_public_url="", **kw)))
            st.enter_context(patch.object(keyboards, "mini_app_url", return_value=""))
            st.enter_context(patch.object(welcome.db, "get_user", AsyncMock(return_value={})))
            st.enter_context(patch.object(welcome.db, "mark_legal_notice", AsyncMock()))
            st.enter_context(patch.object(welcome.db, "complete_welcome_support", AsyncMock()))
            st.enter_context(patch.object(welcome.db, "get_kv", AsyncMock(return_value=cached)))
            self.kv = st.enter_context(patch.object(welcome.db, "set_kv", AsyncMock()))
            st.enter_context(patch.object(welcome, "trial_is_available", return_value=True))
            st.enter_context(patch.object(auto_gift, "grant_if_auto", AsyncMock(return_value=granted)))
            st.enter_context(patch.object(welcome_test, "enter", AsyncMock(return_value=arm)))
            self.sticker = st.enter_context(patch.object(welcome, "send_welcome_sticker", AsyncMock()))
            for name in ("_pause", "_log"):
                st.enter_context(patch.object(welcome, name, AsyncMock()))
            self.assertTrue(await welcome.send_welcome_intro(message, in_channel=True))
        return message

    async def test_the_card_replaces_sticker_and_text(self):
        m = await self.intro("card")
        self.sticker.assert_not_awaited()
        m.answer.assert_not_awaited()
        call = m.answer_photo.call_args
        caption, kb = call.kwargs["caption"], call.kwargs["reply_markup"]
        self.assertTrue(caption.startswith("<b>Лягушка VPN</b>"))
        for part in ("до 5 устройств", "6 ₽ в день", "3 дня бесплатно", "займёт минуту", '<a href="o">оферту</a>', "<tg-emoji"):
            self.assertIn(part, caption)
        self.assertLessEqual(len(caption), 1024)
        button = kb.inline_keyboard[0][0]
        self.assertEqual((button.text, button.style), ("Подключить за минуту", "success"))
        self.assertTrue(button.icon_custom_emoji_id)
        self.kv.assert_awaited_once_with(welcome.CARD_FILE_KV, "big")   # the upload is reused next time

    async def test_a_cached_banner_is_sent_by_id_and_the_credited_gift_is_named(self):
        m = await self.intro("card", cached="cached-id", granted=18)
        self.assertEqual(m.answer_photo.call_args.args[0], "cached-id")
        self.assertIn("Подарок уже на балансе", m.answer_photo.call_args.kwargs["caption"])
        self.kv.assert_not_awaited()

    async def test_the_other_group_and_no_test_keep_the_usual_welcome(self):
        for arm in ("plain", None):
            m = await self.intro(arm)
            self.sticker.assert_awaited_once()
            m.answer_photo.assert_not_awaited()
            self.assertIn("Дарим 3 дня VPN", m.answer.call_args.args[0])

    async def test_a_failed_banner_falls_back_to_text(self):
        from aiogram.exceptions import TelegramBadRequest
        # the cached id is refused and there is no file: the welcome goes out as the usual text
        with patch.object(welcome, "CARD_BANNER", Path("/nonexistent.jpg")):
            message = SimpleNamespace(answer_photo=AsyncMock(side_effect=TelegramBadRequest(method=None, message="bad")))
            with patch.object(welcome.db, "get_kv", AsyncMock(return_value="stale")), \
                    patch.object(welcome.db, "set_kv", AsyncMock()) as kv:
                self.assertFalse(await welcome._send_card(message, "x", None))
                kv.assert_awaited_once_with(welcome.CARD_FILE_KV, "")


class VerdictTest(unittest.TestCase):
    def test_card_wins_when_more_connect_in_a_day(self):
        rows = {"plain": {"users": 400, "day_done": 400, "connected_day": 100},
                "card": {"users": 400, "day_done": 400, "connected_day": 160}}
        out = welcome_test.summarize(rows)
        self.assertEqual(out["arms"][1]["connected_day_pct"], 40.0)
        self.assertTrue(out["verdicts"][0]["verdict"].startswith("Карточка лучше"))
        self.assertEqual(welcome_test.summarize({})["verdicts"], [])


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class WelcomeTestDb(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        p = patch.object(db, "_pool_req", return_value=self.pool)
        p.start()
        self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_groups_stick_and_results_count(self):
        await self.pool.execute("INSERT INTO users (telegram_id) SELECT g FROM generate_series(1, 60) g")
        self.assertIsNone(await welcome_test.enter(1))   # no test: the usual welcome
        await welcome_test.start()
        with self.assertRaises(ValueError):
            await welcome_test.start()
        arms = {i: await welcome_test.enter(i) for i in range(1, 61)}
        self.assertEqual(set(arms.values()), {"plain", "card"})
        self.assertEqual(await welcome_test.enter(1), arms[1])
        card = next(i for i, a in arms.items() if a == "card")
        await self.pool.execute("UPDATE welcome_arms SET assigned_at = NOW() - INTERVAL '2 days'")
        await self.pool.execute("UPDATE users SET first_online_at = NOW() - INTERVAL '47 hours', trial_used = TRUE WHERE telegram_id=$1", card)
        item = (await welcome_test.overview())["items"][0]
        got = {a["arm"]: a for a in item["arms"]}
        self.assertEqual(got["card"]["connected_day"], 1)
        self.assertEqual(got["card"]["gift"], 1)
        self.assertEqual(got["plain"]["users"] + got["card"]["users"], 60)
        await welcome_test.stop()
        self.assertIsNone(await welcome_test.enter(2))


if __name__ == "__main__":
    unittest.main()
