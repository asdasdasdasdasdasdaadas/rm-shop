import unittest
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from aiogram.methods import SendMessage, EditMessageReplyMarkup
from aiogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup as Markup
from aiogram.exceptions import TelegramBadRequest
from app.button_icons import decorate, kind_for, ButtonIconsMiddleware, install_button_icons, PINNED_ICONS, ICONS, PACK

class ButtonIconsTest(unittest.IsolatedAsyncioTestCase):
    def test_semantics_and_preservation(self):
        source=Markup(inline_keyboard=[[Button(text='Главное меню',callback_data='profile',style='success'),Button(text='О сервисе',callback_data='about_service')],[Button(text='Своя иконка',callback_data='profile',icon_custom_emoji_id='123')]])
        result=decorate(source,{'home':'456','about':'789'}, {'123', '456', '789'})
        self.assertEqual(result.inline_keyboard[0][0].icon_custom_emoji_id,'456')
        self.assertEqual(result.inline_keyboard[0][1].icon_custom_emoji_id,'789')
        self.assertEqual(result.inline_keyboard[1][0].icon_custom_emoji_id,'123')
        self.assertEqual(result.inline_keyboard[0][0].callback_data,'profile')
        self.assertEqual(result.inline_keyboard[0][0].style,'success')
        self.assertIsNone(source.inline_keyboard[0][0].icon_custom_emoji_id)
        self.assertEqual(decorate(decorate(source,{}),{}),decorate(source,{}))

    async def test_permission_fallback_does_not_change_action(self):
        method=SendMessage(chat_id=123,text='hello',reply_markup=Markup(inline_keyboard=[[Button(text='Главное меню',callback_data='profile')]]))
        request=AsyncMock(side_effect=[TelegramBadRequest(method=method,message='CUSTOM_EMOJI_INVALID'),'ok'])
        middleware=ButtonIconsMiddleware({'home':'456'})
        self.assertEqual(await middleware(request,None,method),'ok')
        retried=request.call_args.args[1].reply_markup.inline_keyboard[0][0]
        self.assertEqual(retried.text,'🏠 Главное меню')
        self.assertEqual(retried.callback_data,'profile')
        self.assertFalse(middleware.ids)

    async def test_unrelated_failure_not_retried(self):
        method=SendMessage(chat_id=123,text='hello',reply_markup=Markup(inline_keyboard=[[Button(text='Главное меню',callback_data='profile')]]))
        request=AsyncMock(side_effect=TelegramBadRequest(method=method,message='chat not found'))
        with self.assertRaises(TelegramBadRequest): await ButtonIconsMiddleware({'home':'456'})(request,None,method)
        self.assertEqual(request.await_count,1)

    async def test_real_ids_are_resolved_from_set(self):
        installed=[]
        bot=SimpleNamespace(get_sticker_set=AsyncMock(return_value=SimpleNamespace(sticker_type='custom_emoji',stickers=[SimpleNamespace(emoji='🏠',custom_emoji_id='777')])),session=SimpleNamespace(middleware=installed.append))
        await install_button_icons(bot)
        self.assertEqual(set(installed[0].ids), set(ICONS))
        self.assertEqual(set(installed[0].ids.values()), {'777'})
        self.assertEqual(installed[0].allowed_ids, {'777'})
        bot.get_sticker_set.assert_awaited_once_with(PACK)

    async def test_pinned_home_survives_pack_failure(self):
        installed=[]
        bot=SimpleNamespace(get_sticker_set=AsyncMock(side_effect=RuntimeError('unavailable')),session=SimpleNamespace(middleware=installed.append))
        await install_button_icons(bot)
        self.assertEqual(installed[0].ids['home'],'5257963315258204021')

    def test_all_literal_buttons_receive_same_pack_icons(self):
        checked = 0
        for path in (Path(__file__).resolve().parents[1] / 'app').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != 'InlineKeyboardButton':
                    continue
                fields = {kw.arg: kw.value.value for kw in node.keywords if isinstance(kw.value, ast.Constant)}
                if not isinstance(fields.get('text'), str):
                    continue
                original = Button(**fields)
                markup = Markup(inline_keyboard=[[original]])
                button = decorate(markup, {'action': '777'}).inline_keyboard[0][0]
                self.assertEqual(button.icon_custom_emoji_id, '777', (path.name, original.text))
                self.assertEqual(button.callback_data, original.callback_data)
                self.assertEqual(button.url, original.url)
                checked += 1
        self.assertGreater(checked, 40)

    def test_foreign_icons_replaced_and_unicode_not_duplicated(self):
        source = Markup(inline_keyboard=[[Button(text='🤝 Я помогу', callback_data='welcome:continue', icon_custom_emoji_id='999')]])
        decorated = decorate(source, {'check': '777'})
        button = decorated.inline_keyboard[0][0]
        self.assertEqual(button.icon_custom_emoji_id, '777')
        self.assertEqual(button.text, 'Я помогу')
        self.assertEqual(decorate(decorated, {'check': '777'}), decorated)
        fallback = decorate(source, {})
        self.assertIsNone(fallback.inline_keyboard[0][0].icon_custom_emoji_id)
        self.assertEqual(decorate(fallback, {}), fallback)

    def test_missing_semantics(self):
        cases = {'lk:y:1': 'check', 'lk:n:1': 'cancel', 'accept_legal': 'check',
                 'ticket_rate:1:5': 'rating', 'ticket_close:1': 'check',
                 'try_again': 'retry', 'buy:month': 'pay', 'payreason:later:x': 'message',
                 'unknown': 'action'}
        for callback, expected in cases.items():
            self.assertEqual(kind_for(Button(text='Кнопка', callback_data=callback)), expected)
        self.assertEqual(kind_for(Button(text='Нужна помощь', callback_data='help:connect')), 'help')
        self.assertEqual(kind_for(Button(text='Оферта', url='https://example.com')), 'document')

    async def test_group_and_inline_edits_are_decorated(self):
        markup = Markup(inline_keyboard=[[Button(text='Кнопка', callback_data='custom')]])
        for method in (SendMessage(chat_id=-123, text='test', reply_markup=markup),
                       EditMessageReplyMarkup(inline_message_id='inline', reply_markup=markup)):
            request = AsyncMock(return_value=True)
            await ButtonIconsMiddleware({'action': '777'})(request, None, method)
            self.assertEqual(request.call_args.args[1].reply_markup.inline_keyboard[0][0].icon_custom_emoji_id, '777')

    async def test_rejected_existing_pack_icon_is_removed_on_retry(self):
        markup = Markup(inline_keyboard=[[Button(text='Кнопка', callback_data='custom', icon_custom_emoji_id='777')]])
        method = SendMessage(chat_id=123, text='test', reply_markup=markup)
        request = AsyncMock(side_effect=[TelegramBadRequest(method=method, message='CUSTOM_EMOJI_INVALID'), True])
        await ButtonIconsMiddleware({'action': '777'})(request, None, method)
        self.assertIsNone(request.call_args.args[1].reply_markup.inline_keyboard[0][0].icon_custom_emoji_id)
