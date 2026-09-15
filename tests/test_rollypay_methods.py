"""Provider routing regression tests without credentials or network calls."""
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class RollyPayMethodsTest(unittest.TestCase):
    def setUp(self):
        config = ModuleType('app.config')
        config.get_settings = lambda: SimpleNamespace(webapp_public_url='', rollypay_test=False)
        sdk = ModuleType('rollypay')
        sdk.RollyPayClient = Mock
        errors = ModuleType('rollypay.exceptions')
        errors.RollyPayError = Exception
        spec = importlib.util.spec_from_file_location('provider_under_test', Path(__file__).parents[1] / 'app/rollypay.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'app.config': config, 'rollypay': sdk, 'rollypay.exceptions': errors}):
            spec.loader.exec_module(self.module)
        self.client = self.module.RollyPayClient.__new__(self.module.RollyPayClient)
        self.client._sdk = Mock()
        self.client._sdk.payments.create.return_value = {'payment_id': 'test', 'pay_url': 'https://pay.rollypay.io/pay/test'}
        self.client._live_key = True

    def create(self, method):
        return asyncio.run(self.client.create_payment(amount_rub='100.00', order_id='test', description='Test', customer_id='1', payment_method=method))

    def test_card_is_sent_as_card(self):
        result = self.create('card')
        args = self.client._sdk.payments.create.call_args.kwargs
        self.assertEqual(args['payment_method'], 'card')
        self.assertEqual(args['payment_currency'], 'RUB')
        self.assertEqual(result['pay_url'], 'https://pay.rollypay.io/pay/test')

    def test_crypto_sent_with_ruble_amount(self):
        self.create('crypto')
        args = self.client._sdk.payments.create.call_args.kwargs
        self.assertEqual(args['payment_method'], 'crypto')
        self.assertEqual(args['payment_currency'], 'RUB')
        self.assertEqual(args['amount'], '100.00')

    def test_sbp_is_preserved(self):
        self.create('sbp')
        self.assertEqual(self.client._sdk.payments.create.call_args.kwargs['payment_method'], 'sbp')

    def test_invalid_method_never_falls_back_to_sbp(self):
        for method in ('unknown', 'stars'):
            with self.assertRaises(ValueError):
                self.create(method)
        self.client._sdk.payments.create.assert_not_called()
