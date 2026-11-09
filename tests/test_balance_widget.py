import json
import unittest
import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.types import Update

from app import widgets


def settings(**kw):
    base = dict(brand_name='Лягушка <VPN>', vpn_day_price_rub=5, webapp_public_url='', admin_id_set={1})
    base.update(kw)
    return SimpleNamespace(**base)


class BalanceWidgetTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(widgets, 'get_settings', return_value=settings())
        p.start()
        self.addCleanup(p.stop)

    def test_html_fits_telegram_limits_and_escapes_brand(self):
        page = widgets.widget_html().encode()
        self.assertLessEqual(len(page), 32768)
        self.assertLessEqual(len(zlib.compress(page, 9)), 4096)
        self.assertIn('Лягушка &lt;VPN&gt;', page.decode())
        self.assertNotIn('\0', page.decode())

    async def test_state_counts_only_billable_devices(self):
        devices = [{'id': 1, 'platform': 'ios'}, {'id': 2, 'platform': 'router'}]
        with patch.object(widgets.db, 'get_user', AsyncMock(return_value={'balance_rub': 50})), \
                patch.object(widgets.db, 'list_devices', AsyncMock(return_value=devices)), \
                patch('app.web.balance_runway', return_value=(10, 240)), \
                patch('app.web._is_router_device', side_effect=lambda d: d['platform'] == 'router'):
            state = await widgets.balance_state(7)
        self.assertEqual({k: state[k] for k in 'bdhnp'}, {'b': 50, 'd': 10, 'h': 240, 'n': 1, 'p': 5})

    async def test_refresh_query_is_answered_with_fresh_state_for_the_tapping_user(self):
        bot = AsyncMock()
        update = Update.model_validate({'update_id': 1, 'widget_query': {
            'id': 'q1', 'from': {'id': 42, 'is_bot': False, 'first_name': 'A'}, 'data': 'r'}})
        handler = AsyncMock()
        with patch.object(widgets, 'balance_state', AsyncMock(return_value={'b': 9})) as state:
            await widgets.WidgetQueryMiddleware()(handler, update, {'bot': bot})
        state.assert_awaited_once_with(42)
        handler.assert_not_awaited()
        method = bot.await_args.args[0]
        self.assertEqual(method.__api_method__, 'answerWidgetQuery')
        self.assertEqual((method.widget_query_id, json.loads(method.data)), ('q1', {'b': 9}))

    async def test_unknown_query_gets_an_error_answer(self):
        bot = AsyncMock()
        with patch.object(widgets, 'balance_state', AsyncMock()) as state:
            await widgets.answer_widget_query(bot, {'id': 'q2', 'from': {'id': 42}, 'data': 'pay:999'})
        state.assert_not_awaited()
        self.assertIn('e', json.loads(bot.await_args.args[0].data))

    async def test_failed_state_still_answers_so_widget_does_not_time_out(self):
        bot = AsyncMock()
        with patch.object(widgets, 'balance_state', AsyncMock(side_effect=RuntimeError)):
            await widgets.answer_widget_query(bot, {'id': 'q3', 'from': {'id': 42}, 'data': 'r'})
        self.assertEqual(json.loads(bot.await_args.args[0].data), {'e': 'Не удалось обновить'})

    async def test_other_updates_pass_through(self):
        handler = AsyncMock(return_value='ok')
        update = Update.model_validate({'update_id': 2})
        self.assertEqual(await widgets.WidgetQueryMiddleware()(handler, update, {'bot': AsyncMock()}), 'ok')

    async def test_send_widget_payload(self):
        bot = AsyncMock()
        state = {'b': 120, 'd': 12, 'h': 290, 'n': 2, 'p': 5, 't': 0}
        with patch.object(widgets, 'balance_state', AsyncMock(return_value=state)), \
                patch.object(widgets, 'balance_widget_keyboard', return_value=None):
            await widgets.send_balance_widget(bot, 7)
        method = bot.await_args.args[0]
        self.assertEqual(method.__api_method__, 'sendWidget')
        self.assertTrue(method.allow_queries)
        self.assertEqual(json.loads(method.chat_data), state)
        self.assertEqual(method.caption, 'Баланс: 120 ₽ · хватит на 12 дн.')


if __name__ == '__main__':
    unittest.main()
