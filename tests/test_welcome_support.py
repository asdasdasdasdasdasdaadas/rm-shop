import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from app import welcome

class WelcomeSupportTest(unittest.IsolatedAsyncioTestCase):
    async def test_intro_goes_straight_to_cabinet_without_support_step(self):
        message=SimpleNamespace(bot=object(),from_user=SimpleNamespace(id=1,first_name='Друг'),chat=SimpleNamespace(id=1),answer=AsyncMock())
        # Even with the old admin switch on, «Будем на связи» is gone from the chain.
        settings=SimpleNamespace(brand_name='VPN',referral_invitee_reward_rub=0,referral_program_enabled=False,balance_enabled=True,trial_days=3,welcome_tariff_enabled=False,welcome_support_enabled=True)
        with ExitStack() as stack:
            stack.enter_context(patch.object(welcome,'get_settings',return_value=settings))
            stack.enter_context(patch.object(welcome.db,'get_user',AsyncMock(return_value={})))
            done=stack.enter_context(patch.object(welcome.db,'complete_welcome_support',AsyncMock()))
            stack.enter_context(patch.object(welcome,'trial_is_available',return_value=True))
            stack.enter_context(patch.object(welcome,'notice_text',side_effect=lambda key,**kw:key))
            cont=stack.enter_context(patch.object(welcome,'send_welcome_continuation',AsyncMock()))
            for name in ('send_welcome_sticker','_pause','_log'):
                stack.enter_context(patch.object(welcome,name,AsyncMock()))
            self.assertTrue(await welcome.send_welcome_intro(message,in_channel=True))
        self.assertEqual([call.args[0] for call in message.answer.call_args_list],['welcome_intro_hi','welcome_intro_hello'])
        self.assertFalse(hasattr(welcome,'show_pending_welcome'))
        done.assert_awaited_once_with(1)
        cont.assert_awaited_once_with(message,1,in_channel=True)

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
                stack.enter_context(patch.object(welcome.db,'complete_welcome_support',AsyncMock()))
                stack.enter_context(patch.object(welcome,'send_welcome_continuation',AsyncMock()))
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
            self.assertEqual('ему 50 ₽ сразу, вам 50 ₽, когда он подключит VPN' in hello, enabled)
