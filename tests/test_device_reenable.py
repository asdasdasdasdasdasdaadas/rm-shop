"""A device switched off for lack of money comes back on by itself once the balance covers a day."""
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import balance, db


class ReenableTest(unittest.IsolatedAsyncioTestCase):
    async def run_billing(self, due, reenable, paid_per_user):
        charged = []

        async def decide(devices, price, paused):
            n = paid_per_user.get(int(devices[0]["telegram_id"]), 0)
            charged.append([d["id"] for d in devices])
            return devices[:n], devices[n:]

        rw = SimpleNamespace()
        settings = SimpleNamespace(vpn_day_price_rub=6, billing_bulk_chunk=100, billing_concurrency=4)
        with ExitStack() as stack:
            stack.enter_context(patch.object(balance, "get_settings", return_value=settings))
            stack.enter_context(patch.object(balance, "collect_due_trusts", AsyncMock()))
            stack.enter_context(patch.object(balance, "_sync_router_slots", AsyncMock()))
            stack.enter_context(patch.object(db, "get_flags", AsyncMock(return_value={})))
            stack.enter_context(patch.object(db, "devices_due_for_billing", AsyncMock(return_value=due)))
            stack.enter_context(patch.object(db, "devices_to_retry_disable", AsyncMock(return_value=[])))
            stack.enter_context(patch.object(db, "devices_to_reenable", AsyncMock(return_value=reenable)))
            stack.enter_context(patch.object(db, "devices_needing_revive", AsyncMock(return_value=[])))
            stack.enter_context(patch.object(db, "set_job_report", AsyncMock()))
            stack.enter_context(patch.object(balance, "_decide_user_devices", side_effect=decide))
            ext = stack.enter_context(patch.object(balance, "_commit_extends", AsyncMock(return_value=(0, "нет"))))
            dis = stack.enter_context(patch.object(balance, "_commit_disables", AsyncMock(return_value=(0, "нет"))))
            await balance.charge_due_devices(rw, None)
        paid = [d["id"] for call in ext.await_args_list for d in call.args[1]]
        off = [d["id"] for d in dis.await_args.args[1]]
        return charged, paid, off

    async def test_topped_up_device_is_charged_and_turned_on(self):
        row = {"id": 7, "telegram_id": 1, "remnawave_id": 70, "title": "iPhone"}
        _, paid, off = await self.run_billing([], [row], {1: 1})
        self.assertEqual(paid, [7])
        self.assertEqual(off, [])

    async def test_device_that_is_on_gets_the_money_first(self):
        on = {"id": 9, "telegram_id": 1, "remnawave_id": 90, "title": "Mac"}
        was_off = {"id": 3, "telegram_id": 1, "remnawave_id": 30, "title": "iPhone"}
        charged, paid, off = await self.run_billing([on], [was_off], {1: 1})
        self.assertEqual(charged, [[9, 3]])  # the lower id still waits behind the device that is on
        self.assertEqual(paid, [9])
        self.assertEqual(off, [])  # no second «баланс закончился» for a device that is already off

    async def test_reenable_query_needs_a_day_of_money_and_an_old_charge(self):
        pool = SimpleNamespace(fetch=AsyncMock(return_value=[]))
        with patch.object(db, "_pool_req", return_value=pool):
            await db.devices_to_reenable(6)
        sql, price, paused, uid = pool.fetch.await_args.args
        self.assertIn("= 'DISABLED'", sql)
        self.assertIn("balance_rub, 0) >= $1", sql)
        self.assertIn("INTERVAL '24 hours'", sql)
        self.assertIn("blocked_at IS NULL", sql)
        self.assertEqual((price, paused, uid), (6, False, None))


if __name__ == "__main__":
    unittest.main()
