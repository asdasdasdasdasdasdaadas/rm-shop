import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("BOT_USERNAME", "test_bot")
os.environ.setdefault("REQUIRED_CHANNEL_ID", "@test")
os.environ.setdefault("REQUIRED_CHANNEL_URL", "https://t.me/test")
os.environ.setdefault("REMNAWAVE_BASE_URL", "https://panel.example.com")
os.environ.setdefault("REMNAWAVE_TOKEN", "rw-token")
os.environ.setdefault("LEGAL_OFFER_URL", "https://example.com/offer")
os.environ.setdefault("LEGAL_PRIVACY_URL", "https://example.com/privacy")
os.environ.setdefault("ADMIN_PASSWORD", "kirill-admin")
os.environ.setdefault("OFFICE_STATUS_TOKEN", "office-secret")
os.environ.setdefault("OFFICE_STALE_MINUTES", "8")
os.environ.setdefault("WEBAPP_ENABLED", "false")

from aiohttp.test_utils import AioHTTPTestCase

from app.web import build_web_app


class OfficeHttpTest(AioHTTPTestCase):
    async def get_application(self):
        return build_web_app()

    async def test_health_still_ok(self):
        resp = await self.client.get("/health")
        self.assertEqual(resp.status, 200)
        body = await resp.json()
        self.assertTrue(body.get("ok"))

    async def test_office_read_requires_admin(self):
        resp = await self.client.get("/admin/api/office")
        self.assertEqual(resp.status, 401)
        body = await resp.json()
        self.assertNotIn("agents", body)

    async def test_office_write_requires_token(self):
        resp = await self.client.post("/api/office/status", json={"agent_id": "monday", "state": "busy"})
        self.assertEqual(resp.status, 403)

    async def test_office_write_and_admin_read(self):
        now = datetime.now(timezone.utc)
        stored = {
            "agent_id": "monday",
            "state": "busy",
            "message": "пишет кабинет",
            "updated_at": now.isoformat(),
            "source_ts": None,
        }
        with (
            patch("app.db.upsert_office_status", new=AsyncMock(return_value=stored)),
            patch("app.db.list_office_status", new=AsyncMock(return_value=[stored])),
        ):
            write = await self.client.post(
                "/api/office/status",
                json={"agent_id": "Понедельник", "state": "active", "message": "пишет кабинет"},
                headers={"X-Office-Token": "office-secret"},
            )
            self.assertEqual(write.status, 200)
            written = await write.json()
            self.assertTrue(written["ok"])
            self.assertEqual(written["agent_id"], "monday")

            login = await self.client.post("/admin/api/login", json={"password": "kirill-admin"})
            self.assertEqual(login.status, 200)

            read = await self.client.get("/admin/api/office")
            self.assertEqual(read.status, 200)
            body = await read.json()
            self.assertEqual([a["id"] for a in body["agents"]], ["monday", "friday", "thursday", "product"])
            self.assertEqual(body["agents"][0]["state"], "busy")
            self.assertEqual(body["agents"][0]["message"], "пишет кабинет")
            self.assertEqual(body["agents"][1]["state"], "offline")
