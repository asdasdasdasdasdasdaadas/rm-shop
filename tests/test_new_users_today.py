"""«Новые пользователи · сегодня» counts from midnight in Moscow, not the last 24 hours."""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app import db

MIDNIGHT = db.MSK_MIDNIGHT_SQL


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class NewUsersTodayTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_yesterday_evening_is_not_today(self):
        await self.pool.execute(f"""INSERT INTO users (telegram_id, created_at) VALUES
            (1, {MIDNIGHT}),                               -- right at midnight: today
            (2, {MIDNIGHT} - INTERVAL '1 minute'),         -- yesterday 23:59, within 24 hours
            (3, NOW() - INTERVAL '3 days')""")
        today = await self.pool.fetchval(f"SELECT COUNT(*)::int FROM users WHERE created_at >= {MIDNIGHT}")
        day = await self.pool.fetchval("SELECT COUNT(*)::int FROM users WHERE created_at >= NOW() - INTERVAL '1 day'")
        self.assertEqual(today, 1)   # yesterday 23:59 is not today…
        self.assertEqual(day, 2)     # …though it is within the last 24 hours
        import inspect
        self.assertIn("created_at >= {MSK_MIDNIGHT_SQL})::int AS new_1d", inspect.getsource(db.admin_stats))


if __name__ == "__main__":
    unittest.main()
