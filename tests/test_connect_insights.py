"""IP history in the client card, the daily «Подключения за сутки» digest and the first-day activation rate."""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, stuck_alert

MB = 1024 * 1024


class DigestTextTest(unittest.TestCase):
    def test_groups_worst_first_and_names_the_worst(self):
        text = stuck_alert.format_digest([
            {"platform": "iOS", "client": "Happ", "total": 9, "works": 9, "no_traffic": 0, "never": 0},
            {"platform": "Android", "client": "v2rayNG", "total": 8, "works": 3, "no_traffic": 4, "never": 1},
            {"platform": "Windows", "client": "Hiddify", "total": 2, "works": 1, "no_traffic": 0, "never": 1},
        ])
        self.assertIn("Новых устройств: <b>19</b> · заработало <b>13</b> (68%)", text)
        lines = text.split("\n")
        first = next(i for i, x in enumerate(lines) if "v2rayNG" in x)
        self.assertLess(first, next(i for i, x in enumerate(lines) if "Hiddify" in x))
        self.assertIn("🔴 Android · v2rayNG — 4 без трафика, 1 не включались из 8", text)
        self.assertIn("🟡 Windows · Hiddify — 1 не включались из 2", text)
        self.assertIn("✅ iOS · Happ — все 9 работают", text)
        self.assertIn("Хуже всего: <b>Android · v2rayNG</b> — не работает у 62%", text)

    def test_nothing_new_nothing_sent(self):
        self.assertIsNone(stuck_alert.format_digest([]))


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class InsightsTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_ip_history_marks_shared_addresses(self):
        await self.pool.execute("INSERT INTO users (telegram_id) VALUES (1), (2), (3)")
        await self.pool.execute("INSERT INTO devices (id, telegram_id, title) VALUES (10, 1, 'a'), (11, 1, 'b'), (20, 2, 'c'), (30, 3, 'd')")
        await self.pool.execute("""INSERT INTO device_ips (device_id, ip, first_seen, last_seen) VALUES
            (10, '1.1.1.1', NOW() - INTERVAL '3 days', NOW()), (10, '2.2.2.2', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 hour'),
            (11, '1.1.1.1', NOW(), NOW()), (20, '1.1.1.1', NOW(), NOW()), (30, '1.1.1.1', NOW(), NOW() - INTERVAL '40 days'),
            (10, '9.9.9.9', NOW() - INTERVAL '50 days', NOW() - INTERVAL '45 days')""")
        got = await db.device_ip_history([10])
        self.assertEqual([(x["ip"], x["others"]) for x in got[10]], [("1.1.1.1", 1), ("2.2.2.2", 0)])  # own 2nd device and a 40-day-old one don't count

    async def test_digest_once_a_day_after_ten(self):
        await self.pool.execute("INSERT INTO users (telegram_id) VALUES (1)")
        await self.pool.execute("""INSERT INTO devices (telegram_id, title, platform, client, created_at, lifetime_traffic_bytes) VALUES
            (1, 'a', 'Android', 'v2rayNG', NOW() - INTERVAL '5 hours', 0),
            (1, 'b', 'Android', 'v2rayNG', NOW() - INTERVAL '5 hours', 10 * 1024 * 1024),
            (1, 'c', 'iOS', 'Happ', NOW() - INTERVAL '30 hours', 0)""")
        await self.pool.execute("UPDATE devices SET last_online_at = NOW() WHERE title = 'a'")
        bot = SimpleNamespace(send_message=AsyncMock())
        s = SimpleNamespace(connect_digest_enabled=True, no_traffic_alert_min_mb=1)
        early = datetime(2026, 11, 18, 6, 30, tzinfo=timezone.utc)  # 9:30 Moscow
        late = datetime(2026, 11, 18, 7, 5, tzinfo=timezone.utc)
        with patch("app.config.get_settings", return_value=s), patch.object(stuck_alert, "_targets", AsyncMock(return_value=[777])):
            self.assertFalse(await stuck_alert.send_digest(bot, early))
            self.assertTrue(await stuck_alert.send_digest(bot, late))
            self.assertFalse(await stuck_alert.send_digest(bot, late))
        text = bot.send_message.call_args.args[1]
        self.assertIn("Новых устройств: <b>2</b> · заработало <b>1</b> (50%)", text)  # the 30-hour-old one is yesterday's
        self.assertIn("Android · v2rayNG — 1 без трафика из 2", text)

    async def test_activation_counts_finished_days_only(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, bot_started_at, first_online_at) VALUES
            (1, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days' + INTERVAL '1 hour'),
            (2, NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day'),
            (3, NOW() - INTERVAL '3 days', NULL),
            (4, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour'),
            (5, NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days' + INTERVAL '2 hours')""")
        await self.pool.execute(f"""INSERT INTO devices (telegram_id, title, lifetime_traffic_bytes) VALUES
            (1, 'x', {5 * MB}), (2, 'x', {5 * MB}), (4, 'x', {5 * MB}), (5, 'x', 1000)""")
        got = await db.admin_activation()
        # 1 works in a day; 2 came online too late; 3 never; 5 online but no real traffic; 4 is not a finished day.
        self.assertEqual((got["week"]["new"], got["week"]["ok"], got["week"]["pct"]), (3, 1, 33))
        self.assertEqual((got["prev"]["new"], got["prev"]["ok"]), (1, 0))
        self.assertFalse(got["days"][-1]["done"])


if __name__ == "__main__":
    unittest.main()
