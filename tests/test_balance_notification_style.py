import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from app import db, reminder_tracking
from app.balance_notifications import BALANCE_ENDING, BALANCE_EMPTY, balance_details


class BalanceNotificationStyleTest(unittest.IsolatedAsyncioTestCase):
    def test_truthful_details_and_caption_size(self):
        text = BALANCE_ENDING + balance_details(12, 2, 6)
        self.assertIn('12 ₽', text)
        self.assertNotIn('Устройств:', text)
        self.assertNotIn('Расход:', text)
        self.assertNotIn('Стоимость:', BALANCE_EMPTY)
        self.assertIn('<blockquote>', text)
        self.assertLess(len(text), 1024)
        self.assertNotIn('последний день', text.lower())
        self.assertLess(len(BALANCE_EMPTY.format(price='6 ₽')), 1024)

    async def test_photo_delivery_preserves_tracking_and_topup(self):
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text='Пополнить баланс', web_app=WebAppInfo(url='https://example.com/?screen=topup'))]])
        bot = SimpleNamespace(send_photo=AsyncMock(return_value=SimpleNamespace(message_id=7)), send_message=AsyncMock())
        with patch.object(db, 'create_reminder_delivery', AsyncMock(return_value='token')), patch.object(db, 'finish_reminder_delivery', AsyncMock()) as finish:
            await reminder_tracking.send_reminder(bot, 1, BALANCE_ENDING, kind='nudge_trial_end', title='Баланс', reply_markup=markup, preserve=True)
        bot.send_message.assert_not_called()
        sent = bot.send_photo.call_args.kwargs
        self.assertEqual(sent['caption'], BALANCE_ENDING)
        self.assertEqual(sent['parse_mode'], 'HTML')
        self.assertIn('screen=topup', sent['reply_markup'].inline_keyboard[0][0].web_app.url)
        self.assertIn('nt=token', sent['reply_markup'].inline_keyboard[0][0].web_app.url)
        finish.assert_awaited_once_with('token', 'sent', 7)

    async def test_long_custom_message_stays_text(self):
        bot = AsyncMock()
        with patch.object(db, 'create_reminder_delivery', AsyncMock(return_value='token')), patch.object(db, 'finish_reminder_delivery', AsyncMock()):
            await reminder_tracking.send_reminder(bot, 1, 'x' * 1500, kind='low_balance', title='Баланс', reply_markup=None, preserve=True)
        bot.send_message.assert_awaited_once()
        bot.send_photo.assert_not_called()

    async def test_failed_photo_marks_failure(self):
        bot = AsyncMock()
        bot.send_photo.side_effect = TimeoutError()
        with patch.object(db, 'create_reminder_delivery', AsyncMock(return_value='token')), patch.object(db, 'finish_reminder_delivery', AsyncMock()) as finish:
            with self.assertRaises(TimeoutError):
                await reminder_tracking.send_reminder(bot, 1, BALANCE_ENDING, kind='low_balance', title='Баланс', reply_markup=None, preserve=True)
        finish.assert_awaited_once_with('token', 'failed', None)
