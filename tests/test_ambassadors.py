"""Real PostgreSQL accounting scenarios; no external payments or messages."""

import asyncio
import os
import unittest
from unittest.mock import patch, AsyncMock
import test_funnel_integration as harness
from app import ambassadors as amb, db


@unittest.skipUnless(
    os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE for PostgreSQL scenarios"
)
class AmbassadorTest(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = harness.FunnelPostgresTest.asyncTearDown

    async def asyncSetUp(self):
        await harness.FunnelPostgresTest.asyncSetUp(self)
        self.settings.bot_username = "test_bot"
        p = patch.object(amb, "get_settings", return_value=self.settings)
        p.start()
        self.addCleanup(p.stop)
        await amb.admin_action(
            dict(action="settings", recruitment=True, accruing=True, budget=10000)
        )
        await amb.apply(1, "Мой канал о технологиях")
        await amb.admin_action(dict(action="approve", telegram_id=1))
        self.token = await self.pool.fetchval(
            "SELECT token FROM ambassadors WHERE telegram_id=1"
        )
        self.assertTrue(await amb.register_new(2, "client", "Друг", self.token))
        self.n = 0

    async def pay(self, uid=2, amount=300, key=None, router_days=0):
        self.n += 1
        key = key or f"rollypay:p{self.n}"
        if key.startswith("rollypay:"):
            await self.pool.execute(
                "INSERT INTO rollypay_orders(order_id,telegram_id,plan_code,status) VALUES($1,$2,$3,'created') ON CONFLICT DO NOTHING",
                key.split(":")[1],
                uid,
                f"topup_{amount}",
            )
        return await db.credit_payment_once(
            uid, f"topup_{amount}", key, amount, router_days=router_days, stars=50
        )

    async def mature(self):
        await self.pool.execute(
            "UPDATE ambassador_awards SET available_at=NOW()-INTERVAL '1 day'"
        )

    async def test_new_users_only_and_no_regular_referral_hijack(self):
        self.assertFalse(await amb.register_new(1, None, "Self", self.token))
        self.assertFalse(await amb.register_new(2, None, "Existing", self.token))
        self.assertFalse(await amb.register_new(3, None, "Invalid", "bad"))
        await db.upsert_user(2, "client", "Друг", referred_by=1)
        self.assertIsNone(
            await self.pool.fetchval(
                "SELECT referred_by FROM users WHERE telegram_id=2"
            )
        )
        await self.pool.execute("UPDATE users SET referred_by=1 WHERE telegram_id=2")
        await self.pay()
        self.assertIsNone(
            await db.reward_referral_payment(
                2, "rollypay:ordinary", 300, enabled=True, first_payment=True
            )
        )
        self.assertIsNone(await db.credit_invitee_bonus_once(2, 50))
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT balance_rub FROM users WHERE telegram_id=1"
            ),
            0,
        )

    async def test_first_cap_repeat_cents_and_duplicate(self):
        receipt = await self.pay(amount=1000, key="rollypay:same")
        self.assertEqual(receipt["ambassador_id"], 1)
        results = await asyncio.gather(
            *(self.pay(amount=1000, key="rollypay:same") for _ in range(5))
        )
        self.assertTrue(all(r is None for r in results))
        await self.pay(amount=101)
        w = await amb.wallet(1)
        self.assertEqual(w["earned"], 50505)
        self.assertEqual(w["holding"], 50505)
        self.assertEqual(w["available"], 0)
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT balance_rub FROM users WHERE telegram_id=2"
            ),
            1101,
        )
        self.assertEqual(
            await self.pool.fetchval("SELECT COUNT(*) FROM ambassador_awards"), 2
        )
        overview = await amb.overview(1)
        self.assertEqual(overview["stats"]["repeat_paid"], 1)
        self.assertIn("start=amb_", overview["link"])
        data = await amb.admin_data(uid=1)
        self.assertEqual(data["clients_total"], 1)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        self.assertEqual((await amb.wallet(1))["earned"], 50505)

    async def test_pause_keeps_attribution_without_retroactive_first_bonus(self):
        await amb.admin_action(dict(action="settings", accruing=False))
        self.assertTrue(await amb.register_new(3, None, "New", self.token))
        await self.pay(uid=3)
        await amb.admin_action(dict(action="settings", accruing=True))
        await self.pay(uid=3)
        self.assertEqual((await amb.wallet(1))["earned"], 1500)
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT COUNT(*) FROM ambassador_awards WHERE status='skipped'"
            ),
            1,
        )

    async def test_stars_and_router_do_not_consume_first_cash_topup(self):
        await self.pay(key="stars:initial")
        await self.pay(router_days=30)
        await self.pay()
        self.assertEqual((await amb.wallet(1))["earned"], 30000)
        self.assertEqual((await amb.overview(1))["stats"]["repeat_paid"], 0)

    async def test_budget_and_member_limit_skip_entire_award(self):
        await amb.admin_action(dict(action="settings", budget=400))
        await self.pay()
        await self.pay(uid=2, amount=3000)
        self.assertEqual((await amb.wallet(1))["earned"], 30000)
        await amb.admin_action(dict(action="settings", budget=10000, member_cap=310))
        await self.pay(amount=300)
        self.assertEqual((await amb.wallet(1))["earned"], 30000)
        with self.assertRaises(ValueError):
            await amb.admin_action(dict(action="settings", budget=0))

    async def test_payout_reservation_rejection_paid_and_refund_debt(self):
        await amb.admin_action(dict(action="settings", payout_min=100))
        await self.pay()
        with self.assertRaises(ValueError):
            await amb.request_payout(1, "+79990000000 Банк Имя")
        await self.mature()
        results = await asyncio.gather(
            *(amb.request_payout(1, "+79990000000 Банк Имя") for _ in range(3)),
            return_exceptions=True,
        )
        self.assertEqual(sum(r is None for r in results), 1)
        self.assertEqual((await amb.wallet(1))["available"], 0)
        payout = await self.pool.fetchval("SELECT id FROM ambassador_payouts")
        await amb.admin_action(
            dict(action="reject_payout", id=payout, note="Уточните банк")
        )
        self.assertEqual((await amb.wallet(1))["available"], 30000)
        await amb.request_payout(1, "+79990000000 Банк Имя")
        payout = await self.pool.fetchval(
            "SELECT id FROM ambassador_payouts WHERE status='pending'"
        )
        await amb.admin_action(dict(action="pay", id=payout, note="Перевод №42"))
        with self.assertRaises(ValueError):
            await amb.admin_action(dict(action="pay", id=payout, note="Повтор"))
        self.assertEqual((await amb.wallet(1))["paid"], 30000)
        await amb.admin_action(
            dict(
                action="revoke",
                payment_key="rollypay:p1",
                note="Возврат подтверждён №42",
            )
        )
        self.assertEqual((await amb.wallet(1))["available"], -30000)
        self.assertTrue(
            await self.pool.fetchval(
                "SELECT risk_hold FROM ambassadors WHERE telegram_id=1"
            )
        )

    async def test_pending_payout_blocked_after_refund_and_on_hold(self):
        await amb.admin_action(dict(action="settings", payout_min=100))
        await self.pay()
        await self.mature()
        await amb.request_payout(1, "Телефон Банк Имя")
        payout = await self.pool.fetchval("SELECT id FROM ambassador_payouts")
        await amb.admin_action(dict(action="risk_hold", telegram_id=1, note="Проверка"))
        with self.assertRaises(ValueError):
            await amb.admin_action(dict(action="pay", id=payout, note="Перевод"))
        await amb.admin_action(dict(action="risk_release", telegram_id=1))
        await amb.admin_action(
            dict(action="revoke", payment_key="rollypay:p1", note="Возврат")
        )
        with self.assertRaises(ValueError):
            await amb.admin_action(dict(action="pay", id=payout, note="Перевод"))
        await amb.admin_action(dict(action="reject_payout", id=payout, note="Возврат"))
        self.assertEqual((await amb.wallet(1))["available"], 0)

    async def test_award_failure_rolls_back_payment_and_retry(self):
        with patch.object(
            amb, "notify", new=AsyncMock(side_effect=RuntimeError("outbox unavailable"))
        ):
            with self.assertRaisesRegex(RuntimeError, "outbox"):
                await self.pay(key="rollypay:retry")
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT balance_rub FROM users WHERE telegram_id=2"
            ),
            0,
        )
        self.assertEqual(
            await self.pool.fetchval("SELECT COUNT(*) FROM ambassador_awards"), 0
        )
        await self.pay(key="rollypay:retry")
        self.assertEqual((await amb.wallet(1))["earned"], 30000)

    async def test_snapshot_and_suspension_preserve_earned(self):
        await self.pay()
        await amb.admin_action(
            dict(action="settings", first_percent=50, hold_days=7, max_members=1)
        )
        row = await self.pool.fetchrow(
            "SELECT percent,hold_days FROM ambassador_awards"
        )
        self.assertEqual(dict(row), {"percent": 100, "hold_days": 14})
        await amb.apply(2, "Другой канал для рекламы")
        with self.assertRaises(ValueError):
            await amb.admin_action(dict(action="approve", telegram_id=2))
        await amb.admin_action(
            dict(action="suspend", telegram_id=1, note="Проверка условий")
        )
        await self.pay()
        self.assertEqual((await amb.wallet(1))["earned"], 30000)
        self.assertFalse(await amb.register_new(4, None, "New", self.token))

    async def test_notification_queue_retry_and_history(self):
        from types import SimpleNamespace
        from app import funnel_ui

        bot = SimpleNamespace()
        await self.pool.execute("DELETE FROM ambassador_notifications")
        await self.pay()
        with patch.object(
            funnel_ui,
            "send_funnel_message",
            AsyncMock(side_effect=RuntimeError("network")),
        ):
            await amb.deliver_notifications(bot)
        self.assertEqual(
            await self.pool.fetchval("SELECT status FROM ambassador_notifications"),
            "pending",
        )
        await self.pool.execute(
            "UPDATE ambassador_notifications SET retry_at=NOW()-INTERVAL '1 minute'"
        )
        with patch.object(funnel_ui, "send_funnel_message", AsyncMock()) as send:
            await amb.deliver_notifications(bot)
            await amb.deliver_notifications(bot)
        send.assert_awaited_once()
        self.assertEqual(send.call_args.args[1], 1)
        self.assertEqual(
            await self.pool.fetchval("SELECT status FROM ambassador_notifications"),
            "sent",
        )
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT COUNT(*) FROM message_log WHERE kind='ambassador'"
            ),
            1,
        )

    async def test_start_handler_preserves_attribution_before_welcome(self):
        from types import SimpleNamespace
        from app.handlers import start
        from aiogram.filters import CommandObject

        message = SimpleNamespace(
            from_user=SimpleNamespace(id=9, username="new", first_name="New"),
            text="/start amb_" + self.token,
            bot=object(),
        )
        with patch.object(
            start, "is_channel_member", AsyncMock(return_value=True)
        ), patch.object(
            start, "send_welcome_intro", AsyncMock(return_value=True)
        ) as welcome:
            await start.cmd_start(
                message, None, CommandObject(command="start", args="amb_" + self.token)
            )
        welcome.assert_awaited_once()
        self.assertEqual(
            await self.pool.fetchval(
                "SELECT ambassador_id FROM ambassador_clients WHERE telegram_id=9"
            ),
            1,
        )
        self.assertIsNotNone(
            await self.pool.fetchval(
                "SELECT bot_started_at FROM users WHERE telegram_id=9"
            )
        )

    async def test_deleted_customer_cannot_reset_first_reward(self):
        await self.pay()
        self.assertTrue(await db.delete_user(2))
        self.assertTrue(await amb.register_new(2, "client", "Друг", self.token))
        await self.pay()
        self.assertEqual((await amb.wallet(1))["earned"], 31500)


class AmbassadorApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_requires_admin_and_user_auth(self):
        from types import SimpleNamespace
        from aiohttp import web
        from app import admin, web as customer

        denied = web.json_response({"ok": False}, status=401)
        with patch.object(admin, "_need_auth", return_value=denied), patch.object(
            amb, "admin_action", AsyncMock()
        ) as change:
            result = await admin.api_ambassadors(SimpleNamespace())
        self.assertEqual(result.status, 401)
        change.assert_not_awaited()
        with patch.object(
            customer, "_require_tg", AsyncMock(return_value=(None, denied))
        ), patch.object(amb, "request_payout", AsyncMock()) as pay:
            result = await customer.api_ambassador(SimpleNamespace())
        self.assertEqual(result.status, 401)
        pay.assert_not_awaited()

    async def test_payout_uses_authenticated_identity_not_body(self):
        from types import SimpleNamespace
        from app import web as customer

        request = SimpleNamespace(
            method="POST",
            json=AsyncMock(
                return_value={
                    "action": "payout",
                    "telegram_id": 999,
                    "details": "Банк Имя Телефон",
                }
            ),
        )
        with patch.object(
            customer, "_require_tg", AsyncMock(return_value=(12, None))
        ), patch.object(amb, "request_payout", AsyncMock()) as pay, patch.object(
            amb, "overview", AsyncMock(return_value={})
        ):
            result = await customer.api_ambassador(request)
        self.assertEqual(result.status, 200)
        pay.assert_awaited_once_with(12, "Банк Имя Телефон")

    async def test_blocked_customer_denied_before_accounting(self):
        from aiohttp import web
        from app import web as customer

        denied = web.json_response({"ok": False}, status=403)
        with patch.object(
            customer, "_if_down", AsyncMock(return_value=None)
        ), patch.object(
            customer, "_resolve_telegram_id", AsyncMock(return_value=(12, None))
        ), patch.object(
            customer, "_if_blocked", AsyncMock(return_value=denied)
        ):
            uid, result = await customer._require_tg(object())
        self.assertIsNone(uid)
        self.assertEqual(result.status, 403)
