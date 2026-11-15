"""«+10% к первому пополнению»: who gets it, and that the credit lands once, inside the payment."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import first_bonus


def settings(**kw):
    return SimpleNamespace(**{"first_bonus_enabled": True, "first_bonus_min_rub": 200, "first_bonus_percent": 10,
                              "vpn_day_price_rub": 6, "referral_program_enabled": False, "referral_invitee_reward_rub": 0, **kw})


class RulesTest(unittest.TestCase):
    def setUp(self):
        p = patch.object(first_bonus, "get_settings", return_value=settings())
        self.s = p.start()
        self.addCleanup(p.stop)

    def test_gift_running_first_payment(self):
        user = {"trial_used": True, "has_paid_topup": False, "balance_rub": 10}
        self.assertEqual(first_bonus.bonus_for_payment(user, 200), 20)
        self.assertEqual(first_bonus.bonus_for_payment(user, 555), 55)  # 10%, whole rubles
        self.assertEqual(first_bonus.bonus_for_payment(user, 199), 0)

    def test_not_for_payers_without_gift_or_after_it(self):
        self.assertEqual(first_bonus.bonus_for_payment({"trial_used": True, "has_paid_topup": True, "balance_rub": 10}, 200), 0)
        self.assertEqual(first_bonus.bonus_for_payment({"trial_used": False, "balance_rub": 10}, 200), 0)
        self.assertEqual(first_bonus.bonus_for_payment({"trial_used": True, "balance_rub": 0}, 200), 0)
        self.s.return_value = settings(first_bonus_enabled=False)
        self.assertEqual(first_bonus.bonus_for_payment({"trial_used": True, "balance_rub": 10}, 200), 0)

    def test_checkout_started_before_the_gift_ran_out(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(first_bonus.eligible({"trial_used": True, "balance_rub": 0, "checkout_started_at": now - timedelta(minutes=30)}))
        self.assertFalse(first_bonus.eligible({"trial_used": True, "balance_rub": 0, "checkout_started_at": now - timedelta(hours=5)}))

    def test_offer_for_the_cabinet(self):
        user = {"trial_used": True, "has_paid_topup": False}
        self.assertEqual(first_bonus.offer(user, balance_rub=10, hours_left=38),
                         {"min_rub": 200, "percent": 10, "hours_left": 38})
        self.assertIsNone(first_bonus.offer(user, balance_rub=0, hours_left=0))


DSN = os.environ.get("TEST_DATABASE_URL")


@unittest.skipUnless(DSN, "TEST_DATABASE_URL is not set")
class CreditTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import asyncpg
        from app import db
        self.db = db
        self.pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
        self.addAsyncCleanup(self.pool.close)
        await self.pool.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        await self.pool.execute(db.SCHEMA_PATH.read_text(encoding="utf-8"))
        s = settings()
        for p in (patch.object(db, "_pool", self.pool), patch.object(db, "get_settings", return_value=s),
                  patch.object(first_bonus, "get_settings", return_value=s)):
            p.start()
            self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id, trial_used, balance_rub) VALUES (1, TRUE, 10), (2, TRUE, 10)")

    async def order(self, uid, oid, amount):
        await self.pool.execute("INSERT INTO pay_orders (order_id, telegram_id, plan_code, status) VALUES ($1,$2,$3,'pending')",
                                oid, uid, f"b{amount}")
        return await self.db.credit_payment_once(uid, f"b{amount}", f"order:{oid}", amount)

    async def test_first_payment_gets_days_once(self):
        receipt = await self.order(1, "o1", 200)
        self.assertEqual(receipt["first_bonus_rub"], 20)
        self.assertEqual(await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=1"), 230)
        self.assertEqual(await self.pool.fetchval("SELECT note FROM billing_events WHERE kind='first_bonus'"), "Бонус за первую оплату")
        again = await self.order(1, "o2", 300)  # the second payment: no bonus
        self.assertEqual(again["first_bonus_rub"], 0)
        self.assertEqual(await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=1"), 530)

    async def test_small_first_payment_gets_nothing(self):
        receipt = await self.order(2, "o3", 100)
        self.assertEqual(receipt["first_bonus_rub"], 0)
        self.assertEqual(await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=2"), 110)


class BotButtonsTest(unittest.TestCase):
    def test_quick_buttons_show_the_bonus_amount(self):
        from app import funnel_board
        with patch("app.config.get_settings", return_value=SimpleNamespace(
                balance_topup_min=50, balance_topup_step=50, balance_topup_max=100000, vpn_day_price_rub=6)), \
                patch("app.keyboards.mini_app_url", return_value="https://lk.example/app"):
            kb = funnel_board.markup(["topup_quick"], 1, bonus=(200, 10))
        texts = [b.text for row in kb.inline_keyboard for b in row]
        self.assertEqual(texts, ["Пополнить 50 ₽", "🎁 200 ₽ · +10%"])
        self.assertIn("amount=200", kb.inline_keyboard[0][1].web_app.url)

    def test_topup_button_opens_on_the_threshold(self):
        from app import funnel_board
        with patch("app.keyboards.mini_app_url", return_value="https://lk.example/app"):
            kb = funnel_board.markup([{"action": "topup", "text": "Пополнить баланс"}], 1, bonus=(200, 35))
            plain = funnel_board.markup([{"action": "topup", "text": "Пополнить баланс"}], 1)
        self.assertEqual(kb.inline_keyboard[0][0].text, "🎁 Пополнить 200 ₽ · +35%")
        self.assertIn("amount=200", kb.inline_keyboard[0][0].web_app.url)
        self.assertEqual(plain.inline_keyboard[0][0].text, "Пополнить баланс")

    def test_bonus_line_for_plain_texts(self):
        from app import funnel_board
        self.assertEqual(funnel_board.with_first_bonus("Привет", None), "Привет")
        self.assertIn("+35% к сумме", funnel_board.with_first_bonus("Привет", (200, 35)))


if __name__ == "__main__":
    unittest.main()
