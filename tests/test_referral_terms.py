import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import admin, db, faq, keyboards, nudge
from app.config import Settings
from app.referral_terms import referral_terms


class ReferralTermsTest(unittest.IsolatedAsyncioTestCase):
    def settings(self, active=True, **kwargs):
        return Settings.model_construct(balance_enabled=True,referral_program_enabled=active,bot_username='vpn_bot',**kwargs)

    def test_active_faq_has_current_formula_not_obsolete_setting(self):
        settings=self.settings(referral_reward_rub=999,referral_invitee_reward_rub=0)
        with patch.object(faq,'get_settings',return_value=settings), patch.object(faq,'referral_is_payout',return_value=False):
            rows={r['q']:r['a'] for r in faq.faq_items()}
        self.assertIn('50 ₽',rows['Когда начислят за приглашённого друга?'])
        self.assertIn('5%',rows['Сколько дают за друга?'])
        self.assertIn('включая первое',rows['Когда начислят за приглашённого друга?'])
        self.assertNotIn('999',str(rows))
        self.assertEqual(referral_terms(settings)['friend'],'')

    def test_pause_and_resume_terms(self):
        paused=referral_terms(self.settings(False,referral_invitee_reward_rub=30))
        self.assertIn('не начисляются',paused['note'])
        self.assertIn('баланс сохраняется',paused['note'])
        self.assertIn('без выплат за период паузы',paused['when'])
        self.assertIn('50 ₽ позже не начисляется',paused['how'])
        self.assertEqual(paused['friend'],'')
        active=referral_terms(self.settings(True,referral_invitee_reward_rub=30))
        self.assertIn('30',active['friend'])
        self.assertIn('пока программа активна',active['friend'])

    def test_broadcast_preview_and_share_respect_pause(self):
        for active in (False,True):
            settings=self.settings(active)
            with patch.object(admin,'get_settings',return_value=settings), patch.object(keyboards,'get_settings',return_value=settings):
                text=admin._broadcast_template_preview('invite')
                if active:
                    self.assertIn('5%',text)
                    self.assertIn('включая первое',text)
                    self.assertIn('ref_…',text)
                else:
                    self.assertIn('приостановлена',text)
                    self.assertNotIn('После первой оплаты на баланс',keyboards.invite_share_text())

    async def test_old_invite_retry_is_blocked_during_pause(self):
        with patch.object(admin,'get_settings',return_value=self.settings(False)), patch.object(db,'user_is_blocked',AsyncMock(return_value=False)):
            bot=SimpleNamespace(send_message=AsyncMock())
            for row in [dict(id=1,kind='nudge_invite',telegram_id=2,body='Old promise'),dict(id=2,kind='broadcast',telegram_id=2,body='Old promise',extra={'template':'invite'})]:
                ok,message=await admin.retry_logged_message(bot,row)
                self.assertFalse(ok)
                self.assertIn('приостановлена',message)
            bot.send_message.assert_not_awaited()

    async def test_running_referral_broadcast_stops_if_switched_off(self):
        active=self.settings(True);paused=self.settings(False)
        with patch.object(admin,'get_settings',side_effect=[active,active,paused]), \
             patch.object(db,'list_broadcast_targets',AsyncMock(return_value=[{'telegram_id':1},{'telegram_id':2}])), \
             patch.object(admin,'_broadcast_payload',return_value=('message',None)), \
             patch.object(admin,'_deliver_broadcast',AsyncMock()) as deliver, \
             patch.object(db,'log_bot_message',AsyncMock()), patch.object(admin.asyncio,'sleep',AsyncMock()):
            job={'running':True}
            await admin._broadcast_all(None,'',job,template='invite')
            deliver.assert_awaited_once()
            self.assertEqual(job['sent'],1)

    def test_custom_invite_keeps_canonical_conditions(self):
        with patch.object(nudge,'get_settings',return_value=self.settings()), patch.object(nudge,'notice_text',return_value='Custom invitation'):
            self.assertIn('Актуальные условия:',nudge.invite_nudge_text(1,'Друг'))
            self.assertIn('5%',nudge.invite_nudge_text(1,'Друг'))

    def test_copy_text_keeps_complete_link_with_long_brand(self):
        with patch.object(keyboards,'get_settings',return_value=self.settings(brand_name='Очень длинный бренд ' * 20)):
            text=keyboards.invite_copy_text(1234567890)
            self.assertLessEqual(len(text),256)
            self.assertTrue(text.endswith(keyboards.invite_url(1234567890)))
