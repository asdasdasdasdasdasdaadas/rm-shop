"""Money on the balance turns switched-off devices back on at once, whatever brought it."""
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import balance, balance_watch, db


class ReenableUserTest(unittest.IsolatedAsyncioTestCase):
    async def run_once(self, found):
        with ExitStack() as stack:
            stack.enter_context(patch.object(balance_watch, "get_settings", return_value=SimpleNamespace(vpn_day_price_rub=6)))
            stack.enter_context(patch.object(db, "flag_on", AsyncMock(return_value=False)))
            check = stack.enter_context(patch.object(db, "devices_to_reenable", AsyncMock(side_effect=found)))
            sync = stack.enter_context(patch.object(balance, "sync_user_billing", AsyncMock(return_value={"extended": 1})))
            ran = await balance_watch.reenable_user(object(), None, 7)
        return ran, check, sync

    async def test_switched_off_device_is_synced(self):
        ran, check, sync = await self.run_once([[{"id": 1}], [{"id": 1}]])
        self.assertTrue(ran)
        self.assertEqual(check.await_args.kwargs, {"paused": False, "telegram_id": 7})
        self.assertEqual(sync.await_args.kwargs["source"], "balance")

    async def test_nothing_switched_off_means_no_panel_calls(self):
        ran, _, sync = await self.run_once([[]])
        self.assertFalse(ran)
        sync.assert_not_awaited()

    async def test_payment_sync_got_there_first(self):
        ran, _, sync = await self.run_once([[{"id": 1}], []])  # re-check under the lock finds nothing
        self.assertFalse(ran)
        sync.assert_not_awaited()


class CooldownTest(unittest.TestCase):
    def test_one_run_per_user_per_cooldown(self):
        handled = balance_watch._Handled()
        with patch.object(balance_watch.time, "monotonic", side_effect=[100.0, 110.0, 100.0 + balance_watch.COOLDOWN_SECONDS]):
            self.assertTrue(handled.due(1))
            self.assertFalse(handled.due(1))
            self.assertTrue(handled.due(1))


class TriggerTest(unittest.TestCase):
    def test_schema_notifies_only_on_increase(self):
        sql = (Path(__file__).resolve().parents[1] / "app" / "schema.sql").read_text(encoding="utf-8")
        self.assertIn("pg_notify('balance_up', NEW.telegram_id::text)", sql)
        self.assertIn("COALESCE(NEW.balance_rub, 0) > COALESCE(OLD.balance_rub, 0)", sql)
        self.assertIn("DROP TRIGGER IF EXISTS users_balance_up ON users", sql)


if __name__ == "__main__":
    unittest.main()
