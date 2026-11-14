"""Admin sign-in: password guessing is slowed down per address, «Выйти» ends every session."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin

SETTINGS = SimpleNamespace(admin_password='right-pass', bot_token='1:x', brand_name='VPN',
                           webapp_public_url='https://vpn.test')


def request(password, ip='203.0.113.5', cookie=None, remote='127.0.0.1'):
    async def json():
        return {'password': password}
    return SimpleNamespace(json=json, remote=remote, headers={'X-Forwarded-For': f'1.1.1.1, {ip}'},
                           cookies={admin.COOKIE: cookie} if cookie else {})


class LoginGuardTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for p in (patch.object(admin, 'get_settings', return_value=SETTINGS),
                  patch.object(admin.asyncio, 'sleep', AsyncMock()),
                  patch.object(admin, '_sessions_from', 0)):
            p.start()
            self.addCleanup(p.stop)
        admin._login_fails.clear()

    async def test_wrong_passwords_lock_only_that_address(self):
        for _ in range(admin.LOGIN_TRIES):
            self.assertEqual((await admin.api_login(request('nope'))).status, 403)
        locked = await admin.api_login(request('right-pass'))
        self.assertEqual(locked.status, 429)
        self.assertIn('Retry-After', locked.headers)
        self.assertEqual((await admin.api_login(request('right-pass', ip='198.51.100.7'))).status, 200)

    async def test_forged_first_hop_does_not_change_the_address(self):
        for i in range(admin.LOGIN_TRIES):
            req = request('nope')
            req.headers['X-Forwarded-For'] = f'10.0.0.{i}, 203.0.113.5'
            await admin.api_login(req)
        self.assertEqual((await admin.api_login(request('right-pass'))).status, 429)

    async def test_direct_caller_cannot_pick_an_address(self):
        req = request('nope', remote='8.8.8.8')
        self.assertEqual(admin._login_ip(req), '8.8.8.8')

    async def test_success_clears_the_count(self):
        for _ in range(admin.LOGIN_TRIES - 1):
            await admin.api_login(request('nope'))
        self.assertEqual((await admin.api_login(request('right-pass'))).status, 200)
        self.assertEqual((await admin.api_login(request('nope'))).status, 403)

    async def test_logout_ends_every_session(self):
        old = admin._make_token()
        self.assertTrue(admin._token_ok(old))
        with patch.object(admin.db, 'set_kv', AsyncMock()) as save:
            await admin.api_logout(request('', cookie=old))
        save.assert_awaited_once()
        self.assertFalse(admin._token_ok(old))
        # Signing in again right away works.
        self.assertTrue(admin._token_ok(admin._make_token()))

    async def test_logout_without_session_changes_nothing(self):
        with patch.object(admin.db, 'set_kv', AsyncMock()) as save:
            await admin.api_logout(request(''))
        save.assert_not_awaited()


class BodyLimitTest(unittest.IsolatedAsyncioTestCase):
    async def test_limits_by_route(self):
        from aiohttp.test_utils import TestClient, TestServer
        from aiohttp import web
        from app import web as webapp

        async def echo(req):
            return web.Response(text=str(len(await req.read())))
        app = web.Application(client_max_size=webapp.BODY_LIMIT_ADMIN, middlewares=[webapp.body_limit_middleware])
        app.router.add_post('/api/x', echo)
        app.router.add_post('/api/tickets', echo)
        app.router.add_post('/admin/api/x', echo)
        client = TestClient(TestServer(app))
        await client.start_server()
        self.addAsyncCleanup(client.close)
        big = b'x' * (2 * 1024 * 1024)
        self.assertEqual((await client.post('/api/x', data=b'x' * 10)).status, 200)
        self.assertEqual((await client.post('/api/x', data=big)).status, 413)
        self.assertEqual((await client.post('/api/tickets', data=big)).status, 200)
        self.assertEqual((await client.post('/admin/api/x', data=big)).status, 413)
        with patch.object(admin, 'get_settings', return_value=SETTINGS):
            cookie = admin._make_token()
            resp = await client.post('/admin/api/x', data=big, cookies={admin.COOKIE: cookie})
        self.assertEqual(resp.status, 200)
