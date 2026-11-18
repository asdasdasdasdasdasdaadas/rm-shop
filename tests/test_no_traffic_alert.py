"""«Подключился, но трафика нет»: a new device went online, yet moved almost nothing — one admin message."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, stuck_alert


def settings(**kw):
    return SimpleNamespace(**{"no_traffic_alert_enabled": True, "no_traffic_alert_min_mb": 1,
                              "no_traffic_alert_after_minutes": 30, **kw})


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class NoTrafficTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(stuck_alert, "_targets", AsyncMock(return_value=[777])),
                  patch("app.config.get_settings", return_value=settings())):
            p.start()
            self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def device(self, uid, *, added="3 hours", online="1 hour", traffic=0, kind="", username=None):
        await self.pool.execute("INSERT INTO users (telegram_id, first_name, username, trial_used) VALUES ($1, 'Аня', $2, TRUE) "
                                "ON CONFLICT DO NOTHING", uid, username)
        await self.pool.execute(f"""INSERT INTO devices (telegram_id, title, platform, client, kind, created_at, lifetime_traffic_bytes)
            VALUES ($1, 'iPhone', 'iOS', 'Happ', $2, NOW() - INTERVAL '{added}', $3)""", uid, kind, traffic)
        if online:  # the panel sync sets last_online_at; the trigger keeps the first one
            await self.pool.execute(f"UPDATE devices SET last_online_at = NOW() - INTERVAL '{online}' WHERE telegram_id=$1", uid)
            await self.pool.execute("UPDATE devices SET last_online_at = NOW() WHERE telegram_id=$1", uid)

    async def test_alerts_once_for_online_without_traffic(self):
        await self.device(1, traffic=48 * 1024, username="anya")      # alert
        await self.device(2, traffic=5 * 1024 * 1024)                  # works
        await self.device(3, online="10 minutes")                      # too early
        await self.device(4, online=None)                              # never online: «Застрял» covers it
        await self.device(5, added="5 days", online="4 days")          # too old
        await self.device(6, kind="router")
        first = await self.pool.fetchval("SELECT first_online_at < NOW() - INTERVAL '50 minutes' FROM devices WHERE telegram_id=1")
        self.assertTrue(first)
        bot = SimpleNamespace(send_message=AsyncMock())
        self.assertEqual(await stuck_alert.send_no_traffic(bot), 1)
        chat, text = bot.send_message.call_args.args
        self.assertEqual(chat, 777)
        self.assertIn("Подключился, но трафика нет", text)
        self.assertIn("iOS · Happ", text)
        self.assertIn("48.0 КБ", text)
        self.assertIn("нужно от 1 МБ", text)
        self.assertIn("Подарок забран", text)
        self.assertEqual(bot.send_message.call_args.kwargs["reply_markup"].inline_keyboard[0][0].url, "https://t.me/anya")
        self.assertEqual(await stuck_alert.send_no_traffic(bot), 0)  # once per device

    async def test_switched_off(self):
        await self.device(1)
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch("app.config.get_settings", return_value=settings(no_traffic_alert_enabled=False)):
            self.assertEqual(await stuck_alert.send_no_traffic(bot), 0)


if __name__ == "__main__":
    unittest.main()
