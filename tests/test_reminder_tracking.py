import sqlite3
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
from unittest.mock import AsyncMock,patch
from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton,WebAppInfo
from app import db,reminder_tracking as tracking


class TrackingDeliveryTest(unittest.IsolatedAsyncioTestCase):
    def markup(self):
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Open',web_app=WebAppInfo(url='https://example.com/?screen=topup&a=1'))],[InlineKeyboardButton(text='Help',callback_data='help:connect')]])

    async def test_urls_preserve_destination_and_callbacks_remain_unchanged(self):
        original=self.markup();result=tracking.tracked_keyboard(original,'token')
        self.assertEqual(parse_qs(urlsplit(result.inline_keyboard[0][0].web_app.url).query),{'screen':['topup'],'a':['1'],'nt':['token']})
        self.assertEqual(result.inline_keyboard[1][0].callback_data,'help:connect')
        self.assertNotIn('nt=',original.inline_keyboard[0][0].web_app.url)

    async def test_tracking_failure_does_not_prevent_or_repeat_delivery(self):
        bot=SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=7)))
        with patch.object(db,'create_reminder_delivery',AsyncMock(side_effect=RuntimeError())):
            await tracking.send_reminder(bot,1,'message',kind='nudge_info',title='title',reply_markup=self.markup())
        bot.send_message.assert_awaited_once()
        bot.send_message.reset_mock()
        with patch.object(db,'create_reminder_delivery',AsyncMock(return_value='t')),patch.object(db,'finish_reminder_delivery',AsyncMock(side_effect=RuntimeError())):
            await tracking.send_reminder(bot,1,'message',kind='nudge_info',title='title',reply_markup=self.markup())
        bot.send_message.assert_awaited_once()

    async def test_failed_send_is_recorded_as_failure(self):
        bot=SimpleNamespace(send_message=AsyncMock(side_effect=TimeoutError()))
        with patch.object(db,'create_reminder_delivery',AsyncMock(return_value='t')),patch.object(db,'finish_reminder_delivery',AsyncMock()) as finish:
            with self.assertRaises(TimeoutError):
                await tracking.send_reminder(bot,1,'message',kind='nudge_info',title='title',reply_markup=self.markup())
            finish.assert_awaited_once_with('t','failed',None)

    async def test_callback_uses_real_user_and_message_without_changing_action(self):
        event=SimpleNamespace(from_user=SimpleNamespace(id=2),message=SimpleNamespace(message_id=9),data='resume_pay:invoice')
        handler=AsyncMock(return_value='handled')
        with patch.object(db,'record_reminder_click',AsyncMock()) as click:
            self.assertEqual(await tracking.ReminderClickMiddleware()(handler,event,{}),'handled')
            click.assert_awaited_once_with(2,message_id=9)
            self.assertEqual(event.data,'resume_pay:invoice')


class TrackingResultsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        c=self.conn=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        self.addCleanup(c.close)
        c.executescript('''
        CREATE TABLE reminder_deliveries (token TEXT PRIMARY KEY,telegram_id INTEGER,kind TEXT,title TEXT,body TEXT,
          created_at TEXT,status TEXT,message_id INTEGER,sent_at TEXT,clicked_at TEXT,connected_at TEXT);
        CREATE TABLE reminder_clicks (id INTEGER PRIMARY KEY AUTOINCREMENT,token TEXT,clicked_at TEXT DEFAULT '2026-09-21 12:00:00');
        CREATE TABLE payments (telegram_id INTEGER,created_at TEXT);
        CREATE TABLE rollypay_orders (telegram_id INTEGER,status TEXT,paid_at TEXT);
        CREATE TABLE devices (telegram_id INTEGER,last_online_at TEXT);
        ''')
        def query(sql,args):
            sql=sql.replace('::int','').replace('::bigint','').replace('::text','')
            for days in [7,8,30,38]:
                sql=sql.replace(f"NOW() - INTERVAL '{days} days'",f"datetime('2026-09-21 12:00:00','-{days} days')")
            sql=sql.replace("c.clicked_at + INTERVAL '7 days'","datetime(c.clicked_at,'+7 days')")
            sql=sql.replace('NOW()',"'2026-09-21 12:00:00'")
            bindings={str(i):a for i,a in enumerate(args,1)}
            if sql.lstrip().startswith('WITH clicked AS'):
                # SQLite does not support writable CTEs: run the exact UPDATE then its INSERT.
                update=sql.split('WITH clicked AS (',1)[1].split(') INSERT INTO reminder_clicks',1)[0]
                for row in c.execute(update,bindings).fetchall():
                    c.execute('INSERT INTO reminder_clicks (token) VALUES (?)',(row['token'],))
                return c.execute('SELECT 1')
            return c.execute(sql,bindings)
        async def execute(sql,*args):return query(sql,args)
        async def fetch(sql,*args):return query(sql,args).fetchall()
        self.pool=patch.object(db,'_pool_req',return_value=SimpleNamespace(execute=execute,fetch=fetch))
        self.pool.start();self.addCleanup(self.pool.stop)

    def delivery(self,token,user,kind='nudge_info',status='sent',click='2026-09-20 10:00:00'):
        self.conn.execute('INSERT INTO reminder_deliveries VALUES (?,?,?,?,?,?,?,?,?,?,NULL)',(token,user,kind,'title','body','2026-09-20',status,user,'2026-09-20',click))
        if click:self.conn.execute('INSERT INTO reminder_clicks (token,clicked_at) VALUES (?,?)',(token,click))

    async def test_clicks_require_owner_and_successful_delivery(self):
        self.delivery('a',1,click=None);self.delivery('b',2,status='failed',click=None)
        await db.record_reminder_click(2,token='a')
        await db.record_reminder_click(2,token='b')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM reminder_clicks').fetchone()[0],0)
        await db.record_reminder_click(1,token='a');await db.record_reminder_click(1,message_id=1)
        result=await db.admin_reminder_results()
        self.assertEqual(result['groups'][0]['clicked'],1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM reminder_clicks').fetchone()[0],2)

    async def test_last_actual_click_gets_payment_and_connection_only_within_window(self):
        self.delivery('older',1,'nudge_info',click='2026-09-19 10:00:00')
        self.delivery('newer',1,'nudge_trial',click='2026-09-20 10:00:00')
        self.delivery('expired',2,'nudge_trial',click='2026-09-10 10:00:00')
        self.conn.execute("INSERT INTO payments VALUES (1,'2026-09-20 11:00:00'),(2,'2026-09-20 11:00:00')")
        self.conn.execute("INSERT INTO devices VALUES (1,'2026-09-20 11:00:00'),(2,'2026-09-20 11:00:00')")
        await db.track_reminder_connections()
        rows={r['kind']:r for r in (await db.admin_reminder_results())['groups']}
        self.assertEqual((rows['nudge_info']['paid'],rows['nudge_info']['connected']),(0,0))
        self.assertEqual((rows['nudge_trial']['paid'],rows['nudge_trial']['connected']),(1,1))
        # Reopening an older message is a new real click, not a lost/overwritten history.
        self.conn.execute("INSERT INTO reminder_clicks (token,clicked_at) VALUES ('older','2026-09-20 12:00:00')")
        self.conn.execute("INSERT INTO rollypay_orders VALUES (1,'granted','2026-09-20 13:00:00')")
        rows={r['kind']:r for r in (await db.admin_reminder_results())['groups']}
        self.assertEqual(rows['nudge_info']['paid'],1)
        self.assertEqual(rows['nudge_trial']['paid'],1)

    async def test_no_click_or_payment_before_click_is_not_attributed(self):
        self.delivery('a',1,click=None);self.delivery('b',2,click='2026-09-20 10:00:00')
        self.conn.execute("INSERT INTO payments VALUES (1,'2026-09-21'),(2,'2026-09-19')")
        self.assertEqual((await db.admin_reminder_results())['groups'][0]['paid'],0)
