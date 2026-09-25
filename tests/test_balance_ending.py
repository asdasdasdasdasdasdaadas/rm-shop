import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import db


class BalanceEndingTest(unittest.IsolatedAsyncioTestCase):
    async def test_one_warning_per_recovered_balance_and_recheck_before_send(self):
        c=sqlite3.connect(':memory:'); self.addCleanup(c.close)
        c.create_function('GREATEST',2,max)
        c.executescript('''CREATE TABLE users (telegram_id INTEGER,trial_end_nudge_at TEXT,
          bot_started_at TEXT,first_online_at TEXT,bot_blocked_at TEXT,blocked_at TEXT,billing_paused_at TEXT,
          balance_rub INTEGER,has_paid_topup BOOLEAN,checkout_started_at TEXT);
          INSERT INTO users VALUES(1,NULL,'start','online',NULL,NULL,NULL,6,FALSE,NULL);
          CREATE TABLE devices(telegram_id INTEGER,kind TEXT);
          INSERT INTO devices VALUES(1,'phone');
          CREATE TABLE message_log(telegram_id INTEGER,kind TEXT,status TEXT,created_at TEXT);
        ''')
        def query(sql,args):
            sql=sql.replace("NOW()-INTERVAL '24 hours'","'2026-09-24'").replace('NOW()',"'2026-09-25'")
            return c.execute(sql,{str(i):a for i,a in enumerate(args,1)})
        async def fetchrow(sql,*args): return query(sql,args).fetchone()
        async def execute(sql,*args): return query(sql,args)
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetchrow=fetchrow,execute=execute)),patch.object(db,'get_settings',return_value=SimpleNamespace(vpn_day_price_rub=6)):
            self.assertTrue(await db.claim_balance_ending_notice(1,6))
            c.execute("UPDATE users SET trial_end_nudge_at='2020-01-01'")
            self.assertFalse(await db.claim_balance_ending_notice(1,6))
            await db.mark_paid_topup(1) # still low: do not rearm
            self.assertFalse(await db.claim_balance_ending_notice(1,6))
            c.execute('UPDATE users SET balance_rub=100')
            await db.mark_paid_topup(1)
            self.assertFalse(await db.claim_balance_ending_notice(1,6)) # payment since selection
            c.execute('UPDATE users SET balance_rub=6')
            self.assertTrue(await db.claim_balance_ending_notice(1,6))
            await db.release_balance_ending_notice(1)
            self.assertTrue(await db.claim_balance_ending_notice(1,6)) # failed send may retry
            await db.release_balance_ending_notice(1)
            c.execute('DELETE FROM devices')
            self.assertFalse(await db.claim_balance_ending_notice(1,6))
