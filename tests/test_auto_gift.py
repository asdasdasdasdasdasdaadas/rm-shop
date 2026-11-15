"""«Подарок сразу на балансе» A/B test against a real schema. Needs TEST_DATABASE_URL (a disposable database)."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import asyncpg

from app import auto_gift, db

DSN = os.environ.get('TEST_DATABASE_URL')


@unittest.skipUnless(DSN, 'TEST_DATABASE_URL is not set')
class AutoGiftTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
        self.addAsyncCleanup(self.pool.close)
        await self.pool.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
        await self.pool.execute(db.SCHEMA_PATH.read_text(encoding='utf-8'))
        settings = SimpleNamespace(vpn_day_price_rub=6, trial_days=3, trial_enabled=True)
        for patcher in (patch.object(db, '_pool', self.pool), patch.object(db, 'get_settings', return_value=settings),
                        patch('app.referrals.get_settings', return_value=settings)):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def users(self, ids, started="NOW()"):
        for uid in ids:
            await self.pool.execute(f"INSERT INTO users (telegram_id, bot_started_at) VALUES ($1, {started})", uid)

    async def test_no_test_no_gift(self):
        await self.users([1])
        self.assertIsNone(await auto_gift.grant_if_auto(1))
        self.assertFalse((await db.get_user(1))['trial_used'])

    async def test_groups_gift_and_results(self):
        await self.users([900], "NOW() - INTERVAL '1 day'")  # came before the test: stays out
        await auto_gift.start()
        with self.assertRaises(ValueError):
            await auto_gift.start()
        await self.users(range(1, 41))
        given = {uid: await auto_gift.grant_if_auto(uid) for uid in range(1, 41)}
        arms = dict(await self.pool.fetch("SELECT telegram_id, arm FROM auto_gift_arms"))
        self.assertEqual(len(arms), 40)
        self.assertTrue(5 < sum(a == 'auto' for a in arms.values()) < 35)
        for uid, arm in arms.items():
            user = await db.get_user(uid)
            if arm == 'auto':
                self.assertEqual(given[uid], 18)
                self.assertTrue(user['trial_used'] and user['trial_waiting_connection'])
            else:
                self.assertIsNone(given[uid])
                self.assertFalse(user['trial_used'])
        # Once only, and the group never changes.
        auto_uid = next(u for u, a in arms.items() if a == 'auto')
        self.assertIsNone(await auto_gift.grant_if_auto(auto_uid))
        self.assertEqual(int((await db.get_user(auto_uid))['balance_rub']), 18)
        self.assertIsNone(await auto_gift.grant_if_auto(900))
        self.assertIsNone(await self.pool.fetchval("SELECT arm FROM auto_gift_arms WHERE telegram_id=900"))
        await self.pool.execute("UPDATE users SET first_online_at=NOW() WHERE telegram_id=$1", auto_uid)
        await self.pool.execute("""INSERT INTO payment_receipts (payment_key, telegram_id, plan_code, amount, first_payment, referral_enabled)
            VALUES ('k1', $1, 'topup_100', 100, TRUE, FALSE)""", auto_uid)
        view = await auto_gift.overview()
        arms_out = {a['arm']: a for a in view['items'][0]['arms']}
        self.assertEqual(arms_out['auto']['connected'], 1)
        self.assertEqual((arms_out['auto']['payers'], arms_out['auto']['rub']), (1, 100))
        self.assertEqual(arms_out['manual']['took_gift'], 0)
        self.assertEqual(len(view['items'][0]['verdicts']), 2)
        self.assertTrue(await auto_gift.stop())
        self.assertIsNone(await auto_gift.grant_if_auto(auto_uid + 100))


if __name__ == '__main__':
    unittest.main()
