import json
import sqlite3
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db, web


class ExitFeedbackStorageTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        conn=self.conn=sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory=sqlite3.Row
        conn.executescript('''
            CREATE TABLE users (telegram_id INTEGER PRIMARY KEY,username TEXT);
            CREATE TABLE devices (id INTEGER PRIMARY KEY,telegram_id INTEGER);
            CREATE TABLE device_exit_feedback (token TEXT PRIMARY KEY,telegram_id INTEGER,
                created_at TEXT DEFAULT '2026-09-21 12:00:00',reason TEXT,answered_at TEXT);
            INSERT INTO users VALUES (1,'user1'),(2,'user2');
            INSERT INTO devices VALUES (10,1),(11,1),(20,2);
        ''')
        class Connection:
            def query(self,sql,args):
                sql=sql.replace(' FOR UPDATE','').replace('::int','')
                sql=sql.replace("NOW() - INTERVAL '1 day'","'2026-09-20 12:00:00'")
                sql=sql.replace("NOW() - INTERVAL '30 days'","'2026-08-22 12:00:00'")
                sql=sql.replace('NOW()',"'2026-09-21 12:00:00'")
                return conn.execute(sql,{str(i):a for i,a in enumerate(args,1)})
            @asynccontextmanager
            async def transaction(self):
                try:
                    yield
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            async def fetchrow(self,sql,*args): return self.query(sql,args).fetchone()
            async def fetch(self,sql,*args): return self.query(sql,args).fetchall()
            async def fetchval(self,sql,*args):
                row=await self.fetchrow(sql,*args)
                return row[0] if row else None
            async def execute(self,sql,*args): return self.query(sql,args)
            @asynccontextmanager
            async def acquire(self): yield self
        self.patch=patch.object(db,'_pool_req',return_value=Connection())
        self.patch.start();self.addCleanup(self.patch.stop)

    async def test_only_last_owned_device_creates_survey(self):
        self.assertIsNone(await db.delete_device(1,20))
        self.assertNotIn('exit_feedback_token',await db.delete_device(1,10))
        last=await db.delete_device(1,11)
        self.assertTrue(last['exit_feedback_token'])
        self.assertIsNone(await db.delete_device(1,11))
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM device_exit_feedback').fetchone()[0],1)

    async def test_answers_are_owned_valid_expiring_and_idempotent(self):
        token=(await db.delete_device(2,20))['exit_feedback_token']
        self.assertFalse(await db.save_exit_feedback(1,token,'expensive'))
        self.assertFalse(await db.save_exit_feedback(2,token,'invalid'))
        self.assertTrue(await db.save_exit_feedback(2,token,'not_working'))
        self.assertTrue(await db.save_exit_feedback(2,token,'not_working'))
        self.assertFalse(await db.save_exit_feedback(2,token,'other'))
        self.conn.execute("UPDATE device_exit_feedback SET created_at='2026-09-19'")
        self.assertFalse(await db.save_exit_feedback(2,token,'not_working'))

    async def test_admin_distinguishes_answers_from_skips(self):
        await db.delete_device(1,10)
        await db.delete_device(1,11)
        token=(await db.delete_device(2,20))['exit_feedback_token']
        await db.save_exit_feedback(2,token,'expensive')
        result=await db.admin_exit_feedback()
        self.assertEqual((result['total'],result['answered']),(2,1))
        self.assertEqual(result['reasons'][0]['count'],1)
        self.assertEqual(len(result['recent']),1)
        self.assertEqual(result['recent'][0]['telegram_id'],2)


class ExitFeedbackApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_auth_and_invalid_payload(self):
        request=SimpleNamespace(json=AsyncMock(return_value={'token':'t','reason':'expensive'}))
        denied=web.json_error('Unauthorized',401)
        with patch.object(web,'_require_tg',AsyncMock(return_value=(None,denied))), patch.object(db,'save_exit_feedback',AsyncMock()) as save:
            response=await web.api_exit_feedback(request)
            self.assertEqual(response.status,401)
            save.assert_not_awaited()
        with patch.object(web,'_require_tg',AsyncMock(return_value=(1,None))), patch.object(db,'save_exit_feedback',AsyncMock(return_value=True)) as save:
            response=await web.api_exit_feedback(request)
            self.assertTrue(json.loads(response.text)['ok'])
            save.assert_awaited_once_with(1,'t','expensive')
            request.json.return_value={'token':'t','reason':'bad'}
            self.assertEqual((await web.api_exit_feedback(request)).status,400)
