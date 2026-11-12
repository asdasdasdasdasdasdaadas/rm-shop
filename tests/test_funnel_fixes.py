import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from app import db, referrals, keyboards, notices, nudge
from app.config import Settings


class FunnelFixesTest(unittest.IsolatedAsyncioTestCase):
    async def test_payment_cabinet_first_and_quiet_hides_referral(self):
        settings=Settings.model_construct(referral_program_enabled=True,bot_username='test_bot',webapp_public_url='https://example.org')
        with patch.object(referrals,'get_settings',return_value=settings), patch.object(keyboards,'get_settings',return_value=settings):
            for quiet in (False,True):
                local={'first_online_at':'2026-10-01','quiet_notifications':quiet,'balance_rub':94}
                with patch.object(db,'get_user',AsyncMock(return_value=local)):
                    markup=await referrals.after_topup_keyboard(1)
                self.assertEqual(markup.inline_keyboard[0][0].text,'Личный кабинет')
                self.assertEqual(any(b.url and 'share/url' in b.url for row in markup.inline_keyboard for b in row),not quiet)
                body=referrals.topup_ok_text('100 ₽',can_share=True,local=local)
                self.assertIn('94',body)
                self.assertEqual('Пригласите друга' in body,not quiet)

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

