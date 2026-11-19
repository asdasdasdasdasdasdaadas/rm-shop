"""A/B test of the cabinet's install step: who gets a group, that it sticks, and what is counted."""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from app import db, install_test


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class InstallTestTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_no_test_no_group(self):
        await self.pool.execute("INSERT INTO users (telegram_id) VALUES (1)")
        self.assertIsNone(await install_test.arm_for(1, False))
        self.assertIsNone(await install_test.enter(1))

    async def test_groups_stick_and_skip_people_with_devices(self):
        ids = list(range(1, 81))
        await self.pool.execute("INSERT INTO users (telegram_id) SELECT g FROM generate_series(1, 81) g")
        await self.pool.execute("INSERT INTO devices (telegram_id, title) VALUES (81, 'iPhone')")
        test_id = await install_test.start()
        with self.assertRaises(ValueError):
            await install_test.start()
        arms = {i: await install_test.arm_for(i, False) for i in ids}
        self.assertEqual(set(arms.values()), {"old", "new"})
        self.assertTrue(25 <= list(arms.values()).count("new") <= 55)
        for i in ids:
            self.assertEqual(await install_test.enter(i), arms[i])
        self.assertIsNone(await install_test.arm_for(81, True))  # adding a second device: not in the test
        self.assertIsNone(await install_test.enter(81))
        # Once in, the group stays even after the first device appears.
        await self.pool.execute("INSERT INTO devices (telegram_id, title) VALUES (1, 'Mac')")
        self.assertEqual(await install_test.arm_for(1, True), arms[1])
        self.assertEqual(await self.pool.fetchval("SELECT COUNT(*) FROM install_arms WHERE test_id=$1", test_id), 80)

    async def test_results(self):
        await self.pool.execute("INSERT INTO users (telegram_id) SELECT g FROM generate_series(1, 4) g")
        test_id = await install_test.start()
        await self.pool.execute("""INSERT INTO install_arms (test_id, telegram_id, arm, assigned_at) VALUES
            ($1, 1, 'new', NOW() - INTERVAL '2 days'), ($1, 2, 'new', NOW() - INTERVAL '2 days'),
            ($1, 3, 'old', NOW() - INTERVAL '2 days'), ($1, 4, 'old', NOW() - INTERVAL '2 hours')""", test_id)
        await self.pool.execute("""INSERT INTO onboarding_events (telegram_id, stage, created_at) VALUES
            (1, 'wizard_4', NOW() - INTERVAL '47 hours'), (3, 'wizard_4', NOW() - INTERVAL '47 hours')""")
        await self.pool.execute("UPDATE users SET first_online_at = NOW() - INTERVAL '46 hours' WHERE telegram_id = 1")
        await self.pool.execute("UPDATE users SET first_online_at = NOW() - INTERVAL '1 hour' WHERE telegram_id IN (3, 4)")
        got = (await install_test.overview())["items"][0]
        arms = {a["arm"]: a for a in got["arms"]}
        self.assertEqual((arms["new"]["users"], arms["new"]["device"], arms["new"]["connected_day"], arms["new"]["day_done"]),
                         (2, 1, 1, 2))
        # 3 connected a day too late; 4 has not finished its first day yet.
        self.assertEqual((arms["old"]["users"], arms["old"]["connected_day"], arms["old"]["day_done"], arms["old"]["connected"]),
                         (2, 0, 1, 2))
        self.assertEqual(arms["new"]["connected_day_pct"], 50.0)
        self.assertEqual([v["what"] for v in got["verdicts"]], ["Подключили VPN за сутки", "Создали ключ", "Оплатили"])
        self.assertTrue(got["running"])
        self.assertTrue(await install_test.stop())
        self.assertIsNone(await install_test.arm_for(1, False))


if __name__ == "__main__":
    unittest.main()
