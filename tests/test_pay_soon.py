"""«Скоро закончится баланс»: only regular VPN users, not those whose access ended or who barely tried it."""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app import db


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class PaySoonTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_only_regular_users_whose_vpn_is_on(self):
        week, mb = "NOW() - INTERVAL '7 days'", 1024 * 1024
        await self.pool.execute(f"""INSERT INTO users (telegram_id, first_name, balance_rub, first_online_at) VALUES
            (1, 'Пользуется', 8, {week}), (2, 'Отключился давно', 0, {week}), (3, 'Не заходит', 8, {week}),
            (4, 'Много денег', 500, {week}), (5, 'Первый день', 8, NOW()), (6, 'Почти без трафика', 8, {week}),
            (7, 'Позавчера', 8, {week})""")
        await self.pool.execute(f"""INSERT INTO devices (telegram_id, title, kind, panel_status, last_billed_at, last_online_at, lifetime_traffic_bytes) VALUES
            (1, 'a', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour', {500 * mb}),
            (2, 'b', 'phone', 'DISABLED', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days', {500 * mb}),
            (3, 'c', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '10 days', {500 * mb}),
            (4, 'd', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour', {500 * mb}),
            (5, 'e', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour', {500 * mb}),
            (6, 'f', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour', {5 * mb}),
            (7, 'g', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 days', {500 * mb})""")
        people = await db.admin_list_pay_soon(6)
        self.assertEqual([p["telegram_id"] for p in people], [1])
        self.assertEqual(people[0]["days_left"], 1.3)
        self.assertEqual((await db.admin_pay_soon_counts(6))["total"], 1)


    async def test_daily_users_week_streak_and_counts(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, balance_rub) VALUES
            (1, 'Каждый день', 120), (2, 'Пять из семи', 40), (3, 'Иногда', 10)""")
        today = "(timezone('utc', now()))::date"
        await self.pool.execute(f"""INSERT INTO online_days (telegram_id, day)
            SELECT 1, {today} - g FROM generate_series(0, 9) g
            UNION ALL SELECT 2, {today} - g FROM generate_series(0, 6) g WHERE g NOT IN (2, 4)
            UNION ALL SELECT 3, {today} - 1""")
        got = await db.admin_daily_users()
        self.assertEqual((got["every_day"], got["most_days"], got["today"]), (1, 1, 2))
        first, second = got["people"]
        self.assertEqual((first["telegram_id"], first["week"], first["streak"], first["days"]), (1, 7, 10, [True] * 7))
        self.assertEqual((second["telegram_id"], second["week"], second["streak"]), (2, 5, 2))
        self.assertEqual(second["days"], [True, True, False, True, False, True, True])


if __name__ == "__main__":
    unittest.main()
