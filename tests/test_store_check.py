"""Store availability: apps removed from the Russian App Store or from Google Play are not recommended on /connect."""
import json
import unittest
from unittest.mock import AsyncMock, patch

from app import db, store_check

IOS = "https://apps.apple.com/app/id6504287215"
PLAY = "https://play.google.com/store/apps/details?id=com.happproxy"
GH = "https://github.com/Happ-proxy/happ-desktop/releases"
APPS = [{"id": "happ", "stores": {"ios": IOS, "macos": IOS, "android": PLAY, "windows": GH}},
        {"id": "karing", "stores": {"ios": "https://apps.apple.com/app/id6472431552"}}]


class _Resp:
    def __init__(self, status, body=""):
        self.status, self.body = status, body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def text(self):
        return self.body


class _Http:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def get(self, url, params=None, headers=None, allow_redirects=True):
        self.calls.append((url, params, headers))
        return self.answers[(url, (params or {}).get("id"))]


class StoreCheckTest(unittest.IsolatedAsyncioTestCase):
    def test_parse_only_the_two_stores(self):
        self.assertEqual(store_check.parse(IOS), ("appstore", "6504287215"))
        self.assertEqual(store_check.parse("https://apps.apple.com/app/rabbithole-vpn-client/id6683309629"), ("appstore", "6683309629"))
        self.assertEqual(store_check.parse(PLAY), ("play", "com.happproxy"))
        self.assertIsNone(store_check.parse(GH))

    async def test_russian_storefront_and_play_404(self):
        http = _Http({("https://itunes.apple.com/lookup", "6504287215"): _Resp(200, '{"resultCount":0,"results":[]}'),
                      ("https://itunes.apple.com/lookup", "6472431552"): _Resp(200, '{"resultCount":1,"results":[{}]}'),
                      ("https://play.google.com/store/apps/details", "com.happproxy"): _Resp(404)})
        self.assertIs(await store_check.check(http, IOS), False)
        self.assertEqual(http.calls[0][1]["country"], "ru")
        self.assertIs(await store_check.check(http, "https://apps.apple.com/app/id6472431552"), True)
        self.assertIs(await store_check.check(http, PLAY), False)
        self.assertIsNone(await store_check.check(http, "ftp://x.example/a"))

    async def test_other_links_are_asked_for_one_byte(self):
        apk = "https://github.com/x/y/releases/latest/download/A.apk"
        http = _Http({(apk, None): _Resp(206), (GH, None): _Resp(404), ("https://x.example/", None): _Resp(503)})
        self.assertIs(await store_check.check(http, apk), True)
        self.assertEqual(http.calls[0][2], {"Range": "bytes=0-0"})
        self.assertIs(await store_check.check(http, GH), False)
        self.assertIsNone(await store_check.check(http, "https://x.example/"))

    async def test_failed_answer_keeps_the_last_known(self):
        known = {PLAY: {"ok": False, "at": "2026-11-01T00:00:00+00:00"}}
        http = _Http({("https://itunes.apple.com/lookup", "6504287215"): _Resp(200, '{"resultCount":1}'),
                      ("https://itunes.apple.com/lookup", "6472431552"): _Resp(503), (GH, None): _Resp(200),
                      ("https://play.google.com/store/apps/details", "com.happproxy"): _Resp(500)})
        with patch.object(db, "get_kv", AsyncMock(return_value=json.dumps(known))), \
             patch.object(db, "set_kv", AsyncMock()) as save, patch("app.vpn_apps.public_vpn_apps", return_value=APPS):
            out = await store_check.refresh(http)
        self.assertEqual(out[PLAY], known[PLAY])
        self.assertTrue(out[IOS]["ok"])
        self.assertNotIn("https://apps.apple.com/app/id6472431552", out)
        self.assertEqual(json.loads(save.await_args.args[1]), out)

    def test_mark_lists_platforms_with_a_dead_link(self):
        got = store_check.mark(APPS, {IOS: {"ok": False}, PLAY: {"ok": True}})
        self.assertEqual(got[0]["unavailable"], ["ios", "macos"])
        self.assertNotIn("unavailable", got[1])
        self.assertNotIn("unavailable", APPS[0])

    def test_mark_drops_a_dead_direct_link(self):
        apk = "https://github.com/x/y/A.apk"
        got = store_check.mark([{"id": "a", "stores": {}, "direct": {"android": apk}}], {apk: {"ok": False}})
        self.assertEqual(got[0]["direct"], {})


class SavedLinksTest(unittest.TestCase):
    def test_saved_list_gets_happ_tv_and_incy_android_but_keeps_own_links(self):
        from app import vpn_apps
        saved = [{"id": "happ", "name": "Happ", "platforms": ["ios", "appletv"], "stores": {"ios": vpn_apps.HAPP_APPLE, "appletv": vpn_apps.HAPP_APPLE}},
                 {"id": "incy", "name": "Incy", "platforms": ["ios"], "stores": {"ios": "https://example.com/my-incy"}}]
        self.assertTrue(vpn_apps.fix_saved_links(saved))
        self.assertEqual(saved[0]["stores"], {"ios": vpn_apps.HAPP_APPLE, "appletv": vpn_apps.HAPP_TV})
        self.assertEqual(saved[1]["stores"]["ios"], "https://example.com/my-incy")
        self.assertEqual(saved[1]["stores"]["android"], vpn_apps.INCY_PLAY)
        self.assertEqual(saved[1]["direct"], {"android": vpn_apps.INCY_APK})
        self.assertEqual(vpn_apps.validate_vpn_apps(saved)[1]["platforms"], ["ios", "android", "androidtv"])
        self.assertFalse(vpn_apps.fix_saved_links(saved))


if __name__ == "__main__":
    unittest.main()
