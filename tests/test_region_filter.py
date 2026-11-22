"""Iran: newcomers with the Persian interface or name are turned away before they reach the base."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, region_filter


class DetectTest(unittest.TestCase):
    def test_language_and_persian_letters(self):
        self.assertEqual(region_filter.suspicious("fa", "Ali"), "язык fa")
        self.assertEqual(region_filter.suspicious("fa-IR", None), "язык fa")
        self.assertEqual(region_filter.suspicious("en", "علی"), "имя")          # Persian ye
        self.assertEqual(region_filter.suspicious(None, "x", "پویا"), "имя")
        self.assertEqual(region_filter.suspicious("ar", "علي"), "")             # Arabic ye: not Iran
        self.assertEqual(region_filter.suspicious("ru", "Аня"), "")
        self.assertEqual(region_filter.suspicious(None, None), "")


def user(uid, lang="en", name="Ann"):
    return SimpleNamespace(id=uid, language_code=lang, first_name=name, last_name=None, username=None, is_bot=False)


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class FilterDb(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        s = SimpleNamespace(region_filter_enabled=True, admin_id_set={1})
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(region_filter, "get_settings", return_value=s),
                  patch.object(region_filter, "_cache", {})):
            p.start()
            self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def send(self, u, text="/start"):
        msg = SimpleNamespace(from_user=u, chat=SimpleNamespace(type="private"), text=text, answer=AsyncMock())
        handler = AsyncMock(return_value="handled")
        got = await region_filter.RegionFilterMiddleware()(handler, msg, {})
        return got, handler, msg

    async def test_newcomer_from_iran_gets_one_reply_and_no_user_row(self):
        got, handler, msg = await self.send(user(50, "fa", "Reza"))
        self.assertIsNone(got)
        handler.assert_not_awaited()
        msg.answer.assert_awaited_once_with(region_filter.REPLY)
        region_filter._cache.clear()   # even after a restart: no second reply
        _, handler, msg = await self.send(user(50, "fa", "Reza"), "hi")
        handler.assert_not_awaited()
        msg.answer.assert_not_awaited()
        self.assertIsNone(await self.pool.fetchval("SELECT 1 FROM users WHERE telegram_id=50"))
        self.assertEqual(await self.pool.fetchval("SELECT hits FROM region_rejects WHERE telegram_id=50"), 2)
        # the admin lets them in
        self.assertTrue(await region_filter.allow(50))
        _, handler, _ = await self.send(user(50, "fa", "Reza"))
        handler.assert_awaited_once()

    async def test_others_existing_users_and_admins_pass(self):
        for u in (user(60, "ru", "Аня"), user(1, "fa", "Admin")):
            got, handler, _ = await self.send(u)
            self.assertEqual(got, "handled")
        await self.pool.execute("INSERT INTO users (telegram_id, first_name) VALUES (70, 'پویا')")
        got, _, _ = await self.send(user(70, "fa", "پویا"))
        self.assertEqual(got, "handled")   # already in the base: sorted out from the admin

    async def test_admin_finds_unpaid_persian_names(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, has_paid_topup) VALUES
            (70, 'پویا', FALSE), (71, 'مهدی', TRUE), (72, 'Аня', FALSE), (1, 'گل', FALSE)""")
        view = await region_filter.overview()
        self.assertEqual([c["telegram_id"] for c in view["candidates"]], [70])
        await region_filter.remember(70, "پویا", None, "чистка в админке")
        self.assertEqual((await region_filter.overview())["rejected"], 1)


if __name__ == "__main__":
    unittest.main()
