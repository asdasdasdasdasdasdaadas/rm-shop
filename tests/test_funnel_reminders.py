from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

from app import checkout, db, nudge


class ResumeCheckoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_invoice_states_and_owner_token(self):
        user = dict(checkout_token='token', checkout_started_at=datetime.now(timezone.utc)-timedelta(minutes=11),
                    checkout_payment_id='payment', checkout_url='https://example.com/invoice')
        rp = SimpleNamespace(get_payment=AsyncMock())
        with patch.object(db, 'get_user', AsyncMock(return_value=user)), \
             patch.object(db, 'cancel_payment_nudge', AsyncMock()) as cancel:
            for status, expected in [('pending','active'), ('expired','expired'), ('paid','closed'),
                                     ('processing','processing'), ('unknown','unavailable')]:
                rp.get_payment.return_value = {'status':status}
                state, url = await checkout.resume_checkout(1, 'token', rp)
                self.assertEqual(state, expected)
                self.assertEqual(url, user['checkout_url'] if expected == 'active' else None)
            cancel.assert_awaited_once_with(1, 'token')
            rp.get_payment.reset_mock()
            self.assertEqual(await checkout.resume_checkout(1, 'someone-elses-token', rp), ('stale',None))
            rp.get_payment.assert_not_awaited()
            user['checkout_payment_id'] = None  # Stars invoice
            self.assertEqual((await checkout.resume_checkout(1, 'token', None))[0], 'active')
            user['checkout_started_at'] -= timedelta(minutes=10)
            self.assertEqual(await checkout.resume_checkout(1, 'token', None), ('expired',None))

    async def test_provider_failure_and_payment_race(self):
        user = dict(checkout_token='token', checkout_started_at=datetime.now(timezone.utc),
                    checkout_payment_id='payment', checkout_url='https://example.com/invoice')
        rp = SimpleNamespace(get_payment=AsyncMock(side_effect=RuntimeError()))
        with patch.object(db, 'get_user', AsyncMock(return_value=user)):
            self.assertEqual(await checkout.resume_checkout(1, 'token', rp), ('unavailable',None))
        rp.get_payment = AsyncMock(return_value={'status':'pending'})
        with patch.object(db, 'get_user', AsyncMock(side_effect=[user, {**user, 'checkout_started_at':None}])):
            self.assertEqual(await checkout.resume_checkout(1, 'token', rp), ('stale',None))


class FunnelSelectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_gift_first_connection_balance_and_cooldown(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.executescript('''
            CREATE TABLE users (telegram_id INTEGER, first_name TEXT, blocked_at TEXT, bot_blocked_at TEXT,
                bot_started_at TEXT, gift_claimed_at TEXT, first_online_at TEXT, device_nudge_count INTEGER DEFAULT 0, device_nudge_at TEXT,
                trial_end_nudge_at TEXT, low_balance_notified_at TEXT, trial_used INTEGER DEFAULT 1, billing_paused_at TEXT,
                has_paid_topup INTEGER DEFAULT 0, balance_rub INTEGER DEFAULT 6, checkout_started_at TEXT, created_at TEXT DEFAULT '2026-09-18', trial_nudge_sent_at TEXT, invite_nudge_sent_at TEXT);
            CREATE TABLE devices (telegram_id INTEGER, kind TEXT);
            CREATE TABLE message_log (telegram_id INTEGER, status TEXT, kind TEXT, created_at TEXT);
        ''')
        async def fetch(sql, *args):
            sql = sql.replace("timezone('utc', now())", 'NOW()').replace('::int', '')
            sql = sql.replace("NOW() - INTERVAL '48 hours'", "'2026-09-18 12:00:00'")
            sql = sql.replace("NOW() - INTERVAL '24 hours'", "'2026-09-19 12:00:00'")
            sql = sql.replace("NOW() - INTERVAL '30 minutes'", "'2026-09-20 11:30:00'")
            sql = sql.replace("NOW() - INTERVAL '20 minutes'", "'2026-09-20 11:40:00'")
            sql = sql.replace("NOW() - ($1 * INTERVAL '1 hour')", "datetime('2026-09-20 12:00:00', '-' || $1 || ' hours')")
            sql = sql.replace('GREATEST(', 'MAX(')
            sql = sql.replace('u.telegram_id = ANY($2::bigint[])', 'u.telegram_id IN (SELECT value FROM json_each($2))')
            import json
            return conn.execute(sql, {str(i): json.dumps(a) if isinstance(a, list) else a for i,a in enumerate(args,1)}).fetchall()
        for uid in range(1,7):
            conn.execute("INSERT INTO users (telegram_id, bot_started_at, gift_claimed_at) VALUES (?, '2026-09-19', '2026-09-20 11:00:00')", (uid,))
        conn.execute("UPDATE users SET first_online_at='2026-09-20 11:20:00' WHERE telegram_id=2")
        conn.execute("UPDATE users SET device_nudge_count=1, device_nudge_at='2026-09-20 10:00:00' WHERE telegram_id=3")
        conn.execute("UPDATE users SET gift_claimed_at='2026-09-20 11:45:00' WHERE telegram_id=4")
        conn.execute("UPDATE users SET billing_paused_at='2026-09-20' WHERE telegram_id=5")
        conn.executemany('INSERT INTO devices VALUES (?,?)', [(1,'phone'),(1,'phone'),(2,'router'),(5,'phone')])
        with patch.object(db, '_pool_req', return_value=SimpleNamespace(fetch=fetch)):
            self.assertEqual([r['telegram_id'] for r in await db.list_due_device_nudges(skip_ids=[5,6])], [1])
            # Legacy device creation set count=3 without actually sending a reminder.
            conn.execute("UPDATE users SET device_nudge_count=3 WHERE telegram_id=1")
            rows = await db.list_due_device_nudges(skip_ids=[5,6])
            self.assertEqual([r['telegram_id'] for r in rows], [1])
            self.assertTrue(rows[0]['has_device'])
            # An unclaimed gift is eligible without a device, even with a positive balance.
            conn.execute("UPDATE users SET trial_used=0, gift_claimed_at=NULL WHERE telegram_id=6")
            self.assertEqual([r['telegram_id'] for r in await db.list_due_trial_nudges()], [6])
            conn.execute("UPDATE users SET trial_used=1 WHERE telegram_id=6")
            self.assertEqual(await db.list_due_trial_nudges(), [])
            # Payment or device alone is not enough to ask for recommendations.
            conn.execute("UPDATE users SET has_paid_topup=1 WHERE telegram_id=6")
            self.assertEqual(await db.list_due_invite_nudges(), [])
            conn.execute("UPDATE users SET first_online_at='2026-09-18 10:00:00' WHERE telegram_id=6")
            self.assertEqual([r['telegram_id'] for r in await db.list_due_invite_nudges()], [6])
            conn.execute("UPDATE users SET invite_nudge_sent_at='2026-09-20' WHERE telegram_id=6")
            self.assertEqual(await db.list_due_invite_nudges(), [])
            # At 3 rub/device/day, two phones consume 6 rub; a router, paused user, and no-device user do not qualify.
            self.assertEqual([r['telegram_id'] for r in await db.list_due_trial_end_nudges(3)], [1])
            conn.execute("UPDATE users SET checkout_started_at='2026-09-20 11:55:00' WHERE telegram_id=1")
            conn.execute("INSERT INTO message_log VALUES (2,'sent','nudge_invite','2026-09-20 10:00:00')")
            conn.execute("INSERT INTO message_log VALUES (3,'failed','nudge_invite','2026-09-20 10:00:00')")
            self.assertEqual(await db.nudge_suppressed_ids(), [1,2])

    async def test_low_balance_message_has_hours_and_topup(self):
        settings = SimpleNamespace(balance_enabled=True, vpn_day_price_rub=6)
        with patch.object(db, 'nudge_delivery_allowed', AsyncMock(return_value=True)), \
             patch.object(nudge, 'get_settings', return_value=settings), \
             patch.object(db, 'flag_on', AsyncMock(return_value=False)), \
             patch.object(db, 'list_due_trial_end_nudges', AsyncMock(return_value=[{'telegram_id':1,'balance_rub':6,'device_count':2}])), \
             patch.object(db, 'claim_low_balance_notice', AsyncMock(return_value=True)), \
             patch.object(db, 'mark_trial_end_nudge_sent', AsyncMock()), \
             patch.object(db, 'log_bot_message', AsyncMock()), \
             patch.object(nudge, 'payment_nudge_keyboard', return_value='topup'), \
             patch.object(nudge, 'notice_text', return_value='message') as text, \
             patch.object(nudge.asyncio, 'sleep', AsyncMock()):
            bot = SimpleNamespace(send_message=AsyncMock())
            self.assertEqual(await nudge.send_due_trial_end_nudges(bot), (1,[1]))
            text.assert_called_once_with('trial_end_nudge', hours=12, devices=2)
            bot.send_message.assert_awaited_once_with(1,'message',reply_markup='topup')
