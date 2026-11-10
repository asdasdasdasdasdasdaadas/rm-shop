"""Funnel counters against the real schema. Needs TEST_DATABASE_URL pointing at a disposable PostgreSQL database."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import asyncpg

from app import db

DSN = os.environ.get('TEST_DATABASE_URL')


@unittest.skipUnless(DSN, 'TEST_DATABASE_URL is not set')
class FunnelTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
        self.addAsyncCleanup(self.pool.close)
        await self.pool.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
        await self.apply_schema()
        for patcher in (patch.object(db, '_pool', self.pool),
                        patch.object(db, 'get_settings', return_value=SimpleNamespace(vpn_day_price_rub=6))):
            patcher.start()
            self.addCleanup(patcher.stop)
        await self.user(1)

    async def apply_schema(self):
        await self.pool.execute(db.SCHEMA_PATH.read_text(encoding='utf-8'))

    async def user(self, telegram_id, **fields):
        fields = {'bot_started_at': "NOW() - INTERVAL '3 days'", **fields}
        await self.pool.execute(
            f"INSERT INTO users (telegram_id, {', '.join(fields)}) VALUES ({int(telegram_id)}, {', '.join(fields.values())})")

    async def counts(self):
        return db._funnel_row(await self.pool.fetchrow(db._funnel_cte() + db._FUNNEL_SELECT, None, None))

    async def test_unpaid_stars_checkout(self):
        await self.pool.execute("UPDATE users SET first_checkout_at = NOW() - INTERVAL '1 hour'")
        row = await self.counts()
        self.assertEqual((row['checkout'], row['checkout_drop'], row['paid']), (1, 1, 0))

    async def test_repeat_stars_and_mixed_payments(self):
        await self.pool.execute("INSERT INTO payments (telegram_id, plan_code) VALUES (1, 'topup_100')")
        self.assertEqual((await self.counts())['repeat_paid'], 0)
        await self.pool.execute("INSERT INTO pay_orders (order_id, telegram_id, plan_code, status) VALUES ('o1', 1, 'topup_100', 'granted')")
        row = await self.counts()
        self.assertEqual((row['paid'], row['repeat_paid']), (1, 1))

    async def test_device_milestone_survives_deleted_device(self):
        await db.add_device(1, 'iPhone', 10)
        await self.pool.execute("UPDATE users SET first_online_at = NOW()")
        await self.pool.execute('DELETE FROM devices')
        row = await self.counts()
        self.assertEqual((row['device'], row['connected'], row['device_no_online']), (1, 1, 0))
        self.assertIsNotNone(await self.pool.fetchval('SELECT first_device_at FROM users WHERE telegram_id = 1'))

    async def test_first_device_is_kept_when_another_is_added(self):
        await db.add_device(1, 'iPhone', 10)
        first = await self.pool.fetchval('SELECT first_device_at FROM users WHERE telegram_id = 1')
        await db.add_device(1, 'Mac', 11)
        self.assertEqual(await self.pool.fetchval('SELECT first_device_at FROM users WHERE telegram_id = 1'), first)

    async def test_backfill_uses_earliest_device_or_connection(self):
        await self.user(2, first_online_at="NOW() - INTERVAL '2 days'")
        await self.pool.execute("INSERT INTO devices (telegram_id, title, created_at) VALUES (2, 'Mac', NOW())")
        await self.user(3, first_online_at="NOW() - INTERVAL '1 day'")
        await self.pool.execute('UPDATE users SET first_device_at = NULL')
        await self.apply_schema()
        rows = dict(await self.pool.fetch(
            'SELECT telegram_id, first_device_at = first_online_at FROM users WHERE telegram_id IN (2, 3)'))
        self.assertEqual(rows, {2: True, 3: True})
        self.assertIsNone(await self.pool.fetchval('SELECT first_device_at FROM users WHERE telegram_id = 1'))

    async def test_trial_is_not_activation(self):
        await self.pool.execute('UPDATE users SET trial_used = TRUE')
        row = await self.counts()
        self.assertEqual((row['trial'], row['device'], row['connected']), (1, 0, 0))

    async def test_invitee_historical_connection(self):
        await self.user(2, referred_by='1', first_device_at="NOW() - INTERVAL '2 days'", first_online_at="NOW() - INTERVAL '2 days'")
        row = await self.counts()
        self.assertEqual((row['inv_device'], row['inv_connected']), (1, 1))


if __name__ == '__main__':
    unittest.main()
