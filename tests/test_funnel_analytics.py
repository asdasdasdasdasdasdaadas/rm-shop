import sqlite3
import unittest
import re
from types import SimpleNamespace
from unittest.mock import patch
from app import db


class FunnelAnalyticsTest(unittest.TestCase):
    def setUp(self):
        settings = patch.object(db, 'get_settings', return_value=SimpleNamespace(vpn_day_price_rub=6))
        settings.start(); self.addCleanup(settings.stop)
        self.conn=sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript('''
            CREATE TABLE users (telegram_id INTEGER, bot_started_at TEXT, referred_by INTEGER, ad_link_id INTEGER,
                accepted_legal_at TEXT, trial_used INTEGER DEFAULT 0, blocked_at TEXT, first_online_at TEXT,
                first_checkout_at TEXT, has_paid_topup INTEGER DEFAULT 0, gift_claimed_at TEXT,
                balance_rub INTEGER DEFAULT 0, billing_paused_at TEXT, vpn_feedback TEXT, router_expire_at TEXT, trial_waiting_connection INTEGER DEFAULT 0);
            CREATE TABLE app_flags (key TEXT,value TEXT);
            CREATE TABLE devices (telegram_id INTEGER,created_at TEXT,kind TEXT,last_billed_at TEXT,expire_at TEXT);
            CREATE TABLE rollypay_orders (telegram_id INTEGER,status TEXT);
            CREATE TABLE payments (telegram_id INTEGER);
            CREATE TABLE promo_uses (telegram_id INTEGER);
        ''')
        for uid in range(1,10):
            self.conn.execute("INSERT INTO users (telegram_id,bot_started_at) VALUES (?,'2026-09-10')",(uid,))
        self.conn.execute("UPDATE users SET bot_started_at='2026-08-01' WHERE telegram_id IN (5,9)")
        self.conn.execute('UPDATE users SET bot_started_at=NULL WHERE telegram_id=6')
        self.conn.execute('UPDATE users SET trial_used=1 WHERE telegram_id IN (1,2,8)')
        self.conn.execute("UPDATE users SET first_online_at='2026-09-12' WHERE telegram_id IN (2,3,8)")
        self.conn.execute("UPDATE users SET first_checkout_at='2026-09-13' WHERE telegram_id=4")
        self.conn.execute('UPDATE users SET referred_by=2 WHERE telegram_id=9')
        self.conn.executemany('INSERT INTO payments VALUES (?)',[(2,),(2,),(3,),(6,),(9,)])
        self.conn.executemany('INSERT INTO rollypay_orders VALUES (?,?)',[(3,'granted'),(7,'granted'),(4,'pending')])
        self.bounds=['2026-09-01','2026-10-01']

    def query(self,sql,args):
        sql=sql.replace('::timestamptz','').replace('::int','')
        sql=re.sub(r"NOW\(\) - INTERVAL '([^']+)'", lambda m: "datetime('2026-10-13 12:00:00','-"+m[1]+"')", sql)
        sql=sql.replace('NOW()',"datetime('2026-10-13 12:00:00')")
        return self.conn.execute(sql,{str(i):a.isoformat() if hasattr(a,'isoformat') else a for i,a in enumerate(args,1)})

    def test_stars_mixed_payments_and_durable_online(self):
        row=dict(self.query(db._funnel_cte() + db._FUNNEL_SELECT,self.bounds).fetchone())
        self.assertEqual(row['entered'],6)
        self.assertEqual(row['trial'],3)
        self.assertEqual(row['connected'],3)  # No current devices, historical online remains.
        self.assertEqual(row['checkout'],4)  # Includes a Stars checkout with no order record.
        self.assertEqual(row['paid'],3)
        self.assertEqual(row['repeat_paid'],2)  # Two Stars and one Stars + one cash payment.
        self.assertEqual(row['paid_stars'],2)
        self.assertEqual(row['paid_rollypay'],2)
        self.assertEqual(row['connected_transition'],2)  # User 3 skipped the gift.
        self.assertEqual(row['checkout_transition'],2)
        self.assertEqual(row['gift_no_online'],1)
        self.assertEqual(row['checkout_drop'],1)
        self.assertEqual(row['inv_paid'],1)

    def test_every_drilldown_matches_its_counter(self):
        row=dict(self.query(db._funnel_cte() + db._FUNNEL_SELECT,self.bounds).fetchone())
        for key in db._FUNNEL_KEYS:
            with self.subTest(key=key):
                where,args=db._admin_users_filter('',dict(funnel_step=key,funnel_from=self.bounds[0],funnel_to=self.bounds[1]))
                ids=self.query('SELECT u.telegram_id FROM users u '+where,args).fetchall()
                self.assertEqual(len(ids),row[key])

    def test_all_time_still_requires_starting_bot(self):
        self.assertEqual(self.query(db._funnel_cte() + db._FUNNEL_SELECT,[None,None]).fetchone()['entered'],8)

    def test_newcomers_and_active_access_are_not_losses(self):
        self.conn.execute("UPDATE users SET bot_started_at='2026-10-13 10:00:00',gift_claimed_at='2026-10-13 10:00:00' WHERE telegram_id=1")
        self.conn.execute("UPDATE users SET balance_rub=18 WHERE telegram_id=8")
        self.conn.execute("INSERT INTO devices VALUES (7,'2026-09-10','', '2026-10-13 11:00:00',NULL)")
        row=dict(self.query(db._funnel_cte()+db._FUNNEL_SELECT,[None,None]).fetchone())
        self.assertEqual(row['gift_no_online'],0)
        self.assertEqual(row['progress_gift_no_online'],1)
        self.assertEqual(row['online_no_paid'],0)
        self.assertEqual(row['progress_online_no_paid'],1)
        self.assertEqual(row['paid_no_repeat'],1) # historical payers without any remaining access
        self.assertEqual(row['progress_paid_no_repeat'],1)
        self.conn.execute("UPDATE devices SET last_billed_at='2026-10-12 11:59:59' WHERE telegram_id=7")
        row=dict(self.query(db._funnel_cte()+db._FUNNEL_SELECT,[None,None]).fetchone())
        self.assertEqual(row['progress_paid_no_repeat'],0)
        self.assertEqual(row['paid_no_repeat'],2)
