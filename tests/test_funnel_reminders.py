from aiogram.types import InlineKeyboardMarkup
from app.funnel_ui import funnel_keyboard
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
                trial_end_nudge_at TEXT, low_balance_notified_at TEXT, trial_used INTEGER DEFAULT 1, billing_paused_at TEXT, welcome_support_pending BOOLEAN DEFAULT FALSE,
                has_paid_topup INTEGER DEFAULT 0, balance_warn3_at TEXT, balance_rub INTEGER DEFAULT 6, checkout_started_at TEXT, created_at TEXT DEFAULT '2026-09-18', trial_nudge_sent_at TEXT, invite_nudge_sent_at TEXT);
            CREATE TABLE devices (telegram_id INTEGER, kind TEXT);
            CREATE TABLE payment_receipts (telegram_id INTEGER, router_days INTEGER, created_at TEXT);
            CREATE TABLE message_log (telegram_id INTEGER, status TEXT, kind TEXT, created_at TEXT);
        ''')
        conn.executescript("ALTER TABLE users ADD COLUMN vpn_feedback TEXT; ALTER TABLE devices ADD COLUMN last_online_at TEXT; CREATE TABLE tickets(telegram_id INTEGER,status TEXT);")
        async def fetch(sql, *args):
            sql = sql.replace("timezone('utc', now())", 'NOW()').replace('::int', '')
            sql = sql.replace("NOW() - INTERVAL '48 hours'", "'2026-09-18 12:00:00'")
            sql = sql.replace("NOW() - INTERVAL '24 hours'", "'2026-09-19 12:00:00'")
            sql = sql.replace("NOW() - INTERVAL '30 minutes'", "'2026-09-20 11:30:00'")
            sql = sql.replace("NOW() - INTERVAL '20 minutes'", "'2026-09-20 11:40:00'")
            sql = sql.replace("NOW() - ($1 * INTERVAL '1 hour')", "datetime('2026-09-20 12:00:00', '-' || $1 || ' hours')")
            sql = sql.replace("u.first_online_at + INTERVAL '24 hours'", "datetime(u.first_online_at, '+24 hours')")
            sql = sql.replace("NOW() - INTERVAL '7 days'", "'2026-09-13 12:00:00'")
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
        conn.executemany('INSERT INTO devices (telegram_id,kind) VALUES (?,?)', [(1,'phone'),(1,'phone'),(2,'router'),(5,'phone')])
        with patch.object(db, '_pool_req', return_value=SimpleNamespace(fetch=fetch)):
            conn.execute("UPDATE users SET first_online_at='2026-09-18' WHERE telegram_id=1")
            # At 3 rub/device/day, two phones consume 6 rub; a router, paused user, and no-device user do not qualify.
            self.assertEqual([r['telegram_id'] for r in await db.list_due_trial_end_nudges(3)], [1])
            conn.execute("UPDATE users SET checkout_started_at='2026-09-20 11:55:00' WHERE telegram_id=1")
            conn.execute("INSERT INTO message_log VALUES (2,'sent','nudge_invite','2026-09-20 10:00:00')")
            conn.execute("INSERT INTO message_log VALUES (3,'failed','nudge_invite','2026-09-20 10:00:00')")
            self.assertEqual(await db.nudge_suppressed_ids(), [1,2])

    async def test_low_balance_message_has_no_inaccurate_hours(self):
        settings = SimpleNamespace(balance_enabled=True, vpn_day_price_rub=6)
        with patch.object(db, 'nudge_delivery_allowed', AsyncMock(return_value=True)), \
             patch.object(nudge, 'get_settings', return_value=settings), \
             patch.object(db, 'flag_on', AsyncMock(return_value=False)), \
             patch.object(db, 'rearm_balance_warnings', AsyncMock()), \
             patch.object(db, 'list_due_trial_end_nudges', AsyncMock(return_value=[{'telegram_id':1,'balance_rub':6,'device_count':2,'paid':True}])), \
             patch.object(db, 'claim_balance_ending_notice', AsyncMock(return_value=True)), \
             patch.object(nudge, 'notice_text', return_value='message') as text, \
             patch('app.trust.promise_available', AsyncMock(return_value=False)), \
             patch.object(nudge, '_deliver', AsyncMock(return_value=True)) as deliver:
            self.assertEqual(await nudge.send_due_trial_end_nudges(SimpleNamespace()), (1,[1]))
            text.assert_called_once_with('balance_ending_nudge')
            body = deliver.call_args.kwargs['body']
            self.assertIn('Остаток: <b>6 ₽</b>', body)
            self.assertNotIn('час', body)
            from app.balance_notifications import balance_keyboard
            self.assertEqual(deliver.call_args.kwargs['reply_markup'], balance_keyboard())
