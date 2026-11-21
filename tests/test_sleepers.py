"""«Спящие» and the panel cleanup of devices that never connected."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, sleepers


def settings(**kw):
    return SimpleNamespace(**{"vpn_day_price_rub": 10, "balance_topup_min": 50, "panel_cleanup_enabled": True,
                              "panel_cleanup_days": 30, **kw})


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class SleepersTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(db, "get_settings", return_value=SimpleNamespace(vpn_day_price_rub=10)),
                  patch.object(sleepers, "get_settings", return_value=settings())):
            p.start()
            self.addCleanup(p.stop)
        # 1 sleeper without a device; 2 new; 3 paid; 4 sleeper with a device that never connected;
        # 5 old but added a device two days ago; 6 old but connected.
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, bot_started_at, has_paid_topup, first_online_at) VALUES
            (1, 'А', NOW() - INTERVAL '30 days', FALSE, NULL), (2, 'Б', NOW() - INTERVAL '5 days', FALSE, NULL),
            (3, 'В', NOW() - INTERVAL '40 days', TRUE, NULL), (4, 'Г', NOW() - INTERVAL '100 days', FALSE, NULL),
            (5, 'Д', NOW() - INTERVAL '50 days', FALSE, NULL), (6, 'Е', NOW() - INTERVAL '50 days', FALSE, NOW())""")
        await self.pool.execute("""INSERT INTO devices (id, telegram_id, title, remnawave_id, created_at) VALUES
            (40, 4, 'iPhone', 940, NOW() - INTERVAL '60 days'), (50, 5, 'Mac', 950, NOW() - INTERVAL '2 days')""")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def ids(self, audience):
        return await db.list_broadcast_ids(audience)

    async def test_who_is_asleep_and_where_they_get_messages(self):
        self.assertEqual(await self.ids("sleepers"), [1, 4])
        self.assertNotIn(1, await self.ids("all"))
        self.assertNotIn(4, await self.ids("all"))
        self.assertIn(2, await self.ids("all"))
        self.assertIn(1, await self.ids("everyone"))
        counts = await db.broadcast_audience_counts()
        self.assertEqual(counts["sleepers"], 2)
        # The funnel is over for sleepers: automatic messages get no slot; a manual broadcast still does.
        self.assertIsNone(await db.reserve_optional_message(1, "nudge_test"))
        self.assertIsNotNone(await db.reserve_optional_message(1, "broadcast", manual=True))
        stats = await db.admin_sleepers()
        self.assertEqual((stats["total"], stats["no_device"], stats["no_online"], stats["older"], stats["quarter"]), (2, 1, 1, 1, 1))

    async def test_cleanup_waits_then_removes_never_online_devices(self):
        await self.pool.execute("""INSERT INTO devices (id, telegram_id, title, remnawave_id, created_at, lifetime_traffic_bytes) VALUES
            (60, 6, 'Old used', 960, NOW() - INTERVAL '60 days', 5000)""")
        rw = SimpleNamespace(delete_panel_user=AsyncMock())
        self.assertEqual(await sleepers.cleanup_panel(rw), 0)  # the first run only sets the start, 3 days ahead
        rw.delete_panel_user.assert_not_awaited()
        await db.set_kv(sleepers.CLEANUP_FROM_KEY, (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
        self.assertEqual(await sleepers.cleanup_panel(rw), 1)
        rw.delete_panel_user.assert_awaited_once_with(940)
        left = [r["id"] for r in await self.pool.fetch("SELECT id FROM devices ORDER BY id")]
        self.assertEqual(left, [50, 60])  # too new, and one that carried traffic
        note = await self.pool.fetchval("SELECT note FROM billing_events WHERE kind='device_delete' AND source='cleanup'")
        self.assertIn("не подключалось 30 дней", note)
        self.assertEqual((await db.admin_sleepers())["cleaned"], 1)


if __name__ == "__main__":
    unittest.main()
