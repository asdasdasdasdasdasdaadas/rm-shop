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
            CREATE TABLE ad_links(id INTEGER,slug TEXT,title TEXT,kind TEXT,clicks INTEGER,created_at TEXT,archived_at TEXT);
            CREATE TABLE users(telegram_id INTEGER,ad_link_id INTEGER,trial_used BOOLEAN,has_paid_topup BOOLEAN,first_online_at TEXT);
            INSERT INTO ad_links VALUES (1,'a','A','manual',5,'2026-09-27',NULL),(2,'b','B','manual',0,'2026-09-27',NULL);
            INSERT INTO users VALUES (1,1,1,0,'2026-09-26'),(2,1,0,1,'2026-09-27'),(3,1,1,0,NULL),(4,NULL,1,0,'2026-09-27');
        ''')
        async def fetch(sql, archived, kind):
            sql = sql.replace('::int','').replace('::bool','')
            return conn.execute(sql, {'1':archived,'2':kind}).fetchall()
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetch=fetch)):
            rows = {r['id']:r for r in await db.list_ad_links()}
        self.assertEqual(rows[1]['users'],3)
        self.assertEqual(rows[1]['connected'],2)
        self.assertEqual(rows[1]['trial'],2)
        self.assertEqual(rows[2]['connected'],0)
