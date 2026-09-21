from contextlib import ExitStack
from types import SimpleNamespace
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch
from app import balance, db, nudge


class BalanceMessageCooldownTest(unittest.IsolatedAsyncioTestCase):
    async def test_shared_claim_and_failed_messages_do_not_suppress(self):
        conn=sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.executescript('''
            CREATE TABLE users (telegram_id INTEGER,low_balance_notified_at TEXT,bot_started_at TEXT,
                bot_blocked_at TEXT,blocked_at TEXT,billing_paused_at TEXT);
            CREATE TABLE message_log (telegram_id INTEGER,status TEXT,kind TEXT,created_at TEXT);
            INSERT INTO users VALUES (1,NULL,'2026-09-01',NULL,NULL,NULL);
        ''')
        async def fetchrow(sql,*args):
            sql=sql.replace("timezone('utc', now()) - INTERVAL '24 hours'", "'2026-09-20 12:00:00'")
            sql=sql.replace("timezone('utc', now())", "'2026-09-21 12:00:00'")
            return conn.execute(sql,{'1':args[0]}).fetchone()
        async def execute(sql,*args): return conn.execute(sql,{'1':args[0]})
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetchrow=fetchrow,execute=execute)):
            self.assertTrue(await db.claim_low_balance_notice(1))
            self.assertFalse(await db.claim_low_balance_notice(1))
            await db.release_low_balance_notice(1)
            for kind in ['nudge_trial_end','low_balance','cabinet_link','nudge_first_online']:
                conn.execute('DELETE FROM message_log')
                conn.execute('INSERT INTO message_log VALUES (1,?,?,?)',('sent',kind,'2026-09-21 11:00:00'))
                self.assertFalse(await db.claim_low_balance_notice(1))
            conn.execute("UPDATE message_log SET status='failed'")
            self.assertTrue(await db.claim_low_balance_notice(1))
            await db.release_low_balance_notice(1)
            conn.execute("UPDATE users SET billing_paused_at='2026-09-21'")
            self.assertFalse(await db.claim_low_balance_notice(1))

    async def test_zero_balance_sends_one_message_and_releases_failed_claim(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(db,'nudge_delivery_allowed',AsyncMock(return_value=True)))
            stack.enter_context(patch.object(db,'claim_low_balance_notice',AsyncMock(return_value=True)))
            release=stack.enter_context(patch.object(db,'release_low_balance_notice',AsyncMock()))
            stack.enter_context(patch.object(db,'log_bot_message',AsyncMock()))
            link=stack.enter_context(patch.object(balance,'send_cabinet_link_to',AsyncMock()))
            stack.enter_context(patch.object(balance,'payment_nudge_keyboard',return_value='topup'))
            bot=SimpleNamespace(send_message=AsyncMock())
            await balance._notify_empty(bot,1,6,set())
            bot.send_message.assert_awaited_once()
            link.assert_not_awaited()
            release.assert_not_awaited()
            bot.send_message.side_effect=TimeoutError()
            with patch.object(balance.logger,'warning'):
                await balance._notify_empty(bot,1,6,set())
            release.assert_awaited_once_with(1)

    async def test_warning_respects_shared_claim(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(nudge,'get_settings',return_value=SimpleNamespace(balance_enabled=True,vpn_day_price_rub=6)))
            stack.enter_context(patch.object(db,'flag_on',AsyncMock(return_value=False)))
            stack.enter_context(patch.object(db,'nudge_delivery_allowed',AsyncMock(return_value=True)))
            stack.enter_context(patch.object(db,'claim_low_balance_notice',AsyncMock(return_value=False)))
            stack.enter_context(patch.object(db,'list_due_trial_end_nudges',AsyncMock(return_value=[{'telegram_id':1}])))
            bot=SimpleNamespace(send_message=AsyncMock())
            self.assertEqual(await nudge.send_due_trial_end_nudges(bot),(0,[]))
            bot.send_message.assert_not_awaited()
