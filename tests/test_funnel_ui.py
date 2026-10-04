import unittest
from unittest.mock import patch
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from app.funnel_ui import CTA, funnel_body, funnel_keyboard
from app.reminder_tracking import tracked_keyboard


class FunnelUITest(unittest.TestCase):
    def test_plain_and_legal_footer_are_idempotent(self):
        from app.legal_notice import MARKER, without_notice
        body=funnel_body('Hello\n\n'+MARKER+'documents')
        self.assertIn(CTA,without_notice(body))
        self.assertEqual(body,funnel_body(body))

    def test_primary_keeps_tracked_deep_link_and_help(self):
        markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Gift',web_app=WebAppInfo(url='https://example.com/?screen=gift'))],
            [InlineKeyboardButton(text='Help',callback_data='help:connect')]])
        normalized=funnel_keyboard(markup)
        self.assertEqual(funnel_keyboard(normalized),normalized)
        buttons=[r[0] for r in normalized.inline_keyboard]
        self.assertEqual([b.text for b in buttons],['Личный кабинет','В главное меню','Help'])
        self.assertEqual(buttons[0].style,'success')
        self.assertIsNone(buttons[1].style)
        self.assertIn('screen=gift',tracked_keyboard(normalized,'test').inline_keyboard[0][0].web_app.url)
        self.assertIn('nt=test',tracked_keyboard(normalized,'test').inline_keyboard[0][0].web_app.url)

    def test_payment_callback_is_preserved(self):
        with patch('app.keyboards.mini_app_url',return_value='https://example.com'):
            markup=funnel_keyboard(InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='Pay',callback_data='resume_pay:one')]]))
        self.assertEqual(markup.inline_keyboard[2][0].callback_data,'resume_pay:one')

    def test_missing_url_still_has_navigation(self):
        with patch('app.keyboards.mini_app_url',return_value=''):
            markup=funnel_keyboard()
        self.assertEqual(len(markup.inline_keyboard),2)
        self.assertEqual(markup.inline_keyboard[1][0].callback_data,'profile')
