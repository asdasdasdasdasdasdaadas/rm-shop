import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from contextlib import ExitStack
from app import payment_notice as notice


class PaymentNoticeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.receipt=dict(payment_key='rollypay:one',telegram_id=1,amount=100,router_days=0)
        self.claim=self.stack.enter_context(patch.object(notice.db,'claim_payment_notice',AsyncMock(return_value=True)))
        self.finish=self.stack.enter_context(patch.object(notice.db,'finish_payment_notice',AsyncMock()))
        self.stack.enter_context(patch.object(notice.db,'log_bot_message',AsyncMock()))
        self.user=self.stack.enter_context(patch.object(notice.db,'get_user',AsyncMock(return_value={'balance_rub':94})))
        self.devices=self.stack.enter_context(patch.object(notice.db,'list_devices',AsyncMock(return_value=[])))
        self.stack.enter_context(patch('app.keyboards.mini_app_url',return_value='https://example.com'))
        self.bot=SimpleNamespace(send_message=AsyncMock())

    async def test_new_payer_gets_next_step_and_navigation(self):
        await notice.deliver_payment_notice(self.bot,self.receipt)
        args=self.bot.send_message.call_args
        self.assertIn('100',args.args[1]);self.assertIn('94',args.args[1])
        self.assertIn('Добавьте устройство',args.args[1])
        rows=args.kwargs['reply_markup'].inline_keyboard
        self.assertEqual(rows[0][0].text,'Личный кабинет')
        self.assertEqual(rows[1][0].callback_data,'profile')
        self.finish.assert_awaited_once_with('rollypay:one','sent')

    async def test_failure_stays_pending_and_retry_succeeds(self):
        self.bot.send_message.side_effect=[TimeoutError(),None]
        await notice.deliver_payment_notice(self.bot,self.receipt)
        self.finish.assert_not_awaited()
        await notice.deliver_payment_notice(self.bot,self.receipt)
        self.finish.assert_awaited_once_with('rollypay:one','sent')

    async def test_already_claimed_or_sent_does_not_send(self):
        self.claim.return_value=False
        await notice.deliver_payment_notice(self.bot,self.receipt)
        self.bot.send_message.assert_not_awaited()

    async def test_paid_but_not_connected_continues_setup(self):
        self.devices.return_value=[{'id':1}]
        await notice.deliver_payment_notice(self.bot,self.receipt)
        self.assertIn('Продолжите настройку',self.bot.send_message.call_args.args[1])

    async def test_quiet_payer_still_gets_confirmation(self):
        self.user.return_value={'balance_rub':100,'quiet_notifications':True,'first_online_at':'date'}
        self.devices.return_value=[{'id':1}]
        await notice.deliver_payment_notice(self.bot,self.receipt)
        self.assertIn('Включите VPN',self.bot.send_message.call_args.args[1])


class PaymentNoticeQueueTest(unittest.IsolatedAsyncioTestCase):
    async def test_claim_retry_and_sent_state_use_durable_receipt(self):
        import sqlite3
        from app import db
        conn=sqlite3.connect(':memory:');self.addCleanup(conn.close)
        conn.row_factory=sqlite3.Row
        conn.executescript("""CREATE TABLE payment_receipts(payment_key TEXT, notice_status TEXT,
            notice_retry_at TEXT, notice_sent_at TEXT, created_at TEXT);
            INSERT INTO payment_receipts VALUES('one','pending','2026-10-01',NULL,'2026-10-01');
            INSERT INTO payment_receipts VALUES('old','legacy','2026-10-01',NULL,'2026-10-01');""")
        def sql(text):
            return text.replace("NOW()+INTERVAL '5 minutes'", "'2026-10-04 12:05:00'").replace("NOW()+($3::int*INTERVAL '1 second')", "'2026-10-04 12:05:00'").replace('NOW()',"'2026-10-04 12:00:00'")
        async def fetch(text,*args):
            return conn.execute(sql(text),{str(i):v for i,v in enumerate(args,1)}).fetchall()
        async def fetchval(text,*args):
            rows=await fetch(text,*args)
            return rows[0][0] if rows else None
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetch=fetch,fetchval=fetchval,execute=fetch)):
            self.assertEqual(len(await db.pending_payment_notices()),1)
            self.assertTrue(await db.claim_payment_notice('one'))
            self.assertFalse(await db.claim_payment_notice('one'))
            self.assertEqual(await db.pending_payment_notices(),[])
            conn.execute("UPDATE payment_receipts SET notice_retry_at='2026-10-01'")
            self.assertTrue(await db.claim_payment_notice('one'))
            await db.finish_payment_notice('one','sent')
            conn.execute("UPDATE payment_receipts SET notice_retry_at='2026-10-01'")
            self.assertEqual(await db.pending_payment_notices(),[])
            self.assertFalse(await db.claim_payment_notice('one'))
