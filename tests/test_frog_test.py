"""The living frog's A/B test: who sees the frog, what is kept, and how the verdict reads."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, frog_test


def arm(users, ret_done, returned, players=0, fans=0, topups=0, payers=0, rub=0):
    return {"users": users, "ret_done": ret_done, "returned": returned, "active_days": users, "players": players,
            "fans": fans, "plays": players * 3, "topup_clickers": topups, "payers": payers, "rub": rub}


class VerdictTest(unittest.TestCase):
    def bottom(self, plain, frog):
        return frog_test.summarize({"plain": plain, "frog": frog})["verdicts"][0]["verdict"]

    def test_pulls_when_more_come_back(self):
        self.assertTrue(self.bottom(arm(400, 400, 80), arm(400, 400, 140, players=200)).startswith("Притягивает"))

    def test_puts_off_when_fewer_come_back_or_top_up(self):
        self.assertTrue(self.bottom(arm(400, 400, 140), arm(400, 400, 80)).startswith("Отталкивает"))
        self.assertIn("реже пополняют", self.bottom(arm(400, 400, 100, topups=120), arm(400, 400, 100, topups=60)))

    def test_leaves_cold_when_nobody_plays(self):
        self.assertTrue(self.bottom(arm(200, 200, 50), arm(200, 200, 52, players=10)).startswith("Похоже, пофиг"))

    def test_too_early(self):
        self.assertTrue(self.bottom(arm(10, 2, 1), arm(10, 2, 1)).startswith("Пока рано"))
        self.assertEqual(frog_test.summarize({})["verdicts"], [])

    def test_rates(self):
        frog = frog_test.summarize({"plain": arm(10, 10, 2), "frog": arm(10, 5, 2, players=4, fans=1)})["arms"][1]
        self.assertEqual((frog["return_pct"], frog["play_pct"], frog["fan_pct"]), (40.0, 40.0, 10.0))


class PeopleFieldTest(unittest.TestCase):
    def test_ids_and_usernames_are_cleaned(self):
        from app.shop_config import _as_people
        self.assertEqual(_as_people("123,  @Kva_Kva\nhttps://t.me/frogfan 123", "x"), "123, @kva_kva, @frogfan")
        self.assertEqual(_as_people("", "x"), "")
        with self.assertRaises(ValueError):
            _as_people("лягушка", "x")


class ViewTest(unittest.IsolatedAsyncioTestCase):
    async def test_outside_a_test_the_switch_decides_and_admins_always_see_it(self):
        with patch.object(frog_test, "running", AsyncMock(return_value=None)):
            off = SimpleNamespace(frog_enabled=False, admin_id_set={1}, frog_user_ids="")
            with patch.object(frog_test, "get_settings", return_value=off):
                self.assertEqual(await frog_test.view(7), {"on": False, "ab": None})
                self.assertEqual(await frog_test.view(1), {"on": True, "ab": None})
            with patch.object(frog_test, "get_settings", return_value=SimpleNamespace(frog_enabled=True, admin_id_set=set(), frog_user_ids="")):
                self.assertEqual(await frog_test.view(7), {"on": True, "ab": None})

    async def test_listed_people_always_see_it_and_stay_out_of_the_test(self):
        listed = SimpleNamespace(frog_enabled=False, admin_id_set=set(), frog_user_ids="42, @Kva_Kva")
        pool = SimpleNamespace(fetchval=AsyncMock(return_value="kva_kva"))
        test = AsyncMock(return_value={"id": 1})
        with patch.object(frog_test, "get_settings", return_value=listed), patch.object(frog_test, "running", test), \
                patch.object(frog_test.db, "_pool_req", return_value=pool):
            self.assertEqual(await frog_test.view(42), {"on": True, "ab": None})
            self.assertEqual(await frog_test.view(7), {"on": True, "ab": None})
            test.assert_not_awaited()
            pool.fetchval = AsyncMock(return_value=None)
            self.assertFalse(await frog_test.listed(8))

    async def test_unknown_event(self):
        with self.assertRaises(ValueError):
            await frog_test.record(7, "hack")


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class FrogTestDb(unittest.IsolatedAsyncioTestCase):
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

    async def test_groups_stick_and_events_count_per_day(self):
        await self.pool.execute("INSERT INTO users (telegram_id) SELECT g FROM generate_series(1, 80) g")
        self.assertFalse(await frog_test.record(1, "open"))   # no test: nothing kept
        await frog_test.start()
        with self.assertRaises(ValueError):
            await frog_test.start()
        views = {i: await frog_test.view(i) for i in range(1, 81)}
        self.assertEqual({v["ab"] for v in views.values()}, {"frog", "plain"})
        self.assertTrue(all(v["on"] == (v["ab"] == "frog") for v in views.values()))
        self.assertEqual(await frog_test.view(1), views[1])
        for kind in ("open", "open", "play", "topup"):
            self.assertTrue(await frog_test.record(1, kind))
        row = await self.pool.fetchrow("SELECT opens, plays, topups FROM frog_days WHERE telegram_id=1")
        self.assertEqual((row["opens"], row["plays"], row["topups"]), (2, 1, 1))
        await frog_test.stop()
        self.assertFalse(await frog_test.record(1, "open"))

    async def test_results_count_returns_on_another_day(self):
        await self.pool.execute("INSERT INTO users (telegram_id) SELECT g FROM generate_series(1, 3) g")
        test_id = await frog_test.start()
        await self.pool.execute("""INSERT INTO frog_arms (test_id, telegram_id, arm, assigned_at) VALUES
            ($1, 1, 'frog', NOW() - INTERVAL '5 days'), ($1, 2, 'frog', NOW() - INTERVAL '5 days'),
            ($1, 3, 'plain', NOW() - INTERVAL '5 days')""", test_id)
        await self.pool.execute("""INSERT INTO frog_days (test_id, telegram_id, day, opens, plays) VALUES
            ($1, 1, ((NOW() - INTERVAL '5 days') AT TIME ZONE 'Europe/Moscow')::date, 1, 6),
            ($1, 1, ((NOW() - INTERVAL '4 days') AT TIME ZONE 'Europe/Moscow')::date, 2, 0),
            ($1, 2, ((NOW() - INTERVAL '5 days') AT TIME ZONE 'Europe/Moscow')::date, 1, 0)""", test_id)
        item = (await frog_test.overview())["items"][0]
        plain, frog = item["arms"]
        self.assertEqual((frog["users"], frog["ret_done"], frog["returned"], frog["players"], frog["fans"]), (2, 2, 1, 1, 1))
        self.assertEqual((plain["users"], plain["returned"]), (1, 0))


if __name__ == "__main__":
    unittest.main()
