import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import db, referrals
from app.config import Settings


class ReferralMenuBonusTest(unittest.IsolatedAsyncioTestCase):
    def settings(self, active=True):
        return Settings.model_construct(referral_program_enabled=active, bot_username='vpn_bot')

    async def test_pays_both_and_notifies_both(self):
        result = {'referrer_id': 10, 'invitee_id': 20, 'amount': 50, 'friend_name': 'Аня'}
        bot = SimpleNamespace()
        with patch.object(referrals, 'get_settings', return_value=self.settings()), \
             patch.object(db, 'reward_referral_menu', AsyncMock(return_value=result)) as reward, \
             patch.object(referrals, 'send_funnel_message', AsyncMock()) as send, \
             patch.object(referrals, 'with_referral_share', side_effect=lambda chat, kb: kb), \
             patch.object(referrals, 'cabinet_keyboard', return_value=None):
            self.assertEqual(await referrals.maybe_reward_menu(bot, 20), 50)
        reward.assert_awaited_once_with(20, 50)
        self.assertEqual({c.args[1] for c in send.await_args_list}, {10, 20})
        self.assertTrue(all('50 ₽' in c.args[2] for c in send.await_args_list))

    async def test_nothing_when_paused_or_already_paid(self):
        with patch.object(referrals, 'get_settings', return_value=self.settings(False)), \
             patch.object(db, 'reward_referral_menu', AsyncMock()) as reward:
            self.assertEqual(await referrals.maybe_reward_menu(None, 20), 0)
        reward.assert_not_awaited()
        with patch.object(referrals, 'get_settings', return_value=self.settings()), \
             patch.object(db, 'reward_referral_menu', AsyncMock(return_value=None)), \
             patch.object(referrals, 'send_funnel_message', AsyncMock()) as send:
            self.assertEqual(await referrals.maybe_reward_menu(SimpleNamespace(), 20), 0)
        send.assert_not_awaited()
