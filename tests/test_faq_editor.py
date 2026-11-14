import unittest
from unittest.mock import patch

from app import faq


class FaqEditorTest(unittest.TestCase):
    def test_custom_plain_text_and_reset(self):
        rows = faq.validate_faq([{'q':' <Вопрос> ', 'a':' Ответ & текст '}])
        with patch.object(faq, 'shop_overlay', return_value={'faq_items': rows}):
            self.assertEqual(faq.faq_items(), faq.tariff_faq_items() + rows)
            self.assertIn('&lt;Вопрос&gt;', faq.faq_pages()[0])
        self.assertIsNone(faq.validate_faq(None))
        with self.assertRaises(ValueError): faq.validate_faq([{'q':'', 'a':'Ответ'}])

    def test_long_faq_is_split_between_messages(self):
        rows = [{'q':str(i), 'a':'Текст ' * 180} for i in range(10)]
        with patch.object(faq, 'shop_overlay', return_value={'faq_items': rows}):
            pages = faq.faq_pages()
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) < 4096 for page in pages))
