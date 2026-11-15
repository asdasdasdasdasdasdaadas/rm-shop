"""«Застрял на подключении» alert against a real schema. Needs TEST_DATABASE_URL (a disposable database)."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import asyncpg

from app import db, stuck_alert

DSN = os.environ.get('TEST_DATABASE_URL')


@unittest.skipUnless(DSN, 'TEST_DATABASE_URL is not set')
class StuckAlertTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
        self.addAsyncCleanup(self.pool.close)
        await self.pool.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
        await self.pool.execute(db.SCHEMA_PATH.read_text(encoding='utf-8'))
        p = patch.object(db, '_pool', self.pool)
        p.start(); self.addCleanup(p.stop)
        p = patch.object(stuck_alert, '_targets', AsyncMock(return_value=[777]))
        p.start(); self.addCleanup(p.stop)

    async def device(self, uid, added, online=None, **user):
        await self.pool.execute("INSERT INTO users (telegram_id, first_name, username, trial_used) VALUES ($1, $2, $3, $4) "
                                "ON CONFLICT DO NOTHING", uid, user.get('name', 'Аня'), user.get('username'), True)
        await self.pool.execute(f"""INSERT INTO devices (telegram_id, title, platform, client, created_at, last_online_at)
            VALUES ($1, 'iPhone', 'iOS', 'Happ', NOW() - INTERVAL '{added}', {online or 'NULL'})""", uid)

    async def test_alerts_once_for_stuck_people_only(self):
        await self.device(1, '3 hours', username='anya')          # stuck: alert
        await self.device(2, '1 hour')                            # too early
        await self.device(3, '3 hours', online='NOW()')           # works
        await self.device(4, '5 days')                            # too old
        await self.device(5, '3 hours')
        await self.pool.execute("UPDATE users SET first_online_at=NOW() WHERE telegram_id=5")  # another device works
        bot = SimpleNamespace(send_message=AsyncMock())
        self.assertEqual(await stuck_alert.send_due(bot), 1)
        chat, text = bot.send_message.call_args.args
        self.assertEqual(chat, 777)
        self.assertIn('Застрял на подключении', text)
        self.assertIn('iPhone', text)
        self.assertIn('iOS · Happ', text)
        self.assertIn('3 ч', text)
        self.assertEqual(bot.send_message.call_args.kwargs['reply_markup'].inline_keyboard[0][0].url, 'https://t.me/anya')
        self.assertEqual(await stuck_alert.send_due(bot), 0)  # once per person
        self.assertEqual(bot.send_message.await_count, 1)

    async def test_no_username_no_button(self):
        await self.device(1, '3 hours')
        bot = SimpleNamespace(send_message=AsyncMock())
        await stuck_alert.send_due(bot)
        self.assertIsNone(bot.send_message.call_args.kwargs['reply_markup'])


if __name__ == '__main__':
    unittest.main()
