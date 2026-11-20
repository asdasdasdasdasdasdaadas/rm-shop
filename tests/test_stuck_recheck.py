"""Before «Застрял на подключении» / «Подключился, но трафика нет» go out, the panel is asked right now:
the regular sync can be hours behind, and the admin should not write to someone who is already connected."""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, stuck_alert


class Panel:
    def __init__(self, users, fail=False):
        self.users, self.fail, self.asked = users, fail, []

    async def get_user_by_id(self, panel_id):
        self.asked.append(panel_id)
        if self.fail:
            raise RuntimeError("panel down")
        return self.users.get(panel_id)


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class RecheckTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(stuck_alert, "_targets", AsyncMock(return_value=[777])),
                  patch("app.live.note_first_online_from_panels", AsyncMock())):
            p.start()
            self.addCleanup(p.stop)
        await self.pool.execute("INSERT INTO users (telegram_id, first_name, trial_used) VALUES (1, 'Аня', TRUE), (2, 'Боря', TRUE)")
        await self.pool.execute("""INSERT INTO devices (telegram_id, title, remnawave_id, created_at)
            VALUES (1, 'iPhone', 501, NOW() - INTERVAL '3 hours'), (2, 'Mac', 502, NOW() - INTERVAL '3 hours')""")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_connected_by_panel_is_not_reported(self):
        now = datetime.now(timezone.utc).isoformat()
        panel = Panel({501: {"id": 501, "uuid": "u501", "userTraffic": {"onlineAt": now, "lifetimeUsedTrafficBytes": 5 << 20}},
                       502: {"id": 502, "uuid": "u502", "userTraffic": {}}})
        bot = SimpleNamespace(send_message=AsyncMock())
        self.assertEqual(await stuck_alert.send_due(bot, panel), 1)
        self.assertEqual(sorted(panel.asked), [501, 502])
        self.assertIn("Боря", bot.send_message.call_args.args[1])         # only the one really stuck
        self.assertIsNotNone(await self.pool.fetchval("SELECT last_online_at FROM devices WHERE remnawave_id = 501"))
        self.assertEqual(await stuck_alert.send_due(bot, panel), 0)        # still once per person

    async def test_panel_down_alerts_as_before(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        self.assertEqual(await stuck_alert.send_due(bot, Panel({}, fail=True)), 2)
        self.assertEqual(bot.send_message.await_count, 2)

    async def test_no_traffic_skips_when_traffic_came(self):
        await self.pool.execute("""UPDATE devices SET first_online_at = NOW() - INTERVAL '40 minutes',
            last_online_at = NOW() - INTERVAL '40 minutes', lifetime_traffic_bytes = 0""")
        settings = SimpleNamespace(no_traffic_alert_enabled=True, no_traffic_alert_min_mb=1, no_traffic_alert_after_minutes=30)
        panel = Panel({501: {"id": 501, "uuid": "u501", "userTraffic": {"lifetimeUsedTrafficBytes": 50 << 20}},
                       502: {"id": 502, "uuid": "u502", "userTraffic": {"lifetimeUsedTrafficBytes": 1000}}})
        bot = SimpleNamespace(send_message=AsyncMock())
        with patch("app.config.get_settings", return_value=settings):
            self.assertEqual(await stuck_alert.send_no_traffic(bot, panel), 1)
        self.assertIn("Mac", bot.send_message.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
