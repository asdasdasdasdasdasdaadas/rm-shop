"""Telegram Ads statistics: ads are read from promoteapi.telegram.org and tied to our ad links by start=ad_<slug>."""
import asyncio
import json
import os
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app import db, tg_ads


class SlugTest(unittest.TestCase):
    def test_slug_from_url(self):
        self.assertEqual(tg_ads.slug_from_url("https://t.me/WayVpnBot?start=ad_tech_news"), "tech_news")
        self.assertEqual(tg_ads.slug_from_url("t.me/WayVpnBot?start=ad_TECH"), "tech")
        self.assertIsNone(tg_ads.slug_from_url("https://t.me/WayVpnBot?start=ref_123"))
        self.assertIsNone(tg_ads.slug_from_url("https://t.me/somechannel"))
        self.assertIsNone(tg_ads.slug_from_url("https://t.me/WayVpnBot?start=ad_a"))
        self.assertIsNone(tg_ads.slug_from_url("https://t.me/WayVpnBot?start=ad_bad-slug"))
        self.assertIsNone(tg_ads.slug_from_url(None))


def _settings(token="tok", rate=0):
    return SimpleNamespace(tg_ads_token=token, tg_ads_rub_rate=rate)


class SettingsTest(unittest.TestCase):
    def test_token_is_saved_from_the_admin(self):
        from app.config import SHOP_KEYS
        from app.shop_config import validate_shop
        self.assertIn("tg_ads_token", SHOP_KEYS)
        self.assertIn("tg_ads_rub_rate", SHOP_KEYS)
        from app.shop_config import snapshot
        body = {**snapshot()["values"], "tg_ads_token": "  abc:DEF  ", "tg_ads_rub_rate": 95}
        out = validate_shop(body)
        self.assertEqual((out["tg_ads_token"], out["tg_ads_rub_rate"]), ("abc:DEF", 95))


class SyncTest(unittest.IsolatedAsyncioTestCase):
    def _client(self, handler):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_reads_every_page_and_stores(self):
        calls = []

        def handler(request: httpx.Request):
            body = json.loads(request.content or b"{}")
            method = request.url.path.strip("/")
            calls.append((method, body, request.headers.get("authorization")))
            if method == "getCurrentAccount":
                return httpx.Response(200, json={"ok": True, "result": {"currency": "EUR", "remaining_budget": "12.5"}})
            if body.get("offset") is None:
                return httpx.Response(200, json={"ok": True, "result": {"ads": [{"ad_id": 1}], "next_offset": "p2"}})
            return httpx.Response(200, json={"ok": True, "result": {"ads": [{"ad_id": 2}]}})

        save = AsyncMock(return_value=1)
        with patch.object(tg_ads, "get_settings", return_value=_settings(rate=100)), \
                patch.object(db, "save_tg_ads", save), patch.object(db, "set_job_report", AsyncMock()) as rep:
            async with self._client(handler) as client:
                report = await tg_ads.sync(client)
        self.assertTrue(report["ok"])
        self.assertEqual((report["ads"], report["matched"], report["currency"], report["rate"]), (2, 1, "EUR", 100.0))
        self.assertEqual([c[0] for c in calls], ["getCurrentAccount", "getAdsList", "getAdsList"])
        self.assertEqual(calls[2][1]["offset"], "p2")
        self.assertEqual(calls[0][2], "Bearer tok")
        self.assertEqual([a["ad_id"] for a in save.call_args.args[0]], [1, 2])
        rep.assert_awaited_once()

    async def test_api_error_is_reported(self):
        def handler(request):
            return httpx.Response(401, json={"ok": False, "error": "ACCESS_TOKEN_INVALID"})

        with patch.object(tg_ads, "get_settings", return_value=_settings()), \
                patch.object(db, "save_tg_ads", AsyncMock()) as save, \
                patch.object(db, "set_job_report", AsyncMock()) as rep:
            async with self._client(handler) as client:
                report = await tg_ads.sync(client)
        self.assertFalse(report["ok"])
        self.assertIn("ACCESS_TOKEN_INVALID", report["error"])
        save.assert_not_awaited()
        self.assertFalse(rep.call_args.args[1]["ok"])

    async def test_no_token(self):
        with patch.object(tg_ads, "get_settings", return_value=_settings(token="")):
            report = await tg_ads.sync()
        self.assertFalse(report["ok"])

    async def test_ton_uses_market_rate(self):
        with patch.object(tg_ads, "get_settings", return_value=_settings()), \
                patch("app.ton.rub_per_ton", AsyncMock(return_value=Decimal("300"))):
            self.assertEqual(await tg_ads._rate("TON"), Decimal("300"))
            self.assertIsNone(await tg_ads._rate("EUR"))
        with patch.object(tg_ads, "get_settings", return_value=_settings(rate=95)):
            self.assertEqual(await tg_ads._rate("EUR"), Decimal(95))


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class StoreTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        import tests.test_funnel_integration as bridge

        def dumps(obj, default=None, **kw):     # asyncpg takes Decimal for NUMERIC; the JSON bridge needs a hint
            return json.dumps(obj, default=lambda v: str(v) if isinstance(v, Decimal) else default(v), **kw)

        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(bridge, "json", SimpleNamespace(dumps=dumps, loads=json.loads))):
            p.start()
            self.addCleanup(p.stop)
        self.tech = await self.pool.fetchval("INSERT INTO ad_links (slug, title) VALUES ('tech', 'Тех') RETURNING id")
        self.hand = await self.pool.fetchval(
            "INSERT INTO ad_links (slug, title, spend_rub) VALUES ('hand', 'Ручной', 5000) RETURNING id")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_ads_are_tied_to_links_and_spend_counts(self):
        from app.admin import _ad_public
        ads = [
            {"ad_id": 11, "title": "A", "promote_url": "https://t.me/Bot?start=ad_tech", "spent_budget": "1.5",
             "views": 1000, "clicks": 20, "actions": 5, "created_date": 1760000000},
            {"ad_id": 12, "title": "B", "promote_url": "https://t.me/Bot?start=ad_tech", "spent_budget": "0.5",
             "views": 1000, "clicks": 10, "joins": 2},
            {"ad_id": 13, "title": "C", "promote_url": "https://t.me/Bot?start=ad_hand", "spent_budget": "3"},
            {"ad_id": 14, "title": "Чужое", "promote_url": "https://t.me/somechannel", "spent_budget": "2"},
        ]
        self.assertEqual(await db.save_tg_ads(ads, "TON", Decimal(300), tg_ads.slug_from_url), 3)
        # A second sync without a rate keeps the rubles counted earlier.
        self.assertEqual(await db.save_tg_ads(ads, "TON", None, tg_ads.slug_from_url), 3)
        self.assertEqual([a["ad_id"] for a in await db.tg_ads_unmatched()], [14])

        links = {r["slug"]: dict(r) for r in await db.list_ad_links()}
        for row in links.values():
            row.pop("created_at", None)
        tech = _ad_public(links["tech"])
        self.assertEqual(tech["spend_rub"], 600)                 # (1.5 + 0.5) TON × 300 ₽
        self.assertTrue(tech["spend_auto"])
        self.assertEqual((tech["tg"]["ads"], tech["tg"]["views"], tech["tg"]["clicks"]), (2, 2000, 30))
        self.assertEqual(tech["tg"]["ctr"], 1.5)
        self.assertAlmostEqual(tech["tg"]["spent"], 2.0)
        hand = _ad_public(links["hand"])
        self.assertEqual(hand["spend_rub"], 5000)                # typed by hand wins
        self.assertFalse(hand["spend_auto"])
        self.assertEqual(await self.pool.fetchval("SELECT actions FROM tg_ads WHERE ad_id = 12"), 2)


if __name__ == "__main__":
    unittest.main()
