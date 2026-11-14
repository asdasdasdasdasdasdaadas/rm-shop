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
