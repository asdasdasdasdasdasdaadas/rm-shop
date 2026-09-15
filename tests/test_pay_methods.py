"""Payment menu contract tests; no database or provider requests."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class PaymentMethodsTest(unittest.TestCase):
    def setUp(self):
        self.overlay = {}
        config = ModuleType('app.config')
        config.get_settings = lambda: SimpleNamespace(rollypay_configured=True)
        config.shop_overlay = lambda: self.overlay
        spec = importlib.util.spec_from_file_location(
            'payment_menu_under_test', Path(__file__).parents[1] / 'app/pay_methods.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'app.config': config}):
            spec.loader.exec_module(self.module)

    def test_order_and_enabled_methods(self):
        self.overlay['pay_methods'] = [
            {'id': 'stars', 'enabled': True, 'title': 'Звёзды'},
            {'id': 'card', 'enabled': False},
            {'id': 'sbp', 'enabled': True},
        ]
        methods = self.module.public_pay_methods()
        self.assertEqual([m['id'] for m in methods], ['stars', 'sbp'])
        self.assertEqual(methods[0]['title'], 'Звёзды')

    def test_all_disabled(self):
        self.overlay['pay_methods'] = [
            {'id': key, 'enabled': False} for key in ('stars', 'card', 'sbp')]
        self.assertEqual(self.module.public_pay_methods(), [])

    def test_unconfigured_provider_hidden(self):
        self.module.get_settings = lambda: SimpleNamespace(rollypay_configured=False)
        self.overlay['pay_methods'] = [
            {'id': key, 'enabled': True} for key in ('card', 'stars', 'sbp')]
        self.assertEqual([m['id'] for m in self.module.public_pay_methods()], ['stars'])

    def test_duplicates_and_unknown_methods_not_exposed(self):
        result = self.module.validate_pay_methods([
            {'id': 'stars', 'enabled': True}, {'id': 'stars', 'enabled': True},
            {'id': 'unknown', 'enabled': True}])
        self.assertEqual([m['id'] for m in result], ['stars', 'sbp', 'card'])


if __name__ == '__main__':
    unittest.main()
