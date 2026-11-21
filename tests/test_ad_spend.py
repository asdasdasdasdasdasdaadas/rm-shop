"""Ad links: the spend entered by hand turns into the price of one payer and the payback."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import admin, db


@unittest.skipUnless(os.environ.get("PGLITE_MODULE"), "Set PGLITE_MODULE to run PostgreSQL integration scenarios")
class AdSpendTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import PgPool
        self.proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BIN", "node"), str(Path(__file__).parent / "support/pglite_bridge.mjs"),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.pool = PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(), script=True)
        for p in (patch.object(db, "_pool_req", return_value=self.pool),
                  patch.object(admin, "get_settings", return_value=SimpleNamespace(bot_username="frogbot"))):
            p.start()
            self.addCleanup(p.stop)

    async def asyncTearDown(self):
        self.proc.stdin.close()
        await self.proc.wait()

    async def test_payer_cost_and_revenue(self):
        link = await self.pool.fetchval("INSERT INTO ad_links (slug, title) VALUES ('tech', 'Канал') RETURNING id")
        await self.pool.execute("""INSERT INTO users (telegram_id, ad_link_id, has_paid_topup, first_online_at) VALUES
            (1, $1, TRUE, NOW()), (2, $1, TRUE, NOW()), (3, $1, FALSE, NULL), (4, NULL, TRUE, NOW())""", link)
        await self.pool.execute("""INSERT INTO payment_receipts (payment_key, telegram_id, plan_code, amount, first_payment, referral_enabled) VALUES
            ('order:a', 1, 'b300', 300, TRUE, FALSE), ('order:b', 2, 'b500', 500, TRUE, FALSE),
            ('order:c', 1, 'b200', 200, FALSE, FALSE), ('order:d', 4, 'b900', 900, TRUE, FALSE)""")
        row = admin._ad_public({**(await db.list_ad_links())[0], "created_at": None})
        self.assertEqual((row["users"], row["connected"], row["paid"], row["revenue"]), (3, 2, 2, 1000))
        self.assertIsNone(row["payer_cost"])
        self.assertEqual((row["ltv"], row["payer_ltv"]), (333, 500))  # 1000 ₽ over 3 people, 2 of them paid
        self.assertTrue(await db.set_ad_link_spend(link, 1500))
        row = admin._ad_public({**(await db.list_ad_links())[0], "created_at": None})
        self.assertEqual((row["spend_rub"], row["payer_cost"], row["user_cost"]), (1500, 750, 500))


if __name__ == "__main__":
    unittest.main()
