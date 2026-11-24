"""«Новые пользователи»: today's bars are Moscow hours from 00:00 to the current hour, and they add up to «+N сегодня»."""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app import db

MIDNIGHT = db.MSK_MIDNIGHT_SQL


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class SignupsHourlyTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_moscow_hours_up_to_now(self):
        from datetime import datetime, timedelta, timezone
        hour_now = datetime.now(timezone(timedelta(hours=3))).hour
        await self.pool.execute("SET TIME ZONE 'UTC'")   # the server's zone must not shift the hours
        await self.pool.execute(f"""INSERT INTO users (telegram_id, created_at) VALUES
            (1, {MIDNIGHT}),                                -- 00:00 MSK
            (2, {MIDNIGHT} + INTERVAL '59 minutes'),        -- still 00:xx
            (3, {MIDNIGHT} - INTERVAL '1 minute'),          -- yesterday 23:59: not today
            (4, date_trunc('hour', NOW()) + INTERVAL '1 second'),  -- the current hour
            (5, NOW() - INTERVAL '3 days')""")
        rows = await db.admin_signups_today_hourly()
        self.assertEqual([r["hour"] for r in rows], list(range(hour_now + 1)))
        by_hour = {r["hour"]: r["registered"] for r in rows}
        if hour_now == 0:
            self.assertEqual(by_hour, {0: 3})
        else:
            self.assertEqual(by_hour[0], 2)
            self.assertEqual(by_hour[hour_now], 1)
            self.assertEqual(sum(by_hour.values()), 3)
        today = await self.pool.fetchval(f"SELECT COUNT(*)::int FROM users WHERE created_at >= {MIDNIGHT}")
        self.assertEqual(sum(by_hour.values()), today)   # the bars add up to the big «+N»

    async def test_empty_day_is_all_zeros(self):
        rows = await db.admin_signups_today_hourly()
        self.assertTrue(rows)
        self.assertEqual({r["registered"] for r in rows}, {0})


if __name__ == "__main__":
    unittest.main()
