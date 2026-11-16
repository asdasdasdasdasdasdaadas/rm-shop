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
        await friend_nft.give(self.bot, reward["id"], "t.me/nft/IceCream-162005")
        self.assertIn("Подарок у вас", self.texts()[-1][1])
        view = await friend_nft.user_view(1)
        self.assertEqual((view["steps"][0]["state"], view["steps"][0]["nft_link"]), ("got", "https://t.me/nft/IceCream-162005"))
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
