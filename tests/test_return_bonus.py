"""«Возвращайтесь с бонусом»: the 4th «paid-empty» step, its buttons, and the credit landing once inside the payment."""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import db, first_bonus, return_bonus


def settings(**kw):
    return SimpleNamespace(**{
        "return_bonus_enabled": True, "return_bonus_min_rub": 200, "return_bonus_percent": 20, "return_bonus_days": 7,
        "first_bonus_enabled": True, "first_bonus_min_rub": 200, "first_bonus_percent": 35,
        "vpn_day_price_rub": 10, "referral_program_enabled": False, "referral_invitee_reward_rub": 0,
        "balance_topup_min": 50, "balance_topup_step": 50, "balance_topup_max": 100000,
        "plan_by_code": lambda code: None, **kw})


class TextAndButtonsTest(unittest.TestCase):
    def test_text_names_threshold_percent_and_last_day(self):
        with patch.object(return_bonus, "get_settings", return_value=settings()):
            body = return_bonus.fill("от {bonus_min} до {bonus_until} +{bonus_pct}%",
                                     now=datetime(2026, 11, 18, 10, tzinfo=timezone.utc))
        self.assertEqual(body, "от 200 ₽ до 25 ноября +20%")

    def test_off_means_no_step(self):
        with patch.object(return_bonus, "get_settings", return_value=settings(return_bonus_enabled=False)):
            self.assertIsNone(return_bonus.fill("x"))

    def test_buttons_show_what_lands_on_the_balance(self):
        from app import funnel_board
        s = settings()
        with patch("app.config.get_settings", return_value=s), patch.object(return_bonus, "get_settings", return_value=s), \
                patch("app.keyboards.mini_app_url", return_value="https://lk.example/app"):
            kb = funnel_board.markup(["topup_return"], 1)
        texts = [[b.text for b in row] for row in kb.inline_keyboard]
        self.assertEqual(texts, [["200 ₽ → 240 ₽", "300 ₽ → 360 ₽"], ["Пополнить другую сумму"]])
        self.assertIn("amount=300", kb.inline_keyboard[0][1].web_app.url)

    def test_step_is_the_last_in_paid_empty(self):
        from app.recovery_funnel import paid_branches
        steps = paid_branches()[0]["steps"]
        self.assertEqual(steps[-1]["id"], return_bonus.STEP_ID)
        self.assertEqual(sum(s["wait_hours"] for s in steps), 240)  # 10 days after the money ran out


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class CreditTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        s = settings()
        for p in (patch.object(db, "_pool_req", return_value=self.pool), patch.object(db, "get_settings", return_value=s),
                  patch.object(first_bonus, "get_settings", return_value=s), patch.object(return_bonus, "get_settings", return_value=s)):
            p.start()
            self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id, trial_used, has_paid_topup, balance_rub) VALUES (1, TRUE, TRUE, 0), (2, TRUE, TRUE, 0)")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def order(self, uid, oid, amount):
        await self.pool.execute("INSERT INTO pay_orders (order_id, telegram_id, plan_code, status) VALUES ($1,$2,$3,'pending')",
                                oid, uid, f"b{amount}")
        return await db.credit_payment_once(uid, f"b{amount}", f"order:{oid}", amount)

    async def test_offer_pays_once(self):
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id, sent_at) VALUES (1, $1, NOW() - INTERVAL '2 days')",
                                return_bonus.STEP_ID)
        small = await self.order(1, "o0", 100)  # below the threshold: nothing, the offer stays
        self.assertEqual(small["return_bonus_rub"], 0)
        receipt = await self.order(1, "o1", 300)
        self.assertEqual(receipt["return_bonus_rub"], 60)
        self.assertEqual(await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=1"), 460)
        self.assertEqual(await self.pool.fetchval("SELECT note FROM billing_events WHERE kind='return_bonus'"), "Бонус за возвращение")
        again = await self.order(1, "o2", 300)
        self.assertEqual(again["return_bonus_rub"], 0)
        self.assertEqual(await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=1"), 760)
        items = await db.user_billing_history(1, days=7)
        self.assertIn("return_bonus", [x["kind"] for x in items])

    async def test_no_offer_or_expired_offer_gets_nothing(self):
        self.assertEqual((await self.order(2, "o3", 300))["return_bonus_rub"], 0)
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id, sent_at) VALUES (2, $1, NOW() - INTERVAL '8 days')",
                                return_bonus.STEP_ID)
        self.assertEqual((await self.order(2, "o4", 300))["return_bonus_rub"], 0)

    async def test_cabinet_offer_and_ab_arms(self):
        local = {"has_paid_topup": True}
        self.assertIsNone(await return_bonus.offer(1, local))
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id, sent_at) VALUES (1, $1, NOW() - INTERVAL '1 day')",
                                return_bonus.STEP_ID)
        got = await return_bonus.offer(1, local)
        self.assertEqual((got["kind"], got["min_rub"], got["percent"]), ("return", 200, 20))
        self.assertTrue(140 <= got["hours_left"] <= 144)
        # Arm B of an A/B test gets its own percent, in the cabinet and in the credit.
        exp = await self.pool.fetchval("""INSERT INTO funnel_experiments (step_id, holdout_pct, b_pct, b_bonus_pct, started_at)
            VALUES ($1, 10, 50, 10, NOW() - INTERVAL '2 days') RETURNING id""", return_bonus.STEP_ID)
        await self.pool.execute("INSERT INTO funnel_experiment_users (experiment_id, telegram_id, arm) VALUES ($1, 1, 'b'), ($1, 2, 'control')", exp)
        self.assertEqual((await return_bonus.offer(1, local))["percent"], 10)
        self.assertEqual((await self.order(1, "o5", 300))["return_bonus_rub"], 30)
        # The control group never saw the message: no bonus, nothing in the cabinet.
        await self.pool.execute("INSERT INTO funnel_step_sends (telegram_id, step_id, sent_at) VALUES (2, $1, NOW() - INTERVAL '1 day')",
                                return_bonus.STEP_ID)
        self.assertIsNone(await return_bonus.offer(2, local))
        self.assertEqual((await self.order(2, "o6", 300))["return_bonus_rub"], 0)


class ExperimentFormTest(unittest.TestCase):
    def test_bonus_percent_only_for_the_bonus_step(self):
        from app import experiments
        steps = {return_bonus.STEP_ID: {"id": return_bonus.STEP_ID, "text": "t", "gift": False, "bonus": True},
                 "other": {"id": "other", "text": "t", "gift": False, "bonus": False}}
        clean = experiments.check({"step_id": return_bonus.STEP_ID, "holdout_pct": "10", "b_pct": "50", "b_bonus_pct": "10"}, steps)
        self.assertEqual(clean["b_bonus_pct"], 10)
        with self.assertRaises(ValueError):
            experiments.check({"step_id": "other", "b_pct": "50", "b_bonus_pct": "10"}, steps)


if __name__ == "__main__":
    unittest.main()
