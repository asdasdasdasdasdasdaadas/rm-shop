"""Funnel gifts after a broadcast gift, the one-time repair of burned gift steps.
Needs TEST_DATABASE_URL pointing at a disposable PostgreSQL database."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import asyncpg

from app import db, funnel_gifts, funnel_board

DSN = os.environ.get('TEST_DATABASE_URL')


@unittest.skipUnless(DSN, 'TEST_DATABASE_URL is not set')
class GiftEndTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
        self.addAsyncCleanup(self.pool.close)
        await self.pool.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
        await self.pool.execute(db.SCHEMA_PATH.read_text(encoding='utf-8'))
        settings = SimpleNamespace(vpn_day_price_rub=6)
        for patcher in (patch.object(db, '_pool', self.pool), patch.object(db, 'get_settings', return_value=settings),
                        patch('app.config.get_settings', return_value=settings)):
            patcher.start()
            self.addCleanup(patcher.stop)
        for uid in (1, 2, 3):
            await self.pool.execute("INSERT INTO users (telegram_id, bot_started_at) VALUES ($1, NOW()-INTERVAL '20 days')", uid)
        funnel_board._unburned = False

    async def test_unclaimed_broadcast_gift_does_not_block_funnel_gift(self):
        await funnel_gifts.issue_for_broadcast(1, 7)
        self.assertTrue(await funnel_gifts.can_issue(1))
        await self.pool.execute("UPDATE funnel_gifts SET claimed_at=NOW() WHERE telegram_id=1")
        self.assertFalse(await funnel_gifts.can_issue(1))
        await self.pool.execute("INSERT INTO funnel_gifts (telegram_id, step_id, days, expires_at) VALUES (2, 'x', 3, NOW())")
        self.assertFalse(await funnel_gifts.can_issue(2))

    async def test_burned_gift_steps_come_back_once(self):
        await funnel_board._ensure_tables()
        step = 'recovery-recover-idle-3'
        for uid in (1, 2, 3):
            await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id) VALUES ($1, $2)", uid, step)
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id) VALUES (1, 'recovery-recover-idle-1')")
        # 2 really got the message; 3 is the A/B control group, skipped on purpose.
        await self.pool.execute("""INSERT INTO message_log (kind, telegram_id, status, extra)
            VALUES ('nudge_recover_idle', 2, 'sent', jsonb_build_object('step_id', $1::text))""", step)
        exp = await self.pool.fetchval("INSERT INTO funnel_experiments (step_id) VALUES ($1) RETURNING id", step)
        await self.pool.execute("INSERT INTO funnel_experiment_users VALUES ($1, 3, 'control')", exp)
        graph = {'branches': [{'steps': [{'id': step, 'buttons': [funnel_board.GIFT_ACTION]},
                                         {'id': 'recovery-recover-idle-1', 'buttons': ['connect']}]}]}
        await funnel_board._unburn_gift_steps(graph)
        rows = await self.pool.fetch("SELECT telegram_id, step_id FROM funnel_step_sends ORDER BY 1, 2")
        self.assertEqual([tuple(r) for r in rows],
                         [(1, 'recovery-recover-idle-1'), (2, step), (3, step)])
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id) VALUES (1, $1)", step)
        funnel_board._unburned = False
        await funnel_board._unburn_gift_steps(graph)  # the kv flag keeps it to one run
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM funnel_step_sends WHERE step_id=$1", step), 3)

    async def test_board_quiet_steps(self):
        from unittest.mock import AsyncMock
        with patch.object(funnel_board, '_flag', AsyncMock(return_value=True)):
            graph = await funnel_board.default_graph()
        steps = {s['id']: s for b in graph['branches'] for s in b['steps']}
        for sid in ('recovery-recover-idle-1', 'recovery-recover-idle-2', 'recovery-recover-late-1',
                    'recovery-recover-late-2', 'recovery-recover-payment-1', 'recovery-recover-payment-2',
                    'recovery-recover-online-2', 'recovery-recover-online-3', 'recovery-recover-gift-2',
                    'recovery-recover-gift-3', 'info-1', 'recovery-recover-quality-1',
                    'recovery-recover-quality-2', 'recovery-recover-quality-3'):
            self.assertNotIn(sid, steps)  # removed: the 90-day statistics showed they bring nothing
        for sid in ('recovery-recover-online-1', 'recovery-recover-online-mid', 'recovery-recover-gift-1'):
            self.assertTrue(steps[sid]['enabled'], sid)
        gift = steps['recovery-recover-payment-3']
        self.assertEqual((gift['enabled'], gift['wait_hours'], gift['wait_from']), (True, 24, 'anchor'))

    async def test_gift_after_access_ended_counts_from_the_end(self):
        await funnel_board._ensure_tables()
        await self.pool.execute("UPDATE users SET first_online_at=NOW()-INTERVAL '5 days', balance_rub=0 WHERE telegram_id=1")
        await self.pool.execute("""INSERT INTO devices (telegram_id, title, last_online_at, last_billed_at)
            VALUES (1, 'P', NOW()-INTERVAL '1 hour', NOW()-INTERVAL '30 hours')""")
        step = funnel_board._step('recovery-recover-payment-3', 'recover_payment', 24, 'Дарим', ['claim_gift'])
        self.assertEqual(await funnel_board._due(step, None, 10, []), [])  # access ended 6 hours ago
        await self.pool.execute("UPDATE devices SET last_billed_at=NOW()-INTERVAL '49 hours'")
        self.assertEqual([r['telegram_id'] for r in await funnel_board._due(step, None, 10, [])], [1])

    async def test_one_broadcast_a_week(self):
        self.assertFalse(await db.got_broadcast_recently(1, 5))
        await self.pool.execute("""INSERT INTO message_log (kind, telegram_id, status, extra)
            VALUES ('broadcast', 1, 'sent', '{"broadcast_id": 5}')""")
        self.assertFalse(await db.got_broadcast_recently(1, 5))  # the same run
        self.assertTrue(await db.got_broadcast_recently(1, 6))
        self.assertTrue(await db.got_broadcast_recently(1, None))
        await self.pool.execute("UPDATE message_log SET created_at=NOW()-INTERVAL '8 days'")
        self.assertFalse(await db.got_broadcast_recently(1, 6))
        await self.pool.execute("""INSERT INTO message_log (kind, telegram_id, status, extra)
            VALUES ('broadcast', 1, 'failed', '{"broadcast_id": 7}')""")
        self.assertFalse(await db.got_broadcast_recently(1, 6))


if __name__ == '__main__':
    unittest.main()
