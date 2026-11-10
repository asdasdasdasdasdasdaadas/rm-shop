import hashlib
import hmac
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import cispay, web as webapp
from app.config import Settings

KEY = 'cis_sec_test'


def settings(**kw):
    base = dict(cispay_shop_id='0190-shop', cispay_api_key=KEY, cispay_methods='sbp,crypto', cispay_test=False,
                cispay_api_url='https://api.cispay.app', rollypay_api_key='', webapp_public_url='https://vpn.test')
    base.update(kw)
    return Settings(_env_file=None, bot_token='1:x', required_channel_id='-1', required_channel_url='https://t.me/x',
                    remnawave_base_url='https://panel.test', remnawave_token='t', legal_offer_url='https://o.test',
                    legal_privacy_url='https://p.test', **base)


def signed(event):
    body = json.dumps(event, separators=(',', ':')).encode()
    return body, hmac.new(KEY.encode(), body, hashlib.sha256).hexdigest()


class HelpersTest(unittest.TestCase):
    def test_signature(self):
        body, sig = signed({'status': 'PAID'})
        self.assertTrue(cispay.verify_webhook(body, sig, KEY))
        self.assertTrue(cispay.verify_webhook(body, sig.upper(), KEY))
        self.assertFalse(cispay.verify_webhook(body + b' ', sig, KEY))
        self.assertFalse(cispay.verify_webhook(body, sig, 'other'))
        self.assertFalse(cispay.verify_webhook(body, '', KEY))

    def test_amount_in_kopecks(self):
        self.assertEqual(cispay.kopecks('150'), 15000)
        self.assertEqual(cispay.kopecks('150,49'), 15049)
        with self.assertRaises(ValueError):
            cispay.kopecks('0')

    def test_status_reads_like_the_rest_of_the_shop(self):
        from app.rollypay import payment_is_paid
        paid = cispay.normalize({'id': 'abc', 'status': 'PAID', 'payment_url': 'https://pay'})
        self.assertTrue(payment_is_paid(paid))
        self.assertEqual((paid['payment_id'], paid['pay_url']), ('cis:abc', 'https://pay'))
        self.assertEqual(cispay.normalize({'status': 'EXPIRED'})['status'], 'expired')

    def test_settings_decide_which_methods_go_to_cispay(self):
        s = settings()
        self.assertEqual(s.cispay_method_set, {'sbp', 'crypto'})
        self.assertTrue(s.rub_method_ready('sbp') and s.rub_method_ready('crypto'))
        self.assertFalse(s.rub_method_ready('card'))
        self.assertTrue(settings(rollypay_api_key='rpk_live_x').rub_method_ready('card'))
        self.assertEqual(settings(cispay_api_key='').cispay_method_set, set())


class ClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_sends_kopecks_method_and_customer(self):
        with patch.object(cispay, 'get_settings', return_value=settings()):
            client = cispay.CISPayClient()
            client._request = AsyncMock(return_value={'id': 'u1', 'status': 'PENDING', 'payment_url': 'https://pay/u1'})
            data = await client.create_payment(amount_rub='300', order_id='o1', description='VPN', customer_id='77',
                                               metadata={'plan': 'm300'}, payment_method='crypto')
        method, path = client._request.await_args.args
        body = client._request.await_args.kwargs['json']
        self.assertEqual((method, path), ('POST', '/payments'))
        self.assertEqual((body['amount'], body['currency'], body['payment_method'], body['customer_id']),
                         (30000, 'RUB', 'CRYPTO', '77'))
        self.assertEqual(body['redirect_success_url'], 'https://vpn.test')
        self.assertEqual((data['payment_id'], data['pay_url'], data['status']), ('cis:u1', 'https://pay/u1', 'pending'))

    async def test_status_strips_the_prefix(self):
        with patch.object(cispay, 'get_settings', return_value=settings()):
            client = cispay.CISPayClient()
        client._request = AsyncMock(return_value={'id': 'u1', 'status': 'PAID'})
        self.assertEqual((await client.get_payment('cis:u1'))['status'], 'paid')
        self.assertEqual(client._request.await_args.kwargs['params'], {'id': 'u1'})


class RouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_routes_by_method_and_by_stored_id(self):
        rolly = SimpleNamespace(create_payment=AsyncMock(return_value={'r': 1}), get_payment=AsyncMock(return_value={'r': 2}))
        cis = SimpleNamespace(create_payment=AsyncMock(return_value={'c': 1}), get_payment=AsyncMock(return_value={'c': 2}))
        router = cispay.PaymentRouter(rolly, cis)
        with patch.object(cispay, 'get_settings', return_value=settings()):
            self.assertEqual(await router.create_payment(payment_method='sbp', order_id='a'), {'c': 1})
            self.assertEqual(await router.create_payment(payment_method='crypto', order_id='b'), {'c': 1})
            self.assertEqual(await router.create_payment(payment_method='card', order_id='c'), {'r': 1})
        self.assertEqual(await router.get_payment('cis:x'), {'c': 2})
        self.assertEqual(await router.get_payment('rp-123'), {'r': 2})

    async def test_unconfigured_method_is_an_error_the_checkout_catches(self):
        from app.rollypay import RollyPayError
        router = cispay.PaymentRouter(None, SimpleNamespace())
        with patch.object(cispay, 'get_settings', return_value=settings()):
            with self.assertRaises(RollyPayError):
                await router.create_payment(payment_method='card', order_id='c')


class WebhookTest(unittest.IsolatedAsyncioTestCase):
    def request(self, event, sig=None):
        body, good = signed(event)
        async def read():
            return body
        return SimpleNamespace(read=read, headers={'X-Signature': good if sig is None else sig},
                               app={'rw': object(), 'bot': object()})

    async def call(self, req, order, **kw):
        with patch.object(webapp, 'get_settings', return_value=settings(**kw)), \
                patch.object(webapp.db, 'get_rollypay_order', AsyncMock(return_value=order)), \
                patch.object(webapp.db, 'get_rollypay_order_by_payment', AsyncMock(return_value=None)), \
                patch.object(webapp, 'fulfill_rollypay_order', AsyncMock()) as fulfill:
            resp = await webapp.cispay_webhook(req)
        return resp, fulfill

    ORDER = {'order_id': 'o1', 'payment_id': 'cis:u1', 'status': 'created'}

    async def test_paid_credits_the_order(self):
        resp, fulfill = await self.call(self.request({'id': 'u1', 'order_id': 'o1', 'status': 'PAID'}), self.ORDER)
        self.assertEqual(resp.status, 200)
        fulfill.assert_awaited_once()
        self.assertEqual(fulfill.await_args.args[0], 'o1')

    async def test_bad_signature_is_refused(self):
        resp, fulfill = await self.call(self.request({'order_id': 'o1', 'status': 'PAID'}, sig='00'), self.ORDER)
        self.assertEqual(resp.status, 403)
        fulfill.assert_not_awaited()

    async def test_nothing_to_do_without_payment(self):
        for event in ({'order_id': 'o1', 'status': 'PENDING'}, {'event': 'subscription.cancelled', 'status': 'PAID'},
                      {'order_id': 'o1', 'status': 'PAID', 'is_sandbox': True}):
            resp, fulfill = await self.call(self.request(event), self.ORDER)
            self.assertEqual(resp.status, 200)
            fulfill.assert_not_awaited()

    async def test_sandbox_counts_in_test_mode(self):
        _, fulfill = await self.call(self.request({'order_id': 'o1', 'status': 'PAID', 'is_sandbox': True}),
                                     self.ORDER, cispay_test=True)
        fulfill.assert_awaited_once()

    async def test_rollypay_or_paid_orders_are_left_alone(self):
        for order in ({'order_id': 'o1', 'payment_id': 'rp-1', 'status': 'created'},
                      dict(self.ORDER, status='granted'), None):
            _, fulfill = await self.call(self.request({'order_id': 'o1', 'status': 'PAID'}), order)
            fulfill.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
