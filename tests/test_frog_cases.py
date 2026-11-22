"""Кейсы с лягушкой: the draw, where cases come from, opening, the collection and «Подписка» perks."""
import asyncio
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app import autopay, billing, db, frog_cases


def cfg(**kw):
    base = dict(cases_enabled=True, case_topup_min_rub=300, case_subscription_count=3, case_dup_bonus_rub=5,
                autopay_grace_days=3)
    return SimpleNamespace(**{**base, **kw})


class DrawTest(unittest.TestCase):
    def test_every_model_has_a_file_and_rarities_add_up(self):
        self.assertEqual(len(frog_cases.SKINS), 48)
        self.assertEqual(sum(chance for _, chance in frog_cases.RARITY.values()), 100)
        frogs = Path(__file__).parent.parent / "webapp/icons/frog"
        for model in frog_cases.SKINS:
            self.assertTrue((frogs / f"p{model:02d}.json").exists(), model)

    def test_rare_frogs_drop_rarely(self):
        rng = random.Random(7)
        drops = [frog_cases.SKINS[frog_cases.roll(rng)][1] for _ in range(20000)]
        share = {k: drops.count(k) / len(drops) * 100 for k in frog_cases.RARITY}
        for key, (_, chance) in frog_cases.RARITY.items():
            self.assertAlmostEqual(share[key], chance, delta=max(0.6, chance * 0.1), msg=key)

    def test_words(self):
        self.assertEqual([frog_cases.case_word(n) for n in (1, 2, 5, 11, 21, 22, 112)],
                         ["кейс", "кейса", "кейсов", "кейсов", "кейс", "кейса", "кейсов"])
        self.assertIn("подарили 3 кейса", frog_cases.gift_text(3, "Спасибо!"))
        self.assertIn("Спасибо!", frog_cases.gift_text(3, "Спасибо!"))


class PaymentCasesTest(unittest.IsolatedAsyncioTestCase):
    async def run_for(self, key, amount, router_days=0, **kw):
        grant = AsyncMock(return_value=1)
        with patch.object(billing, "get_settings", return_value=cfg(**kw)), \
                patch.object(frog_cases, "get_settings", return_value=cfg(**kw)), \
                patch.object(frog_cases, "grant", grant):
            n = await billing.grant_payment_cases({"telegram_id": 7, "payment_key": key, "router_days": router_days}, amount)
        return n, grant

    async def test_a_big_enough_top_up_gives_one_case_once_per_payment(self):
        n, grant = await self.run_for("order:abc", 300)
        self.assertEqual(n, 1)
        grant.assert_awaited_once_with(7, 1, "topup", ref="order:abc")
        self.assertEqual((await self.run_for("order:abc", 299))[0], 0)
        self.assertEqual((await self.run_for("order:abc", 900, case_topup_min_rub=0))[0], 0)

    async def test_a_subscription_month_gives_its_cases(self):
        n, grant = await self.run_for("order:ap-tx1", 180)
        self.assertEqual(n, 3)
        grant.assert_awaited_once_with(7, 3, "subscription", ref="order:ap-tx1")

    async def test_no_cases_for_a_router_or_while_off(self):
        self.assertEqual((await self.run_for("order:r", 900, router_days=30))[0], 0)
        self.assertEqual((await self.run_for("order:x", 900, cases_enabled=False))[0], 0)


class SubscriptionPerksTest(unittest.IsolatedAsyncioTestCase):
    async def grace(self, status, next_in, days=3):
        row = {"status": status, "next_charge_at": datetime.now(timezone.utc) + next_in if next_in is not None else None}
        with patch.object(autopay, "get_settings", return_value=cfg(autopay_grace_days=days)), \
                patch.object(autopay, "available", return_value=True), \
                patch.object(autopay, "get", AsyncMock(return_value=row)):
            return await autopay.grace(7)

    async def test_the_vpn_stays_on_only_around_the_monthly_charge(self):
        self.assertTrue(await self.grace("active", timedelta(days=1)))
        self.assertTrue(await self.grace("active", timedelta(days=-2)))   # the bank is late
        self.assertFalse(await self.grace("active", timedelta(days=10)))  # money ran out mid-month
        self.assertFalse(await self.grace("active", timedelta(days=-5)))
        self.assertFalse(await self.grace("pending", timedelta(days=1)))
        self.assertFalse(await self.grace("active", timedelta(days=1), days=0))

    async def test_a_subscriber_gets_no_promised_payment(self):
        from app import trust
        with patch.object(trust, "_subscribed", AsyncMock(return_value=True)), \
                patch.object(trust.db, "open_trust_loan", AsyncMock(return_value=None)), \
                patch.object(trust, "get_settings", return_value=SimpleNamespace(
                    trust_enabled=True, vpn_day_price_rub=6, trust_days=3, trust_fee_rub=10, trust_credit_days=3)):
            info = await trust.trust_info(7, {"balance_rub": 0, "has_paid_topup": True}, 1)
        self.assertFalse(info["available"])
        self.assertIn("подпиской", info["reason"])

    def test_the_cabinet_view_of_the_subscription(self):
        from app.web import _plus_view
        self.assertIsNone(_plus_view(None))
        self.assertEqual(_plus_view({"status": "off", "amount": None, "monthly": 180})["price"], 180)
        on = _plus_view({"status": "active", "amount": 240, "monthly": 180, "next_charge_at": "2026-12-01T00:00:00+00:00"})
        self.assertEqual((on["status"], on["price"], on["next_at"]), ("active", 240, "2026-12-01T00:00:00+00:00"))


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class CasesDb(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        await self.pool.execute("INSERT INTO users (telegram_id, balance_rub) VALUES (7, 10)")
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(frog_cases, "get_settings", return_value=cfg())):
            p.start()
            self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_a_payment_gives_cases_once(self):
        self.assertEqual(await frog_cases.grant(7, 3, "subscription", ref="order:ap-1"), 3)
        self.assertEqual(await frog_cases.grant(7, 3, "subscription", ref="order:ap-1"), 3)
        self.assertEqual(await frog_cases.grant(7, 1, "topup", ref="order:x"), 4)
        self.assertIsNone((await frog_cases.view(7))["gift"])
        with self.assertRaises(ValueError):
            await frog_cases.grant(7, 0, "admin")
        with self.assertRaises(ValueError):
            await frog_cases.grant(7, 51, "admin")

    async def test_a_gift_shows_once_and_the_frog_can_be_put_on_the_home_card(self):
        await frog_cases.grant(7, 2, "admin", note="Спасибо, что с нами", notify=True)
        view = await frog_cases.view(7)
        self.assertEqual((view["left"], view["gift"]["count"], view["gift"]["note"]), (2, 2, "Спасибо, что с нами"))
        await frog_cases.gift_seen(7)
        self.assertIsNone((await frog_cases.view(7))["gift"])
        with patch.object(frog_cases, "roll", return_value=32):
            got = await frog_cases.open_case(7)
        self.assertEqual((got["skin"], got["rarity"], got["dup"], got["bonus"], got["left"]), (32, "l", False, 0, 1))
        with self.assertRaises(ValueError):
            await frog_cases.set_skin(7, 19)   # not dropped yet
        await frog_cases.set_skin(7, 32)
        self.assertEqual(await frog_cases.skin(7), 32)
        admin = await frog_cases.admin_view(7)
        self.assertEqual((admin["left"], admin["owned_count"], admin["skin_name"]), (1, 1, "Королевская"))
        self.assertEqual([h["kind"] for h in admin["history"]], ["open", "admin"])

    async def test_a_repeat_gives_money_and_an_empty_stock_gives_nothing(self):
        await frog_cases.grant(7, 2, "admin")
        with patch.object(frog_cases, "roll", return_value=0):
            await frog_cases.open_case(7)
            again = await frog_cases.open_case(7)
        self.assertEqual((again["dup"], again["bonus"], again["left"]), (True, 5, 0))
        self.assertEqual(await self.pool.fetchval("SELECT balance_rub FROM users WHERE telegram_id=7"), 15)
        self.assertEqual((await frog_cases.view(7))["owned"], {"0": 2})
        with self.assertRaises(ValueError):
            await frog_cases.open_case(7)


if __name__ == "__main__":
    unittest.main()
