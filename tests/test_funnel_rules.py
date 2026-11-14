"""Referral rule «другу сразу, вам после подключения», the gift-ending text, reminder hours and retired texts."""
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import funnel_board, notices, nudge, referrals


class ReminderHoursTest(unittest.TestCase):
    def test_moscow_daytime_window(self):
        utc = lambda h, m=0: datetime(2026, 11, 12, h, m, tzinfo=timezone.utc)  # MSK = UTC+3
        self.assertFalse(funnel_board.reminder_hours(utc(6, 59)))   # 09:59 MSK
        self.assertTrue(funnel_board.reminder_hours(utc(7, 0)))     # 10:00 MSK
        self.assertTrue(funnel_board.reminder_hours(utc(17, 59)))   # 20:59 MSK
        self.assertFalse(funnel_board.reminder_hours(utc(18, 0)))   # 21:00 MSK
        self.assertFalse(funnel_board.reminder_hours(utc(23, 0)))   # 02:00 MSK


class NightSendTest(unittest.IsolatedAsyncioTestCase):
    async def test_night_sends_money_warnings_only(self):
        graph = {"branches": [{"id": "b", "title": "b", "steps": [
            {"id": "pay-1", "condition": "unpaid_invoice", "enabled": True, "text": "pay", "buttons": []},
            {"id": "balance-1", "condition": "balance_low", "enabled": True, "text": "bal", "buttons": []},
        ]}]}
        from app import db
        with ExitStack() as stack:
            stack.enter_context(patch.object(db, "flag_on", AsyncMock(return_value=False)))
            stack.enter_context(patch.object(funnel_board, "load", AsyncMock(return_value=graph)))
            stack.enter_context(patch.object(funnel_board, "reminder_hours", return_value=False))
            pay = stack.enter_context(patch.object(nudge, "send_due_payment_nudges", AsyncMock(return_value=(1, [1]))))
            bal = stack.enter_context(patch.object(nudge, "send_due_trial_end_nudges", AsyncMock(return_value=(1, [2]))))
            terms = stack.enter_context(patch.object(db, "terms_feedback_ids", AsyncMock(return_value=[])))
            sent, touched = await funnel_board.send_due(object())
        self.assertEqual((sent, touched), (2, [1, 2]))
        pay.assert_awaited_once()
        bal.assert_awaited_once()
        terms.assert_not_awaited()  # the reminder branches never start at night


class GiftEndingTest(unittest.IsolatedAsyncioTestCase):
    def settings(self):
        return SimpleNamespace(balance_topup_min=50, vpn_day_price_rub=6)

    def test_text(self):
        with patch.object(nudge, "get_settings", return_value=self.settings()):
            text = nudge.gift_ending_text()
        self.assertEqual(text, "🎁 Подарок заканчивается завтра. Понравилось? Пополните от 50 ₽ — это 8 дней VPN.")

    async def test_never_paid_gets_gift_text_paid_gets_balance_text(self):
        rows = [{"telegram_id": 1, "first_name": "A", "balance_rub": 5, "device_count": 1, "paid": False, "stage": 1},
                {"telegram_id": 2, "first_name": "B", "balance_rub": 5, "device_count": 1, "paid": True, "stage": 1}]
        with ExitStack() as stack:
            stack.enter_context(patch.object(nudge, "get_settings", return_value=self.settings()))
            stack.enter_context(patch.object(nudge.db, "flag_on", AsyncMock(return_value=False)))
            stack.enter_context(patch.object(nudge.db, "rearm_balance_warnings", AsyncMock()))
            stack.enter_context(patch.object(nudge.db, "list_due_trial_end_nudges", AsyncMock(return_value=rows)))
            stack.enter_context(patch.object(nudge.db, "nudge_delivery_allowed", AsyncMock(return_value=True)))
            stack.enter_context(patch.object(nudge.db, "claim_balance_ending_notice", AsyncMock(return_value=True)))
            deliver = stack.enter_context(patch.object(nudge, "_deliver", AsyncMock(return_value=True)))
            sent, _ = await nudge.send_due_trial_end_nudges(object(), body="Баланс заканчивается.")
        self.assertEqual(sent, 2)
        first, second = (c.kwargs for c in deliver.await_args_list)
        self.assertIn("Подарок заканчивается завтра", first["body"])
        self.assertEqual(first["title"], "Подарок заканчивается")
        self.assertTrue(second["body"].startswith("Баланс заканчивается."))
        self.assertEqual(second["title"], "Баланс заканчивается")


class ReferralRuleTest(unittest.IsolatedAsyncioTestCase):
    async def test_menu_pays_friend_and_only_tells_inviter(self):
        result = {"referrer_id": 10, "invitee_id": 20, "amount": 50, "friend_name": "Оля"}
        with ExitStack() as stack:
            stack.enter_context(patch.object(referrals, "get_settings", return_value=SimpleNamespace(referral_program_enabled=True)))
            stack.enter_context(patch.object(referrals.db, "reward_referral_menu", AsyncMock(return_value=result)))
            reward = stack.enter_context(patch.object(referrals, "_send_reward", AsyncMock()))
            plain = stack.enter_context(patch.object(referrals, "send_funnel_message", AsyncMock()))
            stack.enter_context(patch.object(referrals, "with_referral_share", side_effect=lambda uid, m=None: m))
            stack.enter_context(patch.object(referrals, "cabinet_keyboard", return_value=None))
            self.assertEqual(await referrals.maybe_reward_menu(object(), 20), 50)
        reward.assert_awaited_once()
        self.assertEqual(reward.await_args.args[1], 20)  # the money card goes to the friend only
        self.assertEqual(plain.await_args.args[1], 10)
        self.assertIn("Как только VPN будет подключён, вам начислим <b>50 ₽</b>", plain.await_args.args[2])

    async def test_connect_pays_inviter(self):
        rows = [{"referrer_id": 10, "invitee_id": 20, "amount": 50, "friend_name": "Оля"}]
        with ExitStack() as stack:
            stack.enter_context(patch.object(referrals, "get_settings", return_value=SimpleNamespace(referral_program_enabled=True)))
            claim = stack.enter_context(patch.object(referrals.db, "claim_referral_connect_rewards", AsyncMock(return_value=rows)))
            reward = stack.enter_context(patch.object(referrals, "_send_reward", AsyncMock()))
            self.assertEqual(await referrals.reward_connected_friends(object()), 1)
        claim.assert_awaited_once_with(50)
        args, kwargs = reward.await_args
        self.assertEqual(args[1], 10)
        self.assertIn("VPN подключён по вашей ссылке", args[2])
        self.assertEqual(kwargs["friend"], {"n": "Оля", "k": "connect"})

    async def test_paused_program_pays_nobody(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(referrals, "get_settings", return_value=SimpleNamespace(referral_program_enabled=False)))
            claim = stack.enter_context(patch.object(referrals.db, "claim_referral_connect_rewards", AsyncMock()))
            self.assertEqual(await referrals.reward_connected_friends(object()), 0)
        claim.assert_not_awaited()

    def test_topup_text(self):
        with patch.object(referrals, "get_settings", return_value=SimpleNamespace(referral_program_enabled=True)), \
                patch.object(referrals, "notice_text", return_value="Пополнено."):
            text = referrals.topup_ok_text("100 ₽", can_share=True, local={"balance_rub": 100})
        self.assertNotIn("Подключение и состояние доступа — в кабинете.", text)
        self.assertIn("другу 50 ₽ сразу, вам 50 ₽, когда он подключит VPN", text)


class RetiredTextsTest(unittest.TestCase):
    def test_idle_and_support_texts_are_gone(self):
        keys = set(notices.DEFAULT_NOTICES) | {f["key"] for f in notices.NOTICE_FIELDS}
        for key in ("idle_setup_7", "idle_topup_20", "idle_return_10", "return_check", "return_last",
                    "idle_comeback", "support_welcome", "trial_resume_welcome"):
            self.assertNotIn(key, keys)
        self.assertFalse(hasattr(nudge, "_idle_notice_key"))

    def test_gift_reminder_has_no_daily_charge_warning(self):
        self.assertNotIn("даже если VPN выключен", notices.DEFAULT_NOTICES["trial_nudge"])
        self.assertIn("gift_ending_nudge", notices.DEFAULT_NOTICES)


class PaidEmptyTest(unittest.TestCase):
    def test_branch_has_no_gift_and_offers_promise(self):
        from app import recovery_funnel as rf
        branch = rf.paid_branches()[0]
        actions = [b if isinstance(b, str) else b["action"] for st in branch["steps"] for b in st["buttons"]]
        self.assertNotIn(rf.GIFT, actions)
        self.assertIn("promise", actions)
        self.assertEqual([st["wait_hours"] for st in branch["steps"]], [24, 48, 96])
        funnel_board.validate({"branches": rf.branches()})

    def test_idle_branch_skips_paid_customers_out_of_money(self):
        from app import recovery_funnel as rf
        idle = next(c for c in rf.CONDITIONS if c["id"] == "recover_idle")
        self.assertIn("{exhausted}", idle["where"])
        self.assertIn("NOT (", idle["where"])

class PromiseButtonTest(unittest.TestCase):
    def setUp(self):
        from app import keyboards
        p = patch.object(keyboards, "mini_app_url", return_value="https://x.test/app")
        p.start(); self.addCleanup(p.stop)

    def test_balance_keyboard(self):
        from app.balance_notifications import balance_keyboard
        rows = balance_keyboard(promise=True).inline_keyboard
        self.assertEqual([r[0].text for r in rows], ["Пополнить баланс", "🤝 Обещанный платёж", "Главное меню"])
        self.assertIn("screen=promise", rows[1][0].web_app.url)
        self.assertNotIn("🤝 Обещанный платёж", [r[0].text for r in balance_keyboard().inline_keyboard])

    def test_funnel_button_only_when_available(self):
        texts = lambda m: [r[0].text for r in m.inline_keyboard]
        with patch("app.keyboards.mini_app_url", return_value="https://x.test/app"):
            self.assertIn("🤝 Обещанный платёж", texts(funnel_board.markup(["topup", "promise"], 1, promise=True)))
            self.assertNotIn("🤝 Обещанный платёж", texts(funnel_board.markup(["topup", "promise"], 1)))


if __name__ == "__main__":
    unittest.main()
