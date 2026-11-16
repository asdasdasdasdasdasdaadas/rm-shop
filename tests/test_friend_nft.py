"""NFT gifts for real friends: checks, rewards, rejection, rotation. PostgreSQL parts run in PGlite."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, friend_nft


class PureTest(unittest.TestCase):
    def test_links(self):
        self.assertEqual(friend_nft.parse_link("https://t.me/nft/IceCream-162005"), ("icecream-162005", "IceCream-162005"))
        self.assertEqual(friend_nft.parse_link("nft.fragment.com/gift/lolpop-207408.webp")[0], "lolpop-207408")
        self.assertIsNone(friend_nft.parse_link("https://example.com"))

    def test_backdrop_and_attrs(self):
        lottie = {"layers": [{"nm": "Gift"}, {"nm": "Background", "shapes": [{"it": [{"ty": "gf", "g": {"p": 2, "k": {
            "a": 0, "k": [0, 0.6157, 0.4549, 0.7569, 1, 0.4745, 0.302, 0.6275]}}}]}]}]}
        self.assertEqual(friend_nft.backdrop_colors(lottie), ["#ac89ca", "#794da0", "#3c2750"])
        html = ('<meta property="og:title" content="Ice Cream #162005">'
                '<th>Model</th><td>Trio Scoop <mark>3%</mark></td><th>Backdrop</th><td>Grape <mark>1.5%</mark></td>'
                '<th>Symbol</th><td>Maple Leaf <mark>0.7%</mark></td>')
        self.assertEqual(friend_nft.page_attrs(html), ("Ice Cream", [["Модель", "Trio Scoop", "3%"], ["Фон", "Grape", "1,5%"], ["Узор", "Maple Leaf", "0,7%"]]))

    def test_rotation_moves_every_period(self):
        start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        cfg = friend_nft.normalize({"epoch": start.isoformat()})
        self.assertEqual(friend_nft.rotation(cfg, start + timedelta(hours=1))[:2], (0, 0))
        period, idx, nxt = friend_nft.rotation(cfg, start + timedelta(days=7))
        self.assertEqual((period, idx, nxt), (2, 2, start + timedelta(days=9)))
        self.assertEqual(friend_nft.rotation(cfg, start + timedelta(days=9))[1], 0)
        self.assertEqual(friend_nft.showcase(cfg, start + timedelta(days=4))[0]["name"], "Lunar Snake")

    def test_last_step_is_on_black(self):
        for gifts in friend_nft.DEFAULT_SETS:
            self.assertEqual(gifts[-1]["a"][1][1], "Onyx Black")
            self.assertEqual(len(gifts), len(friend_nft.DEFAULT["steps"]))

    def test_black_backdrop_is_pure_black(self):
        old = {"slug": "lolpop-1", "name": "Lol Pop", "bg": ["#5d6265", "#313537", "#121416"], "a": [["Модель", "X", "1%"], ["Фон", "Onyx Black", "1%"]]}
        self.assertEqual(friend_nft.normalize({"sets": [[old]]})["sets"][0][0]["bg"], friend_nft.BLACK)
        self.assertEqual(friend_nft.DEFAULT_SETS[0][-1]["bg"][-1], "#000000")
        self.assertEqual(friend_nft.paint({"a": [["Фон", "Grape", "1%"]], "bg": ["#1"]})["bg"], ["#1"])

    def test_market_page(self):
        def item(slug, ton, timer=False):
            return (f'<a href="/gift/{slug}?collection=all" class="tm-grid-item"><div>'
                    + ('<div class="tm-timer">6 days</div>' if timer else '')
                    + f'<div class="tm-grid-item-value tm-value icon-before icon-ton">{ton}</div>'
                    + '<div class="tm-grid-item-status tm-status-avail">For sale</div></div></a>')
        html = "".join([item("bigyear-1", 5, True), item("lunarsnake-2", 5), item("lunarsnake-3", 5), item("snakebox-4", "5.5"),
                        item("icecream-5", 6), item("candycane-6", "1,200")])
        rows = friend_nft.market_rows(html)
        self.assertEqual([(r["slug"], r["ton"], r["auction"]) for r in rows][:4],
                         [("bigyear-1", 5, True), ("lunarsnake-2", 5, False), ("lunarsnake-3", 5, False), ("snakebox-4", 5.5, False)])
        self.assertEqual(rows[-1]["ton"], 1200)
        # One per collection, a fixed price before an auction, the last showcase's collections only if nothing else.
        picks = friend_nft.pick_regular(rows, 3, {"icecream"}, 8)
        self.assertEqual([p["slug"] for p in picks], ["lunarsnake-2", "snakebox-4", "bigyear-1"])
        self.assertEqual([p["slug"] for p in friend_nft.pick_regular(rows, 4, {"icecream"}, 8)][-1], "icecream-5")
        self.assertIn("Onyx+Black", friend_nft.similar_url(friend_nft.DEFAULT_SETS[0][-1]))
        self.assertTrue(friend_nft.similar_url(friend_nft.DEFAULT_SETS[0][0]).endswith("/gifts/icecream?sort=price_asc&filter=sale"))

    def test_discover_skips_a_gift_that_does_not_open(self):
        def item(slug, ton):
            return (f'<a href="/gift/{slug}"><div class="tm-grid-item-value tm-value icon-before icon-ton">{ton}</div>'
                    '<div class="tm-grid-item-status tm-status-avail">For sale</div></a>')
        market = "".join(item(x, 5) for x in ["aa-1", "bb-2", "cc-3"])
        black = {"aa": item("aa-9", 12), "bb": item("bb-8", 10), "cc": ""}
        page_attrs = lambda back: ('<meta property="og:title" content="Gift #1"><th>Model</th><td>M <mark>1%</mark></td>'
                                   f'<th>Backdrop</th><td>{back} <mark>1%</mark></td><th>Symbol</th><td>S <mark>1%</mark></td>')

        class Resp:
            def __init__(self, status, text=""): self.status, self._text = status, text
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def text(self): return self._text
            async def json(self, content_type=None): return {"layers": []}

        class Http:
            def __init__(self, *a, **k): self.urls = []
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            def get(self, url, headers=None):
                if "/gifts?" in url: return Resp(200, market)
                if "/gifts/" in url: return Resp(200, black[url.split("/gifts/")[1].split("?")[0]])
                if "t.me/nft/aa-1" in url: return Resp(200, "no table")  # sold and gone
                if "t.me/nft/bb-8" in url: return Resp(200, page_attrs("Onyx Black"))
                if "t.me/nft/" in url: return Resp(200, page_attrs("Grape"))
                return Resp(200)

        import aiohttp
        store = {}
        with patch.object(aiohttp, "ClientSession", Http), \
             patch.object(db, "get_kv", AsyncMock(side_effect=lambda k: store.get(k, ""))), \
             patch.object(db, "set_kv", AsyncMock(side_effect=lambda k, v: store.__setitem__(k, v))):
            gifts = asyncio.run(friend_nft.discover(friend_nft.normalize({"steps": [1, 2, 3]})))
        self.assertEqual([g["slug"] for g in gifts], ["bb-2", "cc-3", "bb-8"])  # aa-1 skipped, the cheapest black last
        self.assertEqual((gifts[-1]["ton"], gifts[-1]["bg"], gifts[-1]["fragment"]), (10, friend_nft.BLACK, "https://fragment.com/gift/bb-8"))
        self.assertEqual(gifts[0]["bg"], ["#b48ad6", "#794da0", "#3f2457"])  # Grape is known: no animation download

    def test_validate(self):
        with self.assertRaisesRegex(ValueError, "расти"):
            friend_nft.validate(friend_nft.normalize({"steps": [5, 5, 10, 20, 40]}))
        with self.assertRaisesRegex(ValueError, "4 подарков"):
            friend_nft.validate(friend_nft.normalize({"steps": [5, 10, 20, 40]}))

    def test_verdict(self):
        cfg = friend_nft.normalize({})
        self.assertEqual(friend_nft.verdict({"online": 3}, cfg), ("ok", None))
        self.assertEqual(friend_nft.verdict({"online": 0}, cfg)[1], "за 7 дней ни разу не включал VPN")
        self.assertEqual(friend_nft.verdict({"online": 2}, cfg)[1], "включал VPN 2 дня из 7, нужно 3")
        self.assertEqual(friend_nft.verdict({"online": 5, "refunded": True}, cfg)[1], "платёж вернули")


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class FriendNftPostgresTest(unittest.IsolatedAsyncioTestCase):
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
        p = patch("app.stuck_alert._targets", AsyncMock(return_value=[999]))
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(friend_nft, "_button", return_value=None)
        p.start()
        self.addCleanup(p.stop)
        # No network in tests: Fragment «does not answer» unless a test says otherwise.
        self.discover = AsyncMock(side_effect=ValueError("Fragment не ответил"))
        p = patch.object(friend_nft, "discover", self.discover)
        p.start()
        self.addCleanup(p.stop)
        self.fetch = AsyncMock(return_value={"slug": "icecream-777", "name": "Ice Cream", "no": "777", "ton": 0, "bg": ["#1", "#2", "#3"],
                                             "a": [["Фон", "Grape", "1%"]], "link": "https://t.me/nft/IceCream-777"})
        p = patch.object(friend_nft, "fetch_gift", self.fetch)
        p.start()
        self.addCleanup(p.stop)
        self.bot = SimpleNamespace(send_message=AsyncMock())
        await self.pool.execute("INSERT INTO users (telegram_id, first_name) VALUES (1, 'Иван')")
        await friend_nft.save_config({"enabled": True, "steps": [2, 3], "sets": [s[:2] for s in friend_nft.DEFAULT_SETS]})
        # Everybody came after the promotion started.
        cfg = await friend_nft.config()
        cfg["since"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        await db.set_kv(friend_nft.KEY, json.dumps(cfg))

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def friend(self, uid, name, paid=150, ago=8, online_days=3, ref=1):
        await self.pool.execute(
            "INSERT INTO users (telegram_id, first_name, referred_by, created_at) VALUES ($1, $2, $3, NOW() - INTERVAL '10 days')",
            uid, name, ref)
        if paid:
            await self.pool.execute(
                f"""INSERT INTO payment_receipts (payment_key, telegram_id, plan_code, amount, first_payment, referral_enabled, created_at)
                VALUES ($1, $2, 'topup', $3, TRUE, TRUE, NOW() - INTERVAL '{ago} days')""", f"order:{uid}", uid, paid)
        await self.pool.execute("INSERT INTO devices (telegram_id, title) VALUES ($1, 'iPhone')", uid)
        for d in range(online_days):
            await self.pool.execute(
                f"UPDATE devices SET last_online_at = NOW() - INTERVAL '{ago - d} days' WHERE telegram_id = $1", uid)

    def texts(self):
        return [(c.args[0], c.args[1]) for c in self.bot.send_message.call_args_list]

    async def test_full_cycle(self):
        await self.friend(10, "Оля")
        await self.friend(11, "Дима", online_days=1)
        await self.friend(12, "Аня", paid=60)            # paid less than 100 ₽
        await self.friend(13, "Миша", ago=2)             # still on check
        await self.friend(14, "Катя")
        stats = await friend_nft.run_once(self.bot)
        self.assertEqual((stats["checks"], stats["ok"], stats["bad"], stats["rewards"]), (4, 2, 1, 1))
        said = self.texts()
        self.assertTrue(any("Миша оплатил(а) VPN" in t for _, t in said))
        self.assertTrue(any("Дима</b> не засчитан(а): включал VPN 1 день из 7, нужно 3" in t for _, t in said))
        self.assertTrue(any("Это ваш 2-й настоящий друг" in t and "Ice Cream" in t for _, t in said))
        self.assertTrue(any(chat == 999 and "Выдать NFT" in t for chat, t in said))

        view = await friend_nft.user_view(1)
        self.assertEqual((view["counted"], view["checking"]), (2, 1))
        self.assertEqual([s["state"] for s in view["steps"]], ["wait", "none"])
        by_name = {f["name"]: f for f in view["friends"]}
        self.assertEqual((by_name["Миша"]["st"], by_name["Миша"]["day"]), ("check", 2))
        self.assertEqual(by_name["Аня"]["st"], "pay")

        # Nothing new on the second run.
        self.bot.send_message.reset_mock()
        self.assertEqual((await friend_nft.run_once(self.bot))["checks"], 0)
        self.bot.send_message.assert_not_called()

        # The admin finds Катя is Иван's second account: the gift that was not given yet is cancelled.
        await friend_nft.set_friend(self.bot, 14, "bad", "это ваш второй аккаунт")
        self.assertEqual([s["state"] for s in (await friend_nft.user_view(1))["steps"]], ["none", "none"])
        self.assertIn("Подарок за этот шаг снят", self.texts()[-1][1])

        # Counted back: the gift comes again; then the admin gives it with the link.
        await friend_nft.set_friend(self.bot, 14, "ok")
        reward = (await friend_nft.rewards_of(1))[0]
        await friend_nft.give(self.bot, reward["id"], "t.me/nft/IceCream-777")
        self.assertIn("Подарок у вас", self.texts()[-1][1])
        self.assertIn("Ice Cream #777", self.texts()[-1][1])  # the gift actually bought, not the shown number
        view = await friend_nft.user_view(1)
        self.assertEqual((view["steps"][0]["state"], view["steps"][0]["nft_link"]), ("got", "https://t.me/nft/IceCream-777"))
        self.assertEqual((view["steps"][0]["gift"]["no"], view["steps"][0]["gift"]["ton"]), ("777", 5))
        with self.assertRaisesRegex(ValueError, "уже выдан"):
            await friend_nft.give(self.bot, reward["id"], "")
        overview = await friend_nft.admin_overview()
        self.assertEqual(overview["totals"]["given"], 1)

    async def test_earned_gift_stays_after_rotation_and_off(self):
        await self.friend(10, "Оля")
        await self.friend(11, "Дима")
        await friend_nft.run_once(self.bot)
        await friend_nft.rotate_now()
        steps = (await friend_nft.user_view(1))["steps"]
        self.assertEqual([s["gift"]["name"] for s in steps], ["Ice Cream", "Spiced Wine"])
        await friend_nft.save_config({"enabled": False})
        view = await friend_nft.user_view(1)
        self.assertEqual((view["enabled"], [r["gift"]["name"] for r in view["rewards"]]), (False, ["Ice Cream"]))
        self.assertEqual(await friend_nft.run_once(self.bot), {"checks": 0, "ok": 0, "bad": 0, "rewards": 0})

    async def test_old_users_and_self_do_not_count(self):
        cfg = await friend_nft.config()
        cfg["since"] = datetime.now(timezone.utc).isoformat()
        await db.set_kv(friend_nft.KEY, json.dumps(cfg))
        await self.friend(10, "Оля")  # came 10 days ago, before the promotion
        self.assertEqual((await friend_nft.run_once(self.bot))["checks"], 0)
        self.assertEqual((await friend_nft.user_view(1))["friends"][0]["st"], "old")

    async def test_showcase_found_on_fragment(self):
        found = [dict(g, slug=f"x{i}-1", name=f"Найден {i}") for i, g in enumerate(friend_nft.DEFAULT_SETS[1][:2])]
        self.discover.side_effect = None
        self.discover.return_value = found
        cfg = await friend_nft.config()
        await friend_nft.refresh_live(cfg)
        self.assertEqual([g["name"] for g in friend_nft.showcase(await friend_nft.config())], ["Найден 0", "Найден 1"])
        self.assertEqual(self.discover.await_count, 1)
        await friend_nft.refresh_live(await friend_nft.config())  # found already: Fragment is not asked again
        self.assertEqual(self.discover.await_count, 1)
        # A new rotation start drops it; a failure falls back to the saved sets and waits half an hour.
        await friend_nft.rotate_now()
        self.discover.side_effect = ValueError("нет сети")
        cfg = await friend_nft.config()
        await friend_nft.refresh_live(cfg)
        self.assertEqual(friend_nft.showcase(cfg)[0]["name"], "Lunar Snake")
        self.assertEqual(cfg["live"]["error"], "нет сети")
        await friend_nft.refresh_live(await friend_nft.config())
        self.assertEqual(self.discover.await_count, 2)
        # Off: the saved sets.
        await friend_nft.save_config({"auto": False})
        self.assertEqual(friend_nft.showcase(await friend_nft.config())[0]["name"], "Lunar Snake")

    async def test_next_showcase_is_found_ahead(self):
        self.discover.side_effect = None
        self.discover.return_value = friend_nft.DEFAULT_SETS[2][:2]
        cfg = await friend_nft.config()
        cfg["epoch"] = (datetime.now(timezone.utc) - timedelta(days=3) + timedelta(minutes=10)).isoformat()
        await db.set_kv(friend_nft.KEY, json.dumps({k: v for k, v in cfg.items() if k != "live"}))
        live = await friend_nft.refresh_live(await friend_nft.config())
        self.assertEqual(sorted(live["by_period"]), ["0", "1"])
        later = datetime.now(timezone.utc) + timedelta(minutes=11)
        self.assertEqual(friend_nft.showcase(await friend_nft.config(), later)[0]["name"], "B-Day Candle")

    async def test_rotation_announces_once(self):
        await self.friend(10, "Оля", paid=0)
        await friend_nft.run_once(self.bot)  # remembers the period
        await friend_nft.rotate_now()
        self.bot.send_message.reset_mock()
        cfg = await friend_nft.config()
        await friend_nft._rotation_tick(self.bot, cfg)
        await asyncio.sleep(0.2)
        self.assertEqual(self.bot.send_message.await_count, 1)
        self.assertIn("Новые NFT-подарки", self.texts()[0][1])
        await friend_nft._rotation_tick(self.bot, cfg)
        await asyncio.sleep(0.1)
        self.assertEqual(self.bot.send_message.await_count, 1)


if __name__ == "__main__":
    unittest.main()
