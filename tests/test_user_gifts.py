import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import user_gifts as ug


def sticker(fid="s1", thumb="t1", animated=True):
    return SimpleNamespace(file_id=fid, emoji="🧸", is_animated=animated, is_video=False,
                           thumbnail=SimpleNamespace(file_id=thumb) if thumb else None)


def regular(stars, limited=False):
    return SimpleNamespace(type="regular", send_date=1, gift=SimpleNamespace(
        star_count=stars, total_count=100 if limited else None, sticker=sticker()))


def unique(per_mille, *, burned=False):
    return SimpleNamespace(type="unique", send_date=2, gift=SimpleNamespace(
        base_name="Plush Pepe", number=42, name="PlushPepe-42", is_burned=burned, is_from_blockchain=False,
        model=SimpleNamespace(name="Frog", rarity_per_mille=per_mille, rarity="rare", sticker=sticker("m1", "mt")),
        backdrop=SimpleNamespace(name="Emerald", colors=SimpleNamespace(center_color=0x5FD38D, edge_color=0x16804A)),
        symbol=SimpleNamespace(name="Crown")))


class UserGiftsTest(unittest.TestCase):
    def test_simplify_regular_and_unique(self):
        r = ug.simplify(regular(50, limited=True))
        self.assertEqual((r["kind"], r["stars"], r["limited"], r["thumb"], r["title"]), ("regular", 50, True, "t1", "🧸"))
        u = ug.simplify(unique(8))
        self.assertEqual((u["title"], u["slug"], u["model"], u["center"], u["edge"], u["thumb"]),
                         ("Plush Pepe #42", "PlushPepe-42", "Frog", "#5fd38d", "#16804a", "mt"))

    def test_animated_sticker_without_preview_has_no_image(self):
        self.assertIsNone(ug._thumb(sticker(thumb=None)))
        self.assertEqual(ug._thumb(sticker(thumb=None, animated=False)), "s1")

    def test_rating_levels(self):
        self.assertEqual(ug.summarize([])["level"], 0)
        self.assertEqual(ug.summarize([ug.simplify(regular(50))])["label"], "Скромный")
        common = ug.summarize([ug.simplify(unique(200))])
        self.assertEqual((common["level"], common["points"]), (3, 2500))
        rare = ug.summarize([ug.simplify(unique(5)), ug.simplify(unique(10)), ug.simplify(regular(100))])
        self.assertEqual((rare["points"], rare["level"], rare["rare_count"], rare["unique_count"]),
                         (2500 * 6 + 2500 * 3 + 100, 4, 2, 2))
        burned = ug.summarize([ug.simplify(unique(5, burned=True))])
        self.assertEqual(burned["level"], 0)


class UserGiftsFetchTest(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_fetch_is_stored_and_errors_keep_the_cache(self):
        page = SimpleNamespace(total_count=2, gifts=[regular(50), unique(200)], next_offset=None)
        bot = AsyncMock(return_value=page)
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value=None), execute=AsyncMock())
        with patch.object(ug.db, "_pool_req", return_value=pool):
            data = await ug.user_gifts(bot, 7)
        self.assertEqual(len(data["gifts"]), 2)
        self.assertEqual(data["summary"]["level"], 3)
        stored = pool.execute.await_args.args
        self.assertEqual((stored[1], stored[3]), (7, 3))
        self.assertEqual(json.loads(stored[2])["summary"]["points"], 2550)

        cached = {"data": json.dumps(data | {"fetched_at": 0}), "at": 0}
        pool = SimpleNamespace(fetchrow=AsyncMock(return_value=cached), execute=AsyncMock())
        bot = AsyncMock(side_effect=RuntimeError("Bad Request: user not found"))
        with patch.object(ug.db, "_pool_req", return_value=pool):
            data = await ug.user_gifts(bot, 7)
        self.assertEqual(len(data["gifts"]), 2)
        self.assertIn("Telegram не отдал подарки", data["error"])


class GiftsScanTest(unittest.IsolatedAsyncioTestCase):
    async def test_scan_stores_results_and_errors_and_waits_on_flood(self):
        from aiogram.exceptions import TelegramRetryAfter
        from aiogram.methods import GetUserGifts
        pool = SimpleNamespace(execute=AsyncMock())
        with patch.object(ug.db, "_pool_req", return_value=pool):
            ok = AsyncMock(return_value=SimpleNamespace(total_count=1, gifts=[unique(200)], next_offset=None))
            self.assertEqual(await ug.scan_one(ok, 7), ug.SCAN_EVERY_SECONDS)
            self.assertEqual(pool.execute.await_args.args[3], 3)
            broken = AsyncMock(side_effect=RuntimeError("Bad Request: user not found"))
            self.assertEqual(await ug.scan_one(broken, 8), ug.SCAN_EVERY_SECONDS)
            self.assertIn("user not found", json.loads(pool.execute.await_args.args[2])["error"])
            calls = pool.execute.await_count
            flood = AsyncMock(side_effect=TelegramRetryAfter(method=GetUserGifts(user_id=9), message="Flood", retry_after=30))
            self.assertEqual(await ug.scan_one(flood, 9), 31)
            self.assertEqual(pool.execute.await_count, calls)  # nothing stored: try this user again later


if __name__ == "__main__":
    unittest.main()
