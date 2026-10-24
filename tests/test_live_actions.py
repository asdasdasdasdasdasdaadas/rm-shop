import unittest
from unittest.mock import AsyncMock, patch
from app import live

class LiveActionsTest(unittest.IsolatedAsyncioTestCase):
    def test_action_contains_identity_and_escaped_name(self):
        with patch.object(live, 'post') as post:
            live.user_action({'telegram_id': 123, 'first_name': '<Имя>', 'username': 'test'}, 'invite')
        text = post.call_args.args[0]
        self.assertIn('Пользователь нажал «Пригласить друзей»', text)
        self.assertIn('&lt;Имя&gt;', text)
        self.assertIn('<code>123</code>', text)
        self.assertIn('<tg-emoji', text)
        self.assertIn('Telegram-бот', text)

    def test_all_supported_actions_and_unknown_action(self):
        for action in ('invite', 'share', 'copy', 'about', 'cabinet', 'gift_view'):
            with self.subTest(action=action), patch.object(live, 'post') as post:
                live.user_action({'telegram_id': 1}, action, source='web')
                self.assertIn('Веб-кабинет', post.call_args.args[0])
        with patch.object(live, 'post') as post:
            live.user_action({}, 'unknown')
            post.assert_not_called()

    async def test_disabled_channel_does_not_query_user(self):
        with patch.object(live, '_chat_id', return_value=None), patch.object(live.db, 'get_user', AsyncMock()) as get:
            await live.web_user_action(123, 'share')
        get.assert_not_awaited()

    async def test_lookup_failure_does_not_break_main_action(self):
        with patch.object(live, '_chat_id', return_value=-100123), patch.object(live.db, 'get_user', AsyncMock(side_effect=RuntimeError())):
            await live.web_user_action(123, 'copy')

    async def test_web_action_uses_authenticated_user(self):
        with patch.object(live, '_chat_id', return_value=-100123), patch.object(live.db, 'get_user', AsyncMock(return_value={'first_name':'Иван'})), patch.object(live, 'post') as post:
            await live.web_user_action(123, 'share')
        self.assertIn('<code>123</code>', post.call_args.args[0])
        self.assertIn('Поделиться ссылкой', post.call_args.args[0])
