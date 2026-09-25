import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from app import welcome

class WelcomeSupportTest(unittest.IsolatedAsyncioTestCase):
    async def test_support_message_between_presentation_and_cabinet(self):
        message=SimpleNamespace(bot=object(),from_user=SimpleNamespace(id=1,first_name='Друг'),chat=SimpleNamespace(id=1),answer=AsyncMock())
        settings=SimpleNamespace(brand_name='VPN',referral_invitee_reward_rub=0,referral_program_enabled=False,balance_enabled=True,trial_days=3)
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
        self.assertEqual([call.args[0] for call in calls],['welcome_intro_hi','welcome_intro_hello','support_welcome'])
        self.assertEqual(calls[2].kwargs['reply_markup'].inline_keyboard[0][0].callback_data,'welcome:continue')
