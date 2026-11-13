"""A broadcast reaches people: Telegram's flood limit is waited out, and a hand-sent broadcast goes ahead of reminders."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage

from app import admin, db


def flood(seconds=3):
    return TelegramRetryAfter(method=SendMessage(chat_id=1, text="x"), message="Too Many Requests", retry_after=seconds)


class FloodRetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_waits_what_telegram_asks_and_sends_again(self):
        send = AsyncMock(side_effect=[flood(3), flood(1), "ok"])
        with patch.object(admin.asyncio, "sleep", AsyncMock()) as sleep:
            self.assertEqual(await admin._flood_retry(send), "ok")
        self.assertEqual([c.args[0] for c in sleep.await_args_list], [3.5, 1.5])

    async def test_gives_up_after_a_few_tries(self):
        send = AsyncMock(side_effect=flood(1))
        with patch.object(admin.asyncio, "sleep", AsyncMock()), self.assertRaises(TelegramRetryAfter):
            await admin._flood_retry(send)
        self.assertEqual(send.await_count, admin.FLOOD_RETRIES + 1)

    async def test_other_errors_are_not_retried(self):
        send = AsyncMock(side_effect=TelegramForbiddenError(method=SendMessage(chat_id=1, text="x"), message="bot was blocked by the user"))
        with self.assertRaises(TelegramForbiddenError):
            await admin._flood_retry(send)
        self.assertEqual(send.await_count, 1)

    async def test_a_long_wait_is_capped(self):
        send = AsyncMock(side_effect=[flood(600), "ok"])
        with patch.object(admin.asyncio, "sleep", AsyncMock()) as sleep:
            await admin._flood_retry(send)
        self.assertEqual(sleep.await_args.args[0], 60.5)


class BroadcastTest(unittest.IsolatedAsyncioTestCase):
    async def test_hand_sent_broadcast_reserves_as_manual_and_survives_a_flood(self):
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=[flood(2), SimpleNamespace(message_id=5)]))
        reserve = AsyncMock(return_value=11)
        job = {"running": True}
        with patch.object(db, "list_broadcast_targets", AsyncMock(return_value=[{"telegram_id": 1, "first_name": "Ann"}])), \
                patch.object(db, "notification_allowed", AsyncMock(return_value=True)), \
                patch.object(db, "reserve_optional_message", reserve), \
                patch.object(db, "finish_optional_message", AsyncMock()) as finish, \
                patch.object(db, "log_bot_message", AsyncMock()), \
                patch("app.funnel_ui.funnel_body", side_effect=lambda b: b), \
                patch("app.funnel_ui.funnel_keyboard", side_effect=lambda m: m), \
                patch.object(admin.asyncio, "sleep", AsyncMock()):
            await admin._broadcast_all(bot, "Привет", job)
        reserve.assert_awaited_once_with(1, "broadcast", manual=True)
        self.assertEqual((job.get("sent"), job.get("failed")), (1, None))
        finish.assert_awaited_once_with(11, True)


class ManualReservationSqlTest(unittest.IsolatedAsyncioTestCase):
    async def test_only_another_broadcast_holds_a_manual_one_back(self):
        user = {"quiet_notifications": False, "blocked_at": None, "bot_blocked_at": None, "bot_started_at": 1, "vpn_feedback": None}
        conn = SimpleNamespace(fetchrow=AsyncMock(return_value=user), fetchval=AsyncMock(side_effect=[True, 9]))

        class Ctx:
            def __init__(self, v): self.v = v
            async def __aenter__(self): return self.v
            async def __aexit__(self, *a): return False

        conn.transaction = lambda: Ctx(None)
        with patch.object(db, "_pool_req", return_value=SimpleNamespace(acquire=lambda: Ctx(conn))):
            self.assertEqual(await db.reserve_optional_message(1, "broadcast", manual=True), 9)
        sql = conn.fetchval.await_args_list[0].args[0]
        self.assertIn("kind='broadcast' AND sent_at > NOW()-INTERVAL '24 hours'", sql)
        self.assertIn("tickets", sql)
        self.assertNotIn("7 days", sql)
        self.assertNotIn("nudge_", sql)


if __name__ == "__main__":
    unittest.main()
