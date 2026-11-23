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

    def get(self, url, params=None):
        self.calls.append((url, params))
        return self.answers[(url, params.get("id"))]


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
        self.assertIsNone(await store_check.check(http, GH))

    async def test_failed_answer_keeps_the_last_known(self):
        known = {PLAY: {"ok": False, "at": "2026-11-01T00:00:00+00:00"}}
        http = _Http({("https://itunes.apple.com/lookup", "6504287215"): _Resp(200, '{"resultCount":1}'),
                      ("https://itunes.apple.com/lookup", "6472431552"): _Resp(503),
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


if __name__ == "__main__":
    unittest.main()
