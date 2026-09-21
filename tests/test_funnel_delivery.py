from contextlib import ExitStack
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app import db, nudge


class FunnelDeliveryTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.allowed = self.stack.enter_context(patch.object(db, 'nudge_delivery_allowed', AsyncMock(return_value=True)))
        self.log = self.stack.enter_context(patch.object(db, 'log_bot_message', AsyncMock()))
        self.mark = self.stack.enter_context(patch.object(db, 'mark_nudge_sent', AsyncMock()))
        self.stack.enter_context(patch.object(db, 'flag_on', AsyncMock(return_value=False)))
        self.stack.enter_context(patch.object(nudge.asyncio, 'sleep', AsyncMock()))
        self.stack.enter_context(patch.object(nudge, 'get_settings', return_value=SimpleNamespace(balance_enabled=True)))
        self.stack.enter_context(patch.object(nudge, 'onboarding_keyboard', side_effect=lambda **kw: kw))
        self.stack.enter_context(patch.object(nudge, 'payment_nudge_keyboard', return_value='topup'))
        self.bot = SimpleNamespace(send_message=AsyncMock())

    async def deliver(self):
        return await nudge._deliver(self.bot, kind='nudge_trial', telegram_id=1, first_name=None,
                                    title='Gift', body='Gift', reply_markup=None)

    async def test_failure_is_not_completion_and_success_stops_retry(self):
        self.bot.send_message.side_effect = [TimeoutError('timeout'), None]
        self.assertFalse(await self.deliver())
        self.mark.assert_not_awaited()
        self.assertEqual(self.log.call_args.kwargs['status'], 'failed')
        self.assertTrue(await self.deliver())
        self.mark.assert_awaited_once_with(1, 'trial')

    async def test_retry_budget_blocks_send(self):
        self.allowed.return_value = False
        self.assertFalse(await self.deliver())
        self.bot.send_message.assert_not_awaited()
        self.mark.assert_not_awaited()

    async def test_failed_device_reminder_does_not_advance_stage(self):
        with patch.object(db, 'list_due_device_nudges', AsyncMock(return_value=[{'telegram_id':1,'has_device':True}])), \
             patch.object(db, 'mark_device_nudge_sent', AsyncMock()) as mark:
            self.bot.send_message.side_effect = TimeoutError()
            self.assertEqual(await nudge.send_due_device_nudges(self.bot), (0,[1]))
            mark.assert_not_awaited()

    async def test_return_messages_match_state_and_preserve_stage_on_failure(self):
        for online, balance, trial, segment, markup in [
            (None, 10, False, 'setup', {'gift':True,'has_device':False}),
            ('2026-09-01', 0, True, 'topup', 'topup'),
            ('2026-09-01', 20, True, 'return', {'has_device':False}),
        ]:
            for days in [7,10,15,20]:
                with self.subTest(segment=segment, days=days), \
                     patch.object(db, 'list_due_idle_nudges', AsyncMock(return_value=[dict(telegram_id=1,first_online_at=online,balance_rub=balance,trial_used=trial,idle_days=days)])), \
                     patch.object(db, 'mark_idle_nudge_sent', AsyncMock()) as mark, \
                     patch.object(nudge, 'notice_text', return_value='message') as text:
                    self.bot.send_message.side_effect = [TimeoutError(), None]
                    await nudge.send_due_idle_nudges(self.bot)
                    mark.assert_not_awaited()
                    await nudge.send_due_idle_nudges(self.bot)
                    mark.assert_awaited_once_with(1,days)
                    text.assert_called_with(f'idle_{segment}_{days}')
                    self.assertEqual(self.bot.send_message.call_args.kwargs['reply_markup'],markup)

    async def test_device_created_message_is_next_step_and_skips_connected(self):
        with patch.object(db, 'user_is_blocked', AsyncMock(return_value=False)), \
             patch.object(db, 'get_user', AsyncMock(return_value={'first_online_at':None})) as user, \
             patch.object(db, 'take_first_device_thanks', AsyncMock(return_value=True)) as take, \
             patch.object(db, 'restore_first_device_thanks', AsyncMock()) as restore:
            self.bot.send_message.side_effect = [TimeoutError(), None]
            self.assertFalse(await nudge.send_first_device_thanks(self.bot,1))
            restore.assert_awaited_once_with(1)
            self.assertTrue(await nudge.send_first_device_thanks(self.bot,1))
            body = self.bot.send_message.call_args.args[1]
            self.assertIn('Осталось подключить', body)
            self.assertNotIn('Всё готово', body)
            user.return_value={'first_online_at':'2026-09-21'}
            take.reset_mock()
            self.assertFalse(await nudge.send_first_device_thanks(self.bot,1))
            take.assert_not_awaited()


class RetryPolicySqlTest(IsolatedAsyncioTestCase):
    async def test_budget_delay_and_permanent_errors(self):
        import sqlite3
        import json
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE message_log (telegram_id INTEGER, kind TEXT, status TEXT, created_at TEXT, extra TEXT)')
        conn.execute('CREATE TABLE device_exit_feedback (token TEXT,telegram_id INTEGER,created_at TEXT,answered_at TEXT,reason TEXT,resolved_at TEXT)')
        conn.execute('CREATE TABLE devices (telegram_id INTEGER,last_online_at TEXT)')
        class BoolOr:
            def __init__(self): self.value=False
            def step(self, value): self.value = self.value or bool(value)
            def finalize(self): return int(self.value)
        conn.create_aggregate('BOOL_OR',1,BoolOr)
        async def fetchval(sql,*args):
            sql=sql.replace('::int','').replace('::boolean','')
            sql=sql.replace("created_at + GREATEST(120,\n                COALESCE((extra->>'retry_after'), 120)) * INTERVAL '1 second'", "datetime(created_at, '+' || MAX(120, COALESCE(extra->>'retry_after',120)) || ' seconds')")
            sql=sql.replace("NOW() - INTERVAL '24 hours'", "'2026-09-20 12:00:00'").replace('NOW()', "'2026-09-21 12:00:00'")
            return conn.execute(sql,{str(i):a for i,a in enumerate(args,1)}).fetchone()[0]
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetchval=fetchval)):
            self.assertTrue(await db.nudge_delivery_allowed(1,'nudge_trial'))
            conn.execute('INSERT INTO message_log VALUES (1,?,?,?,?)', ('nudge_trial','failed','2026-09-21 11:59:00','{}'))
            self.assertFalse(await db.nudge_delivery_allowed(1,'nudge_trial'))
            conn.execute("UPDATE message_log SET created_at='2026-09-21 11:57:00'")
            self.assertTrue(await db.nudge_delivery_allowed(1,'nudge_trial'))
            conn.execute('UPDATE message_log SET extra=?',(json.dumps({'retry_after':600}),))
            self.assertFalse(await db.nudge_delivery_allowed(1,'nudge_trial'))
            conn.execute('UPDATE message_log SET extra=?',(json.dumps({'permanent':True}),))
            self.assertFalse(await db.nudge_delivery_allowed(1,'nudge_trial'))
            conn.execute("UPDATE message_log SET extra='{}'")
            conn.executemany('INSERT INTO message_log VALUES (1,?,?,?,?)', [('nudge_trial','failed','2026-09-21 11:50:00','{}')]*2)
            self.assertFalse(await db.nudge_delivery_allowed(1,'nudge_trial'))
            self.assertTrue(await db.nudge_delivery_allowed(2,'nudge_trial'))
            conn.execute("UPDATE message_log SET created_at='2026-09-19 10:00:00'")
            self.assertTrue(await db.nudge_delivery_allowed(1,'nudge_trial'))


class IdleSelectionSqlTest(IsolatedAsyncioTestCase):
    async def test_never_connected_deleted_devices_active_and_finished_sequences(self):
        import sqlite3
        import json
        import re
        conn=sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory=sqlite3.Row
        conn.executescript('''
            CREATE TABLE users (telegram_id INTEGER, first_name TEXT, first_online_at TEXT, balance_rub INTEGER,
                trial_used INTEGER, bot_started_at TEXT, bot_blocked_at TEXT, blocked_at TEXT,
                billing_paused_at TEXT, idle_nudge_at TEXT, idle_nudge_step INTEGER);
            CREATE TABLE devices (telegram_id INTEGER, last_online_at TEXT);
        ''')
        async def fetch(sql,*args):
            # SQLite lacks LATERAL; inline the two scalar expressions without changing the selection rules.
            sql=re.sub(r'            CROSS JOIN LATERAL \(.*?\) step', '', sql, flags=re.S)
            last='COALESCE(seen.last_seen, u.first_online_at, u.bot_started_at)'
            step=f'(CASE WHEN u.idle_nudge_at IS NULL OR {last} > u.idle_nudge_at THEN 0 ELSE COALESCE(u.idle_nudge_step,0) END)'
            sql=sql.replace('activity.last_seen',last).replace('step.v',step)
            sql=re.sub(r"timezone\('utc', now\(\)\) - INTERVAL '(\d+) days'",r"datetime('2026-09-21 12:00:00', '-\1 days')",sql)
            sql=sql.replace('u.telegram_id = ANY($2::bigint[])','u.telegram_id IN (SELECT value FROM json_each($2))')
            return conn.execute(sql,{'1':args[0],'2':json.dumps(args[1])}).fetchall()
        for uid in range(1,7):
            conn.execute("INSERT INTO users (telegram_id,bot_started_at,balance_rub) VALUES (?,'2026-09-10',10)",(uid,))
        conn.execute("UPDATE users SET first_online_at='2026-09-11' WHERE telegram_id IN (2,3)")
        conn.execute("INSERT INTO devices VALUES (3,'2026-09-21 11:00:00')")
        conn.execute("UPDATE users SET bot_blocked_at='2026-09-20' WHERE telegram_id=4")
        conn.execute("UPDATE users SET billing_paused_at='2026-09-20' WHERE telegram_id=5")
        conn.execute("UPDATE users SET idle_nudge_at='2026-09-20',idle_nudge_step=20 WHERE telegram_id=6")
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetch=fetch)):
            rows=await db.list_due_idle_nudges()
            self.assertEqual([r['telegram_id'] for r in rows],[1,2])
            self.assertEqual([r['idle_days'] for r in rows],[10,10])
            self.assertFalse(rows[1]['has_device'])
            self.assertEqual([r['telegram_id'] for r in await db.list_due_idle_nudges(skip_ids=[1])],[2])
            # A new successful connection resets the old completed sequence.
            conn.execute("INSERT INTO devices VALUES (6,'2026-09-13')")
            conn.execute("UPDATE users SET idle_nudge_at='2026-09-01' WHERE telegram_id=6")
            self.assertEqual([r['telegram_id'] for r in await db.list_due_idle_nudges()],[1,2,6])
