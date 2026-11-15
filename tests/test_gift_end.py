"""Funnel gifts after a broadcast gift, the one-time repair of burned gift steps, and «почему не продолжили».
Needs TEST_DATABASE_URL pointing at a disposable PostgreSQL database."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import asyncpg

from app import db, funnel_gifts, funnel_board, gift_end_feedback

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

    async def test_why_question_reaches_exhausted_non_payers_once(self):
        from app.recovery_funnel import WHY_ID, WHY_TEXT, WHY_BUTTONS
        await funnel_board._ensure_tables()
        await self.pool.execute("""UPDATE users SET first_online_at=NOW()-INTERVAL '20 days', balance_rub=0
            WHERE telegram_id IN (1, 2)""")
        await self.pool.execute("""INSERT INTO devices (telegram_id, title, last_online_at, last_billed_at)
            VALUES (1, 'P', NOW()-INTERVAL '10 days', NOW()-INTERVAL '10 days')""")
        await self.pool.execute("INSERT INTO payments (telegram_id, plan_code) VALUES (2, 'topup_100')")
        step = funnel_board._step(WHY_ID, 'recover_why', 3, WHY_TEXT, WHY_BUTTONS)
        due = await funnel_board._due(step, None, 10, [])
        self.assertEqual([r['telegram_id'] for r in due], [1])  # 2 has paid, 3 never connected
        self.assertTrue(await gift_end_feedback.save(1, 'payment'))
        self.assertEqual(await funnel_board._due(step, None, 10, []), [])
        self.assertTrue(await gift_end_feedback.save(1, 'price'))
        self.assertFalse(await gift_end_feedback.save(1, 'nonsense'))
        self.assertEqual(await gift_end_feedback.stats(), [{'reason': 'price', 'users': 1, 'label': 'Дорого'}])

    async def test_board_has_question_and_quiet_steps(self):
        from unittest.mock import AsyncMock
        with patch.object(funnel_board, '_flag', AsyncMock(return_value=True)):
            graph = await funnel_board.default_graph()
        steps = {s['id']: s for b in graph['branches'] for s in b['steps']}
        self.assertTrue(steps['recovery-recover-why-1']['enabled'])
        for sid in ('recovery-recover-idle-1', 'recovery-recover-idle-2', 'recovery-recover-late-1',
                    'recovery-recover-late-2', 'recovery-recover-payment-1', 'recovery-recover-payment-2'):
            self.assertFalse(steps[sid]['enabled'], sid)
        self.assertTrue(steps['recovery-recover-payment-3']['enabled'])
        unpaid = next(b for b in graph['branches'] if b['id'] == 'unpaid')
        self.assertEqual(unpaid['steps'][0]['id'], 'recovery-recover-why-1')
        with patch('app.keyboards.mini_app_url', return_value=None):
            try:
                kb = funnel_board.markup(steps['recovery-recover-why-1']['buttons'], 1)
            except (ImportError, TypeError):  # local Python 3.9 cannot build the widget types
                return
        datas = [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data]
        self.assertEqual(datas[:4], ['giftwhy:price', 'giftwhy:broken', 'giftwhy:payment', 'giftwhy:later'])


if __name__ == '__main__':
    unittest.main()
