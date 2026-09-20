import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
from unittest.mock import AsyncMock,patch
from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup
from app import referrals,keyboards,db
from app.config import Settings


class ReferralShareTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        settings=Settings.model_construct(bot_username='vpn_test_bot',balance_enabled=True,referral_program_enabled=True)
        for target in ('app.keyboards.get_settings','app.referrals.get_settings'):
            patcher=patch(target,return_value=settings)
            patcher.start()
            self.addCleanup(patcher.stop)

    def assertRecipient(self,markup,uid):
        button=markup.inline_keyboard[0][0]
        self.assertEqual(button.text,'Поделиться реферальной ссылкой')
        query=parse_qs(urlsplit(button.url).query)
        self.assertEqual(query['url'],[f'https://t.me/vpn_test_bot?start=ref_{uid}'])

    def test_preserves_existing_actions_and_does_not_duplicate(self):
        original=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Подключиться',callback_data='connect')]])
        result=keyboards.with_referral_share(123,original)
        self.assertRecipient(result,123)
        self.assertEqual(result.inline_keyboard[1][0].callback_data,'connect')
        self.assertEqual(len(original.inline_keyboard),1)
        self.assertEqual(len(keyboards.with_referral_share(123,result).inline_keyboard),2)

    async def test_reward_uses_referrers_link_not_paying_friends(self):
        bot=SimpleNamespace(send_message=AsyncMock())
        with patch.object(referrals,'referral_is_payout',return_value=False), \
             patch.object(referrals,'cabinet_keyboard',return_value=None), \
             patch.object(db,'reward_referral_payment',AsyncMock(return_value={'referrer_id':123,'amount':65,'bonus':50,'percent':15})):
            await referrals.maybe_reward_referrer(bot,None,999,'Друг',payment_key='pay',topup_rub=300,first_payment=True)
        self.assertEqual(bot.send_message.call_args.args[0],123)
        self.assertRecipient(bot.send_message.call_args.kwargs['reply_markup'],123)
