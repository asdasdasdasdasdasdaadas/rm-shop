import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import db

class AdOnlineTest(unittest.IsolatedAsyncioTestCase):
    async def test_source_counts_connected_users_including_no_trial(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.executescript('''
            CREATE TABLE ad_partners(id INTEGER,title TEXT);
            CREATE TABLE ad_links(id INTEGER,slug TEXT,title TEXT,kind TEXT,clicks INTEGER,created_at TEXT,archived_at TEXT,partner_id INTEGER,spend_rub INTEGER);
            CREATE TABLE payment_receipts(telegram_id INTEGER,amount INTEGER);
            CREATE TABLE tg_ads(ad_link_id INTEGER,views INTEGER,clicks INTEGER,spent REAL,currency TEXT,spent_rub INTEGER);
            CREATE TABLE users(telegram_id INTEGER,ad_link_id INTEGER,trial_used BOOLEAN,has_paid_topup BOOLEAN,first_online_at TEXT,created_at TEXT);
            CREATE TABLE devices(telegram_id INTEGER,last_online_at TEXT);
            INSERT INTO devices VALUES (1,'2026-09-30'),(1,'2026-09-30'),(2,'2026-09-20'),(4,'2026-09-30'),(5,'2026-09-30');
            INSERT INTO ad_links VALUES (1,'a','A','manual',5,'2026-09-27',NULL,NULL,NULL),(2,'b','B','manual',0,'2026-09-27',NULL,NULL,NULL);
            INSERT INTO users VALUES (1,1,1,0,'2026-09-26','2026-09-01'),(2,1,0,1,'2026-09-27','2026-09-01'),(3,1,1,0,NULL,'2026-09-29'),(4,NULL,1,0,'2026-09-27','2026-09-01'),(5,1,0,1,'2026-09-28','2026-09-28');
        ''')
        async def fetch(sql, archived, kind, partner, since, matured):
            now = db.datetime.now(db.timezone.utc)
            self.assertEqual(round((now - since).total_seconds() / 86400), db.AD_ACTIVE_DAYS)
            self.assertEqual(round((now - matured).total_seconds() / 86400), db.AD_RETAIN_DAYS)
            sql = sql.replace('::bigint','').replace('::int','').replace('::bool','').replace('::float','').replace('::timestamptz','')
            return conn.execute(sql, {'1':archived,'2':kind,'3':partner,'4':'2026-09-24','5':'2026-09-16'}).fetchall()
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetch=fetch)):
            rows = {r['id']:r for r in await db.list_ad_links()}
        self.assertEqual(rows[1]['users'],4)
        self.assertEqual(rows[1]['connected'],3)
        self.assertEqual(rows[1]['active'],2)   # user 2 was last online too long ago; user 4 came from no ad
        self.assertEqual(rows[1]['paying_active'],1)   # user 5 paid and is online; user 2 paid but left
        self.assertEqual((rows[1]['matured'],rows[1]['retained']),(2,1))   # users 3 and 5 came too recently
        self.assertEqual(rows[1]['trial'],2)
        self.assertEqual(rows[2]['connected'],0)
