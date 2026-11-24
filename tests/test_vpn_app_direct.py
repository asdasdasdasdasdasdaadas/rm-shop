"""Happ for Android: the APK straight from GitHub besides Google Play, kept for lists saved before it existed."""
import unittest

from app.vpn_apps import DEFAULT_VPN_APPS, validate_vpn_apps

APK = "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk"


class DirectDownloadTest(unittest.TestCase):
    def test_happ_android_has_the_apk(self):
        happ = next(a for a in validate_vpn_apps(None) if a["id"] == "happ")
        self.assertEqual(happ["direct"], {"android": APK})
        self.assertNotIn("direct", next(a for a in validate_vpn_apps(None) if a["id"] == "rabbithole"))

    def test_saved_list_without_direct_keeps_the_built_in_link(self):
        saved = [{k: v for k, v in a.items() if k != "direct"} for a in DEFAULT_VPN_APPS]
        happ = next(a for a in validate_vpn_apps(saved) if a["id"] == "happ")
        self.assertEqual(happ["direct"], {"android": APK})

    def test_direct_only_for_the_app_platforms_and_web_links(self):
        base = {"id": "own", "name": "Own", "platforms": ["android"], "stores": {}}
        got = validate_vpn_apps([{**base, "direct": {"android": "https://x.example/a.apk", "ios": "https://x.example/b"}}])[0]
        self.assertEqual(got["direct"], {"android": "https://x.example/a.apk"})
        with self.assertRaises(ValueError):
            validate_vpn_apps([{**base, "direct": {"android": "javascript:alert(1)"}}])


if __name__ == "__main__":
    unittest.main()
