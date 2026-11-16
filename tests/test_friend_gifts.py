"""«Подарить другу»: gift links, limits, the cabinet endpoints and the money moves in real SQL (PGlite)."""
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import db, friend_gifts, web
from app.config import Settings

SETTINGS = Settings.model_construct(gifts_enabled=True, gift_min_rub=60, gift_max_rub=20000,
                                    vpn_day_price_rub=6, bot_username="frog_bot", admin_ids="9")


class GiftLinkTest(unittest.TestCase):
    def setUp(self):
        p = patch.object(friend_gifts, "get_settings", return_value=SETTINGS)
        p.start()
        self.addCleanup(p.stop)

    def test_start_payload_round_trip(self):
        link = friend_gifts.gift_link("Abc_def-1234")
        self.assertEqual(link, "https://t.me/frog_bot?start=present_Abc_def-1234")
        self.assertEqual(friend_gifts.code_from_start("present_Abc_def-1234"), "Abc_def-1234")
        self.assertEqual(friend_gifts.code_from_start("/start present_Abc_def-1234"), "Abc_def-1234")

    def test_other_payloads_are_not_gifts(self):
        for payload in ("gift", "ref_123", "present_", "present_a b", "present_<script>", None, ""):
            with self.subTest(payload=payload):
                self.assertIsNone(friend_gifts.code_from_start(payload))

    def test_days_follow_day_price(self):
        self.assertEqual(friend_gifts.days_text(180), "30 дней")
        self.assertEqual(friend_gifts.days_text(126), "21 день")
        self.assertEqual(friend_gifts.days_text(24), "4 дня")


class GiftShareCardTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for target, name, value in ((friend_gifts, "get_settings", SETTINGS),):
            p = patch.object(target, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def _base(self, url):
        p = patch("app.keyboards.mini_app_url", return_value=url)
        p.start()
        self.addCleanup(p.stop)

    def test_link_goes_through_our_page_when_there_is_one(self):
        self._base("https://cab.example.org/app")
        self.assertEqual(friend_gifts.share_link("Abcd1234"), "https://cab.example.org/g/Abcd1234")
        self.assertEqual(friend_gifts.card_image(), "https://cab.example.org/icons/gift-cards/violet-one.jpg")
        self._base("")
        self.assertEqual(friend_gifts.share_link("Abcd1234"), "https://t.me/frog_bot?start=present_Abcd1234")
        self.assertEqual(friend_gifts.card_image(), "")

    def test_landing_has_card_tags_and_escapes_the_name(self):
        self._base("https://cab.example.org")
        page = friend_gifts.landing_html({"from_first_name": '<b>"Ив"</b>', "amount_rub": 300, "count": 1}, "Abcd1234")
        self.assertIn('property="og:image" content="https://cab.example.org/icons/gift-cards/violet-one.jpg"', page)
        self.assertIn("дарит вам 300 ₽", page)
        self.assertNotIn("<b>", page)
        self.assertIn("https://t.me/frog_bot?start=present_Abcd1234", page)
        group = friend_gifts.landing_html({"from_first_name": "Ив", "amount_rub": 300, "count": 15}, "Abcd1234")
        self.assertIn("раздаёт 15 подарков по 300 ₽", group)
        styled = friend_gifts.landing_html({"from_first_name": "Ив", "amount_rub": 300, "count": 15, "style": "gold"}, "Abcd1234")
        self.assertIn("/icons/gift-cards/gold-chat.jpg", styled)

    def test_each_style_has_its_cards_and_unknown_falls_back(self):
        self._base("https://cab.example.org")
        for style in friend_gifts.STYLES:
            for many in (False, True):
                self.assertTrue((friend_gifts.CARDS_DIR / f"{style}-{'chat' if many else 'one'}.jpg").is_file())
                self.assertTrue((friend_gifts.CARDS_DIR / f"{style}-{'chat' if many else 'one'}.mp4").is_file())
                self.assertTrue(friend_gifts.card_image(style, many).endswith(f"/gift-cards/{style}-{'chat' if many else 'one'}.jpg"))
        self.assertEqual(friend_gifts.clean_style("neon"), "violet")
        self.assertEqual(friend_gifts.clean_style(None), "violet")
        self.assertTrue(friend_gifts.card_image("neon").endswith("/gift-cards/violet-one.jpg"))
        with patch.object(friend_gifts, "CARDS_DIR", friend_gifts.CARDS_DIR / "missing"):
            self.assertEqual(friend_gifts.card_image("gold", True), "https://cab.example.org/icons/gift-card.jpg")

    async def test_prepared_message_is_an_animated_card(self):
        self._base("https://cab.example.org")
        bot = SimpleNamespace(save_prepared_inline_message=AsyncMock(return_value=SimpleNamespace(id="P1")))
        last = lambda: bot.save_prepared_inline_message.await_args.kwargs.get("result")  # noqa: E731
        self.assertEqual(await friend_gifts.prepare_share(bot, 5, "Abcd1234", 300, "Ив"), "P1")
        self.assertEqual(last().type, "mpeg4_gif")
        self.assertEqual(last().mpeg4_url, "https://cab.example.org/icons/gift-cards/violet-one.mp4")
        self.assertEqual(last().thumbnail_url, "https://cab.example.org/icons/gift-cards/violet-one.jpg")
        self.assertIn("300 ₽", last().caption)
        await friend_gifts.prepare_share(bot, 5, "Abcd1234", 60, "Ив", 30, "sunset")
        self.assertEqual(last().mpeg4_url, "https://cab.example.org/icons/gift-cards/sunset-chat.mp4")
        self.assertIn("30 подарков", last().caption)

    async def test_prepared_message_falls_back_to_a_photo(self):
        self._base("https://cab.example.org")
        bot = SimpleNamespace(save_prepared_inline_message=AsyncMock(return_value=SimpleNamespace(id="P1")))
        with patch.object(friend_gifts, "card_video", return_value=""):
            await friend_gifts.prepare_share(bot, 5, "Abcd1234", 300, "Ив", 1, "gold")
        result = bot.save_prepared_inline_message.await_args.kwargs["result"]
        self.assertEqual((result.type, result.photo_url), ("photo", "https://cab.example.org/icons/gift-cards/gold-one.jpg"))
        self.assertEqual(friend_gifts.card_video("gold"), "https://cab.example.org/icons/gift-cards/gold-one.mp4")
        self._base("")
        self.assertEqual(friend_gifts.card_video("gold"), "")

    async def test_landing_route(self):
        self._base("https://cab.example.org")
        gift = {"from_first_name": "Ив", "amount_rub": 300, "count": 1}
        with patch.object(friend_gifts, "get_gift", AsyncMock(return_value=gift)):
            resp = await web.gift_landing(SimpleNamespace(match_info={"code": "Abcd1234"}))
        self.assertIn("og:title", resp.text)


class NewYearTest(unittest.TestCase):
    def test_greeting_drops_links_mentions_and_keeps_200_chars(self):
        clean = friend_gifts.clean_greeting
        self.assertEqual(clean("С Новым годом! Пусть в 2027-м всё открывается 🎄"), "С Новым годом! Пусть в 2027-м всё открывается 🎄")
        self.assertEqual(clean("заходи t.me/chan, vpn.ru! и www.x.org @vasya <b>"), "заходи и b")
        self.assertEqual(clean("т.е.   всё\n\nок"), "т.е. всё ок")
        self.assertEqual(len(clean("а" * 300)), 200)
        self.assertEqual(clean(None), "")

    def test_season_runs_across_the_new_year(self):
        from datetime import date
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS):
            self.assertEqual([friend_gifts.ny_season(date(2026, m, d)) for m, d in [(11, 30), (12, 1), (12, 31), (1, 10), (1, 11)]],
                             [False, True, True, True, False])
        odd = Settings.model_construct(new_year_gifts_from="12-20", new_year_gifts_to="bad")
        with patch.object(friend_gifts, "get_settings", return_value=odd):
            self.assertEqual([friend_gifts.ny_season(date(2026, m, d)) for m, d in [(12, 19), (12, 20), (1, 10), (1, 11)]], [False, True, True, False])

    def test_share_text_says_new_year_and_carries_the_greeting(self):
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS):
            text = friend_gifts.share_text("Аня", 500, 1, "С НГ! @spam", "tree")
            self.assertIn("500 ₽ на VPN к Новому году", text)
            self.assertTrue(text.endswith("«С НГ!»"))
            self.assertNotIn("к Новому году", friend_gifts.share_text("Аня", 500, 1, None, "violet"))
            self.assertIn("Откройте подарок", friend_gifts.share_text("Аня", 500))
        self.assertTrue(set(friend_gifts.NY_STYLES) <= set(friend_gifts.STYLES))


class GiftLimitsTest(unittest.IsolatedAsyncioTestCase):
    async def test_amount_outside_limits_is_refused_before_any_sql(self):
        # Only the unlimited-right lookup runs; nothing is written or locked.
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS), \
             patch.object(friend_gifts, "gives_free", AsyncMock(return_value=False)), \
             patch.object(friend_gifts.db, "_pool_req") as pool:
            for amount, msg in ((59, "Минимальный"), (20001, "Максимальный")):
                with self.subTest(amount=amount), self.assertRaisesRegex(friend_gifts.GiftError, msg):
                    await friend_gifts.create_gift(1, amount)
            pool.assert_not_called()

    async def test_granted_user_goes_past_the_limits(self):
        class Stop(Exception):
            pass
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS), \
             patch.object(friend_gifts, "gives_free", AsyncMock(return_value=True)) as free, \
             patch.object(friend_gifts.db, "_pool_req", side_effect=Stop):
            with self.assertRaises(Stop):
                await friend_gifts.create_gift(1, 50000)
            free.assert_awaited()

    def test_granted_flag_in_limits(self):
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS):
            self.assertEqual(friend_gifts.limits(1, {"gift_unlimited": True}), (1, friend_gifts.ADMIN_MAX_RUB))
            self.assertTrue(friend_gifts.is_granted(1, {"gift_unlimited": True}))
            self.assertFalse(friend_gifts.is_granted(9, {"gift_unlimited": True}))

    async def test_switched_off(self):
        off = Settings.model_construct(gifts_enabled=False, gift_min_rub=60, gift_max_rub=20000)
        with patch.object(friend_gifts, "get_settings", return_value=off), \
             self.assertRaisesRegex(friend_gifts.GiftError, "недоступны"):
            await friend_gifts.create_gift(1, 180)


class GiveawayCountTest(unittest.IsolatedAsyncioTestCase):
    async def test_count_and_total_limits(self):
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS), \
             patch.object(friend_gifts, "gives_free", AsyncMock(return_value=False)), \
             patch.object(friend_gifts.db, "_pool_req") as pool:
            for amount, count, msg in ((300, 0, "от 1 до 100"), (300, 101, "от 1 до 100"), (300, 70, "Всего можно")):
                with self.subTest(count=count), self.assertRaisesRegex(friend_gifts.GiftError, msg):
                    await friend_gifts.create_gift(1, amount, count)
            pool.assert_not_called()

    def test_share_text_for_a_group(self):
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS):
            self.assertIn("15 подарков по 300 ₽", friend_gifts.share_text("Иван", 300, 15))
            self.assertIn("дарит вам 180 ₽", friend_gifts.share_text("Иван", 180))


class AdminGiftTest(unittest.TestCase):
    def test_admin_has_no_limits(self):
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS):
            self.assertEqual(friend_gifts.limits(9), (1, friend_gifts.ADMIN_MAX_RUB))
            self.assertEqual(friend_gifts.limits(1), (60, 20000))
            self.assertTrue(friend_gifts.is_admin(9))
            self.assertFalse(friend_gifts.is_admin(1))


class GiftEndpointTest(unittest.IsolatedAsyncioTestCase):
    def req(self, body=None, code=None):
        return SimpleNamespace(app={"rw": AsyncMock(), "bot": AsyncMock()}, match_info={"code": code},
                               json=AsyncMock(return_value=body or {}))

    async def test_claim_credits_then_tells_the_giver(self):
        claim = AsyncMock(return_value={"amount_rub": 180, "balance_rub": 180, "from_telegram_id": 7, "from_name": "Иван",
                                        "gift_id": 1, "count": 1, "claimed_count": 1, "last": True})
        with patch.object(web, "_require_tg", AsyncMock(return_value=(5, None))), \
             patch.object(web.friend_gifts, "claim_gift", claim), \
             patch.object(web, "_sync_after_gift", AsyncMock(return_value=186)), \
             patch.object(web.db, "get_user", AsyncMock(return_value={"first_name": "Оля"})), \
             patch.object(web.friend_gifts, "notify_giver_claimed", AsyncMock()) as told:
            res = await web.api_gift_claim(self.req(code="Abc_def-1234"))
        self.assertEqual(res.status, 200)
        body = json.loads(res.body)
        self.assertEqual((body["amount_rub"], body["balance_rub"]), (180, 186))
        claim.assert_awaited_once_with(5, "Abc_def-1234")
        self.assertEqual(told.call_args.args[1:], (7, "Оля", 180))

    async def test_giveaway_tells_the_giver_only_when_all_are_taken(self):
        res = {"amount_rub": 300, "balance_rub": 300, "from_telegram_id": 7, "from_name": "Иван", "gift_id": 3, "count": 15}
        claim = AsyncMock(side_effect=[{**res, "claimed_count": 14, "last": False}, {**res, "claimed_count": 15, "last": True}])
        with patch.object(web, "_require_tg", AsyncMock(return_value=(5, None))), \
             patch.object(web.friend_gifts, "claim_gift", claim), \
             patch.object(web, "_sync_after_gift", AsyncMock(return_value=None)), \
             patch.object(web.friend_gifts, "notify_giver_claimed", AsyncMock()) as one, \
             patch.object(web.friend_gifts, "notify_giveaway_done", AsyncMock()) as done:
            first = json.loads((await web.api_gift_claim(self.req(code="Abc_def-1234"))).body)
            done.assert_not_awaited()
            await web.api_gift_claim(self.req(code="Abc_def-1234"))
        self.assertEqual(first["left"], 1)
        one.assert_not_awaited()
        self.assertEqual(done.call_args.args[1:], (7, 3, 15, 300))

    async def test_claim_refusal_is_a_plain_error(self):
        with patch.object(web, "_require_tg", AsyncMock(return_value=(5, None))), \
             patch.object(web.friend_gifts, "claim_gift", AsyncMock(side_effect=friend_gifts.GiftError("Этот подарок уже открыли"))), \
             patch.object(web.friend_gifts, "notify_giver_claimed", AsyncMock()) as told:
            res = await web.api_gift_claim(self.req(code="Abc_def-1234"))
        self.assertEqual(res.status, 400)
        self.assertIn("уже открыли", json.loads(res.body)["error"])
        told.assert_not_awaited()

    async def test_create_rejects_non_numbers(self):
        with patch.object(web, "_require_tg", AsyncMock(return_value=(5, None))), \
             patch.object(web.friend_gifts, "create_gift", AsyncMock()) as create:
            res = await web.api_gift_create(self.req({"amount": "много"}))
        self.assertEqual(res.status, 400)
        create.assert_not_awaited()

    async def test_view_hides_link_from_the_friend(self):
        gift = {"code": "Abc_def-1234", "amount_rub": 180, "from_telegram_id": 7, "from_first_name": "Иван",
                "status": "active", "claimed_by": None, "thanked_at": None}
        with patch.object(web, "_require_tg", AsyncMock(return_value=(5, None))), \
             patch.object(web.friend_gifts, "get_gift", AsyncMock(return_value=gift)), \
             patch.object(friend_gifts, "get_settings", return_value=SETTINGS):
            body = json.loads((await web.api_gift_view(self.req(code="Abc_def-1234"))).body)
        self.assertEqual((body["from_name"], body["mine"], body["url"]), ("Иван", False, None))

    async def test_thanks_reach_the_giver_once(self):
        mark = AsyncMock(side_effect=[{"from_telegram_id": 7, "amount_rub": 180}, None])
        with patch.object(web, "_require_tg", AsyncMock(return_value=(5, None))), \
             patch.object(web.friend_gifts, "mark_thanked", mark), \
             patch.object(web.db, "get_user", AsyncMock(return_value={"first_name": "Оля"})), \
             patch.object(web.friend_gifts, "notify_giver_thanks", AsyncMock()) as told:
            await web.api_gift_thanks(self.req(code="Abc_def-1234"))
            await web.api_gift_thanks(self.req(code="Abc_def-1234"))
        told.assert_awaited_once()


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class GiftPostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool

        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for mod in (db, friend_gifts):
            p = patch.object(mod, "get_settings", return_value=SETTINGS)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(db, "_pool_req", return_value=self.pool)
        p.start()
        self.addCleanup(p.stop)
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, balance_rub, bot_started_at) VALUES
            (1, 'Иван', 300, NOW()), (2, 'Оля', -10, NOW()), (3, 'Нет', 0, NULL), (9, 'Админ', 0, NOW())""")
        # Иван paid 250 ₽ himself; the other 50 ₽ came from a bonus and cannot be gifted.
        await self.pool.execute("""INSERT INTO billing_events (telegram_id, kind, source, amount)
            VALUES (1, 'topup', 'pay', 250), (1, 'referral', 'cron', 50)""")

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def bal(self, tg):
        return await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=$1", tg)

    async def test_full_cycle(self):
        self.assertEqual(await friend_gifts.giftable_rub(1), 250)
        with self.assertRaisesRegex(friend_gifts.GiftError, "до 250"):
            await friend_gifts.create_gift(1, 260)
        gift = await friend_gifts.create_gift(1, 180)
        self.assertEqual(await self.bal(1), 120)
        self.assertEqual(await friend_gifts.giftable_rub(1), 70)
        with self.assertRaisesRegex(friend_gifts.GiftError, "ваш подарок"):
            await friend_gifts.claim_gift(1, gift["code"])
        with self.assertRaisesRegex(friend_gifts.GiftError, "откройте бота"):
            await friend_gifts.claim_gift(3, gift["code"])
        got = await friend_gifts.claim_gift(2, gift["code"])
        self.assertEqual((got["amount_rub"], got["from_name"]), (180, "Иван"))
        self.assertEqual(await self.bal(2), 170)
        with self.assertRaisesRegex(friend_gifts.GiftError, "уже открыли"):
            await friend_gifts.claim_gift(2, gift["code"])
        with self.assertRaisesRegex(friend_gifts.GiftError, "уже открыл"):
            await friend_gifts.return_gift(1, gift["code"])
        self.assertIsNotNone(await friend_gifts.mark_thanked(2, gift["code"]))
        self.assertIsNone(await friend_gifts.mark_thanked(2, gift["code"]))
        kinds = await self.pool.fetch("SELECT telegram_id, kind, amount FROM billing_events WHERE kind LIKE 'gift%' ORDER BY id")
        self.assertEqual([(r["telegram_id"], r["kind"], r["amount"]) for r in kinds], [(1, "gift_sent", -180), (2, "gift_received", 180)])

    async def test_style_is_kept_and_unknown_becomes_violet(self):
        gold = await friend_gifts.create_gift(1, 60, 2, "gold")
        self.assertEqual(gold["style"], "gold")
        self.assertEqual((await friend_gifts.get_gift(gold["code"]))["style"], "gold")
        odd = await friend_gifts.create_gift(1, 60, 1, "neon")
        self.assertEqual(odd["style"], "violet")
        self.assertEqual([g["style"] for g in await friend_gifts.list_sent(1)], ["violet", "gold"])
        self.assertEqual(friend_gifts.public_sent([{"code": "c", "amount_rub": 60, "status": "active", "style": "gold"}])[0]["style"], "gold")

    async def test_greeting_is_kept_clean(self):
        gift = await friend_gifts.create_gift(1, 60, 1, "snow", "  С Новым годом!  пиши @vasya https://x.com  ")
        self.assertEqual((gift["style"], gift["greeting"]), ("snow", "С Новым годом! пиши"))
        self.assertEqual((await friend_gifts.get_gift(gift["code"]))["greeting"], "С Новым годом! пиши")
        plain = await friend_gifts.create_gift(1, 60)
        self.assertEqual(plain["greeting"], "")

    async def test_return_puts_money_back_once(self):
        gift = await friend_gifts.create_gift(1, 100)
        await friend_gifts.return_gift(1, gift["code"])
        self.assertEqual(await self.bal(1), 300)
        self.assertEqual(await friend_gifts.giftable_rub(1), 250)
        with self.assertRaisesRegex(friend_gifts.GiftError, "уже вернулся"):
            await friend_gifts.return_gift(1, gift["code"])
        with self.assertRaisesRegex(friend_gifts.GiftError, "отменён"):
            await friend_gifts.claim_gift(2, gift["code"])
        with self.assertRaisesRegex(friend_gifts.GiftError, "не найден"):
            await friend_gifts.return_gift(2, gift["code"])

    async def test_giveaway_one_each_until_gone_then_rest_returns(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, balance_rub, bot_started_at)
            SELECT g, 'Друг' || g, 0, NOW() FROM generate_series(10, 14) g""")
        with self.assertRaisesRegex(friend_gifts.GiftError, "до 250"):
            await friend_gifts.create_gift(1, 60, 5)
        pack = await friend_gifts.create_gift(1, 60, 4)
        self.assertEqual(await self.bal(1), 60)
        self.assertEqual(await friend_gifts.giftable_rub(1), 10)
        first = await friend_gifts.claim_gift(10, pack["code"])
        self.assertEqual((first["claimed_count"], first["last"]), (1, False))
        with self.assertRaisesRegex(friend_gifts.GiftError, "уже забрали"):
            await friend_gifts.claim_gift(10, pack["code"])
        await friend_gifts.claim_gift(11, pack["code"])
        back = await friend_gifts.return_gift(1, pack["code"])
        self.assertEqual((back["amount_rub"], back["left"]), (120, 2))
        self.assertEqual(await self.bal(1), 180)
        self.assertEqual(await friend_gifts.giftable_rub(1), 130)
        with self.assertRaisesRegex(friend_gifts.GiftError, "отменён"):
            await friend_gifts.claim_gift(12, pack["code"])

    async def test_giveaway_last_gift_closes_it(self):
        await self.pool.execute("""INSERT INTO users (telegram_id, first_name, balance_rub, bot_started_at)
            SELECT g, 'Друг' || g, 0, NOW() FROM generate_series(10, 12) g""")
        pack = await friend_gifts.create_gift(1, 60, 2)
        await friend_gifts.claim_gift(10, pack["code"])
        last = await friend_gifts.claim_gift(11, pack["code"])
        self.assertTrue(last["last"])
        self.assertEqual(await friend_gifts.claimer_names(last["gift_id"]), ["Друг10", "Друг11"])
        with self.assertRaisesRegex(friend_gifts.GiftError, "разобрали"):
            await friend_gifts.claim_gift(12, pack["code"])
        self.assertIsNotNone(await friend_gifts.mark_thanked(10, pack["code"]))
        self.assertIsNotNone(await friend_gifts.mark_thanked(11, pack["code"]))

    async def test_admin_gifts_any_amount_without_paying(self):
        gift = await friend_gifts.create_gift(9, 50000)
        self.assertEqual(await self.bal(9), 0)
        await friend_gifts.claim_gift(2, gift["code"])
        self.assertEqual(await self.bal(2), 49990)
        other = await friend_gifts.create_gift(9, 1)
        self.assertEqual((await friend_gifts.return_gift(9, other["code"]))["amount_rub"], 0)
        self.assertEqual(await self.bal(9), 0)
        self.assertEqual(await friend_gifts.giftable_rub(1), 250)
