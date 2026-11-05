import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiohttp import web

from app import admin, db, partners
from app.config import Settings

TOKEN = "A" * 32
SETTINGS = Settings.model_construct(bot_username="way_bot", brand_name="Way VPN", webapp_public_url="https://vpn.example")
LINK = dict(id=7, slug="tiktok", title="TikTok", clicks=12, users=5, connected=3, paid=1,
            created_at=datetime(2026, 11, 1, tzinfo=timezone.utc), partner_id=2)


def request(method="GET", body=None, token=TOKEN):
    return SimpleNamespace(method=method, match_info={"token": token}, json=AsyncMock(return_value=body or {}))


class PartnerPageTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch.object(partners, "get_settings", return_value=SETTINGS)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_unknown_or_malformed_token_is_404_without_db_lookup_for_garbage(self):
        lookup = AsyncMock(return_value=None)
        with patch.object(db, "_pool_req", return_value=SimpleNamespace(fetchrow=lookup)):
            with self.assertRaises(web.HTTPNotFound):
                await partners.page(request(token="short"))
            lookup.assert_not_awaited()
            with self.assertRaises(web.HTTPNotFound):
                await partners.api(request())
            lookup.assert_awaited_once()

    async def test_stats_show_only_this_partners_links(self):
        with patch.object(partners, "partner_by_token", AsyncMock(return_value={"id": 2, "title": "Блогер"})), \
             patch.object(db, "list_ad_links", AsyncMock(return_value=[LINK])) as links:
            response = await partners.api(request())
        data = json.loads(response.body)
        links.assert_awaited_once_with(partner_id=2)
        self.assertEqual(data["title"], "Блогер")
        self.assertEqual(data["items"][0]["url"], "https://t.me/way_bot?start=ad_tiktok")
        self.assertEqual({k: data["items"][0][k] for k in ("clicks", "users", "connected", "paid")},
                         {"clicks": 12, "users": 5, "connected": 3, "paid": 1})
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")

    async def test_create_link_is_tied_to_partner_and_capped(self):
        with patch.object(partners, "partner_by_token", AsyncMock(return_value={"id": 2, "title": "Блогер"})), \
             patch.object(db, "list_ad_links", AsyncMock(return_value=[LINK])), \
             patch.object(db, "create_ad_link", AsyncMock(return_value=LINK)) as create:
            response = await partners.api(request("POST", {"title": "  TikTok  "}))
            self.assertEqual(response.status, 200)
            create.assert_awaited_once_with("TikTok", kind="manual", partner_id=2)
            bad = await partners.api(request("POST", {"title": "x"}))
            self.assertEqual(bad.status, 400)
        with patch.object(partners, "partner_by_token", AsyncMock(return_value={"id": 2, "title": "Блогер"})), \
             patch.object(db, "list_ad_links", AsyncMock(return_value=[LINK] * partners.MAX_LINKS)), \
             patch.object(db, "create_ad_link", AsyncMock()) as create:
            capped = await partners.api(request("POST", {"title": "Ещё одна"}))
        self.assertEqual(capped.status, 400)
        create.assert_not_awaited()

    def test_no_delete_route(self):
        app = web.Application()
        partners.mount_partners(app)
        methods = {(r.method, r.resource.canonical) for r in app.router.routes()}
        self.assertNotIn("DELETE", {m for m, _ in methods})
        self.assertIn(("POST", "/partner/{token}/api"), methods)


class AdminPartnersTest(unittest.IsolatedAsyncioTestCase):
    async def test_admin_lists_partner_page_url_and_needs_auth(self):
        row = dict(id=2, title="Блогер", token=TOKEN, links=1, clicks=12, users=5, revoked_at=None,
                   created_at=datetime(2026, 11, 1, tzinfo=timezone.utc))
        req = SimpleNamespace(method="GET", url=SimpleNamespace(origin=lambda: "http://internal"))
        with patch.object(admin, "_need_auth", return_value=None), patch.object(admin, "get_settings", return_value=SETTINGS), \
             patch.object(partners, "list_partners", AsyncMock(return_value=[row])):
            data = json.loads((await admin.api_partners(req)).body)
        self.assertEqual(data["items"][0]["url"], f"https://vpn.example/partner/{TOKEN}")
        denied = web.json_response({"ok": False}, status=401)
        with patch.object(admin, "_need_auth", return_value=denied):
            self.assertEqual((await admin.api_partners(req)).status, 401)


if __name__ == "__main__":
    unittest.main()
