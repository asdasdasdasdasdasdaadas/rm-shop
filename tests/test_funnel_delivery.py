from aiogram.types import InlineKeyboardMarkup
from app.funnel_ui import funnel_keyboard
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app import db, nudge


class FunnelDeliveryTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(db, 'reserve_optional_message', AsyncMock(return_value=1)))
        self.stack.enter_context(patch.object(db, 'finish_optional_message', AsyncMock()))
        self.allowed = self.stack.enter_context(patch.object(db, 'nudge_delivery_allowed', AsyncMock(return_value=True)))
        self.log = self.stack.enter_context(patch.object(db, 'log_bot_message', AsyncMock()))
        self.mark = self.stack.enter_context(patch.object(db, 'mark_nudge_sent', AsyncMock()))
        self.stack.enter_context(patch.object(db, 'flag_on', AsyncMock(return_value=False)))
        self.stack.enter_context(patch.object(nudge.asyncio, 'sleep', AsyncMock()))
        self.stack.enter_context(patch.object(nudge, 'get_settings', return_value=SimpleNamespace(balance_enabled=True)))
        self.stack.enter_context(patch.object(nudge, 'onboarding_keyboard', side_effect=lambda **kw: InlineKeyboardMarkup(inline_keyboard=[])))
        self.stack.enter_context(patch.object(nudge, 'payment_nudge_keyboard', return_value=InlineKeyboardMarkup(inline_keyboard=[])))
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
            self.assertIn('включите VPN', body)
            self.assertNotIn('Всё готово', body)
            user.return_value={'first_online_at':'2026-09-21'}
            take.reset_mock()
            self.assertFalse(await nudge.send_first_device_thanks(self.bot,1))
            take.assert_not_awaited()


class RetryPolicySqlTest(IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(db, "notification_allowed", AsyncMock(return_value=True))
        p.start(); self.addCleanup(p.stop)

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
