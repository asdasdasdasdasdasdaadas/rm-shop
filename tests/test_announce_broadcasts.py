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
            ('got_broadcast_recently', AsyncMock(return_value=False)),
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
        self.list_broadcast_targets.assert_awaited_once_with('everyone')  # sleepers get big news too
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

    async def test_new_year_gift_opens_the_gift_tab_with_its_card(self):
        job = {'running': True, 'run_id': 8, 'media': {'id': 'gift-ny.mp4', 'kind': 'animation'}}
        from aiogram.types import WebAppInfo
        app = WebAppInfo(url='https://cab.example.org/?screen=giftsend')
        with patch('app.keyboards.mini_app_screen', return_value=app) as screen, \
                patch('app.broadcast_media.send', AsyncMock(return_value=SimpleNamespace(message_id=7))) as send:
            await admin._broadcast_all(self.bot, 'Подарите VPN', job, None, 'gift_ny')
        screen.assert_called_with('giftsend')
        self.reserve_optional_message.assert_not_awaited()
        self.assertEqual(job['sent'], 2)
        call = send.await_args_list[0]
        self.assertEqual(call.args[2]['id'], 'gift-ny.mp4')
        button = call.args[4].inline_keyboard[0][0]
        self.assertEqual(button.text, '🎁 Выбрать подарок')

    def test_new_year_template_gets_its_card_and_needs_gifts(self):
        on = SimpleNamespace(referral_program_enabled=True, gifts_enabled=True)
        with patch.object(admin, 'get_settings', return_value=on):
            spec, error = admin._check_broadcast({'template': 'gift_ny', 'text': ''})
        self.assertIsNone(error)
        self.assertEqual(spec['media'], {'id': 'gift-ny.mp4', 'kind': 'animation'})
        self.assertIn('Подарите близким VPN', spec['text'])
        with patch.object(admin, 'get_settings', return_value=SimpleNamespace(referral_program_enabled=True, gifts_enabled=False)):
            self.assertEqual(admin._check_broadcast({'template': 'gift_ny'})[1], 'Подарки другу выключены')

    async def test_friend_nft_opens_the_invite_tab_with_its_showcase(self):
        job = {'running': True, 'run_id': 9, 'media': {'id': 'friend-nft.mp4', 'kind': 'animation'}}
        from aiogram.types import WebAppInfo
        app = WebAppInfo(url='https://cab.example.org/?screen=friends')
        with patch('app.keyboards.mini_app_screen', return_value=app) as screen, \
                patch('app.broadcast_media.send', AsyncMock(return_value=SimpleNamespace(message_id=7))) as send:
            await admin._broadcast_all(self.bot, 'NFT', job, None, 'friend_nft')
        screen.assert_called_with('friends')
        self.assertEqual(job['sent'], 2)
        call = send.await_args_list[0]
        self.assertEqual(call.args[2]['id'], 'friend-nft.mp4')
        self.assertEqual(call.args[4].inline_keyboard[0][0].text, '💎 Получить подарок')

    async def test_friend_nft_template_gets_its_clip_and_needs_the_promotion(self):
        from app import broadcast_media, friend_nft
        self.assertTrue(broadcast_media.BUILTIN['friend-nft.mp4'].is_file())
        spec, error = admin._check_broadcast({'template': 'friend_nft', 'text': ''})
        self.assertIsNone(error)
        self.assertEqual(spec['media'], {'id': 'friend-nft.mp4', 'kind': 'animation'})
        self.assertIn('NFT-подарки за друзей', spec['text'])
        self.assertLessEqual(len(spec['text']), 964)
        with patch.object(friend_nft, 'config', AsyncMock(return_value={'enabled': False})):
            self.assertEqual(await admin._template_off('friend_nft'), 'Акция «NFT-подарки за друзей» выключена')
        with patch.object(friend_nft, 'config', AsyncMock(return_value={'enabled': True})):
            self.assertIsNone(await admin._template_off('friend_nft'))
