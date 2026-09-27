import sqlite3
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db

class CohortOutcomesTest(unittest.IsolatedAsyncioTestCase):
    async def test_mature_windows_exclude_early_successes_and_count_first_payment_only(self):
        conn=sqlite3.connect(':memory:'); self.addCleanup(conn.close); conn.row_factory=sqlite3.Row
        conn.create_function('LEAST',2,min)
        conn.executescript('''CREATE TABLE users(telegram_id INTEGER,bot_started_at TEXT,first_online_at TEXT);
            CREATE TABLE payments(telegram_id INTEGER,created_at TEXT);
            CREATE TABLE rollypay_orders(telegram_id INTEGER,paid_at TEXT,status TEXT);
            INSERT INTO users VALUES
            (1,'2026-09-01 00:00:00','2026-09-01 01:00:00'),
            (2,'2026-09-10 00:00:00','2026-09-12 00:00:00'),
            (3,'2026-09-20 00:00:00','2026-09-20 01:00:00'),
            (4,'2026-09-26 12:00:00','2026-09-26 13:00:00'),
            (5,'2026-09-25 00:00:00',NULL),
            (6,'2026-09-19 00:00:00',NULL);
            INSERT INTO payments VALUES (1,'2026-09-02 00:00:00'),(3,'2026-09-21 00:00:00'),(4,'2026-09-26 14:00:00'),(5,'2026-09-25 01:00:00'),(6,'2026-09-27 00:00:00');
            INSERT INTO rollypay_orders VALUES (1,'2026-09-03 00:00:00','granted'),(2,'2026-09-12 00:00:00','created');''')
        async def fetch(sql,epoch,now):
            sql=sql.replace('::timestamptz','').replace('::int','')
            for expression,replacement in [
                ("$1 - INTERVAL '28 days'","datetime($1,'-28 days')"),
                ("$1 + INTERVAL '28 days'","datetime($1,'+28 days')"),
                ("$2 - INTERVAL '24 hours'","datetime($2,'-24 hours')"),
                ("$2 - INTERVAL '7 days'","datetime($2,'-7 days')"),
                ("u.bot_started_at + INTERVAL '24 hours'","datetime(u.bot_started_at,'+24 hours')"),
                ("u.bot_started_at + INTERVAL '7 days'","datetime(u.bot_started_at,'+7 days')"),
            ]: sql=sql.replace(expression,replacement)
            return conn.execute(sql,{'1':epoch.strftime('%Y-%m-%d %H:%M:%S'),'2':now.strftime('%Y-%m-%d %H:%M:%S')}).fetchall()
        epoch=datetime(2026,9,15,tzinfo=timezone.utc)
        pool=SimpleNamespace(fetchval=AsyncMock(return_value=epoch),fetch=fetch)
        with patch.object(db,'_pool_req',return_value=pool),patch.object(db,'_utc_now',return_value=datetime(2026,9,27,tzinfo=timezone.utc)):
            result=await db.admin_cohort_outcomes()
        items={r['period']:r for r in result['items']}
        self.assertEqual(items['before']['online_rate'],50)
        self.assertEqual(items['before']['paid_success'],1)
        self.assertEqual(items['after']['online_mature'],3)
        self.assertEqual(items['after']['online_success'],1)
        self.assertEqual(items['after']['online_pending'],1)
        self.assertEqual(items['after']['paid_mature'],2)
        self.assertEqual(items['after']['paid_success'],1)
        self.assertEqual(items['after']['paid_pending'],2)
        self.assertEqual(items['after']['paid_rate'],50)

    async def test_missing_epoch_has_no_synthetic_comparison(self):
        pool=SimpleNamespace(fetchval=AsyncMock(return_value=None),fetch=AsyncMock())
        with patch.object(db,'_pool_req',return_value=pool):
            self.assertEqual((await db.admin_cohort_outcomes())['items'],[])
        pool.fetch.assert_not_awaited()
