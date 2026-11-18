"""«Скоро закончится баланс»: only people using the VPN right now, not those whose access ended days ago."""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app import db


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class PaySoonTest(unittest.IsolatedAsyncioTestCase):
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

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_only_people_whose_vpn_is_on(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, balance_rub, first_online_at) VALUES
            (1, 'Пользуется', 8, NOW()), (2, 'Отключился давно', 0, NOW()), (3, 'Не заходит', 8, NOW()),
            (4, 'Много денег', 500, NOW())""")
        await self.pool.execute("""INSERT INTO devices (telegram_id, title, kind, panel_status, last_billed_at, last_online_at) VALUES
            (1, 'a', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour'),
            (2, 'b', 'phone', 'DISABLED', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'),
            (3, 'c', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '10 days'),
            (4, 'd', 'phone', 'ACTIVE', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour')""")
        people = await db.admin_list_pay_soon(6)
        self.assertEqual([p["telegram_id"] for p in people], [1])
        self.assertEqual(people[0]["days_left"], 1.3)
        self.assertEqual((await db.admin_pay_soon_counts(6))["total"], 1)


if __name__ == "__main__":
    unittest.main()
