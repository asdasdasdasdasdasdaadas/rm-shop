import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import admin, db


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class SupportInboxTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool

        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        p = patch.object(db, "_pool_req", return_value=self.pool)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(admin, "_authed", return_value=True)
        p.start()
        self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id, first_name, balance_rub) VALUES (5, 'Макс', 240), (6, 'Аня', 0)")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_inbox_shows_preview_photo_and_new_messages(self):
        t, _ = await db.open_or_get_ticket(5, "max", "Макс")
        await db.add_ticket_message(t["id"], "user", "Не подключается")
        await db.add_ticket_message(t["id"], "admin", "Обновите подписку")
        m = await db.add_ticket_message(t["id"], "user", "")
        await db.add_ticket_attachment(m["id"], {"stored_name": "a.jpg", "original_name": "shot.jpg", "mime": "image/jpeg", "kind": "photo", "size_bytes": 10})
        await db.add_ticket_message(t["id"], "user", "всё ещё handshake")
        other, _ = await db.open_or_get_ticket(6, "", "Аня")
        await db.add_ticket_message(other["id"], "user", "Оплатила, баланс не пополнился")

        items, total = await db.admin_list_tickets("", 25, 0, {})
        self.assertEqual(total, 2)
        row = next(x for x in items if x["id"] == t["id"])
        self.assertEqual((row["last_body"], row["last_author"], row["unread"]), ("всё ещё handshake", "user", 2))
        self.assertIsNone(row["last_photo_id"])  # the picture is not in the last message
        # Search finds a dialog by what the client wrote.
        found, n = await db.admin_list_tickets("баланс не", 25, 0, {})
        self.assertEqual((n, found[0]["id"]), (1, other["id"]))
        self.assertEqual((await db.admin_ticket_counts())["open"], 2)

        m = await db.add_ticket_message(other["id"], "user", "")
        att = await db.add_ticket_attachment(m["id"], {"stored_name": "b.png", "original_name": "b.png", "mime": "image/png", "kind": "file", "size_bytes": 5})
        items, _ = await db.admin_list_tickets("Аня", 25, 0, {})
        self.assertEqual((items[0]["last_photo_id"], items[0]["last_body"]), (att["id"], "b.png"))

    async def test_client_card(self):
        t, _ = await db.open_or_get_ticket(5, "max", "Макс")
        await self.pool.execute("UPDATE tickets SET support_rating = 4 WHERE id = $1", t["id"])
        request = SimpleNamespace(match_info={"ticket_id": str(t["id"])}, cookies={})
        with patch("app.web.get_settings", return_value=SimpleNamespace(vpn_day_price_rub=10)):
            res = await admin.api_ticket_client(request)
        data = json.loads(res.body)
        self.assertEqual((data["user"]["balance_rub"], data["user"]["days_left"]), (240, 24))
        self.assertEqual(data["history"], {"total": 1, "rating": 4.0})
        self.assertEqual((data["devices"], data["payments"]), ([], []))
