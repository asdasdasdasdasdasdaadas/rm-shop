import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app import admin, db

class BroadcastTrackingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for name, value in [('reserve_optional_message', 1), ('finish_optional_message', None)]:
            p = patch.object(db, name, AsyncMock(return_value=value))
            p.start(); self.addCleanup(p.stop)
        p = patch.object(db, "notification_allowed", AsyncMock(return_value=True))
        p.start(); self.addCleanup(p.stop)

    async def test_custom_broadcast_adds_tracked_button_and_records_delivery(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Кабинет', web_app=WebAppInfo(url='https://example.com/'))]])
        job = {'running':True, 'run_id':42}
        with patch.object(admin, 'get_settings'), patch.object(admin, 'cabinet_keyboard', return_value=keyboard), patch.object(db,'update_broadcast_run',AsyncMock()), patch.object(db,'create_reminder_delivery',AsyncMock(return_value='token')) as create, patch.object(db,'log_bot_message',AsyncMock(side_effect=RuntimeError('log unavailable'))), patch.object(admin,'finish_tracked_delivery',AsyncMock()) as finish, patch.object(admin,'_deliver_broadcast',AsyncMock(return_value=SimpleNamespace(message_id=123))) as send, patch.object(admin.asyncio,'sleep',AsyncMock()):
            with self.assertLogs(admin.logger, level='ERROR'):
                await admin._broadcast_all(None,'Text',job,[1])
        create.assert_awaited_once_with(1,'broadcast','Рассылка','Text',broadcast_id=42)
        self.assertIn('nt=token', send.call_args.args[3].inline_keyboard[0][0].web_app.url)
        finish.assert_awaited_once_with('token','sent',123)
        self.assertEqual(job['sent'],1)
        self.assertEqual(job.get('failed',0),0)

    def test_actual_payment_attribution_handles_competing_and_repeated_clicks(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.executescript('''
            CREATE TABLE reminder_deliveries(token TEXT,telegram_id INTEGER,status TEXT,broadcast_id INTEGER);
            CREATE TABLE reminder_clicks(id INTEGER,token TEXT,clicked_at TEXT);
            CREATE TABLE rollypay_orders(telegram_id INTEGER,status TEXT,paid_at TEXT,plan_code TEXT);
            CREATE TABLE payments(telegram_id INTEGER,created_at TEXT,plan_code TEXT,stars INTEGER);
            INSERT INTO reminder_deliveries VALUES ('a',1,'sent',42),('b',1,'sent',43),('auto',1,'sent',NULL),('old',2,'sent',42);
            INSERT INTO reminder_clicks VALUES (1,'a','2026-09-01 10:00:00'),(2,'a','2026-09-01 11:00:00'),(3,'b','2026-09-02 10:00:00'),(4,'auto','2026-09-03 10:00:00'),(5,'old','2026-08-01 10:00:00');
            INSERT INTO rollypay_orders VALUES (1,'granted','2026-09-01 12:00:00','100'),(1,'granted','2026-09-02 12:00:00','200'),(1,'granted','2026-09-03 12:00:00','300'),(2,'granted','2026-09-03 12:00:00','500'),(1,'created','2026-09-02 12:00:00','900');
            INSERT INTO payments VALUES (1,'2026-09-02 13:00:00','stars',50);
        ''')
        sql = db._BROADCAST_PAYMENTS_SQL.replace("p.paid_at - INTERVAL '7 days'", "datetime(p.paid_at, '-7 days')").replace('=ANY($1::bigint[])',' IN (42,43)').replace('::bigint', '')
        rows = conn.execute(sql + 'SELECT broadcast_id,currency,plan_code FROM attributed ORDER BY paid_at').fetchall()
        self.assertEqual(rows,[(42,'rub','100'),(43,'rub','200'),(43,'stars','stars')])

    async def test_delivery_insert_supports_optional_broadcast_id(self):
        pool = SimpleNamespace(execute=AsyncMock())
        with patch.object(db,'_pool_req',return_value=pool):
            await db.create_reminder_delivery(1,'broadcast','Title','Body',broadcast_id=42)
        sql,*args = pool.execute.call_args.args
        self.assertEqual(sql.count('broadcast_id'),1)
        self.assertEqual(len(args),6)
        self.assertEqual(args[-1],42)
