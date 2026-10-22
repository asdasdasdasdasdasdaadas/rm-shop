import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app import keyboards

class AboutServiceTest(unittest.TestCase):
    def test_layout_and_real_links(self):
        settings = SimpleNamespace(brand_name='WAY & VPN', legal_offer_url='https://example.com/offer', support_username='way_support')
        with patch.object(keyboards, 'get_settings', return_value=settings), patch.object(keyboards, 'mini_app_url', return_value='https://example.com'):
            text, markup = keyboards.about_service_content()
        self.assertIn('WAY &amp; VPN', text)
        self.assertIn('подтвердите вход в боте', text)
        self.assertEqual([len(row) for row in markup.inline_keyboard], [1, 1, 2])
        self.assertEqual(markup.inline_keyboard[1][0].url, 'https://example.com')
        self.assertEqual(markup.inline_keyboard[2][0].url, settings.legal_offer_url)
        self.assertEqual(markup.inline_keyboard[2][1].url, 'https://t.me/way_support')

    def test_no_browser_promise_without_site(self):
        settings = SimpleNamespace(brand_name='WAY', legal_offer_url='https://example.com/offer', support_username='way_support')
        with patch.object(keyboards, 'get_settings', return_value=settings), patch.object(keyboards, 'mini_app_url', return_value=''):
            text, markup = keyboards.about_service_content()
        self.assertNotIn('Войти через сайт', text)
        self.assertEqual([len(row) for row in markup.inline_keyboard], [1, 2])
