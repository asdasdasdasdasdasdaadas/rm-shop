"""Run real PostgreSQL SQL in isolated PGlite; set PGLITE_MODULE and NODE_BIN.
Telegram and panel calls are mocked; no user messages or real credits are sent.
"""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from app import db, billing, referrals, nudge
from app.config import Settings


class PgPool:
    def __init__(self, proc):
        self.proc = proc
        self.lock = asyncio.Lock()

    async def query(self, sql, args=(), script=False):
        self.proc.stdin.write((json.dumps(dict(sql=sql,args=args,script=script))+'\n').encode())
        await self.proc.stdin.drain()
        line = await self.proc.stdout.readline()
        if not line:
            raise RuntimeError('PGlite stopped')
        response = json.loads(line)
        if 'error' in response:
            raise RuntimeError(response['error'])
        return response['rows']

    @asynccontextmanager
    async def acquire(self):
        async with self.lock:
            yield PgConnection(self)

    async def fetch(self, sql, *args):
        async with self.acquire() as conn:
            return await conn.fetch(sql,*args)

    async def fetchrow(self, sql, *args):
        rows = await self.fetch(sql,*args)
        return rows[0] if rows else None

    async def fetchval(self, sql, *args):
        row = await self.fetchrow(sql,*args)
        return next(iter(row.values())) if row else None

    async def execute(self, sql, *args):
        await self.fetch(sql,*args)


class PgConnection:
    def __init__(self,pool): self.pool=pool
    @asynccontextmanager
    async def transaction(self):
        await self.pool.query('BEGIN')
        try:
            yield
        except BaseException:
            await self.pool.query('ROLLBACK')
            raise
        else:
            await self.pool.query('COMMIT')
    async def fetch(self,sql,*args): return await self.pool.query(sql,args)
    async def fetchrow(self,sql,*args):
        rows=await self.fetch(sql,*args)
        return rows[0] if rows else None
    async def fetchval(self,sql,*args):
        row=await self.fetchrow(sql,*args)
        return next(iter(row.values())) if row else None
    async def execute(self,sql,*args): await self.fetch(sql,*args)


@unittest.skipUnless(os.environ.get('PGLITE_MODULE'), 'Set PGLITE_MODULE to run PostgreSQL integration scenarios')
class FunnelPostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.proc=await asyncio.create_subprocess_exec(os.environ.get('NODE_BIN','node'),
            str(Path(__file__).parent/'support/pglite_bridge.mjs'),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE)
        self.pool=PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(),script=True)
        self.settings=Settings.model_construct(referral_program_enabled=True,referral_invitee_reward_rub=0,vpn_day_price_rub=6)
        for mod in (db,billing,referrals,nudge):
            p=patch.object(mod,'get_settings',return_value=self.settings);p.start();self.addCleanup(p.stop)
        p=patch.object(db,'_pool_req',return_value=self.pool);p.start();self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id,bot_started_at,has_paid_topup) VALUES (1,NOW()-INTERVAL '2 days',FALSE)")
        await self.pool.execute("INSERT INTO rollypay_orders (order_id,telegram_id,plan_code,status) VALUES ('one',1,'topup_100','created')")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def credit(self,key='rollypay:one'):
        return await db.credit_payment_once(1,'topup_100',key,100,stars=50)

    async def balance(self):
        return await self.pool.fetchval('SELECT balance_rub FROM users WHERE telegram_id=1')

    async def test_schema_rerunnable_and_duplicate_payment(self):
        receipt=await self.credit()
        self.assertTrue(receipt['first_payment'])
        await self.pool.query(db.SCHEMA_PATH.read_text(),script=True)
        self.assertIsNone(await self.credit())
        self.assertEqual(await self.balance(),100)
        self.assertEqual(await self.pool.fetchval("SELECT status FROM rollypay_orders WHERE order_id='one'"),'granted')
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM billing_events WHERE kind='topup'"),1)

    async def test_accounting_failure_rolls_back_then_retry_succeeds(self):
        await self.pool.query("""CREATE FUNCTION fail_accounting() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'test accounting failure'; END $$;
            CREATE TRIGGER fail_log BEFORE INSERT ON billing_events FOR EACH ROW EXECUTE FUNCTION fail_accounting();""",script=True)
        with self.assertRaisesRegex(RuntimeError,'accounting failure'):
            await self.credit()
        self.assertEqual(await self.balance(),0)
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM payment_receipts'),0)
        self.assertEqual(await self.pool.fetchval("SELECT status FROM rollypay_orders WHERE order_id='one'"),'created')
        await self.pool.execute('DROP TRIGGER fail_log ON billing_events')
        await self.credit()
        self.assertEqual(await self.balance(),100)

    async def test_duplicate_stars_and_serialized_first_payment(self):
        results=await asyncio.gather(*(self.credit('stars:same') for _ in range(12)))
        self.assertEqual(sum(r is not None for r in results),1)
        receipt=await self.credit('stars:second')
        self.assertFalse(receipt['first_payment'])
        self.assertEqual(await self.balance(),200)
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM payments'),2)

    async def test_historical_stars_and_order_never_recredited(self):
        await self.pool.execute("INSERT INTO payments (telegram_id,plan_code,stars,telegram_payment_id) VALUES (1,'topup_100',50,'old')")
        await self.pool.execute("UPDATE rollypay_orders SET status='granted' WHERE order_id='one'")
        self.assertIsNone(await self.credit('stars:old'))
        self.assertIsNone(await self.credit())
        self.assertEqual(await self.balance(),0)

    async def test_effect_failure_retries_without_crediting_again(self):
        receipt=await self.credit()
        with patch('app.balance.sync_user_billing',AsyncMock(side_effect=RuntimeError('panel offline'))), \
             patch.object(referrals,'maybe_reward_referrer',AsyncMock()), patch.object(referrals,'maybe_reward_invitee',AsyncMock()):
            with self.assertRaisesRegex(RuntimeError,'panel offline'):
                await billing.apply_payment_effects(receipt,None,None)
        self.assertEqual(await self.balance(),100)
        await self.pool.execute('UPDATE payment_receipts SET retry_at=NOW()')
        with patch('app.balance.sync_user_billing',AsyncMock()), patch.object(referrals,'maybe_reward_referrer',AsyncMock()), patch.object(referrals,'maybe_reward_invitee',AsyncMock()):
            await billing.apply_payment_effects((await db.pending_payment_effects())[0],None,None)
        self.assertEqual(await db.pending_payment_effects(),[])
        self.assertIsNone(await self.credit())
        self.assertEqual(await self.balance(),100)

    async def test_cross_sender_caps_failure_release_and_transactional_exemption(self):
        first=await db.reserve_optional_message(1,'nudge_invite')
        self.assertIsNotNone(first)
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))
        await db.finish_optional_message(first,False)
        second=await db.reserve_optional_message(1,'broadcast')
        self.assertIsNotNone(second)
        await db.finish_optional_message(second,True)
        self.assertIsNone(await db.reserve_optional_message(1,'referral_campaign_start'))
        for kind in ('nudge_trial_end','nudge_payment','first_device_thanks'):
            self.assertFalse(db.is_marketing_message(kind))
        await self.pool.execute("UPDATE optional_message_slots SET sent_at=NOW()-INTERVAL '2 days'")
        await self.pool.execute("INSERT INTO optional_message_slots (telegram_id,kind,sent_at) VALUES (1,'broadcast',NOW()-INTERVAL '3 days'),(1,'nudge_info',NOW()-INTERVAL '4 days')")
        self.assertIsNone(await db.reserve_optional_message(1,'nudge_invite'))

    async def test_pending_support_checkout_and_quiet_block_marketing(self):
        await self.pool.execute("INSERT INTO tickets (telegram_id,status) VALUES (1,'pending')")
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))
        await self.pool.execute("UPDATE tickets SET status='closed',closed_at=NOW()")
        await self.pool.execute('UPDATE users SET checkout_started_at=NOW()')
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))
        await self.pool.execute('UPDATE users SET checkout_started_at=NULL,quiet_notifications=TRUE')
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))
        await self.pool.execute('UPDATE users SET quiet_notifications=FALSE')
        self.assertIsNotNone(await db.reserve_optional_message(1,'broadcast'))

    async def test_recovery_requires_online_after_closed_ticket(self):
        await self.pool.execute("UPDATE users SET vpn_feedback='help',vpn_feedback_at=NOW()-INTERVAL '3 days'")
        await self.pool.execute("INSERT INTO tickets (telegram_id,status,closed_at) VALUES (1,'closed',NOW()-INTERVAL '1 day')")
        await self.pool.execute("INSERT INTO devices (telegram_id,title,last_online_at) VALUES (1,'Phone',NOW()-INTERVAL '2 days')")
        await db.resolve_recovered_vpn_feedback()
        self.assertEqual(await self.pool.fetchval('SELECT vpn_feedback FROM users'),'help')
        await self.pool.execute('UPDATE devices SET last_online_at=NOW()')
        await db.resolve_recovered_vpn_feedback()
        self.assertIsNone(await self.pool.fetchval('SELECT vpn_feedback FROM users'))

    async def test_quality_and_info_require_resolved_support_and_online(self):
        await self.pool.execute("UPDATE users SET first_online_at=NOW()-INTERVAL '5 days'")
        await self.pool.execute("INSERT INTO devices (telegram_id,title,last_online_at) VALUES (1,'Phone',NOW())")
        self.assertEqual(len(await db.list_due_info_nudges()),1)
        self.assertEqual(len(await db.list_due_first_online_nudges()),1)
        await self.pool.execute("INSERT INTO tickets (telegram_id,status) VALUES (1,'pending')")
        self.assertEqual(await db.list_due_info_nudges(),[])
        self.assertEqual(await db.list_due_first_online_nudges(),[])
        self.assertEqual(await db.list_due_invite_nudges(),[])

    async def test_public_fulfillment_and_replay_run_effects_once(self):
        await self.pool.execute("UPDATE rollypay_orders SET plan_code='b100'")
        with patch('app.balance.sync_user_billing',AsyncMock()) as sync, patch('app.live.paid'):
            first=await billing.fulfill_rollypay_order('one',None,None)
            second=await billing.fulfill_rollypay_order('one',None,None)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        sync.assert_awaited_once()
        self.assertEqual(await self.balance(),100)
        self.assertEqual(await db.pending_payment_effects(),[])

    async def test_stars_failed_transaction_does_not_consume_charge_id(self):
        await self.pool.query("""CREATE FUNCTION fail_accounting() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'test accounting failure'; END $$;
            CREATE TRIGGER fail_log BEFORE INSERT ON billing_events FOR EACH ROW EXECUTE FUNCTION fail_accounting();""",script=True)
        with self.assertRaises(RuntimeError):
            await self.credit('stars:retryable')
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM payments'),0)
        self.assertEqual(await self.balance(),0)
        await self.pool.execute('DROP TRIGGER fail_log ON billing_events')
        await self.credit('stars:retryable')
        self.assertEqual(await self.balance(),100)

    async def test_pending_payment_cannot_join_new_campaign_retroactively(self):
        await self.pool.execute('INSERT INTO users (telegram_id) VALUES (2)')
        await self.pool.execute('UPDATE users SET referred_by=2 WHERE telegram_id=1')
        receipt=await self.credit()
        await self.pool.execute('INSERT INTO referral_campaigns (reward_rub) VALUES (540)')
        result=await db.reward_referral_payment(1,receipt['payment_key'],100,enabled=True,
            first_payment=True,paid_at=receipt['created_at'])
        self.assertEqual(result['amount'],55)
        self.assertIsNone(result['campaign'])
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM referral_campaign_friends'),0)

    async def test_gift_setup_online_payment_path_with_real_selections(self):
        from app import keyboards
        self.settings=Settings.model_construct(trial_enabled=True,trial_days=3,
            vpn_day_price_rub=6,referral_program_enabled=True,referral_invitee_reward_rub=0,
            bot_username='test_bot',webapp_public_url='https://example.org')
        with patch.object(nudge,'get_settings',return_value=self.settings), \
             patch.object(referrals,'get_settings',return_value=self.settings), \
             patch.object(keyboards,'get_settings',return_value=self.settings), \
             patch.object(nudge,'_trial_channel_ready',AsyncMock(return_value=True)):
            bot=SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=10)))
            self.assertEqual((await nudge.send_due_trial_nudges(bot))[0],1)
            self.assertEqual((await nudge.send_due_trial_nudges(bot))[0],0)
            self.assertEqual(await self.balance(),0)  # Reminder never grants gift.
            self.assertEqual(await db.claim_trial_balance(1,18),18)
            self.assertIsNone(await db.claim_trial_balance(1,18))
            await self.pool.execute("UPDATE users SET gift_claimed_at=NOW()-INTERVAL '31 minutes'")
            self.assertEqual(len(await db.list_due_device_nudges()),1)
            await db.claim_first_online(1)
            self.assertEqual(await db.list_due_device_nudges(),[])
            await self.credit()
            self.assertEqual(await self.balance(),118)
            self.assertEqual(await db.list_due_trial_nudges(),[])

    async def test_marketing_prefilter_and_delivery_stats(self):
        await self.pool.execute("INSERT INTO tickets (telegram_id,status) VALUES (1,'pending')")
        self.assertIn(1,await db.marketing_suppressed_ids())
        await db.log_bot_message(kind='nudge_info',source='auto',telegram_id=1,title='Test',body='Test',status='sent')
        stats=await db.funnel_message_stats()
        self.assertEqual(stats['nudge_info']['sent'],1)
        self.assertIsNotNone(stats['nudge_info']['last_sent'])
