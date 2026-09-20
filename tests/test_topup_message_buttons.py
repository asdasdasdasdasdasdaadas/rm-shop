import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest.mock import AsyncMock, patch

from app import admin, balance, db, nudge


class TopupMessageButtonsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('app.keyboards.mini_app_url', return_value='https://example.com/app?theme=green'))
        self.stack.enter_context(patch.object(db, 'log_bot_message', AsyncMock()))
        self.bot = SimpleNamespace(send_message=AsyncMock())

    def assert_topup(self, markup):
        button = markup.inline_keyboard[0][0]
        self.assertEqual(button.text, 'Пополнить баланс')
        self.assertIsNone(button.url)
        self.assertIsNone(button.callback_data)
        self.assertEqual(parse_qs(urlsplit(button.web_app.url).query), {'theme':['green'], 'screen':['topup']})

    async def test_first_online_notification_opens_topup(self):
        self.stack.enter_context(patch.object(nudge, 'get_settings', return_value=SimpleNamespace(balance_enabled=True, vpn_day_price_rub=6)))
        self.stack.enter_context(patch.object(db, 'flag_on', AsyncMock(return_value=False)))
        self.stack.enter_context(patch.object(db, 'list_due_first_online_nudges', AsyncMock(return_value=[{'telegram_id':1,'balance_rub':12,'device_count':1}])))
        self.stack.enter_context(patch.object(db, 'mark_first_online_nudge_sent', AsyncMock()))
        self.stack.enter_context(patch.object(nudge.asyncio, 'sleep', AsyncMock()))
        self.assertEqual(await nudge.send_due_first_online_nudges(self.bot), (1,[1]))
        self.assert_topup(self.bot.send_message.call_args.kwargs['reply_markup'])

    async def test_empty_balance_notification_has_own_topup_button(self):
        self.stack.enter_context(patch.object(db, 'claim_low_balance_notice', AsyncMock(return_value=True)))
        self.stack.enter_context(patch.object(balance, 'send_cabinet_link_to', AsyncMock()))
        await balance._notify_empty(self.bot,1,6,set())
        self.assert_topup(self.bot.send_message.call_args.kwargs['reply_markup'])

    async def test_admin_resends_preserve_topup_action(self):
        self.stack.enter_context(patch.object(admin, 'get_settings'))
        for kind in ('low_balance','nudge_first_online','nudge_trial_end'):
            with self.subTest(kind=kind):
                self.assert_topup(await admin._retry_markup(kind,1,{}))
