import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from aiohttp import web
from app import admin, db


class DeviceReissueTest(unittest.IsolatedAsyncioTestCase):
    async def run_request(self, *, missing=False, send_error=False, save_error=False):
        rw = SimpleNamespace(get_user_by_id=AsyncMock(return_value={'id': 7}),
                             revoke_subscription=AsyncMock(return_value={'id': 7, 'subscriptionUrl': 'https://vpn.test/new?a=1&b=2'}))
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=RuntimeError('delivery failed') if send_error else None))
        request = SimpleNamespace(match_info={'telegram_id': '123', 'device_id': '9'}, app={'rw': rw, 'bot': bot})
        with patch.object(admin, '_need_auth', return_value=None), \
             patch.object(db, 'get_device', AsyncMock(return_value=None if missing else {'id': 9, 'remnawave_id': 7, 'title': '<iPhone>'})) as get_device, \
             patch.object(db, 'save_device_subscription', AsyncMock(side_effect=RuntimeError('database unavailable') if save_error else None)) as save, \
             patch.object(db, 'log_bot_message', AsyncMock()) as log, \
             patch.object(admin, 'cabinet_keyboard', return_value=None):
            response = await admin.api_device_reissue(request)
        get_device.assert_awaited_once_with(123, 9)
        return response, rw, bot, save, log

    async def test_reissue_saves_new_link_sends_and_logs(self):
        response, rw, bot, save, log = await self.run_request()
        self.assertTrue(json.loads(response.body)['notified'])
        rw.revoke_subscription.assert_awaited_once_with({'id': 7})
        save.assert_awaited_once_with(7, {'id': 7, 'subscriptionUrl': 'https://vpn.test/new?a=1&b=2'})
        args, kwargs = bot.send_message.call_args
        self.assertEqual(args[0], 123)
        self.assertIn('&lt;iPhone&gt;', args[1])
        self.assertIn('https://vpn.test/new?a=1&amp;b=2', args[1])
        self.assertTrue(kwargs['link_preview_options'].is_disabled)
        self.assertEqual(log.call_args.kwargs['status'], 'sent')

    async def test_delivery_failure_does_not_report_rotation_failure(self):
        response, rw, bot, save, log = await self.run_request(send_error=True)
        data = json.loads(response.body)
        self.assertTrue(data['ok'])
        self.assertFalse(data['notified'])
        self.assertEqual(log.call_args.kwargs['status'], 'failed')
        rw.revoke_subscription.assert_awaited_once()
        save.assert_awaited_once()

    async def test_other_users_device_cannot_be_rotated(self):
        response, rw, bot, save, log = await self.run_request(missing=True)
        self.assertEqual(response.status, 404)
        rw.revoke_subscription.assert_not_awaited()
        bot.send_message.assert_not_awaited()

    async def test_requires_admin_auth(self):
        with patch.object(admin, '_need_auth', return_value=web.json_response({'ok': False}, status=401)), patch.object(db, 'get_device', AsyncMock()) as fetch:
            response = await admin.api_device_reissue(SimpleNamespace())
        self.assertEqual(response.status, 401)
        fetch.assert_not_awaited()

    async def test_save_failure_still_delivers_rotated_link(self):
        response, rw, bot, save, log = await self.run_request(save_error=True)
        data = json.loads(response.body)
        self.assertTrue(data['ok'])
        self.assertTrue(data['notified'])
        self.assertIn('не сохранена', data['warning'])
        bot.send_message.assert_awaited_once()
        rw.revoke_subscription.assert_awaited_once()

    async def test_large_traffic_parameters_explicitly_use_bigint(self):
        panel = {'id': 77, 'subscriptionUrl': 'https://vpn.test/new', 'lifetimeUsedTrafficBytes': 96003472116}
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value={'title': 'iPhone'}), execute=AsyncMock())
        with patch.object(db, '_pool_req', return_value=pool):
            await db.save_device_subscription(77, panel)
            await db.save_panel_snapshot(123, panel)
        sql, *args = pool.fetchrow.call_args.args
        self.assertEqual(args[6], 96003472116)
        self.assertIn('$7::bigint', sql)
        for call, parameter in zip(pool.execute.call_args_list, (9, 3)):
            sql, *args = call.args
            self.assertEqual(args[parameter - 1], 96003472116)
            self.assertIn(f'${parameter}::bigint', sql)
