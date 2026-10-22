import unittest
from unittest.mock import AsyncMock, patch
from app import live
from app.button_icons import PINNED_ICONS


class LiveMessageTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = {'telegram_id': 123, 'first_name': '<Иван & Анна>', 'username': 'user'}

    def test_first_and_repeat_payment_labels(self):
        for repeat, label, kind in [(False, 'Первая оплата', 'pay'), (True, 'Повторная оплата', 'retry')]:
            with self.subTest(repeat=repeat), patch.object(live, 'post') as post:
                live.paid(self.user, amount=1300, title='Тариф', repeat=repeat)
                text = post.call_args.args[0]
                self.assertIn(f'<b>{label}</b>', text)
                self.assertIn(f'emoji-id="{PINNED_ICONS[kind]}"', text)
                self.assertIn('Сумма: <b>1 300 ₽</b>', text)
                self.assertIn('&lt;Иван &amp; Анна&gt;', text)
                self.assertIn('<code>123</code>', text)
                self.assertNotIn('Продлил', text)

    def test_title_is_escaped(self):
        with patch.object(live, 'post') as post:
            live.paid(None, amount=0, title='<Тариф>', repeat=True)
        self.assertIn('Тариф: <b>&lt;Тариф&gt;</b>', post.call_args.args[0])

    def test_first_connection(self):
        with patch.object(live, 'post') as post:
            live.first_online(self.user)
        text = post.call_args.args[0]
        self.assertIn('<b>Первое подключение</b>', text)
        self.assertIn(f'emoji-id="{PINNED_ICONS["connect"]}"', text)
        self.assertIn('tg://user?id=123', text)

    async def test_explicit_html_delivery(self):
        bot = AsyncMock()
        with patch.object(live, '_chat_id', return_value=-100123), patch.object(live.runtime, 'bot', bot):
            await live._send('<b>Тест</b>')
        bot.send_message.assert_awaited_once_with(-100123, '<b>Тест</b>', parse_mode='HTML')
