import sqlite3
import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

from app import db


class ReferralProgramTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function('pg_advisory_xact_lock',1,lambda _: None)
        self.conn.executescript('''
            CREATE TABLE referral_campaigns (id INTEGER PRIMARY KEY, stopped_at TEXT, reward_rub INTEGER);
            CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, referred_by INTEGER, referral_rewarded BOOLEAN DEFAULT FALSE,
                referral_fraction INTEGER DEFAULT 0, balance_rub INTEGER DEFAULT 0, referral_earned INTEGER DEFAULT 0,
                low_balance_notified_at TEXT);
            CREATE TABLE referral_payment_rewards (payment_key TEXT PRIMARY KEY, invitee_id INTEGER, referrer_id INTEGER,
                topup_rub INTEGER, enabled BOOLEAN, reward_rub INTEGER DEFAULT 0);
            CREATE TABLE billing_events (telegram_id INTEGER,kind TEXT,source TEXT,amount INTEGER,balance_after INTEGER,note TEXT);
            INSERT INTO users (telegram_id) VALUES (1);
            INSERT INTO users (telegram_id,referred_by) VALUES (2,1);
        ''')
        conn = self.conn
        class Connection:
            @asynccontextmanager
            async def transaction(self):
                try:
                    yield
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            async def fetchrow(self,sql,*args):
                return conn.execute(sql.replace(' FOR UPDATE',''),{str(i):v for i,v in enumerate(args,1)}).fetchone()
            async def fetchval(self,sql,*args):
                row = await self.fetchrow(sql,*args)
                return row[0] if row else None
            async def execute(self,sql,*args):
                return await self.fetchrow(sql,*args)
        class Pool:
            @asynccontextmanager
            async def acquire(self):
                yield Connection()
        self.patch = patch.object(db,'_pool_req',return_value=Pool())
        self.patch.start()
        self.addCleanup(self.patch.stop)

    async def reward(self,key,amount=300,enabled=True,first=False):
        return await db.reward_referral_payment(2,key,amount,enabled=enabled,first_payment=first)

    def balance(self):
        return self.conn.execute('SELECT balance_rub FROM users WHERE telegram_id=1').fetchone()[0]

    async def test_first_repeat_and_duplicate_payment(self):
        self.assertEqual((await self.reward('rp:1',first=True))['amount'],65)
        self.assertIsNone(await self.reward('rp:1',first=True))
        self.assertEqual((await self.reward('stars:2'))['amount'],15)
        self.assertEqual(self.balance(),80)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM billing_events').fetchone()[0],2)

    async def test_pause_no_retroactive_rewards_and_no_delayed_first_bonus(self):
        self.assertIsNone(await self.reward('rp:paused',enabled=False,first=True))
        self.assertIsNone(await self.reward('rp:paused',enabled=True,first=True))
        self.assertEqual((await self.reward('rp:next'))['amount'],15)
        self.assertEqual(self.balance(),15)
        self.assertIsNone(await self.reward('rp:paused_again',enabled=False))
        self.assertEqual(self.balance(),15)

    async def test_fractional_rewards_accumulate_and_first_bonus_once(self):
        for i in range(4):
            await self.reward(f'pay:{i}',25,first=True)
        self.assertEqual(self.balance(),55)
        self.assertEqual(self.conn.execute('SELECT referral_fraction FROM users WHERE telegram_id=1').fetchone()[0],0)

    async def test_no_self_reward_or_reward_without_referrer(self):
        self.conn.execute('UPDATE users SET referred_by=2 WHERE telegram_id=2')
        self.assertIsNone(await self.reward('self',first=True))
        self.conn.execute('UPDATE users SET referred_by=NULL WHERE telegram_id=2')
        self.assertIsNone(await self.reward('none',first=True))
        self.assertEqual(self.balance(),0)

    async def test_failure_rolls_back_ledger_balance_and_bonus(self):
        self.conn.execute("CREATE TRIGGER fail_log BEFORE INSERT ON billing_events BEGIN SELECT RAISE(ABORT,'failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            await self.reward('retry',first=True)
        self.assertEqual(self.balance(),0)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM referral_payment_rewards').fetchone()[0],0)
        self.conn.execute('DROP TRIGGER fail_log')
        self.assertEqual((await self.reward('retry',first=True))['amount'],65)


class ReferralGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_paused_program_records_payment_but_does_not_offer_invitee_bonus(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from app import referrals
        settings = SimpleNamespace(balance_enabled=True, referral_program_enabled=False)
        with patch.object(referrals,'get_settings',return_value=settings), \
             patch.object(referrals,'referral_is_payout',return_value=False), \
             patch.object(db,'reward_referral_payment',AsyncMock(return_value=None)) as reward, \
             patch.object(db,'claim_invitee_payment_bonus',AsyncMock()) as bonus:
            await referrals.maybe_reward_referrer(None,None,2,'Друг',payment_key='pay:1',topup_rub=300,first_payment=True)
            reward.assert_awaited_once_with(2,'pay:1',300,enabled=False,first_payment=True)
            self.assertEqual(await referrals.maybe_reward_invitee(None,2),0)
            bonus.assert_not_awaited()

    def test_program_defaults_to_paused(self):
        from app.config import Settings
        self.assertFalse(Settings.model_construct().referral_program_enabled)
