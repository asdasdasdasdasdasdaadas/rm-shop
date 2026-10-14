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
        self.proc.stdin.write((json.dumps(dict(sql=sql,args=args,script=script), default=lambda value: value.isoformat())+'\n').encode())
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

    async def test_recovery_requires_closed_ticket_not_online(self):
        await self.pool.execute("UPDATE users SET vpn_feedback='help',vpn_feedback_at=NOW()-INTERVAL '3 days'")
        await self.pool.execute("INSERT INTO tickets (telegram_id,status,closed_at) VALUES (1,'closed',NOW()-INTERVAL '4 days')")
        await self.pool.execute("INSERT INTO devices (telegram_id,title,last_online_at) VALUES (1,'Phone',NOW()-INTERVAL '2 days')")
        await db.resolve_recovered_vpn_feedback()
        self.assertEqual(await self.pool.fetchval('SELECT vpn_feedback FROM users'),'help')
        await self.pool.execute('UPDATE devices SET last_online_at=NOW()')
        await db.resolve_recovered_vpn_feedback()
        self.assertEqual(await self.pool.fetchval('SELECT vpn_feedback FROM users'),'help')
        await self.pool.execute('UPDATE tickets SET closed_at=NOW()')
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

    async def test_pending_gift_starts_billing_only_after_confirmed_connection(self):
        self.assertEqual(await db.claim_trial_balance(1,18),18)
        self.assertTrue((await db.get_user(1))['trial_waiting_connection'])
        await db.add_device(1,'Phone',77,'ios')
        await self.pool.execute("UPDATE devices SET panel_status='ACTIVE',last_billed_at=NOW()-INTERVAL '3 days',last_billed_on=NULL WHERE telegram_id=1")
        self.assertEqual(await db.devices_due_for_billing(),[])
        self.assertEqual(await self.balance(),18)
        await db.claim_first_online_for_panel_ids([77])
        self.assertFalse((await db.get_user(1))['trial_waiting_connection'])
        self.assertEqual(len(await db.devices_due_for_billing()),1)
        self.assertEqual(await db.take_device_charges(1,6,1),1)
        device=(await db.list_devices(1))[0]
        await db.mark_devices_billed([device['id']])
        await db.claim_first_online_for_panel_ids([77])
        self.assertEqual(await db.devices_due_for_billing(),[])
        self.assertEqual(await self.balance(),12)
        self.assertIsNone(await db.claim_trial_balance(1,18))

    async def test_real_postgres_funnel_separates_pending_and_exhausted_access(self):
        await self.pool.execute("UPDATE users SET has_paid_topup=TRUE,balance_rub=0 WHERE telegram_id=1")
        device=await db.add_device(1,'Phone',77,'ios')
        row=await self.pool.fetchrow(db._funnel_cte()+db._FUNNEL_SELECT,None,None)
        self.assertEqual(row['paid_no_repeat'],0)
        self.assertEqual(row['progress_paid_no_repeat'],1)
        self.assertTrue(await db.has_funded_access(1))
        await self.pool.execute("UPDATE devices SET last_billed_at=NOW()-INTERVAL '25 hours' WHERE id=$1",device['id'])
        row=await self.pool.fetchrow(db._funnel_cte()+db._FUNNEL_SELECT,None,None)
        self.assertEqual(row['paid_no_repeat'],1)
        self.assertEqual(row['progress_paid_no_repeat'],0)
        self.assertFalse(await db.has_funded_access(1))

    async def test_payment_offer_waits_for_exhaustion_and_respects_feedback(self):
        from app import config, funnel_board
        await self.pool.execute("UPDATE users SET first_online_at=NOW(),balance_rub=18 WHERE telegram_id=1")
        step=funnel_board._step('unpaid-test','recover_payment',0,'Тест',['topup'])
        with patch.object(config,'get_settings',return_value=self.settings):
            self.assertEqual(await funnel_board._due(step,None,20,[]),[])
            await self.pool.execute('UPDATE users SET balance_rub=1 WHERE telegram_id=1')
            self.assertEqual(len(await funnel_board._due(step,None,20,[])),1)
            await db.save_vpn_feedback(1,'terms')
            self.assertEqual(await funnel_board._due(step,None,20,[]),[])

    async def test_recovery_segments_and_stop_on_progress(self):
        from app import config, funnel_board
        from app.recovery_funnel import CONDITIONS
        await funnel_board._ensure_tables()
        async def eligible():
            result=[]
            for condition in CONDITIONS:
                step=funnel_board._step('test-'+condition['id'],condition['id'],0,'Тест',['cabinet'])
                if await funnel_board._due(step,None,10,[]): result.append(condition['id'])
            return result
        with patch.object(config,'get_settings',return_value=self.settings):
            self.assertEqual(await eligible(),['recover_gift'])
            await db.claim_trial_balance(1,18)
            self.assertEqual(await eligible(),['recover_setup'])
            await db.add_device(1,'Phone',77)
            self.assertEqual(await eligible(),['recover_online'])
            await self.pool.execute("UPDATE users SET first_online_at=NOW(),trial_waiting_connection=FALSE WHERE telegram_id=1")
            await self.pool.execute('UPDATE devices SET last_online_at=NOW()')
            self.assertEqual(await eligible(),['recover_quality'])
            await self.pool.execute("UPDATE devices SET last_billed_at=NOW()-INTERVAL '2 days'")
            await self.pool.execute('UPDATE users SET balance_rub=0 WHERE telegram_id=1')
            self.assertEqual(await eligible(),['recover_payment'])
            await self.credit()
            self.assertEqual(await eligible(),[])
            await self.pool.execute("UPDATE users SET first_online_at=NOW()-INTERVAL '8 days',bot_started_at=NOW()-INTERVAL '9 days' WHERE telegram_id=1")
            await self.pool.execute("UPDATE devices SET last_online_at=NOW()-INTERVAL '8 days'")
            self.assertEqual(await eligible(),['recover_idle'])
            await db.save_vpn_feedback(1,'later')
            self.assertEqual(await eligible(),[])

    async def test_recovery_followup_delay_cooldown_and_quiet(self):
        from app import config, funnel_board
        from app.recovery_funnel import branches
        await funnel_board._ensure_tables()
        first,second,last=branches()[0]['steps']
        with patch.object(config,'get_settings',return_value=self.settings):
            self.assertEqual(len(await funnel_board._due(first,None,10,[])),1)
            self.assertEqual(await funnel_board._due(second,first['id'],10,[]),[])
            await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id,step_id,sent_at) VALUES (1,$1,NOW()-INTERVAL '47 hours')",first['id'])
            self.assertEqual(await funnel_board._due(second,first['id'],10,[]),[])
            await self.pool.execute("UPDATE funnel_step_sends SET sent_at=NOW()-INTERVAL '49 hours'")
            self.assertEqual(len(await funnel_board._due(second,first['id'],10,[])),1)
            await db.log_bot_message(kind='nudge_recover_setup',source='auto',telegram_id=1,title='Test',body='Test',status='sent')
            self.assertEqual(await funnel_board._due(second,first['id'],10,[]),[])
            await self.pool.execute("DELETE FROM message_log")
            await self.pool.execute('UPDATE users SET quiet_notifications=TRUE WHERE telegram_id=1')
            self.assertEqual(await funnel_board._due(second,first['id'],10,[]),[])

    async def test_recovery_migration_keeps_backup_and_later_edits(self):
        from app import funnel_board
        from app.recovery_funnel import migrate, VERSION
        await funnel_board._ensure_tables()
        graph=funnel_board.validate({'branches':[{'id':'custom','title':'Моя ветка','steps':[funnel_board._step('custom-step','info',24,'Мой текст',['cabinet'])]}]})
        await self.pool.execute('INSERT INTO funnel_graphs(id,graph) VALUES (1,$1::jsonb)',json.dumps(graph))
        updated=await migrate(self.pool,graph)
        self.assertEqual(len(updated['branches']),7)
        self.assertEqual(json.loads(await self.pool.fetchval('SELECT value FROM app_flags WHERE key=$1',VERSION+'_backup')),graph)
        updated['branches'][0]['steps'][0]['text']='Изменено администратором'
        await self.pool.execute('UPDATE funnel_graphs SET graph=$1::jsonb WHERE id=1',json.dumps(updated))
        self.assertEqual(await migrate(self.pool,graph),updated)

    async def test_recovery_attribution_latest_click_without_double_revenue(self):
        a=await db.create_reminder_delivery(1,'nudge_recover_gift','A','A')
        b=await db.create_reminder_delivery(1,'nudge_recover_setup','B','B')
        await db.finish_reminder_delivery(a,'sent',11)
        await db.finish_reminder_delivery(b,'sent',12)
        await db.record_reminder_click(1,message_id=11)
        self.assertIsNone(await self.pool.fetchval('SELECT cabinet_opened_at FROM reminder_deliveries WHERE token=$1',a))
        await db.record_reminder_click(1,token=b)
        device=await db.add_device(1,'Phone',77)
        await self.credit()
        await self.pool.execute('DELETE FROM devices WHERE id=$1',device['id'])
        stats={g['kind']:g for g in (await db.admin_reminder_results())['groups']}
        self.assertEqual(stats['nudge_recover_gift']['paid_rub'],0)
        self.assertEqual(stats['nudge_recover_setup']['paid_rub'],100)
        self.assertEqual(stats['nudge_recover_setup']['first_paid'],1)
        self.assertEqual(stats['nudge_recover_setup']['opened'],1)
        self.assertEqual(stats['nudge_recover_setup']['devices'],1)

    async def test_checkout_feedback_owner_dedup_and_paid_exclusion(self):
        from app import checkout_feedback as feedback
        await db.track_checkout(1)
        await self.pool.execute("UPDATE users SET checkout_nudge_at=NOW() WHERE telegram_id=1")
        token=await self.pool.fetchval('SELECT checkout_token FROM users WHERE telegram_id=1')
        self.assertFalse(await feedback.save(2,token,'price'))
        self.assertFalse(await feedback.save(1,'stale','price'))
        self.assertFalse(await feedback.save(1,token,'unknown'))
        self.assertTrue(await feedback.save(1,token,'price'))
        self.assertFalse(await feedback.save(1,token,'later'))
        self.assertEqual((await feedback.stats())[0]['responses'],1)
        await db.track_checkout(1)
        await self.pool.execute("UPDATE users SET checkout_nudge_at=NOW() WHERE telegram_id=1")
        token=await self.pool.fetchval('SELECT checkout_token FROM users WHERE telegram_id=1')
        await self.credit()
        self.assertFalse(await feedback.save(1,token,'price'))

    async def test_feedback_changes_journey_without_overriding_quiet(self):
        from app import checkout_feedback as feedback
        await db.track_checkout(1)
        await self.pool.execute('UPDATE users SET checkout_nudge_at=NOW(),quiet_notifications=TRUE WHERE telegram_id=1')
        token=await self.pool.fetchval('SELECT checkout_token FROM users WHERE telegram_id=1')
        self.assertTrue(await feedback.save(1,token,'later'))
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))
        await self.credit()
        await db.resolve_recovered_vpn_feedback()
        user=await db.get_user(1)
        self.assertIsNotNone(user['marketing_pause_until'])
        self.assertTrue(user['quiet_notifications'])
        await db.save_vpn_feedback(1,'terms')
        await self.pool.execute("UPDATE users SET vpn_feedback_at=NOW()-INTERVAL '1 hour' WHERE telegram_id=1")
        await db.resolve_recovered_vpn_feedback()
        self.assertIsNone((await db.get_user(1))['vpn_feedback'])
        self.assertTrue((await db.get_user(1))['quiet_notifications'])

    async def test_broken_checkout_stops_marketing(self):
        from app import checkout_feedback as feedback
        await db.track_checkout(1)
        await self.pool.execute('UPDATE users SET checkout_nudge_at=NOW() WHERE telegram_id=1')
        token=await self.pool.fetchval('SELECT checkout_token FROM users WHERE telegram_id=1')
        self.assertTrue(await feedback.save(1,token,'broken'))
        self.assertEqual((await db.get_user(1))['vpn_feedback'],'help')
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))

    async def test_setup_assistance_bypasses_marketing_cooldown_but_is_bounded(self):
        from app import config, funnel_board
        from app.recovery_funnel import branches
        await funnel_board._ensure_tables()
        await db.claim_trial_balance(1,18)
        await db.add_device(1,'Phone',77)
        await self.pool.execute("UPDATE devices SET created_at=NOW()-INTERVAL '2 hours'")
        await db.log_bot_message(kind='nudge_recover_gift',source='auto',telegram_id=1,title='Gift',body='Gift',status='sent')
        await self.pool.execute("UPDATE message_log SET created_at=NOW()-INTERVAL '3 hours'")
        step=branches()[2]['steps'][0]
        with patch.object(config,'get_settings',return_value=self.settings):
            self.assertEqual(len(await funnel_board._due(step,None,10,[])),1)
        self.assertIsNone(await db.reserve_optional_message(1,'broadcast'))
        slot=await db.reserve_setup_assistance(1)
        self.assertIsNotNone(slot)
        self.assertIsNone(await db.reserve_setup_assistance(1))
        await db.finish_optional_message(slot,True)
        self.assertIsNone(await db.reserve_setup_assistance(1))
        await self.pool.execute('UPDATE users SET quiet_notifications=TRUE WHERE telegram_id=1')
        self.assertIsNone(await db.reserve_setup_assistance(1))

    async def test_idle_cycle_restarts_only_after_a_new_connection(self):
        from app import config, funnel_board
        from app.recovery_funnel import branches
        await funnel_board._ensure_tables()
        await self.pool.execute("UPDATE users SET bot_started_at=NOW()-INTERVAL '40 days',first_online_at=NOW()-INTERVAL '30 days' WHERE telegram_id=1")
        await db.add_device(1,'Phone',77)
        await self.pool.execute("UPDATE devices SET last_online_at=NOW()-INTERVAL '20 days'")
        first,second,last=branches()[-1]['steps']
        for step in (first,second,last):
            await self.pool.execute("INSERT INTO funnel_step_sends(telegram_id,step_id,sent_at) VALUES(1,$1,NOW()-INTERVAL '12 days')",step['id'])
        with patch.object(config,'get_settings',return_value=self.settings):
            self.assertEqual(await funnel_board._due(first,None,10,[]),[])
            await self.pool.execute("UPDATE devices SET last_online_at=NOW()-INTERVAL '8 days'")
            self.assertEqual(len(await funnel_board._due(first,None,10,[])),1)
            self.assertEqual(await funnel_board._due(second,first['id'],10,[]),[])
            await self.pool.execute("UPDATE funnel_step_sends SET sent_at=NOW()-INTERVAL '49 hours' WHERE step_id=$1",first['id'])
            self.assertEqual(len(await funnel_board._due(second,first['id'],10,[])),1)

    async def test_happy_trial_user_can_receive_referral_invite(self):
        from app import config, funnel_board
        await funnel_board._ensure_tables()
        await self.pool.execute("UPDATE users SET first_online_at=NOW()-INTERVAL '3 days',vpn_feedback='ok',balance_rub=18 WHERE telegram_id=1")
        step=funnel_board._step('invite-check','invite',48,'Invite',['share'])
        with patch.object(config,'get_settings',return_value=self.settings):
            self.assertEqual(len(await funnel_board._due(step,None,10,[])),1)

    async def test_idle_message_targets_access_state(self):
        from app import config, funnel_board, nudge
        from app.recovery_funnel import branches
        step=branches()[-1]['steps'][0]
        settings=self.settings.model_copy(update={'webapp_public_url':'https://example.test'})
        for funded,destination in [(True,'connect'),(False,'topup')]:
            with patch('app.keyboards.mini_app_url',return_value='https://example.test'), patch.object(config,'get_settings',return_value=settings), patch.object(funnel_board,'_gate',AsyncMock(return_value=True)), patch.object(funnel_board,'_due',AsyncMock(return_value=[{'telegram_id':1}])), patch.object(db,'reserve_optional_message',AsyncMock(return_value=1)), patch.object(db,'finish_optional_message',AsyncMock()), patch.object(db,'has_funded_access',AsyncMock(return_value=funded)), patch.object(nudge,'_deliver_unbudgeted',AsyncMock(return_value=False)) as send:
                await funnel_board._send_step(None,step,None,[])
                self.assertIn('screen='+destination,send.await_args.kwargs['reply_markup'].inline_keyboard[0][0].web_app.url)

    async def test_complaint_queue_and_pause_survive_background_online(self):
        await db.save_vpn_feedback(1,'help')
        await db.save_vpn_feedback(1,'help')
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM tickets'),1)
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM ticket_messages'),1)
        await self.pool.execute("UPDATE tickets SET status='pending'")
        await db.save_vpn_feedback(1,'help')
        self.assertEqual(await self.pool.fetchval('SELECT status FROM tickets'),'open')
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM ticket_messages'),1)
        await self.pool.execute("UPDATE users SET vpn_feedback_at=NOW()-INTERVAL '2 hours',marketing_pause_started_at=NOW()-INTERVAL '2 hours',marketing_pause_until=NOW()+INTERVAL '7 days'")
        await self.pool.execute("INSERT INTO devices (telegram_id,title,last_online_at) VALUES (1,'Phone',NOW())")
        await db.resolve_recovered_vpn_feedback()
        user=await db.get_user(1)
        self.assertEqual(user['vpn_feedback'],'help')
        self.assertIsNotNone(user['marketing_pause_until'])
        await self.pool.execute("UPDATE users SET marketing_pause_until=NOW()-INTERVAL '1 second'")
        await db.resolve_recovered_vpn_feedback()
        self.assertIsNone((await db.get_user(1))['marketing_pause_until'])

    async def test_new_device_restarts_setup_assistance(self):
        from app import funnel_board, config
        settings_patch = patch.object(config, 'get_settings', return_value=self.settings)
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        await funnel_board._ensure_tables()
        await self.pool.execute("UPDATE users SET first_online_at=NOW()-INTERVAL '5 days'")
        await self.pool.execute("INSERT INTO devices (telegram_id,title,last_online_at) VALUES (1,'Old',NOW())")
        step=funnel_board._step('device-help','recover_online',0,'Тест',['connect'])
        self.assertEqual(await funnel_board._due(step,None,10,[]),[])
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id,step_id,sent_at) VALUES (1,'device-help',NOW()-INTERVAL '2 days')")
        await self.pool.execute("INSERT INTO devices (telegram_id,title) VALUES (1,'New')")
        self.assertEqual(len(await funnel_board._due(step,None,10,[])),1)
        await self.pool.execute('UPDATE devices SET last_online_at=NOW()')
        self.assertEqual(await funnel_board._due(step,None,10,[]),[])
