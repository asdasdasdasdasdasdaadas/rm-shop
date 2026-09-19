"""Onboarding transitions without Telegram, panel or database connections."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from aiogram.types import CallbackQuery, Message
from app.handlers import start
from app import welcome
from app.keyboards import legal_text, profile_text, welcome_text


class OnboardingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.db = self.stack.enter_context(patch.object(start, 'db'))
        for name in ('upsert_user', 'claim_welcome_intro', 'mark_legal_notice',
                     'accept_legal_after_notice', 'accept_legal', 'touch_ad_link', 'mark_bot_started'):
            setattr(self.db, name, AsyncMock())
        self.db.upsert_user.return_value = {}
        self.db.claim_welcome_intro.return_value = True
        self.member = self.stack.enter_context(patch.object(start, 'is_channel_member', new_callable=AsyncMock))
        self.member.return_value = True
        self.intro = self.stack.enter_context(patch.object(start, 'send_welcome_intro', new_callable=AsyncMock))
        self.intro.return_value = True
        self.profile = self.stack.enter_context(patch.object(start, 'show_profile', new_callable=AsyncMock))
        self.event = AsyncMock(spec=Message)
        self.event.from_user = SimpleNamespace(id=123, username='test', first_name='Test')
        self.event.answer = AsyncMock()
        self.event.edit_text = AsyncMock()
        self.event.text = '/start'
        self.event.bot = AsyncMock()

    async def test_start_does_not_record_acceptance(self):
        await start.cmd_start(self.event, None, SimpleNamespace(args=None))
        self.intro.assert_awaited_once_with(self.event, in_channel=True)
        self.db.mark_bot_started.assert_awaited_once_with(123)
        self.db.accept_legal_after_notice.assert_not_awaited()
        self.db.accept_legal.assert_not_awaited()
        self.db.claim_trial_balance.assert_not_called()
        self.db.mark_trial_used.assert_not_called()

    async def test_repeat_start_opens_profile_without_legal_gate(self):
        self.db.claim_welcome_intro.return_value = False
        await start.cmd_start(self.event, None, SimpleNamespace(args=None))
        self.profile.assert_awaited_once()
        self.db.accept_legal_after_notice.assert_not_awaited()

    def callback(self):
        cb = AsyncMock(spec=CallbackQuery)
        cb.from_user = self.event.from_user
        cb.bot = self.event.bot
        cb.answer = AsyncMock()
        cb.message = self.event
        return cb

    async def test_subscription_check_goes_straight_to_profile(self):
        cb = self.callback()
        await start.check_sub(cb, None)
        self.db.accept_legal_after_notice.assert_awaited_once_with(123)
        self.profile.assert_awaited_once_with(cb, None)
        self.event.edit_text.assert_not_awaited()

    async def test_failed_subscription_does_not_accept(self):
        self.member.return_value = False
        await start.check_sub(self.callback(), None)
        self.db.accept_legal_after_notice.assert_not_awaited()
        self.profile.assert_not_awaited()

    async def test_legacy_accept_button_still_works(self):
        cb = self.callback()
        await start.accept_legal(cb, None)
        self.db.accept_legal.assert_awaited_once_with(123)
        self.profile.assert_awaited_once_with(cb, None)

    async def test_action_no_longer_has_legal_gate(self):
        self.assertTrue(await start.gate_or_continue(self.callback()))
        self.db.accept_legal_after_notice.assert_awaited_once_with(123)
        self.event.edit_text.assert_not_awaited()


class LegalCopyTest(unittest.TestCase):
    def test_links_are_in_welcome_and_profile_even_with_custom_copy(self):
        settings = SimpleNamespace(legal_offer_url='https://example.com/offer?a=1&b=2',
                                   legal_privacy_url='https://example.com/privacy',
                                   brand_name='VPN', balance_enabled=False)
        with patch('app.keyboards.get_settings', return_value=settings), patch('app.keyboards.notice_text', return_value='Custom'):
            for body in (welcome_text(), profile_text('Test')):
                self.assertIn('https://example.com/offer?a=1&amp;b=2', body)
                self.assertIn('https://example.com/privacy', body)
                self.assertIn('Продолжая работу', body)
                self.assertNotIn('Принимаю', body)


class WelcomeDeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_notice_recorded_only_after_successful_delivery(self):
        for failed in (False, True):
            with self.subTest(failed=failed), ExitStack() as stack:
                db = stack.enter_context(patch.object(welcome, 'db'))
                db.get_user = AsyncMock(return_value={})
                db.mark_legal_notice = AsyncMock()
                stack.enter_context(patch.object(welcome, 'get_settings', return_value=SimpleNamespace(
                    brand_name='VPN', referral_invitee_reward_rub=0,
                    balance_enabled=False, trial_enabled=False, trial_days=0)))
                stack.enter_context(patch.object(welcome.logger, 'warning'))
                stack.enter_context(patch.object(welcome, 'trial_is_available', return_value=False))
                stack.enter_context(patch.object(welcome, 'notice_text', return_value='Hello'))
                stack.enter_context(patch.object(welcome, 'legal_text', return_value='Legal links'))
                keyboard = stack.enter_context(patch.object(welcome, 'profile_keyboard', return_value='full-menu'))
                for name in ('send_welcome_sticker', '_pause', '_log'):
                    stack.enter_context(patch.object(welcome, name, new_callable=AsyncMock))
                message = AsyncMock()
                message.from_user = SimpleNamespace(id=123, first_name='Test')
                message.chat = SimpleNamespace(id=123)
                if failed:
                    message.answer.side_effect = [None, None, RuntimeError('delivery failed')]
                result = await welcome.send_welcome_intro(message, in_channel=True)
                self.assertEqual(result, not failed)
                if failed:
                    db.mark_legal_notice.assert_not_awaited()
                else:
                    db.mark_legal_notice.assert_awaited_once_with(123)
                    keyboard.assert_called_once()
                    self.assertEqual(message.answer.call_args.kwargs['reply_markup'], 'full-menu')
                    self.assertIn('Legal links', message.answer.call_args.args[0])
                    self.assertTrue(message.answer.call_args.kwargs['link_preview_options'].is_disabled)


class AcceptanceStorageTest(unittest.IsolatedAsyncioTestCase):
    async def test_notice_required_and_first_acceptance_preserved(self):
        import sqlite3
        from datetime import datetime, timezone
        from app import db
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE users (telegram_id INTEGER, legal_notice_at TEXT, accepted_legal_at TEXT)')
        conn.execute('INSERT INTO users VALUES (123, NULL, NULL)')

        async def execute(sql, *args):
            return conn.execute(sql, {str(i): x.isoformat() if isinstance(x, datetime) else x
                                      for i, x in enumerate(args, 1)})

        pool = SimpleNamespace(execute=execute)
        with patch.object(db, '_pool_req', return_value=pool):
            await db.accept_legal_after_notice(123)
            self.assertIsNone(conn.execute('SELECT accepted_legal_at FROM users').fetchone()[0])
            await db.mark_legal_notice(123)
            self.assertIsNone(conn.execute('SELECT accepted_legal_at FROM users').fetchone()[0])
            await db.accept_legal_after_notice(123)
            first = conn.execute('SELECT accepted_legal_at FROM users').fetchone()[0]
            self.assertIsNotNone(first)
            with patch.object(db, '_utc_now', return_value=datetime(2030, 1, 1, tzinfo=timezone.utc)):
                await db.accept_legal_after_notice(123)
                await db.accept_legal(123)
            self.assertEqual(conn.execute('SELECT accepted_legal_at FROM users').fetchone()[0], first)
