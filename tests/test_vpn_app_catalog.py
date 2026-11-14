"""Default VPN apps: Karing and RabbitHole are in the catalog with the import links from their docs."""
import unittest

from app.vpn_apps import DEFAULT_VPN_APPS, validate_vpn_apps


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.apps = {a["id"]: a for a in validate_vpn_apps(DEFAULT_VPN_APPS)}

    def test_karing_everywhere_with_encoded_import(self):
        a = self.apps["karing"]
        self.assertEqual(a["deep_link"], "karing://install-config?url={enc}")
        self.assertEqual(set(a["platforms"]), {"ios", "macos", "appletv", "android", "androidtv", "windows"})
        self.assertNotIn("play.google.com", " ".join(a["stores"].values()))  # Karing is not on Google Play

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


class OldSavedList(unittest.TestCase):
    """A list saved in the admin before Karing and RabbitHole existed still shows them; a removed app stays removed."""

    def _public(self, overlay):
        from unittest.mock import patch
        from app import vpn_apps
        with patch.object(vpn_apps, "shop_overlay", lambda: overlay):
            return [a["id"] for a in vpn_apps.public_vpn_apps()]

    def test_old_list_gets_new_apps(self):
        old = [{"id": "happ", "name": "Happ", "platforms": ["ios"]}, {"id": "incy", "name": "Incy", "platforms": ["ios"]}]
        ids = self._public({"vpn_apps": old})
        self.assertEqual(ids[:2], ["happ", "incy"])
        self.assertIn("karing", ids)
        self.assertIn("rabbithole", ids)
        self.assertNotIn("v2rayng", ids)  # was there when the list was saved, so the admin removed it

    def test_removed_after_save_stays_removed(self):
        from app.vpn_apps import default_ids
        saved = [{"id": "happ", "name": "Happ", "platforms": ["ios"]}]
        self.assertEqual(self._public({"vpn_apps": saved, "vpn_apps_seen": default_ids()}), ["happ"])


class RestoreOnce(unittest.IsolatedAsyncioTestCase):
    """A save from a stale admin tab marked Karing and RabbitHole as removed: they come back once at start."""

    async def test_restored_once(self):
        import json
        from unittest.mock import AsyncMock, patch
        from app import shop_config, vpn_apps
        kv = {"shop_settings": json.dumps({"max_devices": 5, "balance_topup_max": 100000,
              "vpn_apps": [{"id": "rabbithole", "name": "RabbitHole", "platforms": ["ios", "macos"]},
                           {"id": "incy", "name": "Incy", "platforms": ["ios", "macos"]}],
              "vpn_apps_seen": vpn_apps.default_ids()}),
              "router_offer_hidden_v1": "1", "device_limit_5_v1": "1"}

        async def get_kv(k):
            return kv.get(k, "")

        async def set_kv(k, v):
            kv[k] = v
        with patch.object(shop_config.db, "get_kv", get_kv), patch.object(shop_config.db, "set_kv", set_kv), \
                patch.object(shop_config.db, "migrate_legacy_promo_codes", AsyncMock()):
            await shop_config.load_shop_overlay()
            ids = [a["id"] for a in vpn_apps.public_vpn_apps()]
            self.assertEqual(ids, ["rabbithole", "incy", "karing"])
            # Removed again in the admin after that: stays removed on the next start.
            data = json.loads(kv["shop_settings"])
            data["vpn_apps_seen"] = vpn_apps.default_ids()
            kv["shop_settings"] = json.dumps(data)
            await shop_config.load_shop_overlay()
            self.assertNotIn("karing", [a["id"] for a in vpn_apps.public_vpn_apps()])
