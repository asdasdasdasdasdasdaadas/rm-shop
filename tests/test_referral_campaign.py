import sqlite3
import unittest
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch
from app import db


class CampaignTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sql = sqlite3.connect(':memory:')
        self.sql.row_factory = sqlite3.Row
        self.addCleanup(self.sql.close)
        self.sql.executescript('''
          CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, referred_by INTEGER, first_name TEXT, username TEXT,
            referral_rewarded BOOLEAN DEFAULT FALSE, balance_rub INTEGER DEFAULT 0,
            bot_started_at TEXT DEFAULT CURRENT_TIMESTAMP, blocked_at TEXT, bot_blocked_at TEXT,
            referral_fraction INTEGER DEFAULT 0, referral_earned INTEGER DEFAULT 0, low_balance_notified_at TEXT);
          INSERT INTO users (telegram_id,referred_by) VALUES (1,NULL),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1),(8,1);
          CREATE TABLE referral_campaign_schedule (id INTEGER PRIMARY KEY, scheduled_at TEXT);
          CREATE TABLE referral_campaigns (id INTEGER PRIMARY KEY, started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            stopped_at TEXT, reward_rub INTEGER);
          CREATE UNIQUE INDEX one_active ON referral_campaigns ((1)) WHERE stopped_at IS NULL;
          CREATE TABLE referral_campaign_messages (campaign_id INTEGER,telegram_id INTEGER,status TEXT DEFAULT 'pending',retryable BOOLEAN DEFAULT FALSE,error TEXT,attempts INTEGER DEFAULT 0,retry_at TEXT,PRIMARY KEY(campaign_id,telegram_id));
          CREATE TABLE referral_campaign_friends (invitee_id INTEGER PRIMARY KEY,campaign_id INTEGER,
            referrer_id INTEGER,payment_key TEXT UNIQUE,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
          CREATE TABLE referral_campaign_awards (campaign_id INTEGER,referrer_id INTEGER,amount INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(campaign_id,referrer_id));
          CREATE TABLE referral_payment_rewards (payment_key TEXT PRIMARY KEY,invitee_id INTEGER,
            referrer_id INTEGER,topup_rub INTEGER,enabled BOOLEAN,reward_rub INTEGER);
          CREATE TABLE billing_events (telegram_id INTEGER,kind TEXT,source TEXT,amount INTEGER,balance_after INTEGER,note TEXT);
        ''')
        sql = self.sql
        class Conn:
            def query(self, statement, args):
                if 'pg_advisory_xact_lock' in statement:
                    return sql.execute('SELECT 1')
                statement = statement.replace(' FOR UPDATE','').replace('clock_timestamp()', 'CURRENT_TIMESTAMP').replace('NOW()', 'CURRENT_TIMESTAMP')
                return sql.execute(statement, {str(i): v for i,v in enumerate(args,1)})
            async def execute(self, statement, *args): return self.query(statement,args)
            async def fetch(self, statement, *args): return self.query(statement,args).fetchall()
            async def fetchrow(self, statement, *args): return self.query(statement,args).fetchone()
            async def fetchval(self, statement, *args):
                row = await self.fetchrow(statement,*args)
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
        p = patch.object(db,'_pool_req',return_value=Conn()); p.start(); self.addCleanup(p.stop)
        p = patch.object(db,'get_settings',return_value=SimpleNamespace(balance_enabled=True,vpn_day_price_rub=6))
        p.start(); self.addCleanup(p.stop)

    async def pay(self, user, key=None, first=True, enabled=False, amount=100):
        return await db.reward_referral_payment(user,key or f'pay:{user}',amount,
            enabled=enabled,first_payment=first)

    def balance(self): return self.sql.execute('SELECT balance_rub FROM users WHERE telegram_id=1').fetchone()[0]

    async def test_three_friends_award_once_independent_of_normal_program(self):
        await db.change_referral_campaign('start')
        self.assertIsNone(await self.pay(2)); self.assertIsNone(await self.pay(3))
        self.assertEqual(self.balance(),0)
        result = await self.pay(4)
        self.assertEqual(result['campaign']['amount'],540)
        await self.pay(4); await self.pay(5)
        self.assertEqual(self.balance(),540)
        self.assertEqual(self.sql.execute('SELECT referral_earned FROM users WHERE telegram_id=1').fetchone()[0],0)

    async def test_repeated_payments_and_same_friend_do_not_count(self):
        await db.change_referral_campaign('start')
        await self.pay(2); await self.pay(2,'another',first=True)
        await self.pay(3,first=False); await self.pay(4,amount=0)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaign_friends').fetchone()[0],1)
        self.assertEqual(self.balance(),0)

    async def test_inactive_payments_not_retroactive_and_new_run_resets_progress(self):
        await self.pay(2)
        await db.change_referral_campaign('start')
        await self.pay(2)  # old provider event replay
        await self.pay(3); await self.pay(4)
        await db.change_referral_campaign('stop',1)
        await self.pay(5)
        await db.change_referral_campaign('start')
        await self.pay(3,'replay-in-new-run')
        await self.pay(6); await self.pay(7)
        self.assertEqual(self.balance(),0)
        await self.pay(8)
        self.assertEqual(self.balance(),540)

    async def test_start_is_idempotent_and_stale_stop_does_not_stop_new_run(self):
        await db.change_referral_campaign('start'); await db.change_referral_campaign('start')
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaigns').fetchone()[0],1)
        await db.change_referral_campaign('stop',1); await db.change_referral_campaign('start')
        await db.change_referral_campaign('stop',1)
        self.assertEqual(self.sql.execute('SELECT id FROM referral_campaigns WHERE stopped_at IS NULL').fetchone()[0],2)

    async def test_standard_rewards_continue_alongside_campaign(self):
        await db.change_referral_campaign('start')
        for user in (2,3,4): await self.pay(user,enabled=True)
        self.assertEqual(self.balance(),540+3*55)

    async def test_money_and_award_roll_back_together(self):
        await db.change_referral_campaign('start')
        await self.pay(2); await self.pay(3)
        self.sql.execute("CREATE TRIGGER reject_ledger BEFORE INSERT ON billing_events BEGIN SELECT RAISE(ABORT,'fail'); END")
        with self.assertRaises(sqlite3.IntegrityError): await self.pay(4)
        self.assertEqual(self.balance(),0)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaign_awards').fetchone()[0],0)
        self.sql.execute('DROP TRIGGER reject_ledger')
        await self.pay(4)
        self.assertEqual(self.balance(),540)

    async def test_start_queues_only_reachable_users_once(self):
        self.sql.execute("UPDATE users SET bot_started_at=NULL WHERE telegram_id=2")
        self.sql.execute("UPDATE users SET blocked_at='now' WHERE telegram_id=3")
        self.sql.execute("UPDATE users SET bot_blocked_at='now' WHERE telegram_id=4")
        await db.change_referral_campaign('start')
        await db.change_referral_campaign('start')
        recipients = [r[0] for r in self.sql.execute('SELECT telegram_id FROM referral_campaign_messages ORDER BY telegram_id')]
        self.assertEqual(recipients,[1,5,6,7,8])
        await db.change_referral_campaign('stop',1)
        self.assertEqual(self.sql.execute("SELECT COUNT(*) FROM referral_campaign_messages WHERE status='pending'").fetchone()[0],0)

    async def test_scheduled_start_waits_then_queues_once(self):
        now = datetime(2030,1,1,12,tzinfo=timezone.utc)
        with patch.object(db,'_utc_now',return_value=now):
            await db.change_referral_campaign('schedule',scheduled_at=now+timedelta(minutes=10))
            await db.change_referral_campaign('scheduled_start')
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaigns').fetchone()[0],0)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaign_messages').fetchone()[0],0)
        with patch.object(db,'_utc_now',return_value=now+timedelta(minutes=11)):
            await db.change_referral_campaign('scheduled_start')
            await db.change_referral_campaign('scheduled_start')
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaigns').fetchone()[0],1)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaign_messages').fetchone()[0],8)
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaign_schedule').fetchone()[0],0)

    async def test_schedule_cancel_and_past_validation(self):
        now = datetime(2030,1,1,12,tzinfo=timezone.utc)
        with patch.object(db,'_utc_now',return_value=now):
            with self.assertRaises(ValueError):
                await db.change_referral_campaign('schedule',scheduled_at=now)
            await db.change_referral_campaign('schedule',scheduled_at=now+timedelta(hours=1))
            await db.change_referral_campaign('cancel_schedule')
        with patch.object(db,'_utc_now',return_value=now+timedelta(days=1)):
            await db.change_referral_campaign('scheduled_start')
        self.assertEqual(self.sql.execute('SELECT COUNT(*) FROM referral_campaigns').fetchone()[0],0)

    async def test_cannot_schedule_over_running_campaign(self):
        await db.change_referral_campaign('start')
        with self.assertRaises(ValueError):
            await db.change_referral_campaign('schedule',scheduled_at=datetime.now(timezone.utc)+timedelta(days=1))

    async def test_campaign_stats_separate_first_payments_and_runs(self):
        await db.change_referral_campaign('start')
        for user in (2,3,4): await self.pay(user,amount=100)
        await self.pay(2,'repeat-payment',first=False,amount=900)
        stats=await db.admin_referral_campaign_stats(1)
        self.assertEqual(stats['summary'],dict(participants=1,one_friend=0,two_friends=0,completed=1,friends=3,paid_rub=300))
        self.assertEqual(stats['awards'],dict(awards=1,awarded_rub=540))
        self.assertEqual(stats['delivery']['recipients'],8)
        self.assertEqual(stats['items'][0]['referrer_id'],1)
        self.assertEqual(stats['items'][0]['award_rub'],540)
        await db.change_referral_campaign('stop',1)
        await db.change_referral_campaign('start')
        await self.pay(5,amount=200)
        self.assertEqual((await db.admin_referral_campaign_stats(2))['summary']['one_friend'],1)
        self.assertEqual((await db.admin_referral_campaign_stats(1))['summary']['paid_rub'],300)
        self.assertEqual((await db.admin_referral_campaign_stats(1,2))['items'],[])
        with self.assertRaises(ValueError): await db.admin_referral_campaign_stats(999)

    async def test_empty_campaign_stats_are_zero(self):
        await db.change_referral_campaign('start')
        stats=await db.admin_referral_campaign_stats(1)
        self.assertEqual(stats['summary']['paid_rub'],0)
        self.assertEqual(stats['summary']['participants'],0)
        self.assertEqual(stats['items'],[])

    async def test_manual_retry_only_temporary_failed_reachable_and_active(self):
        await db.change_referral_campaign('start')
        self.sql.execute("UPDATE referral_campaign_messages SET status='failed',retryable=TRUE WHERE telegram_id IN (1,2,3)")
        self.sql.execute("UPDATE referral_campaign_messages SET status='sent',retryable=TRUE WHERE telegram_id=4")
        self.sql.execute("UPDATE users SET bot_blocked_at='now' WHERE telegram_id=2")
        self.sql.execute("UPDATE referral_campaign_messages SET retryable=FALSE WHERE telegram_id=3")
        self.sql.commit()
        self.assertEqual(await db.retry_campaign_failures(1),1)
        self.assertEqual(await db.retry_campaign_failures(1),0)
        self.assertEqual(self.sql.execute('SELECT status FROM referral_campaign_messages WHERE telegram_id=4').fetchone()[0],'sent')
        await db.change_referral_campaign('stop',1)
        with self.assertRaises(ValueError): await db.retry_campaign_failures(1)
