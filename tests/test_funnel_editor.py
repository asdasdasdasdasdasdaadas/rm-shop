import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import admin, funnel_board as board, config
from app.funnel_ui import answer_funnel


def graph(buttons=None):
    return {'branches':[{'id':'start','title':'Старт','steps':[{'id':'one','condition':'no_device','wait_hours':24,'wait_from':'anchor','text':'Привет, {name}! <tg-emoji emoji-id="123">⭐</tg-emoji>','enabled':True,'buttons': buttons or ['cabinet']}]}]}

class EditorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher=patch("app.keyboards.get_settings",return_value=self.settings())
        patcher.start()
        self.addCleanup(patcher.stop)

    def settings(self):
        return config.Settings.model_construct(bot_username='test_bot',webapp_public_url='https://example.org', required_channel_url='https://t.me/test',admin_ids='123',vpn_day_price_rub=6)

    def test_custom_buttons_roundtrip_and_unsafe_urls(self):
        buttons=[{'action':'topup','text':'Продлить VPN'}, {'action':'url','text':'Новости','url':'https://example.org/news'}]
        value=graph(buttons)
        value['main_menu']={'text':'Привет, {name}! Баланс {balance}', 'buttons':buttons}
        self.assertEqual(board.validate(value),value)
        with patch('app.config.get_settings',return_value=self.settings()):
            kb=board.markup(buttons,123)
        self.assertEqual(kb.inline_keyboard[0][0].text,'Продлить VPN')
        self.assertIn('screen=topup',kb.inline_keyboard[0][0].web_app.url)
        self.assertEqual(kb.inline_keyboard[1][0].url,'https://example.org/news')
        for url in ['javascript:alert(1)','http://example.org','https://user:pass@example.org']:
            with self.assertRaises(ValueError):
                board.validate_buttons([{'action':'url','text':'Ссылка','url':url}])
        with self.assertRaises(ValueError):
            board.validate_buttons([{'action':'url','text':'','url':'https://example.org'}])
        with self.assertRaises(ValueError):
            board.validate_buttons(['cabinet']*7)
        emoji=[{'action':'topup','text':'Продлить','emoji':'5368324170671202286'}]
        self.assertEqual(board.validate_buttons(emoji), emoji)
        self.assertEqual(board.validate_buttons([{'action':'topup','text':'Продлить','emoji':'   '}]), [{'action':'topup','text':'Продлить'}])
        with self.assertRaises(ValueError):
            board.validate_buttons([{'action':'topup','text':'Продлить','emoji':'star'}])
        with patch('app.config.get_settings',return_value=self.settings()):
            icon=board.markup(emoji,123)
        self.assertEqual(icon.inline_keyboard[0][0].icon_custom_emoji_id,'5368324170671202286')
        from app.funnel_test import test_keyboard
        tested=test_keyboard(icon)
        self.assertEqual(tested.inline_keyboard[0][0].icon_custom_emoji_id,'5368324170671202286')
        self.assertEqual(tested.inline_keyboard[0][0].callback_data,'funnel_test:click')

    async def test_draft_branch_test_no_save_or_account_effects(self):
        bot=SimpleNamespace(send_message=AsyncMock())
        request=SimpleNamespace(method='POST',json=AsyncMock(return_value={'telegram_id':123,'scenario':'start','graph':graph()}),app={'bot':bot})
        with patch.object(admin,'_need_auth',return_value=None),patch.object(admin,'get_settings',return_value=SimpleNamespace(admin_id_set={123})),patch('app.config.get_settings',return_value=self.settings()),patch.object(board,'save',AsyncMock()) as save:
            response=await admin.api_funnel_test(request)
        self.assertEqual(json.loads(response.body)['sent'],1)
        save.assert_not_awaited()
        args=bot.send_message.call_args
        self.assertEqual(args.args[0],123)
        self.assertIn('<tg-emoji emoji-id="123">⭐</tg-emoji>',args.args[1])
        self.assertNotIn('{name}',args.args[1])
        for row in args.kwargs['reply_markup'].inline_keyboard:
            for button in row:
                self.assertEqual(button.callback_data,'funnel_test:click')
                self.assertIsNone(button.url)
                self.assertIsNone(button.web_app)

    async def test_main_menu_preview_preserves_two_column_row(self):
        value=graph()
        value['main_menu']={'text':'Menu', 'buttons':['cabinet',{'action':'channel','text':'Channel'},'invite','about']}
        bot=SimpleNamespace(send_message=AsyncMock())
        request=SimpleNamespace(method='POST',json=AsyncMock(return_value={'telegram_id':123,'scenario':'main-menu','graph':value}),app={'bot':bot})
        with patch.object(admin,'_need_auth',return_value=None),patch.object(admin,'get_settings',return_value=SimpleNamespace(admin_id_set={123})),patch('app.config.get_settings',return_value=self.settings()):
            response=await admin.api_funnel_test(request)
        self.assertEqual(json.loads(response.body)['sent'],1)
        self.assertEqual([len(row) for row in bot.send_message.call_args.kwargs['reply_markup'].inline_keyboard],[1,1,2])

    async def test_menu_content_and_preserve(self):
        value=graph();value['main_menu']={'text':'Привет, {name}! {balance}', 'buttons':[{'action':'about','text':'Кто мы'}]}
        with patch.object(board,'load',AsyncMock(return_value=value)),patch('app.config.get_settings',return_value=self.settings()):
            text,kb=await board.menu_content('<Имя>',200,123)
        self.assertIn('&lt;Имя&gt;',text)
        self.assertIn('200',text)
        self.assertEqual(kb.inline_keyboard[0][0].callback_data,'about_service')
        message=SimpleNamespace(answer=AsyncMock())
        await answer_funnel(message,text,reply_markup=kb,preserve=True)
        self.assertEqual(message.answer.call_args.args[0],text)
        self.assertEqual(message.answer.call_args.kwargs['reply_markup'],kb)
        self.assertNotIn('preserve',message.answer.call_args.kwargs)

    async def test_emoji_set_only_custom(self):
        bot=SimpleNamespace(get_sticker_set=AsyncMock(return_value=SimpleNamespace(sticker_type='custom_emoji',title='Stars',stickers=[SimpleNamespace(custom_emoji_id='123',emoji='⭐',thumbnail=None)])))
        request=SimpleNamespace(query={'set':'https://t.me/addemoji/Stars'},app={'bot':bot})
        with patch.object(admin,'_need_auth',return_value=None):
            response=await admin.api_funnel_emojis(request)
        self.assertEqual(json.loads(response.body)['items'][0]['id'],'123')
        bot.get_sticker_set.assert_awaited_once_with(name='Stars')

    async def test_real_delivery_keeps_configured_buttons_and_emoji(self):
        from app import db, nudge
        with patch('app.config.get_settings',return_value=self.settings()):
            kb=board.markup([{'action':'topup','text':'Продлить'}, {'action':'url','text':'Сайт','url':'https://example.org'}],123)
        bot=SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=5)))
        text='<tg-emoji emoji-id="123">⭐</tg-emoji> Текст'
        with patch.object(db,'nudge_delivery_allowed',AsyncMock(return_value=True)),patch.object(db,'create_reminder_delivery',AsyncMock(return_value='track')),patch.object(db,'finish_reminder_delivery',AsyncMock()),patch.object(db,'log_bot_message',AsyncMock()):
            result=await nudge._deliver_unbudgeted(bot,kind='nudge_board',telegram_id=123,first_name='Admin',title='Test',body=text,reply_markup=kb,preserve=True)
        self.assertTrue(result)
        self.assertEqual(bot.send_message.call_args.args[1],text)
        rows=bot.send_message.call_args.kwargs['reply_markup'].inline_keyboard
        self.assertEqual([row[0].text for row in rows],['Продлить','Сайт'])
        self.assertIn('nt=track',rows[0][0].web_app.url)
