import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from app import welcome

class WelcomeSupportTest(unittest.IsolatedAsyncioTestCase):
    async def test_support_message_between_presentation_and_cabinet(self):
        message=SimpleNamespace(bot=object(),from_user=SimpleNamespace(id=1,first_name='Друг'),chat=SimpleNamespace(id=1),answer=AsyncMock())
        settings=SimpleNamespace(brand_name='VPN',referral_invitee_reward_rub=0,referral_program_enabled=False,balance_enabled=True,trial_days=3,welcome_tariff_enabled=False)
        with ExitStack() as stack:
            stack.enter_context(patch.object(welcome,'get_settings',return_value=settings))
            stack.enter_context(patch.object(welcome.db,'get_user',AsyncMock(return_value={})))
            stack.enter_context(patch.object(welcome.db,'mark_legal_notice',AsyncMock()))
            stack.enter_context(patch.object(welcome,'trial_is_available',return_value=True))
            stack.enter_context(patch.object(welcome,'notice_text',side_effect=lambda key,**kw:key))
            stack.enter_context(patch.object(welcome,'legal_text',return_value='legal'))
            stack.enter_context(patch.object(welcome,'profile_keyboard',return_value='cabinet'))
            for name in ('send_welcome_sticker','_pause','_log'):
                stack.enter_context(patch.object(welcome,name,AsyncMock()))
            self.assertTrue(await welcome.send_welcome_intro(message,in_channel=True))
        calls=message.answer.call_args_list
        self.assertEqual([call.args[0].split('\n\nОткройте личный кабинет')[0] for call in calls],['welcome_intro_hi','welcome_intro_hello','support_welcome'])
        # Only «Я помогу»: no cabinet / main menu buttons and no cabinet call to action.
        self.assertEqual([[b.callback_data for b in row] for row in calls[2].kwargs['reply_markup'].inline_keyboard],[['welcome:continue']])
        self.assertEqual(calls[2].args[0],'support_welcome')

    async def test_tariff_block_in_presentation_can_be_switched_off(self):
        from app import keyboards
        tariff=SimpleNamespace(webapp_public_url='',vpn_day_price_rub=6,balance_topup_min=50,referral_program_enabled=True,referral_reward_rub=50,referral_invitee_reward_rub=50)
        for enabled in (True,False):
            message=SimpleNamespace(bot=object(),from_user=SimpleNamespace(id=1,first_name='Друг'),chat=SimpleNamespace(id=1),answer=AsyncMock())
            settings=SimpleNamespace(brand_name='VPN',referral_invitee_reward_rub=0,referral_program_enabled=False,balance_enabled=True,trial_days=3,welcome_tariff_enabled=enabled)
            with ExitStack() as stack:
                stack.enter_context(patch.object(welcome,'get_settings',return_value=settings))
                stack.enter_context(patch.object(keyboards,'get_settings',return_value=tariff))
                stack.enter_context(patch.object(welcome.db,'get_user',AsyncMock(return_value={})))
                stack.enter_context(patch.object(welcome.db,'mark_legal_notice',AsyncMock()))
                stack.enter_context(patch.object(welcome,'trial_is_available',return_value=True))
                stack.enter_context(patch.object(welcome,'notice_text',side_effect=lambda key,**kw:key))
                stack.enter_context(patch.object(welcome,'legal_text',return_value='legal'))
                stack.enter_context(patch.object(welcome,'profile_keyboard',return_value='cabinet'))
                for name in ('send_welcome_sticker','_pause','_log'):
                    stack.enter_context(patch.object(welcome,name,AsyncMock()))
                await welcome.send_welcome_intro(message,in_channel=True)
            hello=message.answer.call_args_list[1].args[0]
            self.assertNotIn('Откройте личный кабинет', hello)
            self.assertIsNone(message.answer.call_args_list[0].kwargs.get('reply_markup'))
            self.assertIsNone(message.answer.call_args_list[1].kwargs.get('reply_markup'))
            self.assertEqual('6 ₽ в день' in hello, enabled)
            self.assertEqual('без подписки · пополнение от 50 ₽' in hello, enabled)
            self.assertEqual('обоим по 50 ₽' in hello, enabled)
