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
                                    vpn_day_price_rub=6, bot_username="frog_bot")


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


class GiftLimitsTest(unittest.IsolatedAsyncioTestCase):
    async def test_amount_outside_limits_is_refused_before_any_sql(self):
        with patch.object(friend_gifts, "get_settings", return_value=SETTINGS), \
             patch.object(friend_gifts.db, "_pool_req") as pool:
            for amount, msg in ((59, "Минимальный"), (20001, "Максимальный")):
                with self.subTest(amount=amount), self.assertRaisesRegex(friend_gifts.GiftError, msg):
                    await friend_gifts.create_gift(1, amount)
            pool.assert_not_called()

    async def test_switched_off(self):
        off = Settings.model_construct(gifts_enabled=False, gift_min_rub=60, gift_max_rub=20000)
        with patch.object(friend_gifts, "get_settings", return_value=off), \
             self.assertRaisesRegex(friend_gifts.GiftError, "недоступны"):
            await friend_gifts.create_gift(1, 180)


class GiftEndpointTest(unittest.IsolatedAsyncioTestCase):
    def req(self, body=None, code=None):
        return SimpleNamespace(app={"rw": AsyncMock(), "bot": AsyncMock()}, match_info={"code": code},
                               json=AsyncMock(return_value=body or {}))

    async def test_claim_credits_then_tells_the_giver(self):
        claim = AsyncMock(return_value={"amount_rub": 180, "balance_rub": 180, "from_telegram_id": 7, "from_name": "Иван"})
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
            (1, 'Иван', 300, NOW()), (2, 'Оля', -10, NOW()), (3, 'Нет', 0, NULL)""")
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
