import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import trust


def _settings():
    return SimpleNamespace(
        trust_enabled=True,
        vpn_day_price_rub=6,
        trust_days=3,
        trust_fee_rub=12,
    )


class TrustCycleTest(unittest.IsolatedAsyncioTestCase):
    def _local(self):
        return {"balance_rub": 0, "has_paid_topup": True, "first_online_at": "yes"}

    async def test_unpaid_user_cannot_take_a_loan(self):
        local = {"balance_rub": 0, "has_paid_topup": False, "first_online_at": "yes"}
        with patch.object(trust, "get_settings", _settings), patch.object(
            trust.db, "open_trust_loan", AsyncMock(return_value=None)
        ), patch.object(trust.db, "trust_unlocked_by_topup", AsyncMock(return_value=True)):
            info = await trust.trust_info(1, local, 1)
        self.assertFalse(info["available"])
        self.assertEqual(info["reason"], "Обещанный платёж откроется после пополнения баланса")

    async def test_first_loan_opens_after_a_payment(self):
        with patch.object(trust, "get_settings", _settings), patch.object(
            trust.db, "open_trust_loan", AsyncMock(return_value=None)
        ), patch.object(trust.db, "trust_unlocked_by_topup", AsyncMock(return_value=True)) as unlocked:
            info = await trust.trust_info(1, self._local(), 1)
        self.assertTrue(info["available"])
        unlocked.assert_awaited_once_with(1)

    async def test_next_loan_waits_for_a_paid_topup(self):
        with patch.object(trust, "get_settings", _settings), patch.object(
            trust.db, "open_trust_loan", AsyncMock(return_value=None)
        ), patch.object(trust.db, "trust_unlocked_by_topup", AsyncMock(return_value=False)):
            info = await trust.trust_info(1, self._local(), 1)
        self.assertFalse(info["available"])
        self.assertEqual(info["reason"], "Следующий обещанный платёж откроется после пополнения баланса")
