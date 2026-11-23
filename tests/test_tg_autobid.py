"""Telegram Ads: the autobid keeps the lowest CPM that still gets views, alerts and the «Рост» cabinet queries."""
import asyncio
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, tg_autobid, tg_cabinet
from app.tg_autobid import decide

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
ACTIVE = {"cpm": "2.00", "status": "active", "is_paused": False, "remaining": "1"}


def tg_ads_error():
    from app.tg_ads import TgAdsError
    return TgAdsError("DAILY_BUDGET_LIMIT_INVALID")


def views(*pairs):
    """(minutes ago, views) → the 5-minute buckets decide() reads."""
    return [(NOW - timedelta(minutes=m), v) for m, v in pairs]


class DecideTest(unittest.TestCase):
    def test_no_views_raises_by_a_step_within_the_ceiling(self):
        got = decide({"max_cpm": "3", "changed_at": NOW - timedelta(hours=1)}, ACTIVE, [], NOW)
        self.assertEqual((got["action"], got["cpm"], got["state"]), ("set", Decimal("2.30"), "searching"))
        got = decide({"max_cpm": "2.1", "changed_at": NOW - timedelta(hours=1)}, ACTIVE, [], NOW)
        self.assertEqual(got["cpm"], Decimal("2.1"))

    def test_waits_after_a_change(self):
        got = decide({"max_cpm": "3", "changed_at": NOW - timedelta(minutes=10), "state": "searching"}, ACTIVE, [], NOW)
        self.assertEqual((got["action"], got["state"]), ("none", "searching"))

    def test_steady_views_try_cheaper_but_not_below_the_floor(self):
        flow = views((90, 3), (30, 2))
        got = decide({"max_cpm": "3", "changed_at": NOW - timedelta(hours=3)}, ACTIVE, flow, NOW)
        self.assertEqual((got["action"], got["cpm"], got["state"], got["good_cpm"]), ("set", Decimal("1.86"), "probing", Decimal("2.00")))
        got = decide({"max_cpm": "3", "changed_at": NOW - timedelta(hours=3), "floor_cpm": "1.95",
                      "floor_until": NOW + timedelta(hours=1)}, ACTIVE, flow, NOW)
        self.assertEqual(got["cpm"], Decimal("1.95"))
        # Views only in the last hour: not steady yet, hold.
        got = decide({"max_cpm": "3", "changed_at": NOW - timedelta(hours=3)}, ACTIVE, views((20, 4)), NOW)
        self.assertEqual((got["action"], got["state"]), ("none", "holding"))

    def test_views_stopped_after_lowering_go_back_and_set_the_floor(self):
        ab = {"max_cpm": "3", "changed_at": NOW - timedelta(hours=1), "state": "probing", "good_cpm": "2.00"}
        got = decide(ab, {**ACTIVE, "cpm": "1.86"}, [], NOW)
        self.assertEqual((got["action"], got["cpm"], got["floor_cpm"], got["state"]), ("set", Decimal("2.00"), Decimal("2.00"), "holding"))

    def test_dead_at_the_ceiling(self):
        ab = {"max_cpm": "2", "changed_at": NOW - timedelta(hours=4)}
        self.assertEqual(decide(ab, ACTIVE, [], NOW)["state"], "dead")
        self.assertEqual(decide({**ab, "changed_at": NOW - timedelta(hours=1)}, ACTIVE, [], NOW)["state"], "ceiling")

    def test_dead_goes_back_to_the_working_price_and_stays(self):
        ab = {"max_cpm": "4", "changed_at": NOW - timedelta(hours=4), "good_cpm": "2.5", "base_cpm": "2"}
        got = decide(ab, {**ACTIVE, "cpm": "4"}, [], NOW)
        self.assertEqual((got["action"], got["cpm"], got["state"]), ("set", Decimal("2.5"), "dead"))
        got = decide({**ab, "good_cpm": None}, {**ACTIVE, "cpm": "4"}, [], NOW)
        self.assertEqual(got["cpm"], Decimal("2"))
        # Back at 2.5 and still silent: no raising again, the place is dead.
        later = {**ab, "state": "dead", "changed_at": NOW - timedelta(hours=1), "note": "площадка не крутит"}
        got = decide(later, {**ACTIVE, "cpm": "2.5"}, [], NOW)
        self.assertEqual((got["action"], got["state"]), ("none", "dead"))
        got = decide({**later, "changed_at": NOW - timedelta(minutes=5)}, {**ACTIVE, "cpm": "2.5"}, [], NOW)
        self.assertEqual(got["state"], "dead")
        # The place came back: normal work.
        got = decide(later, {**ACTIVE, "cpm": "2.5"}, views((20, 3)), NOW)
        self.assertEqual(got["state"], "holding")

    def test_person_cap(self):
        # 100 ₽ for 1 TON; 10 people per 1000 views; a person at most 20 ₽ → CPM at most 0.2 × 10 = 2.
        cap, note = tg_autobid.person_cap(20, 100, 3000, 30)
        self.assertEqual(cap, Decimal("2.00"))
        self.assertIn("20 ₽", note)
        self.assertEqual(tg_autobid.person_cap(20, 100, 3000, 1)[0], None)
        self.assertEqual(tg_autobid.person_cap(20, 100, 6000, 0)[0], Decimal(0))
        self.assertEqual(tg_autobid.person_cap(None, 100, 3000, 30)[0], None)
        self.assertEqual(tg_autobid.person_cap(20, None, 3000, 30)[0], None)

    def test_person_cap_lowers_and_holds_the_bid(self):
        ab = {"max_cpm": "4", "changed_at": NOW - timedelta(hours=1)}
        got = decide(ab, {**ACTIVE, "cpm": "3"}, views((20, 3)), NOW, Decimal("2"), "дорого")
        self.assertEqual((got["action"], got["cpm"], got["state"]), ("set", Decimal("2"), "expensive"))
        # No views at the cap: the ceiling is the cap, so no raising above it.
        got = decide(ab, {**ACTIVE, "cpm": "2"}, [], NOW, Decimal("2"), "дорого")
        self.assertEqual(got["action"], "none")
        # Many views, nobody came: never raise.
        got = decide(ab, {**ACTIVE, "cpm": "2"}, [], NOW, Decimal(0), "5 000 показов и ни одного человека")
        self.assertEqual((got["action"], got["state"]), ("none", "expensive"))

    def test_never_touches_ads_in_review_or_paused(self):
        for ad, state in (({**ACTIVE, "status": "in_review"}, "review"), ({**ACTIVE, "is_paused": True}, "paused"),
                          ({**ACTIVE, "status": "on_hold", "remaining": "0"}, "empty")):
            got = decide({"max_cpm": "3"}, ad, [], NOW)
            self.assertEqual((got["action"], got["state"]), ("none", state))

    def test_ceiling_defaults_to_the_start_plus_30_and_never_above_the_hard_max(self):
        self.assertEqual(tg_autobid.ceiling({}, Decimal("1.5")), Decimal("1.95"))
        self.assertEqual(tg_autobid.ceiling({"max_cpm": "4"}, Decimal("1.5")), Decimal("4"))
        self.assertEqual(tg_autobid.ceiling({}, Decimal("10")), Decimal("5"))
        self.assertEqual(tg_autobid.ceiling({"max_cpm": "20"}, Decimal("10")), Decimal("5"))

    def test_a_bid_above_the_ceiling_comes_down(self):
        got = decide({"max_cpm": "20", "changed_at": NOW - timedelta(hours=1)}, {**ACTIVE, "cpm": "10"}, views((20, 3)), NOW)
        self.assertEqual((got["action"], got["cpm"]), ("set", Decimal("5")))

    def test_suggested_limit(self):
        self.assertEqual(tg_autobid.suggested_limit("4"), Decimal("2.00"))
        self.assertEqual(tg_autobid.suggested_limit("0.6"), Decimal("0.5"))
        self.assertEqual(tg_autobid.suggested_limit("0.3"), Decimal("0.3"))
        self.assertIsNone(tg_autobid.suggested_limit("0"))


class AlertsTest(unittest.TestCase):
    def test_alerts(self):
        ad = {"ad_id": 1, "title": "Боты", "status": "declined", "decline_reason": "Запрещённый контент", "remaining": "1"}
        self.assertIn("Запрещённый контент", tg_autobid.alerts_for(ad, {}, Decimal(0))["declined"])
        ad = {"ad_id": 1, "title": "Боты", "status": "active", "remaining": "0.1", "currency": "TON"}
        self.assertIn("low", tg_autobid.alerts_for(ad, {"state": "dead"}, Decimal("1")))
        self.assertIn("dead", tg_autobid.alerts_for(ad, {"state": "dead"}, Decimal("1")))
        self.assertEqual(tg_autobid.alerts_for(ad, {}, Decimal("0.2")), {})
        self.assertIn("хватит примерно на 2 ч", tg_autobid.alerts_for(ad, {}, Decimal("1"))["low"])

    def test_days_left(self):
        self.assertEqual(tg_autobid.days_left("1", "0.5"), 2.0)
        self.assertIsNone(tg_autobid.days_left("1", "0"))
        self.assertIsNone(tg_autobid.days_left("0", "1"))

    def test_digest_text(self):
        d = {"day": date(2026, 11, 22), "views": 1200, "clicks": 30, "spent": Decimal("2.4"), "currency": "TON",
             "users": 12, "paid": 2, "moves": 5,
             "best": {"title": "Боты: hitvpn", "per_user": Decimal("0.1"), "spent": Decimal("1")},
             "worst": {"title": "Боты: инста", "per_user": None, "spent": Decimal("0.5")}}
        text = tg_autobid.format_digest(d)
        self.assertIn("2.40 TON", text)
        self.assertIn("Пришли в бота: <b>12</b>", text)
        self.assertIn("0.50 TON и никого", text)
        self.assertIn("меняла цену 5 раз", text)
        self.assertNotIn("Скоро кончится", text)
        text = tg_autobid.format_digest({**d, "ending": [{"title": "Каналы", "days": 0.25, "remaining": Decimal("0.3")},
                                                          {"title": "Боты", "days": 1.5, "remaining": Decimal("1")}]})
        self.assertIn("Каналы — 0.30 TON, хватит на ~6 ч", text)
        self.assertIn("Боты — 1.00 TON, хватит на ~1,5 дн", text)
        self.assertIsNone(tg_autobid.format_digest({**d, "spent": Decimal(0), "users": 0}))


class HelpersTest(unittest.TestCase):
    def test_username(self):
        for raw in ("@hitvpnbot", "t.me/hitvpnbot", "https://t.me/hitvpnbot?start=x", "hitvpnbot"):
            self.assertEqual(tg_cabinet.username_of(raw), "hitvpnbot")
        self.assertIsNone(tg_cabinet.username_of("not a name!"))

    def test_target_summary(self):
        t = {"type": "bots", "bots": [{"username": "a_bot", "title": "A"}, {"username": "b_bot", "title": ""}]}
        s = tg_cabinet.target_summary(t)
        self.assertEqual(s["kind"], "bots")
        self.assertEqual(s["text"], "A, @b_bot")
        s = tg_cabinet.target_summary('{"type":"channels","languages":[{"name":"Russian"}],"topics":[{"name":"Games"}]}')
        self.assertEqual(s["text"], "Russian · Games")


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class CabinetDb(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        query = self.pool.query

        async def plain(sql, args=(), script=False):   # the bridge speaks JSON: Decimal goes as text
            return await query(sql, tuple(str(a) if isinstance(a, Decimal) else a for a in args), script)
        self.pool.query = plain

        async def executemany(sql, rows):
            for r in rows:
                await self.pool.execute(sql, *r)
        self.pool.executemany = executemany
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        s = SimpleNamespace(bot_username="frog_bot", tg_ads_token="t", tg_ads_rub_rate=0)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(tg_cabinet, "get_settings", return_value=s),
                  patch("app.tg_ads.get_settings", return_value=s)):
            p.start()
            self.addCleanup(p.stop)
        link = await db.create_ad_link("Боты", "bots_hit")
        self.link = link["id"]
        ad = {"ad_id": 23, "title": "Боты: hitvpn", "promote_url": "t.me/frog_bot?start=ad_bots_hit", "status": "active",
              "cpm": 2.5, "spent_budget": 0.4, "remaining_budget": 1.1, "views": 160, "clicks": 9, "text": "Месяц оплачен",
              "created_date": int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp()),
              "target": {"type": "bots", "bots": [{"username": "hitvpnbot", "title": "HIT VPN"}]}}
        from app import tg_ads
        await db.save_tg_ads([ad], "TON", Decimal(100), tg_ads.slug_from_url)
        now = int(datetime.now(timezone.utc).timestamp())
        items = [{"from_time": now - now % 300 - 300 * i, "views": 5, "clicks": 1 if i == 0 else 0, "spent_budget": 0.01}
                 for i in range(6)]
        with patch.object(tg_ads, "call", AsyncMock(return_value=items)):
            self.assertEqual(await tg_ads.sync_stats([ad]), 6)
        await self.pool.execute(
            "INSERT INTO users (telegram_id, username, first_name, ad_link_id) VALUES (7, 'a', 'A', $1)", self.link)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_cabinet_hours_places(self):
        cab = await tg_cabinet.cabinet("today")
        self.assertEqual(cab["tiles"]["views"]["value"], 30)
        self.assertEqual(cab["tiles"]["users"]["value"], 1)
        self.assertEqual(len(cab["tiles"]["views"]["series"]), 24)
        ad = cab["ads"][0]
        self.assertEqual((ad["ad_id"], ad["link"]["slug"], ad["views_hour"]), (23, "bots_hit", 30))
        self.assertEqual(ad["target"]["text"], "HIT VPN")
        self.assertEqual(ad["autobid"]["state"], "idle")
        h = await tg_cabinet.hours()
        self.assertEqual(sum(map(sum, h["views"])), 30)
        self.assertEqual(sum(map(sum, h["users"])), 1)
        p = await tg_cabinet.places()
        self.assertEqual((p["items"][0]["username"], p["items"][0]["verdict"]), ("hitvpnbot", "крутится"))

    async def test_greeting_only_for_people_from_the_link(self):
        await tg_cabinet.set_greeting(self.link, "Соцсети заработают через минуту")
        self.assertEqual(await db.ad_link_greeting(self.link, 7), "Соцсети заработают через минуту")
        self.assertEqual(await db.ad_link_greeting(self.link, 8), "")

    async def test_autobid_raises_a_silent_ad_and_logs(self):
        await self.pool.execute("DELETE FROM tg_ad_stats")
        with patch("app.tg_ads.call", AsyncMock(return_value={"ad_id": 23, "status": "active", "daily_budget_limit": 0.55})) as call:
            out = await tg_cabinet.set_autobid(23, True, 3)
        # No daily limit on the ad: half of what is left (1.1) is set with the autobid.
        call.assert_awaited_once_with("editAd", ad_id=23, daily_budget_limit=0.55)
        self.assertEqual((out["max_cpm"], out["daily_limit"]), (3.0, 0.55))
        edited = {"ad_id": 23, "cpm": 2.88, "status": "active"}
        with patch("app.tg_ads.call", AsyncMock(return_value=edited)) as call:
            self.assertEqual(await tg_autobid.run_autobid(datetime.now(timezone.utc)), 1)
        call.assert_awaited_once_with("editAd", ad_id=23, cpm=2.88)
        row = await self.pool.fetchrow("SELECT state, enabled FROM tg_ad_autobid WHERE ad_id = 23")
        self.assertEqual((row["state"], row["enabled"]), ("searching", True))
        log = await self.pool.fetch("SELECT who, action FROM tg_ad_log WHERE ad_id = 23 ORDER BY id")
        self.assertEqual([(r["who"], r["action"]) for r in log], [("admin", "autobid_on"), ("admin", "daily_limit"), ("bot", "cpm")])

    async def test_price_change_sent_to_review_turns_the_autobid_off(self):
        await self.pool.execute("DELETE FROM tg_ad_stats")
        with patch("app.tg_ads.call", AsyncMock(side_effect=tg_ads_error())):
            out = await tg_cabinet.set_autobid(23, True, 3)
        self.assertIn("Дневной лимит не поставился", out["limit_error"])   # the autobid is on all the same
        with patch("app.tg_ads.call", AsyncMock(return_value={"ad_id": 23, "cpm": 2.88, "status": "in_review"})):
            await tg_autobid.run_autobid(datetime.now(timezone.utc))
        row = await self.pool.fetchrow("SELECT state, enabled FROM tg_ad_autobid WHERE ad_id = 23")
        self.assertEqual((row["state"], row["enabled"]), ("review", False))

    async def test_refund_pauses_then_returns_the_rest(self):
        with patch("app.tg_ads.call", AsyncMock(return_value={"ad_id": 23, "status": "on_hold", "is_paused": True})):
            out = await tg_cabinet.refund(23)
        self.assertTrue(out["refund_at"])
        later = datetime.now(timezone.utc) + timedelta(minutes=12)
        call = AsyncMock(side_effect=[[{"ad_id": 23, "remaining_budget": 1.1}], {"ad_id": 23}])
        with patch("app.tg_ads.call", call):
            self.assertEqual(await tg_autobid.run_refunds(later), 1)
        self.assertEqual(call.await_args_list[1].args[0], "decreaseAdBudget")
        self.assertIsNone(await self.pool.fetchval("SELECT refund_at FROM tg_ad_autobid WHERE ad_id = 23"))

    async def test_payback_by_days_counts_only_people_who_had_the_time(self):
        old = datetime.now(timezone.utc) - timedelta(days=10)
        await self.pool.execute(
            "INSERT INTO users (telegram_id, username, first_name, ad_link_id, created_at) VALUES (8, 'b', 'B', $1, $2)",
            self.link, old)
        for key, amount, at in (("p1", 100, old + timedelta(days=2)), ("p2", 50, old + timedelta(days=9))):
            await self.pool.execute(
                """INSERT INTO payment_receipts (payment_key, telegram_id, plan_code, amount, first_payment,
                       referral_enabled, created_at) VALUES ($1, 8, 'm1', $2, TRUE, FALSE, $3)""", key, amount, at)
        cab = await tg_cabinet.cabinet("7d")
        ltv = {x["days"]: x for x in cab["ads"][0]["link"]["ltv"]}
        self.assertEqual((ltv[7]["users"], ltv[7]["per_user"]), (1, 100))
        self.assertEqual((ltv[14]["users"], ltv[14]["per_user"]), (0, None))   # nobody came 14+ days ago
        self.assertEqual(ltv[7]["ok"], True)   # 40 ₽ spent / 2 people = 20 ₽ a person, paid 100 in a week
        self.assertEqual(cab["ltv"][0]["per_user"], 100)

    async def test_silent_ad_says_raising_did_not_help(self):
        await self.pool.execute("UPDATE tg_ad_stats SET ts = ts - INTERVAL '5 hours'")
        await tg_autobid.log(23, "cpm", who="admin", old=Decimal("2.5"), new=Decimal("10"))
        await self.pool.execute("UPDATE tg_ads SET cpm = 10 WHERE ad_id = 23")
        await self.pool.execute(
            "INSERT INTO tg_ad_places (username, kind, audience, prev_audience) VALUES ('hitvpnbot', 'bot', 0, 12000)")
        ad = (await tg_cabinet.cabinet("7d"))["ads"][0]
        self.assertGreaterEqual(ad["silence"]["hours"], 4)
        self.assertEqual(ad["silence"]["back_cpm"], 2.5)
        self.assertIn("дело не в цене", ad["silence"]["text"])
        self.assertIn("@hitvpnbot: было 12 000, стало 0", ad["silence"]["text"])

    async def test_places_suggest_where_to_try(self):
        bots = {"@bigbot": {"username": "bigbot", "title": "Big", "monthly_users": 90000},
                "@tinybot": {"username": "tinybot", "title": "Tiny", "monthly_users": 300},
                "@hitvpnbot": {"username": "hitvpnbot", "title": "HIT VPN", "monthly_users": 40000}}

        async def call(method, **kw):
            return bots[kw["bot_id"]]
        with patch("app.tg_ads.call", AsyncMock(side_effect=call)):
            got = await tg_cabinet.check_places(["@bigbot", "t.me/tinybot", "hitvpnbot", "not a name!"])
        self.assertEqual(got["checked"], 3)
        self.assertEqual(len(got["failed"]), 1)
        p = {x["username"]: x["verdict"] for x in (await tg_cabinet.places())["items"]}
        self.assertEqual(p, {"bigbot": "стоит попробовать", "tinybot": "мало людей", "hitvpnbot": "крутится"})
        bots["@hitvpnbot"]["monthly_users"] = 0
        with patch("app.tg_ads.call", AsyncMock(side_effect=call)):
            await tg_cabinet.check_place("hitvpnbot")
        row = await self.pool.fetchrow("SELECT audience, prev_audience FROM tg_ad_places WHERE username = 'hitvpnbot'")
        self.assertEqual((row["audience"], row["prev_audience"]), (0, 40000))

    async def test_autobid_keeps_a_person_under_the_target(self):
        with self.assertRaises(ValueError):
            await tg_cabinet.set_autobid(23, True, 6)
        with patch("app.tg_ads.call", AsyncMock(return_value={})):
            await tg_cabinet.set_autobid(23, True, 4, 20)
        row = await self.pool.fetchrow("SELECT max_user_rub, base_cpm FROM tg_ad_autobid WHERE ad_id = 23")
        self.assertEqual(row["max_user_rub"], 20)
        self.assertEqual(Decimal(str(row["base_cpm"])), Decimal("2.5"))
        # 30 views, 3 people → 100 per 1000; rate 100 ₽ → cap 20/100 × 100 = 20 TON, above the CPM: nothing to cut.
        for i in range(2):
            await self.pool.execute(
                "INSERT INTO users (telegram_id, username, first_name, ad_link_id) VALUES ($1, 'x', 'X', $2)", 20 + i, self.link)
        await db.set_job_report("tg_ads", {"rate": 100})
        with patch("app.tg_ads.call", AsyncMock(return_value={"ad_id": 23, "cpm": 2.5, "status": "active"})) as call:
            await tg_autobid.run_autobid(datetime.now(timezone.utc))
        call.assert_not_awaited()
        # A person must cost at most 1 ₽ → cap 1/100 × 100 = 1 TON: the CPM goes down to 1.
        await self.pool.execute("UPDATE tg_ad_autobid SET max_user_rub = 1, changed_at = NULL WHERE ad_id = 23")
        with patch("app.tg_ads.call", AsyncMock(return_value={"ad_id": 23, "cpm": 1, "status": "active"})) as call:
            await tg_autobid.run_autobid(datetime.now(timezone.utc))
        call.assert_awaited_once_with("editAd", ad_id=23, cpm=1.0)
        self.assertEqual(await self.pool.fetchval("SELECT state FROM tg_ad_autobid WHERE ad_id = 23"), "expensive")

    async def _alert_bot(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        patcher = patch.object(tg_autobid, "_targets", AsyncMock(return_value=[1]))
        patcher.start()
        self.addCleanup(patcher.stop)
        return bot

    async def test_alerts_first_look_is_quiet_then_moderation_and_first_100(self):
        bot = await self._alert_bot()
        await self.pool.execute("UPDATE tg_ads SET views = 160")
        await tg_autobid.run_alerts(bot)
        bot.send_message.assert_not_awaited()     # 160 views before the deploy: not news
        await self.pool.execute("UPDATE tg_ad_autobid SET last_status = 'in_review', alerted = '{}'::jsonb")
        await tg_autobid.run_alerts(bot)
        texts = [c.args[1] for c in bot.send_message.await_args_list]
        self.assertTrue(any("прошло модерацию" in t for t in texts))
        self.assertTrue(any("первые 160 показов — 9 кликов (CTR 5,6%), пришли в бота 1" in t for t in texts))
        bot.send_message.reset_mock()
        await tg_autobid.run_alerts(bot)
        bot.send_message.assert_not_awaited()     # once

    async def test_loss_alert_has_pause_and_refund_buttons(self):
        bot = await self._alert_bot()
        await tg_autobid.run_alerts(bot)          # first look
        old = datetime.now(timezone.utc) - timedelta(days=20)
        for i in range(6):
            await self.pool.execute(
                "INSERT INTO users (telegram_id, username, first_name, ad_link_id, created_at) VALUES ($1, 'x', 'X', $2, $3)",
                100 + i, self.link, old)
        await self.pool.execute("UPDATE tg_ads SET spent_rub = 700")   # 7 people → 100 ₽ a person, they paid nothing
        await tg_autobid.run_alerts(bot)
        call = next(c for c in bot.send_message.await_args_list if "не окупается" in c.args[1])
        self.assertIn("стоит 100 ₽, а за 14 дней приносит 0 ₽ (по 6 пришедшим)", call.args[1])
        buttons = [b.callback_data for b in call.kwargs["reply_markup"].inline_keyboard[0]]
        self.assertEqual(buttons, ["tga_pause:23", "tga_refund:23"])

    async def test_followup_once_to_who_has_not_connected(self):
        from app import ad_followup
        await self.pool.execute("UPDATE ad_links SET followup = '{name}, соцсети всё ещё не грузятся?' WHERE id = $1", self.link)
        now = datetime.now(timezone.utc)
        for tid, ago in ((40, 2), (41, 10), (42, 2)):
            await self.pool.execute(
                "INSERT INTO users (telegram_id, username, first_name, ad_link_id, created_at) VALUES ($1, 'x', 'Аня', $2, $3)",
                tid, self.link, now - timedelta(hours=ago))
        await self.pool.execute("UPDATE users SET first_online_at = NOW() WHERE telegram_id = 42")
        deliver = AsyncMock(return_value=True)
        with patch("app.nudge._deliver", deliver):
            self.assertEqual(await ad_followup.send_due(None), 1)
            self.assertEqual(await ad_followup.send_due(None), 0)
        kw = deliver.await_args.kwargs
        self.assertEqual((kw["telegram_id"], kw["body"], kw["kind"]), (40, "Аня, соцсети всё ещё не грузятся?", "nudge_ad_followup"))

    async def test_greeting_and_followup_saved_together(self):
        await tg_cabinet.set_greeting(self.link, "Привет", "Дожим")
        row = await self.pool.fetchrow("SELECT greeting, followup FROM ad_links WHERE id = $1", self.link)
        self.assertEqual((row["greeting"], row["followup"]), ("Привет", "Дожим"))
        await tg_cabinet.set_greeting(self.link, "Привет 2")       # followup untouched when not given
        self.assertEqual(await self.pool.fetchval("SELECT followup FROM ad_links WHERE id = $1", self.link), "Дожим")


class AlertButtonsTest(unittest.IsolatedAsyncioTestCase):
    def test_loss_of(self):
        link = {"spent_rub": 700, "users": 7, "ltv": {14: {"users": 6, "revenue": 120}}}
        self.assertEqual(tg_autobid.loss_of(link), {"cost": 100, "paid": 20, "people": 6})
        self.assertIsNone(tg_autobid.loss_of({**link, "ltv": {14: {"users": 6, "revenue": 900}}}))
        self.assertIsNone(tg_autobid.loss_of({**link, "ltv": {14: {"users": 4, "revenue": 0}}}))
        self.assertIsNone(tg_autobid.loss_of({**link, "shared": True}))

    async def test_pause_button_admin_only(self):
        from app.handlers import tg_ads_mod
        s = SimpleNamespace(admin_id_set={5})
        msg = SimpleNamespace(html_text="📉 Боты", edit_text=AsyncMock())
        cb = SimpleNamespace(data="tga_pause:23", from_user=SimpleNamespace(id=6, first_name="Кто-то"),
                             answer=AsyncMock(), message=msg)
        with patch.object(tg_ads_mod, "get_settings", return_value=s), \
                patch("app.tg_cabinet.set_paused", AsyncMock()) as pause:
            await tg_ads_mod.tg_ads_action(cb)
            pause.assert_not_awaited()
            cb.from_user = SimpleNamespace(id=5, first_name="Админ")
            await tg_ads_mod.tg_ads_action(cb)
        pause.assert_awaited_once_with(23, True)
        self.assertIn("⏸ Поставлено на паузу — Админ", msg.edit_text.await_args.args[0])
