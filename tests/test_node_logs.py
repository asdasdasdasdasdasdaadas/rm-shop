"""Node xray logs: reading the lines, the verdict, storing them for watched devices, and the node shipper."""
import asyncio
import importlib.util
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, node_logs

NOW = datetime(2026, 11, 22, 18, 0, tzinfo=timezone.utc)
ACC = "2026/11/22 17:30:01.123456 from 91.1.2.3:51234 accepted tcp:www.google.com:443 [VLESS_REALITY >> DIRECT] email: 501"
REJ = "2026/11/22 17:30:02 from 91.1.2.3:51235 rejected  proxy/vless/encoding: invalid request user id"
REAL = "2026/11/22 17:30:03 [Info] transport/internet/tcp: REALITY: processed invalid connection from 91.1.2.3:4444: reality verification failed"
ENDS = "2026/11/22 17:30:04 [Info] [12345] app/proxyman/inbound: connection ends > proxy/vless/inbound: connection ends > io: read/write on closed pipe from 91.1.2.3:51234"


class ParseTest(unittest.TestCase):
    def test_access_and_error_lines(self):
        a = node_logs.parse(ACC, "a", NOW)
        self.assertEqual((a["ip"], a["email"], a["kind"], a["dest"]), ("91.1.2.3", "501", "accepted", "tcp:www.google.com:443"))
        self.assertEqual(a["at"], datetime(2026, 11, 22, 17, 30, 1, tzinfo=timezone.utc))
        self.assertEqual(node_logs.parse(REJ, "a", NOW)["kind"], "refused")
        self.assertEqual((node_logs.parse(REAL, "e", NOW)["kind"], node_logs.parse(REAL, "e", NOW)["ip"]), ("reality", "91.1.2.3"))
        self.assertEqual(node_logs.parse(ENDS, "e", NOW)["kind"], "ends")
        self.assertIsNone(node_logs.parse("2026/11/22 17:30:05 [Warning] core: Xray 1.8 started", "e", NOW))
        self.assertIsNone(node_logs.parse("", "a", NOW))


class VerdictTest(unittest.TestCase):
    def say(self, **kinds):
        rows = [{"node": "de1", "kind": k, "n": v[0] if isinstance(v, tuple) else v,
                 "dests": v[1] if isinstance(v, tuple) else 0} for k, v in kinds.items()]
        return node_logs.diagnose(rows)["verdict"]

    def test_verdicts(self):
        self.assertTrue(self.say().startswith("До ноды не дошло"))
        self.assertTrue(self.say(refused=4).startswith("Нода не принимает ключ"))
        self.assertTrue(self.say(reality=9).startswith("Соединение доходит, но рукопожатие"))
        self.assertTrue(self.say(accepted=(6, 2), ends=6).startswith("Соединения открываются и сразу рвутся"))
        self.assertTrue(self.say(accepted=(40, 25), ends=3).startswith("Через ноду идут запросы"))
        self.assertEqual(node_logs.diagnose([], enabled=False)["verdict"], "")

    def test_token(self):
        with patch.object(node_logs, "get_settings", return_value=SimpleNamespace(node_logs_token="s3cret")):
            self.assertTrue(node_logs.token_ok("Bearer s3cret"))
            self.assertFalse(node_logs.token_ok("Bearer nope"))
            self.assertFalse(node_logs.token_ok(None))
        with patch.object(node_logs, "get_settings", return_value=SimpleNamespace(node_logs_token="")):
            self.assertFalse(node_logs.token_ok("Bearer "))


class AlertTest(unittest.TestCase):
    def test_the_alert_carries_the_verdict(self):
        from app.stuck_alert import format_no_traffic
        row = {"telegram_id": 1, "first_name": "Аня", "title": "iPhone", "traffic": 1000}
        text, _ = format_no_traffic(row, 1, {"verdict": "Рукопожатие не проходит", "details": ["Reality не прошёл: 9"]})
        self.assertIn("Логи ноды:</b> Рукопожатие не проходит", text)
        self.assertNotIn("Скорее всего", text)
        self.assertIn("Скорее всего", format_no_traffic(row, 1, None)[0])


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class NodeLogsDb(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        await self.pool.execute("INSERT INTO users (telegram_id) VALUES (7), (8)")
        await self.pool.execute("""INSERT INTO devices (id, telegram_id, title, remnawave_id) VALUES
            (1, 7, 'iPhone', 501), (2, 8, 'Mac', 502)""")
        await self.pool.execute("UPDATE devices SET created_at = NOW() - INTERVAL '10 days' WHERE id = 2")
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(node_logs, "get_settings", return_value=SimpleNamespace(node_logs_token="t"))):
            p.start()
            self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_watch_list_learns_panel_names(self):
        rw = SimpleNamespace(get_user_by_id=AsyncMock(return_value={"username": "tg7_iphone"}))
        self.assertEqual(await node_logs.watch_list(rw), ["501", "tg7_iphone"])   # the old Mac is not watched
        rw.get_user_by_id.assert_awaited_once_with(501)
        await node_logs.watch_device(2)
        self.assertEqual(await node_logs.watch_list(None), ["501", "502", "tg7_iphone"])

    async def test_lines_land_on_the_device_and_errors_follow_the_ip(self):
        await self.pool.execute("INSERT INTO node_log_names (remnawave_id, username) VALUES (501, 'tg7_iphone')")
        acc = ACC.replace("email: 501", "email: tg7_iphone").replace("2026/11/22 17:30:01.123456",
                                                                     datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S"))
        stored = await node_logs.ingest("de1", [{"f": "a", "line": acc}, {"f": "e", "line": REAL}, {"f": "e", "line": "junk"}])
        self.assertEqual(stored, 2)
        rows = await self.pool.fetch("SELECT kind, device_id, telegram_id FROM node_log_lines ORDER BY id")
        self.assertEqual([(r["kind"], r["device_id"], r["telegram_id"]) for r in rows], [("accepted", 1, 7), ("reality", 1, 7)])
        # a later batch: the error line alone still finds its device by the IP
        await node_logs.ingest("de1", [{"f": "e", "line": ENDS}])
        self.assertEqual(await self.pool.fetchval("SELECT device_id FROM node_log_lines WHERE kind='ends'"), 1)
        view = await node_logs.user_view(7)
        self.assertTrue(view["enabled"])
        self.assertEqual(len(view["lines"]), 3)
        self.assertTrue(view["devices"][0]["seen"])

    async def test_silent_nodes_are_named_as_such(self):
        out = await node_logs.device_summary(1)
        self.assertTrue(out["verdict"].startswith("С нод больше часа не приходят логи"))

    async def test_panel_diagnosis_reads_the_device_and_its_ips(self):
        from app import panel_diag, remnawave
        await self.pool.execute("UPDATE devices SET first_online_at = NOW() - INTERVAL '20 minutes' WHERE id = 1")
        await self.pool.execute("INSERT INTO device_ips (device_id, ip, last_seen) VALUES (1, '91.1.2.3', NOW())")
        panel = {"id": 501, "subLastOpenedAt": datetime.now(timezone.utc).isoformat(),
                 "userTraffic": {"onlineAt": datetime.now(timezone.utc).isoformat(), "usedTrafficBytes": 5000}}
        net = AsyncMock(return_value={"panel": panel, "hwid": [{}], "node": {"name": "de1", "connected": True}})
        with patch.object(remnawave, "fetch_device_network", net):
            out = await panel_diag.diagnose(object(), 1)
        net.assert_awaited_once()
        self.assertTrue(out["verdict"].startswith("Сейчас на связи, но данные почти не идут"))
        self.assertIn("IP на нодах за сутки: 1", out["details"])
        self.assertEqual((await panel_diag.diagnose(None, 1))["verdict"], "")


class PanelVerdictTest(unittest.TestCase):
    def say(self, **f):
        from app import panel_diag
        from datetime import timedelta
        base = {"panel": True, "node": {"name": "de1", "connected": True}, "sub_opened_at": NOW - timedelta(minutes=20),
                "user_agent": "Happ/1.0", "first_online_at": NOW - timedelta(minutes=30), "traffic": 20_000, "ips": 1}
        return panel_diag.verdict({**base, **f}, NOW)

    def test_verdicts(self):
        from datetime import timedelta
        self.assertEqual(self.say(panel=False)["verdict"], "")
        self.assertTrue(self.say(node={"name": "de1", "connected": False})["verdict"].startswith("Нода de1 сейчас не на связи"))
        live = self.say(online_at=NOW - timedelta(minutes=1))
        self.assertTrue(live["verdict"].startswith("Сейчас на связи, но данные почти не идут"))
        self.assertIn("подписку открывали 20 мин назад (Happ/1.0)", live["details"])
        self.assertIn("VPN работает", self.say(online_at=NOW, traffic=600_000)["verdict"])
        self.assertTrue(self.say(online_at=NOW - timedelta(minutes=29))["verdict"].startswith("Подключился на минуту"))
        gone = self.say(online_at=NOW - timedelta(minutes=10), sub_opened_at=None, ips=0)
        self.assertTrue(gone["verdict"].startswith("Был на связи"))
        self.assertIn("IP на нодах не видели", gone["details"])
        self.assertTrue(any("не открывали" in x for x in gone["details"]))


class DiagnosisChoiceTest(unittest.IsolatedAsyncioTestCase):
    async def run_it(self, logs, panel):
        from app import panel_diag, stuck_alert
        with patch.object(stuck_alert, "_node_logs", AsyncMock(return_value=logs)), \
                patch.object(panel_diag, "diagnose", AsyncMock(return_value=panel)):
            return await stuck_alert._diagnosis(object(), 1)

    async def test_node_logs_win_when_they_saw_the_device_otherwise_the_panel(self):
        seen = {"verdict": "Рукопожатие не проходит", "details": [], "seen": True, "source": "nodes"}
        panel = {"verdict": "Подключился на минуту и пропал", "details": ["нода de1"]}
        self.assertIs(await self.run_it(seen, panel), seen)
        got = await self.run_it(None, dict(panel))
        self.assertEqual((got["source"], got["verdict"]), ("panel", panel["verdict"]))
        silent = {"verdict": "С нод больше часа не приходят логи", "details": [], "seen": False, "source": "nodes"}
        got = await self.run_it(silent, dict(panel))
        self.assertEqual(got["source"], "panel")
        self.assertIn(silent["verdict"], got["details"])
        self.assertIsNone(await self.run_it(None, {"verdict": "", "details": []}))

    def test_the_alert_names_the_source(self):
        from app.stuck_alert import format_no_traffic
        row = {"telegram_id": 1, "first_name": "Аня", "title": "iPhone", "traffic": 1000}
        text, _ = format_no_traffic(row, 1, {"verdict": "Нода de1 лежит", "details": [], "source": "panel"})
        self.assertIn("По панели:</b> Нода de1 лежит", text)


class ShipperTest(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location("ship", Path(__file__).parent.parent / "deploy/node-logs/ship.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_tail_starts_at_the_end_waits_for_whole_lines_and_follows_rotation(self):
        ship = self.load()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "access.log")
            Path(path).write_text("old line\n")
            t = ship.Tail(path)
            self.addCleanup(lambda: t.fh and t.fh.close())
            self.assertEqual(t.lines(), [])
            with open(path, "a") as f:
                f.write("one\ntw")
            self.assertEqual(t.lines(), ["one"])
            with open(path, "a") as f:
                f.write("o\n")
            self.assertEqual(t.lines(), ["two"])
            os.rename(path, path + ".1")
            Path(path).write_text("fresh\n")
            self.assertEqual(t.lines(), ["fresh"])

    def test_access_regex_finds_ip_and_user(self):
        ship = self.load()
        m = ship.ACCESS.search(ACC)
        self.assertEqual((m.group(1), m.group(3)), ("91.1.2.3", "501"))
        self.assertEqual(ship.ANY_IP.search(REAL).group(1), "91.1.2.3")


if __name__ == "__main__":
    unittest.main()
