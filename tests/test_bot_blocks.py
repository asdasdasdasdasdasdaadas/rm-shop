"""Exact bot blocks: Telegram's «kicked» in a private chat is recorded with the stage and the last bot message,
«member» undoes it, and «Когда блокируют» counts them."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import db, live


def event(chat_id, status, at):
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id, type="private"),
                           new_chat_member=SimpleNamespace(status=status), date=at)


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class BotBlocksTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(live, "get_settings", return_value=SimpleNamespace(required_channel_enabled=True))):
            p.start()
            self.addCleanup(p.stop)
        # 1 never passed the channel; 2 has a device; 3 paid.
        await self.pool.execute("""INSERT INTO users (telegram_id, bot_started_at, has_paid_topup) VALUES
            (1, NOW() - INTERVAL '5 minutes', FALSE), (2, NOW() - INTERVAL '2 days', FALSE), (3, NOW() - INTERVAL '20 days', TRUE)""")
        await self.pool.execute("INSERT INTO devices (telegram_id, title) VALUES (2, 'iPhone')")
        await self.pool.execute("INSERT INTO onboarding_events (telegram_id, stage) VALUES (2, 'channel_passed')")
        await self.pool.execute("""INSERT INTO message_log (telegram_id, kind, title, status, created_at) VALUES
            (2, 'funnel', 'Нет устройства: сутки', 'sent', NOW() - INTERVAL '3 days'),
            (2, 'funnel', 'Ваш подарок ещё ждёт', 'sent', NOW() - INTERVAL '20 minutes'),
            (2, 'broadcast', 'Рассылка', 'failed', NOW() - INTERVAL '5 minutes')""")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_block_snapshot_unblock_and_report(self):
        now = datetime.now(timezone.utc)
        await live.note_private_block(event(1, "kicked", now))
        await live.note_private_block(event(2, "kicked", now))
        await live.note_private_block(event(2, "kicked", now))  # a repeat does not double count
        await live.note_private_block(event(3, "kicked", now))
        rows = {r["telegram_id"]: dict(r) for r in await self.pool.fetch("SELECT * FROM bot_blocks")}
        self.assertEqual({k: v["stage"] for k, v in rows.items()}, {1: "channel", 2: "device", 3: "paid"})
        self.assertEqual(rows[2]["last_title"], "Ваш подарок ещё ждёт")  # the failed one is not «sent»
        self.assertIsNone(rows[1]["last_kind"])
        self.assertTrue(250 <= int(rows[1]["since_start_sec"]) <= 400)
        self.assertIsNotNone(await self.pool.fetchval("SELECT bot_blocked_at FROM users WHERE telegram_id=2"))

        await live.note_private_block(event(3, "member", now + timedelta(minutes=1)))
        self.assertIsNone(await self.pool.fetchval("SELECT bot_blocked_at FROM users WHERE telegram_id=3"))

        report = await db.admin_block_report(30)
        self.assertEqual((report["total"], report["unblocked"], report["right_after"]), (3, 1, 1))
        self.assertEqual({t["label"]: t["n"] for t in report["timing"]}["до 10 минут"], 1)
        self.assertEqual({s["stage"] for s in report["stages"]}, {"channel", "device", "paid"})
        labels = {r["label"]: (r["n"], r["soon"]) for r in report["last"]}
        self.assertEqual(labels["Ваш подарок ещё ждёт"], (1, 1))
        self.assertEqual(labels["Бот ничего не присылал сам"], (2, 0))

    async def test_unknown_person_and_group_chats_are_ignored(self):
        await live.note_private_block(event(999, "kicked", datetime.now(timezone.utc)))
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM bot_blocks"), 0)


if __name__ == "__main__":
    unittest.main()
