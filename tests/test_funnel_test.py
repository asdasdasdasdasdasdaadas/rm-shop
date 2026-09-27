import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from contextlib import ExitStack
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import admin, funnel_test, faq, keyboards, nudge, config, referrals


class FunnelTest(unittest.IsolatedAsyncioTestCase):
    def test_catalog_uses_current_texts_and_inert_buttons(self):
        settings = config.Settings.model_construct(bot_username='test_bot', balance_enabled=True, webapp_public_url='https://example.org')
        with ExitStack() as stack:
            for module in (funnel_test, keyboards, nudge, referrals):
                stack.enter_context(patch.object(module, 'get_settings', return_value=settings))
            rows = funnel_test.catalog(123)
        self.assertEqual(len(rows), len({row['id'] for row in rows}))
        for row in rows:
            self.assertTrue(row['body'])
            markup = funnel_test.test_keyboard(row['markup'])
            for buttons in markup.inline_keyboard if markup else []:
                for button in buttons:
                    self.assertEqual(button.callback_data, 'funnel_test:click')
                    self.assertIsNone(button.web_app)
                    self.assertIsNone(button.url)
                    self.assertIsNone(button.copy_text)
        keys = {row['id'] for row in rows}
        for _, steps in funnel_test.SCENARIOS.values():
            self.assertTrue(set(steps) <= keys)

    async def test_cannot_send_to_non_admin(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        request = SimpleNamespace(method='POST', json=AsyncMock(return_value={'telegram_id': 999, 'message_id': 'invoice'}), app={'bot': bot})
        with patch.object(admin, '_need_auth', return_value=None), patch.object(admin, 'get_settings', return_value=SimpleNamespace(admin_id_set={123})):
            response = await admin.api_funnel_test(request)
        self.assertEqual(response.status, 403)
        bot.send_message.assert_not_awaited()

    async def test_send_single_only_to_selected_admin(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        request = SimpleNamespace(method='POST', json=AsyncMock(return_value={'telegram_id':123, 'message_id':'invoice'}), app={'bot':bot})
        rows = [{'id':'invoice', 'title':'Счёт', 'condition':'10 минут', 'body':'Оплатите', 'markup':None}]
        with patch.object(admin, '_need_auth', return_value=None), patch.object(admin, 'get_settings', return_value=SimpleNamespace(admin_id_set={123,456})), patch.object(funnel_test, 'catalog', return_value=rows):
            response = await admin.api_funnel_test(request)
        self.assertEqual(json.loads(response.body)['sent'], 1)
        self.assertEqual(bot.send_message.call_args.args[0], 123)
        self.assertIn('ТЕСТ', bot.send_message.call_args.args[1])


class FaqEditorTest(unittest.TestCase):
    def test_custom_plain_text_and_reset(self):
        rows = faq.validate_faq([{'q':' <Вопрос> ', 'a':' Ответ & текст '}])
        with patch.object(faq, 'shop_overlay', return_value={'faq_items': rows}):
            self.assertEqual(faq.faq_items(), rows)
            self.assertIn('&lt;Вопрос&gt;', faq.faq_pages()[0])
        self.assertIsNone(faq.validate_faq(None))
        with self.assertRaises(ValueError): faq.validate_faq([{'q':'', 'a':'Ответ'}])

    def test_long_faq_is_split_between_messages(self):
        rows = [{'q':str(i), 'a':'Текст ' * 180} for i in range(10)]
        with patch.object(faq, 'shop_overlay', return_value={'faq_items': rows}):
            pages = faq.faq_pages()
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) < 4096 for page in pages))
