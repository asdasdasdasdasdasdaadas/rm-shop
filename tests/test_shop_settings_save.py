import unittest

from app import shop_config
from app.config import SHOP_KEYS


class ShopSettingsSaveTest(unittest.TestCase):
    def test_saving_the_current_settings_with_a_new_name_works(self):
        values = dict(shop_config.snapshot()["values"])
        values["brand_name"] = "Лягушка VPN"
        out = shop_config.validate_shop(values)
        self.assertEqual(out["brand_name"], "Лягушка VPN")
        self.assertEqual(set(out), set(SHOP_KEYS))
