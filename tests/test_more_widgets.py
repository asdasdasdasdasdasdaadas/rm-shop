import json
import unittest
import zlib
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from app import payment_notice, tickets, widgets, widgets_more as more


def settings(**kw):
    base = dict(brand_name='Лягушка <VPN>', vpn_day_price_rub=5, admin_id_set={1}, webapp_public_url='https://x.test',
                referral_program_enabled=True, referral_reward_rub=50, referral_invitee_reward_rub=30)
    base.update(kw)
    return SimpleNamespace(**base)


class PagesTest(unittest.TestCase):
    def test_every_new_widget_fits_telegram_limits(self):
        with patch.object(widgets, 'get_settings', return_value=settings()):
            pages = [more.receipt_html(), more.ticket_html(), more.admin_ticket_html(),
                     more.digest_html(), more.forecast_html()]
        for page in pages:
            raw = page.encode()
            with self.subTest(page=page[:80]):
                self.assertLessEqual(len(raw), 32768)
                self.assertLessEqual(len(zlib.compress(raw, 9)), 4096)
                self.assertNotIn('__', page)
                self.assertIn('&lt;VPN&gt;', page) if 'Лягушка' in page else None

    def test_numeric_e_is_data_not_an_error(self):
        # Balance state carries «e» — when access ends; only a string «e» is an error message.
        self.assertIn("typeof v.e=='string'", widgets.BALANCE_HTML)


class QueryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(more, 'get_settings', return_value=settings())
        p.start()
        self.addCleanup(p.stop)
        more._replying.clear()

    async def test_admin_requests_need_an_admin(self):
        for data in ('F', 'A:5', 'C:5', 'W:5'):
            self.assertEqual(await more.handle_query(None, 2, data), {'e': 'Нет доступа'})

    async def test_routed_from_the_common_dispatcher(self):
        with patch.object(more, 'handle_query', AsyncMock(return_value={'ok': 1})) as h:
            self.assertEqual(await widgets.handle_query(None, {'from': {'id': 3}, 'data': 'z:7'}), {'ok': 1})
        h.assert_awaited_once_with(None, 3, 'z:7')

    async def test_owner_closes_and_rates_through_the_widget(self):
        state = AsyncMock(return_value={'i': 7, 'o': 0})
        with patch.object(more.db, 'close_user_ticket', AsyncMock(return_value={'id': 7})) as close, \
                patch.object(more.db, 'rate_user_ticket', AsyncMock(return_value=None)) as rate, \
                patch.object(more, 'ticket_state', state), patch('app.handlers.tickets.close_support') as support:
            self.assertEqual(await more.handle_query(None, 3, 'k:7'), {'i': 7, 'o': 0})
            close.assert_awaited_once_with(3, 7)
            support.assert_called_once_with(3)
            self.assertEqual(await more.handle_query(None, 3, 'v:7:9'), {'e': 'Выберите оценку от 1 до 5'})
            self.assertEqual(await more.handle_query(None, 3, 'v:7:4'), {'e': 'Оценка уже поставлена'})
            rate.assert_awaited_once_with(3, 7, 4)
        state.assert_awaited_with(7, 3)

    async def test_strangers_do_not_see_a_ticket(self):
        with patch.object(more, '_ticket', AsyncMock(return_value={'id': 7, 'telegram_id': 3, 'status': 'open'})):
            self.assertEqual(await more.ticket_state(7, 4), {'e': 'Обращение не найдено'})
            self.assertEqual((await more.ticket_state(7, 3))['o'], 1)

    async def test_reply_here_toggles_and_routes_the_next_message(self):
        with patch.object(more, 'admin_ticket_state', AsyncMock(return_value={})):
            await more.handle_query(None, 1, 'W:9')
            self.assertEqual(more.reply_target(1), 9)
            await more.handle_query(None, 1, 'W:9')
            self.assertIsNone(more.reply_target(1))
            await more.handle_query(None, 1, 'W:9')
        from app.handlers import tickets as handler
        message = SimpleNamespace(from_user=SimpleNamespace(id=1, is_bot=False), text='Перезагрузите приложение',
                                  caption=None, photo=None, video=None, document=None, animation=None,
                                  bot=object(), answer=AsyncMock())
        with patch('app.config.get_settings', return_value=settings()), \
                patch('app.tickets.receive_admin_reply', AsyncMock()) as reply:
            await handler.ticket_from_chat(message)
        reply.assert_awaited_once_with(message.bot, 9, 'Перезагрузите приложение', [])
        self.assertIn('#9', message.answer.await_args.args[0])
        self.assertIsNone(more.reply_target(1))


class DeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_payment_notice_sends_a_receipt_widget(self):
        bot = AsyncMock()
        receipt = dict(payment_key='order:1', telegram_id=5, amount=300, router_days=0)
        with patch.object(payment_notice.db, 'claim_payment_notice', AsyncMock(return_value=True)), \
                patch.object(payment_notice.db, 'finish_payment_notice', AsyncMock()) as finish, \
                patch.object(payment_notice.db, 'log_bot_message', AsyncMock()), \
                patch.object(payment_notice.db, 'get_user', AsyncMock(return_value={'balance_rub': 350})), \
                patch.object(payment_notice.db, 'list_devices', AsyncMock(return_value=[{'id': 1}])), \
                patch('app.keyboards.mini_app_url', return_value='https://example.com'), \
                patch.object(more, 'receipt_state', AsyncMock(return_value={'a': 300})):
            await payment_notice.deliver_payment_notice(bot, receipt)
        method = bot.await_args.args[0]
        self.assertEqual(method.__api_method__, 'sendWidget')
        self.assertIn('300', method.caption)
        self.assertEqual(json.loads(method.chat_data), {'a': 300})
        self.assertEqual(method.reply_markup.inline_keyboard[0][0].text, 'Личный кабинет')
        bot.send_message.assert_not_awaited()
        finish.assert_awaited_once_with('order:1', 'sent')

    async def test_blocked_bot_is_not_retried_as_text(self):
        bot = AsyncMock(side_effect=TelegramForbiddenError(method=SendMessage(chat_id=5, text='x'), message='blocked'))
        receipt = dict(payment_key='order:2', telegram_id=5, amount=300, router_days=0)
        with patch.object(payment_notice.db, 'claim_payment_notice', AsyncMock(return_value=True)), \
                patch.object(payment_notice.db, 'finish_payment_notice', AsyncMock()) as finish, \
                patch.object(payment_notice.db, 'log_bot_message', AsyncMock()), \
                patch.object(payment_notice.db, 'get_user', AsyncMock(return_value={})), \
                patch.object(payment_notice.db, 'list_devices', AsyncMock(return_value=[])), \
                patch('app.keyboards.mini_app_url', return_value='https://example.com'), \
                patch.object(more, 'receipt_state', AsyncMock(return_value={})):
            await payment_notice.deliver_payment_notice(bot, receipt)
        bot.send_message.assert_not_awaited()
        finish.assert_awaited_once_with('order:2', 'blocked')

    async def test_new_ticket_ack_falls_back_to_text(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch.object(more, 'send_ticket_widget', AsyncMock(side_effect=RuntimeError('old client'))):
            await tickets._ack_new_ticket(bot, 5, 7)
        self.assertEqual(bot.send_message.await_args.kwargs['reply_markup'].inline_keyboard[0][0].callback_data,
                         'ticket_close:7')

    async def test_admins_get_a_card_for_a_new_ticket(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        ticket = {'id': 7, 'telegram_id': 5, 'first_name': 'Андрей'}
        with patch.object(tickets, 'get_settings', return_value=settings(admin_id_set={1, 2})), \
                patch.object(more, 'send_admin_ticket_widget', AsyncMock()) as card:
            await tickets._notify_admins(bot, ticket, 'Не работает', created=True, source='bot')
            await tickets._notify_admins(bot, ticket, 'Ещё деталь', created=False, source='bot')
        self.assertEqual(sorted(c.args[1] for c in card.await_args_list), [1, 2])
        self.assertEqual(bot.send_message.await_count, 2)

    async def test_digest_state_ranks_activity(self):
        pool = SimpleNamespace(fetchrow=AsyncMock(side_effect=[{'v': 100, 'p': 2, 'f': 1, 'y': 50},
                                                               {'n': 4, 'nd': 3, 'np': 1}]))
        rows = [{'action': 'share', 'events': 2, 'users': 2}, {'action': 'cabinet', 'events': 9, 'users': 5}]
        with patch.object(more.db, '_pool_req', return_value=pool):
            state = await more.digest_state(date(2026, 11, 9), rows, 6)
        self.assertEqual(state['r'][0], ['Открыли кабинет', 9, 5])
        self.assertEqual((state['v'], state['y'], state['n'], state['u']), (100, 50, 4, 6))
        self.assertIn('09.11.2026', more.digest_caption(state))


if __name__ == '__main__':
    unittest.main()
