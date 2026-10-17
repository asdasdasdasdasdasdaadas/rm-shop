import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from aiogram.methods import SendMessage
from aiogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup as Markup
from aiogram.exceptions import TelegramBadRequest
from app.button_icons import decorate, kind_for, ButtonIconsMiddleware, install_button_icons, PINNED_ICONS

class ButtonIconsTest(unittest.IsolatedAsyncioTestCase):
    def test_semantics_and_preservation(self):
        source=Markup(inline_keyboard=[[Button(text='Главное меню',callback_data='profile',style='success'),Button(text='О сервисе',callback_data='about_service')],[Button(text='Своя иконка',callback_data='profile',icon_custom_emoji_id='123')]])
        result=decorate(source,{'home':'456','about':'789'})
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
        self.assertEqual(installed[0].ids,PINNED_ICONS)

    async def test_pinned_home_survives_pack_failure(self):
        installed=[]
        bot=SimpleNamespace(get_sticker_set=AsyncMock(side_effect=RuntimeError('unavailable')),session=SimpleNamespace(middleware=installed.append))
        await install_button_icons(bot)
        self.assertEqual(installed[0].ids['home'],'5257963315258204021')
