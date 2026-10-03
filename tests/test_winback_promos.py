import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
import test_funnel_integration as pg
from app import db, winback, nudge
from app.config import Settings


@unittest.skipUnless(os.environ.get('PGLITE_MODULE'), 'Set PGLITE_MODULE for PostgreSQL tests')
class WinbackPostgresTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = pg.FunnelPostgresTest.asyncSetUp
    asyncTearDown = pg.FunnelPostgresTest.asyncTearDown
    balance = pg.FunnelPostgresTest.balance

    async def exhausted(self, online=False, hours=0):
        await self.pool.execute('UPDATE users SET trial_used=TRUE,balance_rub=18 WHERE telegram_id=1')
        await self.pool.execute('UPDATE users SET balance_rub=0 WHERE telegram_id=1')
        await self.pool.execute("UPDATE users SET balance_exhausted_at=NOW()-($1 * INTERVAL '1 hour'),first_online_at=CASE WHEN $2 THEN NOW()-INTERVAL '4 days' ELSE NULL END WHERE telegram_id=1",hours,online)

    async def test_new_zero_balance_is_not_an_exhausted_gift(self):
        await db.backfill_balance_exhaustion()
        self.assertEqual(await db.list_due_winback_offers([]),[])
        await self.exhausted()
        self.assertEqual(len(await db.list_due_winback_offers([])),1)

    async def test_used_vpn_requires_48_hours_and_topup_resets_clock(self):
        await self.exhausted(online=True,hours=47)
        self.assertEqual(await db.list_due_winback_offers([]),[])
        await self.exhausted(online=True,hours=48)
        self.assertEqual(len(await db.list_due_winback_offers([])),1)
        await db.add_balance_rub(1,100)
        self.assertEqual(await db.list_due_winback_offers([]),[])
        self.assertIsNone(await self.pool.fetchval('SELECT balance_exhausted_at FROM users WHERE telegram_id=1'))
        await self.pool.execute('UPDATE users SET balance_rub=0 WHERE telegram_id=1')
        self.assertEqual(await db.list_due_winback_offers([]),[])

    async def test_historical_zero_crossing_is_backfilled(self):
        await self.pool.execute('UPDATE users SET trial_used=TRUE WHERE telegram_id=1')
        await self.pool.execute("INSERT INTO billing_events(telegram_id,kind,source,amount,balance_after,created_at) VALUES (1,'charge','cron',-6,0,NOW()-INTERVAL '3 days')")
        await self.pool.execute("UPDATE users SET created_at=NOW()-INTERVAL '10 days',first_online_at=NOW()-INTERVAL '4 days' WHERE telegram_id=1")
        await db.backfill_balance_exhaustion()
        self.assertEqual(len(await db.list_due_winback_offers([])),1)

    async def test_device_snapshot_personal_once_and_debt_repaid_at_redemption(self):
        await self.exhausted()
        await self.pool.execute("INSERT INTO devices(telegram_id,title,kind) VALUES (1,'a',''),(1,'b',''),(1,'router','router')")
        offer=await db.prepare_winback_offer(1,6)
        self.assertEqual((offer['device_count'],offer['gift_rub']),(2,60))
        self.assertRegex(offer['code'],r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$')
        await db.finish_winback_offer(offer['id'],True)
        await self.pool.execute('INSERT INTO users(telegram_id) VALUES (2)')
        with self.assertRaisesRegex(ValueError,'другому'):
            await db.redeem_promo_code(2,offer['code'])
        await self.pool.execute("INSERT INTO devices(telegram_id,title) VALUES (1,'added later')")
        await self.pool.execute('UPDATE users SET balance_rub=-13 WHERE telegram_id=1')
        result=await db.redeem_promo_code(1,offer['code'])
        self.assertEqual(result['credited_rub'],73)
        self.assertEqual(result['balance_rub'],60)
        self.assertEqual(result['days'],5)
        with self.assertRaises(ValueError):
            await db.redeem_promo_code(1,offer['code'])
        self.assertEqual(await self.balance(),60)

    async def test_no_device_gets_one_device_and_paid_balance_keeps_sent_gift(self):
        await self.exhausted()
        offer=await db.prepare_winback_offer(1,6)
        self.assertEqual((offer['device_count'],offer['gift_rub']),(1,30))
        await db.finish_winback_offer(offer['id'],True)
        await db.add_balance_rub(1,100)
        result=await db.redeem_promo_code(1,offer['code'])
        self.assertEqual(result['balance_rub'],130)
        self.assertEqual(result['debt_repaid_rub'],0)

    async def test_two_calendar_month_cooldown_and_expiry(self):
        await self.exhausted()
        offer=await db.prepare_winback_offer(1,6)
        await db.finish_winback_offer(offer['id'],True)
        self.assertEqual(await db.list_due_winback_offers([]),[])
        self.assertTrue(await self.pool.fetchval("SELECT expires_at > NOW()+INTERVAL '6 days 23 hours' FROM promo_codes WHERE id=$1",offer['promo_id']))
        await self.pool.execute("UPDATE promo_codes SET expires_at=NOW()-INTERVAL '1 second' WHERE id=$1",offer['promo_id'])
        with self.assertRaisesRegex(ValueError,'истёк'):
            await db.redeem_promo_code(1,offer['code'])
        await self.pool.execute("UPDATE users SET winback_last_sent_at=NOW()-INTERVAL '1 month' WHERE telegram_id=1")
        self.assertEqual(await db.list_due_winback_offers([]),[])
        await self.pool.execute("UPDATE users SET winback_last_sent_at=NOW()-INTERVAL '2 months 1 second' WHERE telegram_id=1")
        self.assertEqual(len(await db.list_due_winback_offers([])),1)
        second=await db.prepare_winback_offer(1,6)
        self.assertNotEqual(second['code'],offer['code'])

    async def test_failed_send_reuses_code_and_does_not_start_cooldown(self):
        await self.exhausted()
        first=await db.prepare_winback_offer(1,6)
        self.assertIsNone(await db.prepare_winback_offer(1,6))
        await db.finish_winback_offer(first['id'],False)
        self.assertIsNone(await self.pool.fetchval('SELECT winback_last_sent_at FROM users WHERE telegram_id=1'))
        await self.pool.execute('UPDATE winback_offers SET retry_at=NOW()')
        retry=await db.prepare_winback_offer(1,6)
        self.assertEqual(first['code'],retry['code'])
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM promo_codes'),1)

    async def test_atomic_credit_rollback_and_regular_promo(self):
        await self.exhausted()
        offer=await db.prepare_winback_offer(1,6)
        await db.finish_winback_offer(offer['id'],True)
        await self.pool.query("""CREATE FUNCTION fail_promo_log() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'accounting failure'; END $$;
            CREATE TRIGGER fail_log BEFORE INSERT ON billing_events FOR EACH ROW EXECUTE FUNCTION fail_promo_log();""",script=True)
        with self.assertRaisesRegex(RuntimeError,'accounting failure'):
            await db.redeem_promo_code(1,offer['code'])
        self.assertEqual(await self.balance(),0)
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM promo_uses'),0)
        self.assertEqual(await self.pool.fetchval('SELECT used_count FROM promo_codes WHERE id=$1',offer['promo_id']),0)
        await self.pool.execute('DROP TRIGGER fail_log ON billing_events')
        await db.redeem_promo_code(1,offer['code'])
        await self.pool.execute("INSERT INTO promo_codes(code,days) VALUES ('REGULAR',2)")
        self.assertEqual((await db.redeem_promo_code(1,'REGULAR'))['balance_rub'],42)

    async def test_owner_deletion_does_not_turn_code_public(self):
        await self.exhausted()
        offer=await db.prepare_winback_offer(1,6)
        await self.pool.execute('DELETE FROM rollypay_orders WHERE telegram_id=1')
        await self.pool.execute('DELETE FROM users WHERE telegram_id=1')
        await self.pool.execute('INSERT INTO users(telegram_id) VALUES (2)')
        with self.assertRaisesRegex(ValueError,'другому'):
            await db.redeem_promo_code(2,offer['code'])

    async def test_sender_uses_shared_policy_and_records_success(self):
        await self.exhausted()
        settings=Settings.model_construct(vpn_day_price_rub=6)
        bot=SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=77)))
        with patch.object(winback,'get_settings',return_value=settings),patch.object(winback,'mini_app_url',return_value='https://example.org'):
            await self.pool.execute('UPDATE users SET quiet_notifications=TRUE WHERE telegram_id=1')
            self.assertEqual(await winback.send_due(bot),(0,[]))
            bot.send_message.assert_not_awaited()
            await self.pool.execute('UPDATE users SET quiet_notifications=FALSE WHERE telegram_id=1')
            self.assertEqual(await winback.send_due(bot),(1,[1]))
            self.assertEqual(await winback.send_due(bot),(0,[]))
        bot.send_message.assert_awaited_once()
        self.assertIn('5 дней',bot.send_message.call_args.args[1])
        kb=bot.send_message.call_args.kwargs['reply_markup']
        self.assertEqual([row[0].text for row in kb.inline_keyboard],['Личный кабинет','Главное меню'])
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM optional_message_slots WHERE sent_at IS NOT NULL"),1)
