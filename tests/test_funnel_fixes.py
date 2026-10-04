import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from app import db, referrals, keyboards, notices, nudge, campaigns
from app.config import Settings


class FunnelFixesTest(unittest.IsolatedAsyncioTestCase):
    async def test_payment_cabinet_first_and_quiet_hides_referral(self):
        settings=Settings.model_construct(referral_program_enabled=True,bot_username='test_bot',webapp_public_url='https://example.org')
        with patch.object(referrals,'get_settings',return_value=settings), patch.object(keyboards,'get_settings',return_value=settings):
            for quiet in (False,True):
                local={'first_online_at':'2026-10-01','quiet_notifications':quiet,'balance_rub':94}
                with patch.object(db,'get_user',AsyncMock(return_value=local)):
                    markup=await referrals.after_topup_keyboard(1)
                self.assertEqual(markup.inline_keyboard[0][0].text,'Открыть кабинет')
                self.assertEqual(any(b.url and 'share/url' in b.url for row in markup.inline_keyboard for b in row),not quiet)
                body=referrals.topup_ok_text('100 ₽',can_share=True,local=local)
                self.assertIn('94',body)
                self.assertEqual('5%' in body,not quiet)

    def test_html_names_safe_and_custom_templates_preserved(self):
        with patch.object(notices,'shop_overlay',return_value={'notices':{'welcome_intro_hi':'<b>{name}</b>, привет'}}):
            self.assertEqual(notices.notice_text('welcome_intro_hi',name='<b>A&B</b>'),'<b>&lt;b&gt;A&amp;B&lt;/b&gt;</b>, привет')
            self.assertEqual(notices.notice_text('welcome_intro_hi',name='A &amp; B'),'<b>A &amp; B</b>, привет')
        with patch.object(notices,'shop_overlay',return_value={'notices':{'broadcast_unused':notices.LEGACY_NOTICE_DEFAULTS['broadcast_unused']}}):
            self.assertIn('поддержка поможет',notices.notice_text('broadcast_unused'))
        with patch.object(notices,'shop_overlay',return_value={'notices':{'broadcast_unused':'Мой текст'}}):
            self.assertEqual(notices.notice_text('broadcast_unused'),'Мой текст')

    def test_inactive_chains_not_editable_as_live_messages(self):
        active={row['key'] for row in notices.NOTICE_FIELDS}
        self.assertFalse(active & notices.ARCHIVED_NOTICE_KEYS)
        self.assertIn('device_created_next_step',active)
        self.assertIn('trial_resume_channel',active)

    async def test_campaign_cap_defers_instead_of_losing_announcement(self):
        bot=AsyncMock()
        with patch.object(db,'notification_allowed',AsyncMock(return_value=True)), \
             patch.object(db,'reserve_optional_message',AsyncMock(return_value=None)), \
             patch.object(db,'defer_campaign_message',AsyncMock()) as defer:
            await campaigns.deliver_campaign_message(bot,dict(telegram_id=1,campaign_id=9,reward_rub=540))
        bot.send_message.assert_not_awaited()
        defer.assert_awaited_once_with(9,1)

    async def test_trial_reminder_matches_welcome_channel_or_cabinet(self):
        for pending,channel,expected in [(True,False,'Я помогу'),(False,False,'канал'),(False,True,'подарок')]:
            with ExitStack() as stack:
                stack.enter_context(patch.object(nudge,'get_settings',return_value=Settings.model_construct(trial_enabled=True)))
                stack.enter_context(patch.object(nudge,'trial_grant_rub',return_value=18))
                stack.enter_context(patch.object(keyboards,'mini_app_url',return_value='https://example.org'))
                stack.enter_context(patch.object(db,'flag_on',AsyncMock(side_effect=lambda key: key=='trial_nudge')))
                stack.enter_context(patch.object(db,'list_due_trial_nudges',AsyncMock(return_value=[{'telegram_id':1,'welcome_support_pending':pending}])))
                stack.enter_context(patch.object(nudge,'_trial_channel_ready',AsyncMock(return_value=channel)))
                deliver=stack.enter_context(patch.object(nudge,'_deliver',AsyncMock(return_value=True)))
                stack.enter_context(patch.object(nudge,'channel_keyboard',return_value=None))
                await nudge.send_due_trial_nudges(AsyncMock())
                self.assertIn(expected,deliver.call_args.kwargs['body'])
