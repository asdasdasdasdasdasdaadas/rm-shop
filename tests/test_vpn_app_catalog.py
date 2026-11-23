"""Default VPN apps: Karing and RabbitHole are in the catalog with the import links from their docs."""
import unittest

from app.vpn_apps import DEFAULT_VPN_APPS, validate_vpn_apps


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.apps = {a["id"]: a for a in validate_vpn_apps(DEFAULT_VPN_APPS)}

    def test_karing_without_android_with_encoded_import(self):
        a = self.apps["karing"]
        self.assertEqual(a["deep_link"], "karing://install-config?url={enc}")
        self.assertEqual(set(a["platforms"]), {"ios", "macos", "appletv", "windows"})
        self.assertNotIn("play.google.com", " ".join(a["stores"].values()))  # Karing is not on Google Play
        self.assertIn("apps.apple.com", a["stores"]["macos"])  # Mac App Store, same listing as iPhone

    def test_rabbithole_on_apple_devices(self):
        a = self.apps["rabbithole"]
        self.assertEqual(a["deep_link"], "rabbithole://add/{url}")
        self.assertEqual(a["platforms"], ["ios", "macos", "appletv"])
        self.assertTrue(all("id6683309629" in url for url in a["stores"].values()))

    def test_icons_are_local_and_fill_in_for_saved_lists(self):
        self.assertEqual(self.apps["karing"]["icon"], "/icons/karing.png")
        self.assertEqual(self.apps["rabbithole"]["icon"], "/icons/rabbithole.png")
        saved = [{"id": "rabbithole", "name": "RabbitHole", "icon": "", "platforms": ["ios"]}]  # a list saved in the admin
        self.assertEqual(validate_vpn_apps(saved)[0]["icon"], "/icons/rabbithole.png")

    def test_happ_stays_recommended_first(self):
        self.assertEqual([a["id"] for a in validate_vpn_apps(DEFAULT_VPN_APPS)][:2], ["incy", "happ"])


if __name__ == "__main__":
    unittest.main()


class SavedList(unittest.TestCase):
    """Built-in apps are always in the list, whatever an old admin tab saved; the admin hides them instead."""

    def _ids(self, overlay, admin=False):
        from unittest.mock import patch
        from app import vpn_apps
        with patch.object(vpn_apps, "shop_overlay", lambda: overlay):
            return [a["id"] for a in (vpn_apps.admin_vpn_apps() if admin else vpn_apps.public_vpn_apps())]

    def test_saved_without_karing_still_has_it(self):
        old = [{"id": "rabbithole", "name": "RabbitHole", "platforms": ["ios", "macos"]},
               {"id": "incy", "name": "Incy", "platforms": ["ios"]}]
        ids = self._ids({"vpn_apps": old})
        self.assertEqual(ids[:2], ["rabbithole", "incy"])
        self.assertEqual(set(ids), {"rabbithole", "incy", "happ", "karing", "v2rayng", "v2rayn"})

    def test_hidden_only_leaves_the_cabinet(self):
        saved = [{"id": "karing", "name": "Karing", "platforms": ["macos"], "hidden": True},
                 {"id": "own", "name": "Своё", "platforms": ["ios"]}]
        self.assertNotIn("karing", self._ids({"vpn_apps": saved}))
        self.assertIn("own", self._ids({"vpn_apps": saved}))
        self.assertEqual(self._ids({"vpn_apps": saved}, admin=True)[:2], ["karing", "own"])


class KaringStoresOnce(unittest.IsolatedAsyncioTestCase):
    """A saved Karing gets the Mac App Store link and loses Android once at start."""

    async def test_fixed_once(self):
        import json
        from unittest.mock import AsyncMock, patch
        from app import shop_config, vpn_apps
        kv = {"shop_settings": json.dumps({"max_devices": 5, "balance_topup_max": 100000,
              "vpn_apps": [{"id": "karing", "name": "Karing", "platforms": ["macos", "android"],
                            "stores": {"macos": "https://github.com/KaringX/karing/releases/latest",
                                       "android": "https://github.com/KaringX/karing/releases/latest"}}]}),
              "router_offer_hidden_v1": "1", "device_limit_5_v1": "1"}

        async def get_kv(k):
            return kv.get(k, "")

        async def set_kv(k, v):
            kv[k] = v
        with patch.object(shop_config.db, "get_kv", get_kv), patch.object(shop_config.db, "set_kv", set_kv), \
                patch.object(shop_config.db, "migrate_legacy_promo_codes", AsyncMock()), \
                patch("app.frog_test.stop", AsyncMock()):
            await shop_config.load_shop_overlay()
            karing = vpn_apps.public_vpn_apps()[0]
            self.assertEqual(karing["id"], "karing")
            self.assertEqual((karing["platforms"], karing["stores"]["macos"]), (["macos"], "https://apps.apple.com/app/id6472431552"))
