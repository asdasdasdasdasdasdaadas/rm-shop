from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, nudge
from app.keyboards import payment_nudge_keyboard


class PaymentNudgeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(db, "nudge_delivery_allowed", AsyncMock(return_value=True)))
        self.flags = self.stack.enter_context(patch.object(db, 'flag_on', AsyncMock(side_effect=lambda key, **kw: key == 'payment_nudge')))
        self.rows = self.stack.enter_context(patch.object(db, 'list_due_payment_nudges', AsyncMock(return_value=[
            {'telegram_id': 1, 'checkout_token': 'current', 'checkout_payment_id': 'pay-1'}])))
        self.claim = self.stack.enter_context(patch.object(db, 'claim_payment_nudge', AsyncMock(return_value=True)))
        self.cancel = self.stack.enter_context(patch.object(db, 'cancel_payment_nudge', AsyncMock()))
        self.deliver = self.stack.enter_context(patch.object(nudge, '_deliver', AsyncMock(return_value=True)))
        self.stack.enter_context(patch.object(nudge, 'payment_nudge_keyboard', return_value=None))
        self.stack.enter_context(patch.object(nudge, 'notice_text', return_value='Reminder'))
        self.rp = SimpleNamespace(get_payment=AsyncMock(return_value={'status':'pending'}))

    async def test_delivery_failure_releases_current_invoice_for_retry(self):
        self.deliver.return_value=False
        with patch.object(db, 'release_payment_nudge', AsyncMock()) as release:
            self.assertEqual(await nudge.send_due_payment_nudges(None,self.rp),(0,[1]))
            release.assert_awaited_once_with(1,'current')

    async def test_pending_payment_sends_once_claimed(self):
        self.assertEqual(await nudge.send_due_payment_nudges(None, self.rp), (1, [1]))
        self.claim.assert_awaited_once_with(1, 'current')
        self.deliver.assert_awaited_once()

    async def test_paid_refunded_and_unknown_are_not_reminded(self):
        for status in ('paid', 'succeeded', 'refunded', 'unknown'):
            self.rp.get_payment.return_value = {'status':status}
            self.assertEqual(await nudge.send_due_payment_nudges(None, self.rp), (0, []))
        self.claim.assert_not_awaited()
        self.deliver.assert_not_awaited()

    async def test_provider_failure_defers_without_consuming_reminder(self):
        self.rp.get_payment.side_effect = RuntimeError('temporary')
        with patch.object(nudge.logger, 'exception'):
            self.assertEqual(await nudge.send_due_payment_nudges(None, self.rp), (0, []))
        self.claim.assert_not_awaited()

    async def test_payment_or_new_checkout_racing_with_scan_prevents_send(self):
        self.claim.return_value = False
        self.assertEqual(await nudge.send_due_payment_nudges(None, self.rp), (0, []))
        self.deliver.assert_not_awaited()

    async def test_stars_uses_database_claim_without_provider(self):
        self.rows.return_value[0]['checkout_payment_id'] = None
        self.assertEqual(await nudge.send_due_payment_nudges(None), (1, [1]))

    async def test_disabled_reminders_do_not_scan(self):
        self.flags.side_effect = lambda key, **kw: False
        self.assertEqual(await nudge.send_due_payment_nudges(None, self.rp), (0, []))
        self.rows.assert_not_awaited()

    def test_button_opens_topup_and_preserves_existing_query(self):
        with patch('app.keyboards.mini_app_url', return_value='https://example.com/?a=1'):
            keyboard = payment_nudge_keyboard()
        self.assertEqual(keyboard.inline_keyboard[0][0].web_app.url, 'https://example.com/?a=1&screen=topup')


class PaymentNudgeStorageTest(unittest.IsolatedAsyncioTestCase):
    async def test_due_window_deduplication_cancellation_and_completed_stars(self):
        import sqlite3
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, checkout_token TEXT,
                first_checkout_at TEXT, checkout_started_at TEXT, checkout_payment_id TEXT, checkout_url TEXT, checkout_nudge_at TEXT,
                payment_nudge_at TEXT, bot_started_at TEXT, blocked_at TEXT, bot_blocked_at TEXT,
                has_paid_topup INTEGER DEFAULT 0);
            CREATE TABLE payments (telegram_id INTEGER, created_at TEXT);
        """)
        def query(sql, args):
            sql = sql.replace("NOW() - INTERVAL '10 minutes'", "'2026-09-19 11:50:00'")
            sql = sql.replace("NOW() - INTERVAL '24 hours'", "'2026-09-18 12:00:00'")
            sql = sql.replace('NOW()', "'2026-09-19 12:00:00'").replace('UPDATE users u ', 'UPDATE users AS u ')
            return conn.execute(sql, {str(i): x for i, x in enumerate(args, 1)})
        async def fetch(sql, *args): return query(sql,args).fetchall()
        async def fetchrow(sql, *args): return query(sql,args).fetchone()
        async def execute(sql, *args): return query(sql,args)
        pool = SimpleNamespace(fetch=fetch,fetchrow=fetchrow,execute=execute)
        for uid, started in [(1,'2026-09-19 11:50:00'),(2,'2026-09-19 11:50:01'),
                             (3,'2026-09-18 11:00:00'),(4,'2026-09-19 11:00:00')]:
            conn.execute('INSERT INTO users (telegram_id, checkout_token, checkout_started_at, bot_started_at) VALUES (?,?,?,?)',
                         (uid,'token',started,'2026-09-18 10:00:00'))
        conn.execute("INSERT INTO payments VALUES (4, '2026-09-19 11:10:00')")
        with patch.object(db,'_pool_req',return_value=pool):
            self.assertEqual([r['telegram_id'] for r in await db.list_due_payment_nudges()],[1])
            self.assertFalse(await db.claim_payment_nudge(1,'old-token'))
            self.assertTrue(await db.claim_payment_nudge(1,'token'))
            self.assertFalse(await db.claim_payment_nudge(1,'token'))
            await db.track_checkout(1)
            conn.execute("UPDATE users SET checkout_started_at='2026-09-19 11:00:00' WHERE telegram_id=1")
            self.assertEqual(await db.list_due_payment_nudges(),[])  # Daily cooldown survives new invoices.
            first = conn.execute('SELECT first_checkout_at FROM users WHERE telegram_id=1').fetchone()[0]
            self.assertIsNotNone(first)
            await db.mark_paid_topup(1)
            await db.track_checkout(1)
            self.assertEqual(conn.execute('SELECT first_checkout_at FROM users WHERE telegram_id=1').fetchone()[0],first)
            await db.mark_paid_topup(2)
            self.assertIsNone(conn.execute('SELECT checkout_started_at FROM users WHERE telegram_id=2').fetchone()[0])
