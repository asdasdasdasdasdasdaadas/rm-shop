import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from aiogram.methods import SendMessage
from aiogram.types import Message, Chat, User, InlineKeyboardMarkup, InlineKeyboardButton
from app import db
from app.legal_notice import LegalNoticeRequestMiddleware, LegalNoticeInteractionMiddleware, MARKER


class LegalNoticeTest(unittest.IsolatedAsyncioTestCase):
    def message(self):
        return Message(message_id=7, date=datetime.now(timezone.utc), chat=Chat(id=123, type='private'),
                       from_user=User(id=123, is_bot=False, first_name='Test'), text='Меню')

    async def test_first_notice_saved_and_subsequent_footer_removed(self):
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Меню', callback_data='profile')]])
        method = SendMessage(chat_id=123, text='Привет\n\n' + MARKER + 'документы', reply_markup=markup)
        send = AsyncMock(return_value=self.message())
        with patch.object(db, 'get_user', AsyncMock(return_value={})), patch.object(db, 'remember_legal_message', AsyncMock()) as remember, patch.object(db, 'mark_legal_notice', AsyncMock()):
            await LegalNoticeRequestMiddleware()(send, None, method)
            remember.assert_awaited_once_with(123, 7, 'Привет', markup.model_dump_json())
        with patch.object(db, 'get_user', AsyncMock(return_value={'accepted_legal_at': True})), patch.object(db, 'remember_legal_message', AsyncMock()) as remember:
            await LegalNoticeRequestMiddleware()(send, None, method)
            self.assertEqual(send.call_args.args[1].text, 'Привет')
            self.assertEqual(send.call_args.args[1].reply_markup, markup)
            remember.assert_not_awaited()

    async def test_first_message_hides_footer_and_continues_handler(self):
        bot = SimpleNamespace(edit_message_text=AsyncMock())
        handler = AsyncMock(return_value='handled')
        with patch.object(db, 'accept_legal_after_notice', AsyncMock()) as accept, patch.object(db, 'pending_legal_messages', AsyncMock(return_value=[{'message_id': 7, 'body': 'Привет', 'markup': None}])), patch.object(db, 'forget_legal_message', AsyncMock()) as forget:
            result = await LegalNoticeInteractionMiddleware()(handler, self.message(), {'bot': bot})
        self.assertEqual(result, 'handled')
        accept.assert_awaited_once_with(123)
        self.assertEqual(bot.edit_message_text.call_args.args[0], 'Привет')
        forget.assert_awaited_once_with(123, 7)

    async def test_telegram_failure_does_not_block_user_action(self):
        bot = SimpleNamespace(edit_message_text=AsyncMock(side_effect=RuntimeError('unavailable')))
        handler = AsyncMock(return_value='handled')
        with patch.object(db, 'accept_legal_after_notice', AsyncMock()), patch.object(db, 'pending_legal_messages', AsyncMock(return_value=[{'message_id': 7, 'body': 'Привет', 'markup': None}])), patch.object(db, 'forget_legal_message', AsyncMock()) as forget:
            result = await LegalNoticeInteractionMiddleware()(handler, self.message(), {'bot': bot})
        self.assertEqual(result, 'handled')
        forget.assert_not_awaited()
