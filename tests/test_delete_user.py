import sqlite3
import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch
from app import db


class DeleteUserTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        sql = self.sql = sqlite3.connect(':memory:')
        self.addCleanup(sql.close)
        sql.execute('PRAGMA foreign_keys=ON')
        sql.create_function('pg_advisory_xact_lock',1,lambda _: None)
        sql.executescript('''
          CREATE TABLE users (telegram_id INTEGER PRIMARY KEY);
          INSERT INTO users VALUES (1),(2),(3);
          CREATE TABLE referral_campaign_friends (
            invitee_id INTEGER REFERENCES users(telegram_id),
            referrer_id INTEGER REFERENCES users(telegram_id));
          INSERT INTO referral_campaign_friends VALUES (1,2),(2,1),(3,2);
          CREATE TABLE referral_campaign_awards (referrer_id INTEGER REFERENCES users(telegram_id));
          INSERT INTO referral_campaign_awards VALUES (1),(2);
        ''')
        tables = ['trust_loans','vpn_reports','promo_uses','payments','rollypay_orders',
                  'cabinet_tokens','billing_events','referral_payouts','message_log','devices',
                  'referral_campaign_messages','cabinet_login_challenges']
        for table in tables:
            sql.execute(f'CREATE TABLE {table} (telegram_id INTEGER REFERENCES users(telegram_id))')
            sql.execute(f'INSERT INTO {table} VALUES (1),(2)')
        sql.commit()
        class Conn:
            async def execute(self,query,*args):
                return sql.execute(query.replace(' FOR UPDATE',''),{str(i):v for i,v in enumerate(args,1)})
            async def fetchval(self,query,*args):
                row=(await self.execute(query,*args)).fetchone()
                return row[0] if row else None
            @asynccontextmanager
            async def acquire(self): yield self
            @asynccontextmanager
            async def transaction(self):
                try:
                    yield
                    sql.commit()
                except Exception:
                    sql.rollback()
                    raise
        p=patch.object(db,'_pool_req',return_value=Conn());p.start();self.addCleanup(p.stop)

    async def test_removes_both_campaign_roles_and_login_without_touching_other_users(self):
        self.assertTrue(await db.delete_user(1))
        self.assertEqual(self.sql.execute('SELECT * FROM users').fetchall(),[(2,),(3,)])
        self.assertEqual(self.sql.execute('SELECT * FROM referral_campaign_friends').fetchall(),[(3,2)])
        self.assertEqual(self.sql.execute('SELECT * FROM referral_campaign_awards').fetchall(),[(2,)])
        self.assertEqual(self.sql.execute('SELECT * FROM cabinet_login_challenges').fetchall(),[(2,)])
        self.assertTrue(await db.delete_user(2))
        self.assertFalse(await db.delete_user(2))

    async def test_cleanup_rolls_back_on_error(self):
        self.sql.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON users BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError): await db.delete_user(1)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaign_friends').fetchone()[0],3)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM cabinet_login_challenges').fetchone()[0],2)
