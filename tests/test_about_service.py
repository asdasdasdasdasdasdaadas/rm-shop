import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import keyboards

class AboutServiceTest(unittest.TestCase):
    def test_layout_and_real_links(self):
        settings = SimpleNamespace(brand_name='WAY & VPN', vpn_day_price_rub=6, balance_topup_min=50,
                                   referral_program_enabled=True, referral_reward_rub=50, referral_invitee_reward_rub=50,
                                   legal_offer_url='https://example.com/offer', support_username='way_support')
        with patch.object(keyboards, 'get_settings', return_value=settings), patch.object(keyboards, 'mini_app_url', return_value='https://example.com'):
            text, markup = keyboards.about_service_content()
        self.assertIn('WAY &amp; VPN', text)
        self.assertNotIn('В браузере', text)
        self.assertIn('6 ₽ в день за одно устройство', text)
        self.assertIn('Пополнить можно от 50 ₽', text)
        self.assertIn('вы оба получите по 50 ₽', text)
        # No «Открыть в браузере» button, even when the mini app has a public URL.
        self.assertEqual([len(row) for row in markup.inline_keyboard], [1, 2])
        self.assertEqual(markup.inline_keyboard[1][0].url, settings.legal_offer_url)
        self.assertEqual(markup.inline_keyboard[1][1].web_app.url, 'https://example.com?screen=support')

    def test_no_browser_promise_without_site(self):
        settings = SimpleNamespace(brand_name='WAY', legal_offer_url='https://example.com/offer', support_username='way_support')
        with patch.object(keyboards, 'get_settings', return_value=settings), patch.object(keyboards, 'mini_app_url', return_value=''):
            text, markup = keyboards.about_service_content()
        self.assertNotIn('В браузере', text)
        self.assertIn('Сколько стоит', text)
        self.assertEqual([len(row) for row in markup.inline_keyboard], [1, 2])
