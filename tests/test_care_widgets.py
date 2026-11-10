import json
import time
import unittest
import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import db, referrals, reminder_tracking, widgets, widgets_care as care, widgets_more as more


def settings(**kw):
    base = dict(brand_name='Лягушка <VPN>', vpn_day_price_rub=5, referral_program_enabled=True,
                referral_reward_rub=50, referral_invitee_reward_rub=50, bot_username='vpn_bot', admin_id_set={1})
    base.update(kw)
    return SimpleNamespace(**base)


def sent(bot):
    return bot.await_args.args[0]


class PagesTest(unittest.TestCase):
    def test_pages_fit_telegram_limits(self):
        with patch.object(widgets, 'get_settings', return_value=settings()):
            pages = [care.countdown_html(), care.key_html(), care.setup_html(), widgets.referral_html(), more.receipt_html()]
        for page in pages:
            with self.subTest(page=page[:60]):
                self.assertLessEqual(len(page.encode()), 32768)
                self.assertLessEqual(len(zlib.compress(page.encode(), 9)), 4096)
                self.assertNotIn('__', page)


class ReminderRoutingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for p in (patch.object(db, 'create_reminder_delivery', AsyncMock(return_value=None)),
                  patch.object(reminder_tracking, 'with_ton_button', side_effect=lambda m: m),
                  patch.object(widgets, 'get_settings', return_value=settings())):
            p.start()
            self.addCleanup(p.stop)

    async def test_balance_ending_is_a_countdown(self):
        bot = AsyncMock()
        with patch.object(care, 'countdown_state', AsyncMock(return_value={'b': 10, 'e': 1})):
            await reminder_tracking.send_reminder(bot, 5, 'Баланс заканчивается', kind='nudge_trial_end',
                                                  title='t', reply_markup=None, preserve=True)
        self.assertEqual(sent(bot).__api_method__, 'sendWidget')
        self.assertIn('id="tm"', sent(bot).html)
        bot.send_message.assert_not_awaited()

    async def test_setup_reminders_are_a_checklist_and_fall_back_to_text(self):
        bot = AsyncMock()
        with patch.object(care, 'setup_state', AsyncMock(return_value={'d': 1, 's': 0, 'c': 0})):
            await reminder_tracking.send_reminder(bot, 5, 'Следующий шаг', kind='first_device_thanks',
                                                  title='t', reply_markup=None, preserve=True)
        self.assertIn('подключение', sent(bot).html)
        bot = AsyncMock()
        bot.side_effect = RuntimeError('old client')
        with patch.object(care, 'setup_state', AsyncMock(return_value={})):
            await reminder_tracking.send_reminder(bot, 5, 'Добавьте устройство', kind='nudge_nodevice',
                                                  title='t', reply_markup=None, preserve=True)
        bot.send_message.assert_awaited_once()


class SetupStateTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        care._setup_cache.clear()

    async def test_panel_tells_when_the_link_was_opened(self):
        panel = {'subLastOpenedAt': '2026-11-10T10:00:00Z'}
        rw = SimpleNamespace(get_user_by_id=AsyncMock(return_value=panel))
        with patch.object(db, 'get_user', AsyncMock(return_value={})), \
                patch.object(db, 'list_devices', AsyncMock(return_value=[{'title': 'iPhone', 'remnawave_id': 7}])), \
                patch('app.runtime.rw', rw):
            state = await care.setup_state(5)
            self.assertEqual((state['d'], state['s'], state['c'], state['a']), (1, 1, 0, 'iPhone'))
            await care.setup_state(5)  # cached: the panel is asked once
        rw.get_user_by_id.assert_awaited_once_with(7)

    async def test_connected_user_needs_no_panel(self):
        with patch.object(db, 'get_user', AsyncMock(return_value={'first_online_at': 1})), \
                patch.object(db, 'list_devices', AsyncMock(return_value=[{'title': 'Mac', 'remnawave_id': 7}])), \
                patch('app.runtime.rw', None):
            self.assertEqual({k: v for k, v in (await care.setup_state(6)).items() if k in 'dsc'}, {'d': 1, 's': 1, 'c': 1})

    async def test_widget_query_o(self):
        with patch.object(care, 'setup_state', AsyncMock(return_value={'d': 0})) as state:
            self.assertEqual(await widgets.handle_query(None, {'from': {'id': 3}, 'data': 'o'}), {'d': 0})
        state.assert_awaited_once_with(3)


class NewKeyTest(unittest.IsolatedAsyncioTestCase):
    async def test_card_with_links_or_text(self):
        links = [('iPhone', 'https://sub.example/a'), ('', 'https://sub.example/b')]
        bot = AsyncMock()
        with patch.object(widgets, 'get_settings', return_value=settings()), \
                patch('app.keyboards.cabinet_keyboard', return_value=None):
            await care.notify_new_key(bot, 5, links)
            self.assertEqual(json.loads(sent(bot).chat_data)['l'], [['iPhone', 'https://sub.example/a'], ['', 'https://sub.example/b']])
            bot = AsyncMock(side_effect=RuntimeError('old client'))
            await care.notify_new_key(bot, 5, links)
        self.assertIn('https://sub.example/a', bot.send_message.await_args.args[1])


class ReferralRewardTest(unittest.IsolatedAsyncioTestCase):
    async def test_inviter_sees_the_friend_and_the_friend_gets_a_credit_card(self):
        result = {'referrer_id': 10, 'invitee_id': 20, 'amount': 50, 'friend_name': 'Аня'}
        friends, credit = AsyncMock(), AsyncMock()
        with patch.object(referrals, 'get_settings', return_value=settings()), \
                patch.object(db, 'reward_referral_menu', AsyncMock(return_value=result)), \
                patch.object(referrals, 'with_referral_share', side_effect=lambda chat, kb: kb), \
                patch.object(referrals, 'cabinet_keyboard', return_value=None), \
                patch('app.funnel_ui.funnel_keyboard', side_effect=lambda m: m), \
                patch.object(widgets, 'send_referral_widget', friends), \
                patch.object(more, 'send_admin_credit_widget', credit), \
                patch.object(referrals, 'send_funnel_message', AsyncMock()) as text:
            self.assertEqual(await referrals.maybe_reward_menu(SimpleNamespace(), 20), 50)
        self.assertEqual(friends.await_args.args[1], 10)
        self.assertEqual(friends.await_args.kwargs['reward'], {'a': 50, 'n': 'Аня', 'k': 'menu'})
        self.assertEqual((credit.await_args.args[1], credit.await_args.args[2], credit.await_args.kwargs['source']), (20, 50, 'ref'))
        text.assert_not_awaited()

    async def test_credit_card_says_by_invitation(self):
        self.assertIn("ref:'по приглашению'", more.RECEIPT_HTML)
        self.assertIn("J.k=='pay'", widgets.REFERRAL_HTML)


class CabinetReissueTest(unittest.IsolatedAsyncioTestCase):
    async def test_new_link_goes_to_the_chat_too(self):
        from app import web
        request = SimpleNamespace(app={'bot': object()})
        with patch.object(care, 'notify_new_key', AsyncMock()) as notify:
            web._key_to_chat(request, 5, [('iPhone', 'https://sub.example/a')])
            web._key_to_chat(request, 5, [('iPhone', '')])  # nothing to show
            import asyncio
            await asyncio.sleep(0)
        notify.assert_awaited_once_with(request.app['bot'], 5, [('iPhone', 'https://sub.example/a')])


if __name__ == '__main__':
    unittest.main()
