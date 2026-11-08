import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin, db, funnel_gifts


class AnnounceBroadcastTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        targets = [{'telegram_id': 1, 'first_name': 'A'}, {'telegram_id': 2, 'first_name': None}]
        for name, mock in [
            ('list_broadcast_targets', AsyncMock(return_value=targets)),
            ('notification_allowed', AsyncMock(return_value=True)),
            ('reserve_optional_message', AsyncMock(return_value=None)),
            ('finish_optional_message', AsyncMock()),
            ('update_broadcast_run', AsyncMock()),
            ('create_reminder_delivery', AsyncMock(return_value='token')),
            ('log_bot_message', AsyncMock()),
        ]:
            p = patch.object(db, name, mock)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)
        for p in [patch.object(admin, 'get_settings', return_value=SimpleNamespace(referral_program_enabled=True)),
                  patch.object(admin, 'finish_tracked_delivery', AsyncMock()),
                  patch.object(admin.asyncio, 'sleep', AsyncMock())]:
            p.start()
            self.addCleanup(p.stop)
        self.bot = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=7)))

    async def test_gift_reaches_everyone_with_own_claim_button(self):
        job = {'running': True, 'run_id': 5}
        with patch.object(funnel_gifts, 'issue_for_broadcast', AsyncMock(side_effect=[11, 12])) as issue:
            await admin._broadcast_all(self.bot, 'Дарим 3 дня', job, None, 'gift3')
        self.list_broadcast_targets.assert_awaited_once_with('all')
        # The daily/weekly cap of optional messages does not apply to the announcement.
        self.reserve_optional_message.assert_not_awaited()
        self.assertEqual([c.args for c in issue.await_args_list], [(1, 5), (2, 5)])
        self.assertEqual(job['sent'], 2)
        first = self.bot.send_message.await_args_list[0]
        self.assertEqual(first.args, (1, 'Дарим 3 дня'))
        button = first.kwargs['reply_markup'].inline_keyboard[0][0]
        self.assertEqual((button.text, button.callback_data), ('Забрать 3 дня бесплатно', 'fgift:11'))
        self.assertEqual(len(first.kwargs['reply_markup'].inline_keyboard), 1)

    async def test_undelivered_gift_is_cancelled(self):
        self.bot.send_message.side_effect = RuntimeError('blocked')
        job = {'running': True, 'run_id': 5}
        with patch.object(funnel_gifts, 'issue_for_broadcast', AsyncMock(side_effect=[11, 12])), \
                patch.object(funnel_gifts, 'cancel', AsyncMock()) as cancel:
            await admin._broadcast_all(self.bot, 'Дарим 3 дня', job, None, 'gift3')
        self.assertEqual([c.args for c in cancel.await_args_list], [(11,), (12,)])
        self.assertEqual(job['failed'], 2)

    async def test_referral_news_has_invite_button(self):
        job = {'running': True, 'run_id': 6}
        await admin._broadcast_all(self.bot, 'Новая рефералка', job, None, 'referral_news')
        button = self.bot.send_message.await_args_list[0].kwargs['reply_markup'].inline_keyboard[0][0]
        self.assertEqual((button.text, button.callback_data), ('Пригласить друзей', 'share'))
        self.assertEqual(job['sent'], 2)
