import json
import time
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from aiogram.types import Update

from app import widgets


def settings(**kw):
    base = dict(brand_name='Лягушка <VPN>', vpn_day_price_rub=5, webapp_public_url='', admin_id_set={1},
                referral_program_enabled=True, referral_reward_rub=50, referral_invitee_reward_rub=30)
    base.update(kw)
    return SimpleNamespace(**base)


def sent(bot, n=-1):
    return bot.await_args_list[n].args[0]


class WidgetPagesTest(unittest.TestCase):
    def test_every_widget_fits_telegram_limits(self):
        with patch.object(widgets, 'get_settings', return_value=settings()):
            pages = [widgets.widget_html(), widgets.referral_html(), widgets.gift_html(3), widgets.stats_html()]
        for page in pages:
            raw = page.encode()
            with self.subTest(page=page[:60]):
                self.assertLessEqual(len(raw), 32768)
                self.assertLessEqual(len(zlib.compress(raw, 9)), 4096)
                self.assertNotIn('\0', page)
                self.assertNotIn('__', page.replace('__proto__', ''))

    def test_brand_is_escaped(self):
        with patch.object(widgets, 'get_settings', return_value=settings()):
            self.assertIn('Лягушка &lt;VPN&gt;', widgets.widget_html())


class BalanceStateTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(widgets, 'get_settings', return_value=settings())
        p.start()
        self.addCleanup(p.stop)

    async def run_state(self, user, devices, runway=(10, 240)):
        with patch.object(widgets.db, 'get_user', AsyncMock(return_value=user)), \
                patch.object(widgets.db, 'list_devices', AsyncMock(return_value=devices)), \
                patch('app.web.balance_runway', return_value=runway), \
                patch('app.web._is_router_device', side_effect=lambda d: d.get('platform') == 'router'):
            return await widgets.balance_state(7)

    async def test_counts_only_billable_devices(self):
        state = await self.run_state({'balance_rub': 50}, [{'id': 1, 'platform': 'ios'}, {'id': 2, 'platform': 'router'}])
        self.assertEqual({k: state[k] for k in 'bdhnp'}, {'b': 50, 'd': 10, 'h': 240, 'n': 1, 'p': 5})

    async def test_access_ends_at_next_charge_plus_covered_days(self):
        billed = datetime.now(timezone.utc) - timedelta(hours=20)
        devices = [{'id': 1, 'platform': 'ios', 'last_billed_at': billed}, {'id': 2, 'platform': 'mac', 'last_billed_at': billed}]
        state = await self.run_state({'balance_rub': 25}, devices, runway=(2, 64))
        # 25 ₽ at 2 × 5 ₽ covers 2 full days after the charge due in 4 hours.
        expected = (billed + timedelta(hours=24) + timedelta(days=2)).timestamp()
        self.assertAlmostEqual(state['e'], expected, delta=1)

    async def test_without_billing_history_uses_the_hour_estimate(self):
        state = await self.run_state({'balance_rub': 5}, [{'id': 1, 'platform': 'ios'}], runway=(1, 24))
        self.assertAlmostEqual(state['e'], time.time() + 24 * 3600, delta=2)


class WidgetQueryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(widgets, 'get_settings', return_value=settings())
        p.start()
        self.addCleanup(p.stop)
        self.bot = AsyncMock()

    async def answer(self, data, user=42, **extra):
        await widgets.answer_widget_query(self.bot, {'id': 'q', 'from': {'id': user}, 'data': data, **extra})
        method = sent(self.bot)
        self.assertEqual(method.__api_method__, 'answerWidgetQuery')
        return json.loads(method.data)

    async def test_middleware_answers_refresh_for_the_tapping_user(self):
        update = Update.model_validate({'update_id': 1, 'widget_query': {
            'id': 'q1', 'from': {'id': 42, 'is_bot': False, 'first_name': 'A'}, 'data': 'r'}})
        handler = AsyncMock()
        with patch.object(widgets, 'balance_state', AsyncMock(return_value={'b': 9})) as state:
            await widgets.WidgetQueryMiddleware()(handler, update, {'bot': self.bot})
        state.assert_awaited_once_with(42)
        handler.assert_not_awaited()
        self.assertEqual(json.loads(sent(self.bot).data), {'b': 9})

    async def test_other_updates_pass_through(self):
        handler = AsyncMock(return_value='ok')
        self.assertEqual(await widgets.WidgetQueryMiddleware()(handler, Update.model_validate({'update_id': 2}), {'bot': self.bot}), 'ok')

    async def test_unknown_and_failed_queries_still_get_an_answer(self):
        self.assertIn('e', await self.answer('pay:999'))
        with patch.object(widgets, 'balance_state', AsyncMock(side_effect=RuntimeError)):
            self.assertEqual(await self.answer('r'), {'e': 'Не удалось обновить'})

    async def test_referral_numbers(self):
        with patch.object(widgets.db, 'referral_stats', AsyncMock(return_value={'invited': 4, 'rewarded': 3})), \
                patch.object(widgets.db, 'referral_wallet', AsyncMock(return_value={'referral_earned': 100})), \
                patch.object(widgets.db, 'referral_credit_sum', AsyncMock(return_value=150)):
            state = await self.answer('f')
        self.assertEqual({k: state[k] for k in 'iwmrq'}, {'i': 4, 'w': 3, 'm': 150, 'r': 50, 'q': 30})
        self.assertNotIn('c', state)
        with patch.object(widgets, 'get_settings', return_value=settings(referral_program_enabled=False)), \
                patch.object(widgets.db, 'referral_stats', AsyncMock(return_value={'invited': 0, 'rewarded': 0})), \
                patch.object(widgets.db, 'referral_wallet', AsyncMock(return_value={})), \
                patch.object(widgets.db, 'referral_credit_sum', AsyncMock(return_value=0)):
            self.assertNotIn('r', await self.answer('f'))

    async def stats(self, online):
        rows = {'a': 120, 'o': 4, 'ad': 31, 'x': 40, 'k': 2, 'n': 5, 'nr': 2, 'nd': 3, 'nc': 2, 'np': 1}
        pay = {'v': 900, 'p': 3, 'f': 1, 'y': 600}
        traffic = {'tb': 5 * 1024**3, 'ts': 1794200000}
        fetch = AsyncMock(side_effect=[
            [{'m': 'rollypay', 'rub': 500}, {'m': 'ton', 'rub': 400}],
            [{'h': 9, 'n': 500}, {'h': 14, 'n': 400}],
            [{'h': 9, 'n': 5}],
        ])
        pool = SimpleNamespace(fetchrow=AsyncMock(side_effect=[rows, pay, traffic]), fetch=fetch, execute=AsyncMock())
        rw = SimpleNamespace(safe_get=AsyncMock(return_value=online))
        with patch.object(widgets.db, '_pool_req', return_value=pool), patch('app.runtime.rw', rw):
            state = await widgets.stats_state()
        self.assertIn('INSERT INTO traffic_days', pool.execute.await_args.args[0])
        return state

    async def test_stats_numbers_for_today(self):
        state = await self.stats({'onlineStats': {'onlineNow': 17, 'lastDay': 60}})
        self.assertEqual({k: state[k] for k in ('v', 'y', 'p', 'f', 'n', 'nr', 'nd', 'nc', 'np', 'x', 'a', 'k', 'ad')},
                         {'v': 900, 'y': 600, 'p': 3, 'f': 1, 'n': 5, 'nr': 2, 'nd': 3, 'nc': 2, 'np': 1,
                          'x': 40, 'a': 120, 'k': 2, 'ad': 31})
        self.assertEqual((state['on'], state['an'], state['tb'], state['ts']), (17, 1, 5 * 1024**3, 1794200000))
        self.assertEqual(state['m'], {'rollypay': 500, 'ton': 400})
        self.assertEqual((len(state['h']), state['h'][9], state['h'][14], state['g'][9]), (24, 500, 400, 5))
        self.assertLessEqual(len(json.dumps(state, separators=(',', ':'))), 1024)

    async def test_online_now_falls_back_to_the_last_sync(self):
        state = await self.stats({'_error': 'GET /system/stats → 404'})
        self.assertEqual((state['on'], state['an']), (4, 0))

    async def test_stats_only_for_admins(self):
        self.assertEqual(await self.answer('s', user=42), {'e': 'Нет доступа'})
        with patch.object(widgets, 'stats_state', AsyncMock(return_value={'v': 500})):
            self.assertEqual(await self.answer('s', user=1), {'v': 500})

    async def test_gift_claim_updates_widget_and_drops_the_button(self):
        result = {'gift_rub': 30, 'balance_rub': 80, 'days': 3, 'devices': 2, 'debt_repaid_rub': 0}
        with patch('app.funnel_gifts.claim', AsyncMock(return_value=result)) as claim:
            answer = await self.answer('g:17', chat={'id': 42}, message_id=5)
        claim.assert_awaited_once_with(42, 17)
        self.assertEqual(answer, {'a': 30, 'b': 80, 'd': 3})
        edit = self.bot.await_args_list[0].args[0]
        self.assertEqual(edit.__api_method__, 'editMessageWidgetData')
        self.assertEqual(json.loads(edit.chat_data), {'g': 17, 's': 1, 'a': 30, 'b': 80})
        self.bot.edit_message_reply_markup.assert_awaited_once_with(chat_id=42, message_id=5, reply_markup=None)

    async def test_gift_claimed_twice_or_foreign(self):
        with patch('app.funnel_gifts.claim', AsyncMock(side_effect=ValueError('Подарок уже получен'))):
            self.assertEqual(await self.answer('g:17'), {'e': 'Подарок уже получен', 'done': 1})
        with patch('app.funnel_gifts.claim', AsyncMock(side_effect=ValueError('Подарок не найден'))):
            self.assertEqual(await self.answer('g:18'), {'e': 'Подарок не найден'})
        self.assertEqual(await self.answer('g:abc'), {'e': 'Подарок не найден'})


class SendingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.object(widgets, 'get_settings', return_value=settings())
        p.start()
        self.addCleanup(p.stop)

    async def test_balance_widget_payload(self):
        bot = AsyncMock()
        state = {'b': 120, 'd': 12, 'h': 290, 'n': 2, 'p': 5, 't': 0, 'e': 0}
        with patch.object(widgets, 'balance_state', AsyncMock(return_value=state)), \
                patch.object(widgets, 'balance_widget_keyboard', return_value=None):
            await widgets.send_balance_widget(bot, 7)
        method = sent(bot)
        self.assertEqual((method.__api_method__, method.allow_queries, method.parse_mode), ('sendWidget', True, 'HTML'))
        self.assertEqual(json.loads(method.chat_data), state)
        self.assertEqual(method.caption, 'Баланс: 120 ₽ · хватит на 12 дн.')

    async def test_long_caption_is_refused_before_sending(self):
        bot = AsyncMock()
        with self.assertRaises(ValueError):
            await widgets.send_gift_widget(bot, 7, 1, caption='x' * 1025)
        bot.assert_not_awaited()

    async def test_referral_widget_carries_the_copy_text(self):
        bot = AsyncMock()
        with patch.object(widgets, 'referral_state', AsyncMock(return_value={'i': 0, 'c': 'link'})) as state:
            await widgets.send_referral_widget(bot, 7, caption='Пригласите')
        state.assert_awaited_once_with(7, with_link=True)
        self.assertEqual(json.loads(sent(bot).chat_data)['c'], 'link')


class ReminderAsWidgetTest(unittest.IsolatedAsyncioTestCase):
    async def send(self, widget_effect):
        from app import reminder_tracking
        bot = SimpleNamespace(send_photo=AsyncMock(return_value=SimpleNamespace(message_id=8)),
                              send_message=AsyncMock())
        with patch.object(reminder_tracking.db, 'create_reminder_delivery', AsyncMock(return_value=None)), \
                patch('app.widgets.send_balance_widget', AsyncMock(**widget_effect)) as widget:
            message = await reminder_tracking.send_reminder(bot, 7, 'Баланс на исходе', kind='low_balance',
                                                            title='t', reply_markup=None, preserve=True)
        return bot, widget, message

    async def test_low_balance_goes_out_as_widget(self):
        bot, widget, message = await self.send({'return_value': SimpleNamespace(message_id=5)})
        self.assertEqual(message.message_id, 5)
        self.assertEqual(widget.await_args.kwargs['caption'], 'Баланс на исходе')
        bot.send_photo.assert_not_called()

    async def test_widget_error_falls_back_to_banner(self):
        bot, _, message = await self.send({'side_effect': RuntimeError('INPUT_MEDIA_WIDGET_INVALID')})
        bot.send_photo.assert_awaited_once()
        self.assertEqual(message.message_id, 8)

    async def test_blocked_user_is_not_retried_with_banner(self):
        error = TelegramForbiddenError(method=SendMessage(chat_id=7, text='x'), message='blocked')
        with self.assertRaises(TelegramForbiddenError):
            await self.send({'side_effect': error})


class GiftBroadcastTest(unittest.IsolatedAsyncioTestCase):
    async def test_gift_falls_back_to_text_when_widget_fails(self):
        from app import admin
        bot = SimpleNamespace(send_message=AsyncMock(return_value='text'))
        with patch('app.widgets.send_gift_widget', AsyncMock(side_effect=RuntimeError)):
            self.assertEqual(await admin._send_gift(bot, 7, 3, 'Дарим', None), 'text')
        with patch('app.widgets.send_gift_widget', AsyncMock(return_value='widget')):
            self.assertEqual(await admin._send_gift(bot, 7, 3, 'Дарим', None), 'widget')


if __name__ == '__main__':
    unittest.main()
