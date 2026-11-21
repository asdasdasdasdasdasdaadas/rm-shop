"""Автопополнение (app/autopay.py): interval math, and the whole path on real PostgreSQL in PGlite.

CISPay and Telegram are mocked; set PGLITE_MODULE and NODE_BIN for the database scenarios.
"""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from app import autopay, billing, db, referrals
from app.config import Settings


class IntervalTest(unittest.TestCase):
    def test_steady_interval_is_amount_over_cost_per_day(self):
        self.assertEqual(autopay.steady_interval(300, 6), 50)
        self.assertEqual(autopay.steady_interval(300, 12), 25)
        self.assertEqual(autopay.steady_interval(100, 30), 7)  # CISPay minimum
        self.assertEqual(autopay.steady_interval(100000, 6), 360)  # CISPay maximum

    def test_first_charge_comes_with_two_days_left(self):
        # 20 ₽ on the balance + 300 ₽ now, 6 ₽ a day: 53 days, the next 300 ₽ two days before the end.
        self.assertEqual(autopay.first_interval(300, 20, 6), 51)
        self.assertEqual(autopay.first_interval(300, -50, 6), 48)  # a debt is not counted as money

    def test_amounts_that_do_not_last_a_week_cannot_be_chosen(self):
        options = {o["amount"]: o for o in autopay.amount_options(30)}  # five devices
        self.assertFalse(options[100]["ok"])
        self.assertTrue(options[300]["ok"])
        self.assertEqual(autopay.default_amount(30), 300)
        self.assertEqual(autopay.default_amount(50), 500)


class FakeCISPay:
    def __init__(self):
        self.create_subscription = AsyncMock(return_value={"id": "sub-1", "payment_url": "https://pay/sub-1", "status": "PENDING"})
        self.cancel_subscription = AsyncMock(return_value={"id": "sub-1", "status": "CANCELLED"})
        self.update_subscription = AsyncMock(return_value={})
        self.remote = {"id": "sub-1", "status": "ACTIVE", "interval_days": 51, "charges": [],
                       "next_charge_at": "2026-12-20T10:00:00+00:00"}
        self.get_subscription = AsyncMock(side_effect=lambda _id: dict(self.remote))


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class AutopayPostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        self.settings = Settings.model_construct(
            vpn_day_price_rub=6, cispay_shop_id="shop", cispay_api_key="cis_sec_x", autopay_enabled=True,
            brand_name="Лягушка", bot_username="", referral_program_enabled=False, referral_invitee_reward_rub=0)
        from app import cispay
        for mod in (db, billing, referrals, autopay, cispay):
            p = patch.object(mod, "get_settings", return_value=self.settings)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(db, "_pool_req", return_value=self.pool)
        p.start()
        self.addCleanup(p.stop)
        for target, mock in (("app.balance.sync_user_billing", AsyncMock()), ("app.live.paid", None),
                             ("app.payment_notice.deliver_payment_notice", AsyncMock())):
            p = patch(target, mock) if mock else patch(target)
            p.start()
            self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id, bot_started_at, balance_rub) VALUES (7, NOW(), 20)")
        await self.pool.execute("INSERT INTO devices (telegram_id, title) VALUES (7, 'Phone')")
        self.rp = FakeCISPay()
        self.bot = AsyncMock()

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def balance(self):
        return await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=7")

    async def test_turn_on_charge_twice_and_turn_off(self):
        self.assertTrue(await autopay.offer_ok(7))
        out = await autopay.start(self.rp, 7, 300)
        self.assertEqual(out["pay_url"], "https://pay/sub-1")
        kwargs = self.rp.create_subscription.await_args.kwargs
        self.assertEqual((kwargs["amount_rub"], kwargs["interval_days"], kwargs["customer_id"]), (300, 51, "7"))
        # Asking again for the same amount reuses the page instead of a second subscription.
        await autopay.start(self.rp, 7, 300)
        self.rp.create_subscription.assert_awaited_once()

        paid = {"id": "tx-1", "status": "PAID", "amount": 30000, "subscription_id": "sub-1"}
        self.assertTrue(await autopay.on_payment(paid, self.rp, None, self.bot))
        self.assertTrue(await autopay.on_payment(paid, self.rp, None, self.bot))  # CISPay repeats webhooks
        self.assertEqual(await self.balance(), 320)
        self.assertEqual(await self.pool.fetchval("SELECT status FROM pay_orders WHERE order_id='ap-tx-1'"), "granted")

        await autopay.on_event({"event": "subscription.activated", "id": "sub-1", "status": "ACTIVE",
                                "interval_days": 51}, self.rp, self.bot)
        row = await autopay.get(7)
        self.assertEqual(row["status"], "active")
        self.rp.update_subscription.assert_awaited_with("sub-1", interval_days=50)
        self.assertIn("Автопополнение включено", self.bot.send_message.await_args.args[1])
        self.assertFalse(await autopay.offer_ok(7))

        view = await autopay.public(7)
        self.assertEqual((view["status"], view["amount"], len(view["charges"])), ("active", 300, 1))

        # A charge whose webhook never came is credited by the hourly pass.
        self.rp.remote["charges"] = [{"id": "tx-2", "status": "PAID", "amount": 30000}]
        with patch("app.runtime.rw", None), patch("app.runtime.bot", self.bot):
            await autopay.sync_once(self.rp, None)
        self.assertEqual(await self.balance(), 620)

        failed = {"id": "tx-3", "status": "FAILED", "amount": 30000, "subscription_id": "sub-1"}
        self.bot.send_message.reset_mock()
        with patch("app.trust.promise_available", AsyncMock(return_value=False)):
            await autopay.on_payment(failed, self.rp, None, self.bot)
            await autopay.on_payment(failed, self.rp, None, self.bot)
        self.bot.send_message.assert_awaited_once()
        self.assertIn("Не получилось пополнить", self.bot.send_message.await_args.args[1])
        self.assertEqual((await autopay.get(7))["fails"], 1)

        self.assertTrue(await autopay.stop(self.rp, 7))
        self.rp.cancel_subscription.assert_awaited_with("sub-1")
        self.bot.send_message.reset_mock()
        await autopay.on_event({"event": "subscription.cancelled", "id": "sub-1", "status": "CANCELLED",
                                "reason": "cancelled_by_merchant"}, self.rp, self.bot)
        self.bot.send_message.assert_not_awaited()  # they switched it off themselves
        self.assertTrue(await autopay.offer_ok(7))

    async def test_second_decline_in_a_row_switches_it_off(self):
        await autopay.start(self.rp, 7, 300)
        await autopay.on_event({"event": "subscription.activated", "id": "sub-1", "status": "ACTIVE"}, self.rp, self.bot)
        self.bot.send_message.reset_mock()
        with patch("app.trust.promise_available", AsyncMock(return_value=False)):
            for tx in ("tx-a", "tx-b"):
                await autopay.on_payment({"id": tx, "status": "FAILED", "subscription_id": "sub-1"}, self.rp, None, self.bot)
        self.rp.cancel_subscription.assert_awaited_with("sub-1")
        row = await autopay.get(7)
        self.assertEqual((row["status"], row["ended_reason"]), ("failed", "failed_twice"))
        self.assertIn("не прошло дважды", self.bot.send_message.await_args.args[1])
        view = await autopay.public(7)
        self.assertTrue(view["failed"])
        # CISPay's own «cancelled» after our cancel tells nothing more.
        self.bot.send_message.reset_mock()
        await autopay.on_event({"event": "subscription.cancelled", "id": "sub-1", "status": "CANCELLED",
                                "reason": "cancelled_by_merchant"}, self.rp, self.bot)
        self.bot.send_message.assert_not_awaited()

    async def test_repeat_charge_gets_its_own_receipt(self):
        await autopay.start(self.rp, 7, 300)
        self.assertEqual(await autopay.receipt_text(7, 300),
                         "✅ <b>Автопополнение: +300 ₽</b>\n\nБаланс 20 ₽ — хватит до " + autopay._until(3) + ".\nОплата через СБП.")

    async def test_bank_unbinding_is_told(self):
        await autopay.start(self.rp, 7, 300)
        await autopay.on_event({"event": "subscription.activated", "id": "sub-1", "status": "ACTIVE"}, self.rp, self.bot)
        self.bot.send_message.reset_mock()
        await autopay.on_event({"event": "subscription.cancelled", "id": "sub-1", "status": "CANCELLED",
                                "reason": "unbound_in_bank"}, self.rp, self.bot)
        self.assertIn("приложении банка", self.bot.send_message.await_args.args[1])
        self.assertEqual((await autopay.get(7))["status"], "cancelled")

    async def test_not_now_hides_the_offer_for_a_month(self):
        await autopay.decline(7)
        self.assertFalse(await autopay.offer_ok(7))
        self.assertFalse((await autopay.public(7))["offer"])

    async def test_hidden_until_switched_on_except_for_admins(self):
        self.settings.autopay_enabled = False
        self.assertFalse(await autopay.offer_ok(7))
        self.assertIsNone(await autopay.public(7))
        self.settings.admin_ids = "7"
        self.assertTrue(autopay.available(7))


class WebhookRoutingTest(unittest.IsolatedAsyncioTestCase):
    """Subscription events and subscription charges go to app/autopay.py, signed like any CISPay webhook."""

    async def call(self, event):
        from test_cispay import WebhookTest, settings
        from app import web as webapp
        req = WebhookTest.request(None, event)
        with patch.object(webapp, "get_settings", return_value=settings()), \
                patch.object(autopay, "on_event", AsyncMock()) as on_event, \
                patch.object(autopay, "on_payment", AsyncMock(return_value=True)) as on_payment, \
                patch.object(webapp, "fulfill_pay_order", AsyncMock()) as fulfill:
            resp = await webapp.cispay_webhook(req)
        return resp, on_event, on_payment, fulfill

    async def test_subscription_event(self):
        resp, on_event, on_payment, fulfill = await self.call(
            {"event": "subscription.activated", "object": "subscription", "id": "sub-1", "status": "ACTIVE"})
        self.assertEqual(resp.status, 200)
        on_event.assert_awaited_once()
        on_payment.assert_not_awaited()
        fulfill.assert_not_awaited()

    async def test_subscription_charge(self):
        resp, on_event, on_payment, fulfill = await self.call(
            {"id": "tx-1", "order_id": "x", "status": "PAID", "amount": 30000, "subscription_id": "sub-1"})
        self.assertEqual(resp.status, 200)
        on_payment.assert_awaited_once()
        fulfill.assert_not_awaited()
