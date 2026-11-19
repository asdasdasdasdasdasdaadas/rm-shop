import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import welcome


def settings(**kw):
    return SimpleNamespace(**{"brand_name": "VPN", "referral_program_enabled": False, "trial_days": 3,
                              "welcome_tariff_enabled": True, "required_channel_enabled": False,
                              "vpn_day_price_rub": 6, "balance_topup_min": 50, **kw})


class WelcomeOneMessageTest(unittest.IsolatedAsyncioTestCase):
    async def run_intro(self, *, user=None, trial=True, granted=None, **kw):
        from app import keyboards, auto_gift
        message = SimpleNamespace(bot=object(), from_user=SimpleNamespace(id=1, first_name="Иван"),
                                  chat=SimpleNamespace(id=1), answer=AsyncMock())
        with ExitStack() as stack:
            stack.enter_context(patch.object(welcome, "get_settings", return_value=settings(legal_offer_url="o", legal_privacy_url="p", **kw)))
            stack.enter_context(patch.object(keyboards, "get_settings", return_value=settings(
                webapp_public_url="", required_channel_url="https://t.me/ch", legal_offer_url="o", legal_privacy_url="p", **kw)))
            stack.enter_context(patch.object(keyboards, "mini_app_url", return_value=""))
            stack.enter_context(patch.object(welcome.db, "get_user", AsyncMock(return_value=user or {})))
            stack.enter_context(patch.object(welcome.db, "mark_legal_notice", AsyncMock()))
            done = stack.enter_context(patch.object(welcome.db, "complete_welcome_support", AsyncMock()))
            stack.enter_context(patch.object(welcome, "trial_is_available", return_value=trial))
            stack.enter_context(patch.object(auto_gift, "grant_if_auto", AsyncMock(return_value=granted)))
            for name in ("send_welcome_sticker", "_pause", "_log"):
                stack.enter_context(patch.object(welcome, name, AsyncMock()))
            self.assertTrue(await welcome.send_welcome_intro(message, in_channel=True))
        done.assert_awaited_once_with(1)
        self.assertEqual(message.answer.await_count, 1)  # one message after the sticker
        call = message.answer.call_args
        return call.args[0], call.kwargs.get("reply_markup")

    def texts(self, kb):
        return [b.text for row in kb.inline_keyboard for b in row]

    async def test_one_message_with_gift_small_print_and_one_button(self):
        text, kb = await self.run_intro()
        self.assertIn("Иван", text)
        self.assertIn("Дарим 3 дня VPN", text)
        small = text.split("\n\n")[-1]  # price and legal fold into one small last line
        self.assertTrue(small.startswith("<i>6 ₽ в день за устройство после подарка · без подписки · продолжая"))
        self.assertIn('<a href="o">оферту</a>', small)
        self.assertNotIn("Позовите друга", text)
        self.assertEqual(self.texts(kb), ["🎁 Забрать подарок и подключиться"])

    async def test_price_line_can_be_switched_off(self):
        text, _ = await self.run_intro(welcome_tariff_enabled=False)
        self.assertNotIn("6 ₽ в день", text)
        self.assertIn("<i>Продолжая, вы принимаете", text)

    async def test_auto_gift_group_sees_it_credited(self):
        text, kb = await self.run_intro(granted=18)
        self.assertIn("Подарок уже на балансе", text)
        self.assertEqual(self.texts(kb)[0], "Подключить VPN")

    async def test_friend_link_adds_menu_for_the_bonus(self):
        text, kb = await self.run_intro(user={"referred_by": 5}, referral_program_enabled=True)
        self.assertIn("по ссылке друга", text)
        self.assertEqual(self.texts(kb)[-1], "Главное меню")

    async def test_required_channel_asks_to_subscribe(self):
        from app import keyboards
        message = SimpleNamespace(answer=AsyncMock())
        with patch.object(welcome, "get_settings", return_value=settings(required_channel_enabled=True,
                                                                        legal_offer_url="o", legal_privacy_url="p")), \
                patch.object(keyboards, "get_settings", return_value=settings(
                    required_channel_url="https://t.me/ch", legal_offer_url="o", legal_privacy_url="p")), \
                patch.object(keyboards, "mini_app_url", return_value=""), \
                patch.object(welcome.db, "get_user", AsyncMock(return_value={})), \
                patch.object(welcome.db, "mark_legal_notice", AsyncMock()), \
                patch.object(welcome, "trial_is_available", return_value=True):
            await welcome.send_welcome_continuation(message, 1, in_channel=False, first_name="Иван")
        kb = message.answer.call_args.kwargs["reply_markup"]
        self.assertIn("Подписаться на канал", self.texts(kb))
        self.assertIn("Дарим 3 дня VPN", message.answer.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
