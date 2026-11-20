"""«Шеринг подписки»: IPs from the panel's node jobs land per device; too many IPs make one admin message."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, sharing_alert


def settings(**kw):
    return SimpleNamespace(**{"sharing_alert_enabled": True, "sharing_alert_simultaneous": 3, "sharing_alert_daily": 10,
                              "sharing_block_enabled": True, "sharing_block_simultaneous": 5, "sharing_block_daily": 25,
                              "sharing_delete_device": True, "sharing_penalty_enabled": True,
                              "sharing_penalty_balance_rub": -100000, "sharing_notify_user": True,
                              "webapp_public_url": "https://lk.example", "admin_id_set": {42}, **kw})


class FakePanel:
    """Two nodes; node A sees panel user 501 from 3 IPs right now, node B one more an hour ago."""

    def __init__(self, now):
        self.now, self.calls = now, []

    async def _request(self, method, path, **kw):
        self.calls.append((method, path))
        if path == "/nodes":
            return {"response": [{"uuid": "a", "isConnected": True}, {"uuid": "b", "isConnected": True},
                                 {"uuid": "c", "isConnected": False}]}
        if method == "POST" and path.startswith("/connections/by-node/"):
            return {"response": {"jobId": "job-" + path.rsplit("/", 1)[1]}}
        iso = lambda m: (self.now - timedelta(minutes=m)).isoformat()
        users = ([{"userId": 501, "ips": [{"ip": "1.1.1.1", "lastSeen": iso(1)}, {"ip": "2.2.2.2", "lastSeen": iso(2)},
                                          {"ip": "3.3.3.3", "lastSeen": iso(3)}]},
                  {"userId": 777, "ips": [{"ip": "9.9.9.9", "lastSeen": iso(1)}]}]
                 if path.endswith("job-a") else
                 [{"userId": 501, "ips": [{"ip": "4.4.4.4", "lastSeen": iso(60)}, {"ip": "1.1.1.1", "lastSeen": iso(30)}]}])
        return {"response": {"isCompleted": True, "isFailed": False, "result": {"success": True, "nodeUuid": "x", "users": users}}}


class FormatTest(unittest.TestCase):
    def test_message_lists_who_ips_and_traffic(self):
        now = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
        row = {"device_id": 7, "telegram_id": 123, "username": "vasya", "first_name": "Вася", "title": "iPhone",
               "platform": "iOS", "client": "Happ", "created_at": now - timedelta(days=10), "used_traffic_bytes": 0,
               "lifetime_traffic_bytes": 20 * 1024 ** 3, "now_ips": 4, "day_ips": 12}
        ips = [{"ip": f"10.0.0.{i}", "last_seen": now - timedelta(minutes=i * 5)} for i in range(12)]
        with patch.object(sharing_alert, "get_settings", return_value=settings()):
            text, kb = sharing_alert.format_alert(row, ips, now)
        self.assertIn("Шеринг подписки", text)
        self.assertIn("@vasya", text)
        self.assertIn("<code>123</code>", text)
        self.assertIn("Одновременно: <b>4 IP</b> · за сутки: <b>12 IP</b>", text)
        self.assertIn("<code>10.0.0.0</code> — сейчас", text)
        self.assertIn("<code>10.0.0.3</code> — 15 мин назад", text)
        self.assertIn("… и ещё 2", text)
        self.assertIn("всего <b>20.0 ГБ</b> · в среднем 2.0 ГБ в день", text)
        flat = [b for r in kb.inline_keyboard for b in r]
        self.assertEqual([b.text for b in flat], ["Открыть клиента", "Написать", "Сбросить подключения"])
        self.assertEqual(flat[0].url, "https://lk.example/admin#users?q=123")
        self.assertEqual(flat[2].callback_data, "shr:drop:7")
        with patch.object(sharing_alert, "get_settings", return_value=settings()):
            text, kb = sharing_alert.format_alert(row, ips, now, blocked=True)
        self.assertIn("заблокирован", text)
        self.assertIn("Пополнение их не включит", text)
        self.assertEqual(kb.inline_keyboard[-1][0].callback_data, "shr:unblock:123")


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class SharingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(sharing_alert, "get_settings", return_value=settings()),
                  patch.object(sharing_alert.asyncio, "sleep", new=AsyncMock())):
            p.start()
            self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id, username, first_name) VALUES (1, 'vasya', 'Вася'), (2, NULL, 'Петя')")
        await self.pool.execute("""INSERT INTO devices (id, telegram_id, title, remnawave_id, lifetime_traffic_bytes)
            VALUES (10, 1, 'iPhone', 501, 1000), (11, 2, 'Mac', 777, 0)""")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_collect_claim_once_and_drop_old(self):
        panel = FakePanel(datetime.now(timezone.utc))
        self.assertEqual(await sharing_alert.collect(panel), 5)  # 1.1.1.1 on both nodes is one row
        self.assertNotIn(("POST", "/connections/by-node/c"), panel.calls)  # offline node is skipped
        ips = await db.device_ips_recent(10)
        self.assertEqual([x["ip"] for x in ips][:1], ["1.1.1.1"])  # the newest lastSeen of both nodes wins
        self.assertEqual(len(ips), 4)
        rows = await db.claim_sharing_alerts(3, 10)
        self.assertEqual([(r["device_id"], r["now_ips"], r["day_ips"], r["username"]) for r in rows], [(10, 3, 4, "vasya")])
        self.assertEqual(await db.claim_sharing_alerts(3, 10), [])  # once per 3 days
        # Half again as many IPs: reported sooner.
        await self.pool.execute("INSERT INTO device_ips (device_id, ip, last_seen) VALUES (10, '5.5.5.5', NOW()), (10, '6.6.6.6', NOW())")
        self.assertEqual([r["now_ips"] for r in await db.claim_sharing_alerts(3, 10)], [5])
        await self.pool.execute("UPDATE device_ips SET last_seen = NOW() - INTERVAL '40 days' WHERE ip='4.4.4.4'")
        await db.prune_device_ips(30)
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM device_ips WHERE device_id=10"), 5)

    async def test_send_due_goes_to_admins(self):
        await self.pool.execute("""INSERT INTO device_ips (device_id, ip, last_seen) VALUES
            (10, '1.1.1.1', NOW()), (10, '2.2.2.2', NOW()), (10, '3.3.3.3', NOW())""")
        sent = []

        class Bot:
            async def send_message(self, chat, text, **kw):
                sent.append((chat, text))

        with patch("app.live._chat_id", return_value=None), patch("app.config.get_settings", return_value=settings()):
            self.assertEqual(await sharing_alert.send_due(Bot()), 1)
        self.assertEqual(sent[0][0], 42)
        self.assertIn("3 IP", sent[0][1])

    async def test_block_due_switches_off_every_key_once(self):
        await self.pool.execute("UPDATE users SET remnawave_id = 500, balance_rub = 340 WHERE telegram_id = 1")
        await self.pool.execute("INSERT INTO users (telegram_id, first_name) VALUES (42, 'Админ')")
        await self.pool.execute("INSERT INTO devices (id, telegram_id, title, remnawave_id) VALUES (12, 1, 'Mac', 502), (13, 42, 'A', 900)")
        await self.pool.execute("""INSERT INTO device_ips (device_id, ip, last_seen)
            SELECT 10, '10.0.0.' || g, NOW() FROM generate_series(1, 5) g""")
        await self.pool.execute("""INSERT INTO device_ips (device_id, ip, last_seen)
            SELECT 13, '10.1.0.' || g, NOW() FROM generate_series(1, 9) g""")   # the admin: never blocked
        await self.pool.execute("""INSERT INTO device_ips (device_id, ip, last_seen)
            SELECT 11, '10.2.0.' || g, NOW() - INTERVAL '2 hours' FROM generate_series(1, 4) g""")  # under both thresholds

        class Rw:
            def __init__(self):
                self.off, self.calls, self.deleted = [], [], []

            async def delete_panel_user(self, panel_id):
                self.deleted.append(panel_id)

            async def disable_panel_user(self, panel_id):
                self.off.append(panel_id)

            async def _request(self, method, path, **kw):
                self.calls.append((path, kw.get("json")))

        sent = []

        class Bot:
            async def send_message(self, chat, text, **kw):
                sent.append((chat, text, kw.get("reply_markup")))

        rw, told = Rw(), AsyncMock()
        with patch("app.live._chat_id", return_value=None), patch("app.config.get_settings", return_value=settings()), \
                patch("app.block.notify_blocked", new=told):
            caught = await sharing_alert.block_due(rw, Bot())
            self.assertEqual([(c["telegram_id"], c["now_ips"]) for c in caught], [(1, 5)])
            self.assertIn("Устройство «iPhone» удалено", caught[0]["actions"][0])
            self.assertEqual(rw.deleted, [501])                      # the sharing device is gone
            self.assertIsNone(await db.get_device(1, 10))
            self.assertEqual(sorted(rw.off), [500, 502])             # the rest are off
            self.assertEqual(sorted(rw.calls[0][1]["dropBy"]["userIds"]), [500, 502])
            self.assertTrue(await db.user_is_blocked(1))
            u = await self.pool.fetchrow("SELECT balance_rub, sharing_at, sharing_penalty_rub FROM users WHERE telegram_id=1")
            self.assertEqual((u["balance_rub"], u["sharing_penalty_rub"]), (-100000, 100340))
            self.assertIsNotNone(u["sharing_at"])
            ev = await self.pool.fetchrow("SELECT amount, balance_after FROM billing_events WHERE telegram_id=1 AND kind='sharing'")
            self.assertEqual((ev["amount"], ev["balance_after"]), (-100340, -100000))
            self.assertIn("5 IP одновременно", await self.pool.fetchval("SELECT blocked_reason FROM users WHERE telegram_id=1"))
            self.assertFalse(await db.user_is_blocked(2))
            self.assertFalse(await db.user_is_blocked(42))
            told.assert_awaited_once()
            self.assertEqual([c for c, *_ in sent], [42])
            self.assertIn("заблокирован", sent[0][1])
            self.assertIn("Устройство «iPhone» удалено", sent[0][1])
            self.assertIn("Баланс: −100 000 ₽ (списано 100 340 ₽)", sent[0][1])
            self.assertIn("10.0.0.1", sent[0][1])                     # IPs read before the device went
            # Already blocked: not again, and no plain sharing warning either.
            self.assertEqual(await sharing_alert.block_due(rw, Bot()), [])
            self.assertNotIn(1, [r["telegram_id"] for r in await db.claim_sharing_alerts(3, 10)])
            # Off switch: nothing happens.
            with patch.object(sharing_alert, "get_settings", return_value=settings(sharing_block_enabled=False)):
                await self.pool.execute("UPDATE users SET blocked_at = NULL WHERE telegram_id = 1")
                self.assertEqual(await sharing_alert.block_due(rw, Bot()), [])

    async def test_only_block_when_delete_and_fine_are_off(self):
        await self.pool.execute("UPDATE users SET balance_rub = 70 WHERE telegram_id = 1")
        await self.pool.execute("""INSERT INTO device_ips (device_id, ip, last_seen)
            SELECT 10, '10.0.0.' || g, NOW() FROM generate_series(1, 6) g""")

        class Rw:
            off, deleted = [], []

            async def disable_panel_user(self, panel_id):
                self.off.append(panel_id)

            async def delete_panel_user(self, panel_id):
                self.deleted.append(panel_id)

            async def _request(self, method, path, **kw):
                return {}

        class Bot:
            async def send_message(self, *a, **kw):
                pass

        quiet = settings(sharing_delete_device=False, sharing_penalty_enabled=False, sharing_notify_user=False)
        told = AsyncMock()
        with patch.object(sharing_alert, "get_settings", return_value=quiet), patch("app.live._chat_id", return_value=None), \
                patch("app.config.get_settings", return_value=quiet), patch("app.block.notify_blocked", new=told):
            got = await sharing_alert.run_check(Rw(), Bot())
        self.assertEqual(len(got["caught"]), 1)
        self.assertEqual((Rw.deleted, Rw.off), ([], [501]))
        self.assertIsNotNone(await db.get_device(1, 10))
        u = await self.pool.fetchrow("SELECT balance_rub, sharing_at, blocked_at FROM users WHERE telegram_id=1")
        self.assertEqual(u["balance_rub"], 70)
        self.assertIsNotNone(u["sharing_at"])
        self.assertIsNotNone(u["blocked_at"])
        told.assert_not_awaited()
        top = await db.sharing_top()
        self.assertEqual((top[0]["device_id"], top[0]["now_ips"], top[0]["blocked"]), (10, 6, True))

    async def test_unblock_forgets_old_ips_and_gives_balance_back(self):
        await self.pool.execute("UPDATE users SET balance_rub = 50 WHERE telegram_id = 1")
        await self.pool.execute("INSERT INTO device_ips (device_id, ip, last_seen) VALUES (10, '1.1.1.1', NOW())")
        self.assertEqual(await db.apply_sharing_penalty(1), (100050, -100000))
        self.assertEqual(await db.apply_sharing_penalty(1), (0, -100000))   # already there: nothing more taken
        await db.set_user_blocked(1, True, "Шеринг")
        from app.admin import _apply_block
        with patch("app.admin.get_settings", return_value=settings()):
            self.assertEqual(await _apply_block(object(), 1, False), "ok")
        self.assertFalse(await db.user_is_blocked(1))
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM device_ips WHERE device_id=10"), 0)
        u = await self.pool.fetchrow("SELECT balance_rub, sharing_at, sharing_penalty_rub FROM users WHERE telegram_id=1")
        self.assertEqual((u["balance_rub"], u["sharing_penalty_rub"]), (50, None))
        self.assertIsNotNone(u["sharing_at"])                                # the mark stays

    async def test_old_panel_switches_the_check_off(self):
        from app.remnawave import RemnawaveError

        class Old:
            async def _request(self, method, path, **kw):
                if path == "/nodes":
                    return {"response": [{"uuid": "a"}]}
                raise RemnawaveError(f"{method} {path} → 404: Not Found")

        self.addCleanup(setattr, sharing_alert, "_unsupported", False)
        self.assertEqual(await sharing_alert.collect(Old()), 0)
        self.assertTrue(sharing_alert._unsupported)


if __name__ == "__main__":
    unittest.main()
