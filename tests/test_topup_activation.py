import asyncio
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, call
from app import billing, balance, db, live, referrals, runtime
from app.remnawave import RemnawaveError


class TopupActivationTest(unittest.IsolatedAsyncioTestCase):
    async def scenario(self, *, panel_failure=False, already_paid=False, panel_error=None):
        settings = SimpleNamespace(balance_enabled=True, vpn_day_price_rub=6,
                                   plan_by_code=lambda _: {'topup_rub': 100})
        device = {'id': 9, 'remnawave_id': 77, 'panel_status': 'ACTIVE' if already_paid else 'DISABLED',
                  'last_billed_at': datetime.now(timezone.utc) if already_paid else None,
                  'expire_at': datetime.now(timezone.utc) + timedelta(days=30)}
        rw = SimpleNamespace(extend_panel_user=AsyncMock(side_effect=panel_error or (RuntimeError('unavailable') if panel_failure else None)))
        lock = asyncio.Lock()
        credit = AsyncMock()
        spend = AsyncMock(return_value=True)
        with ExitStack() as stack:
            for module in (billing, balance):
                stack.enter_context(patch.object(module, 'get_settings', return_value=settings))
            stack.enter_context(patch.object(runtime, 'panel_cron_lock', return_value=lock))
            values = {'get_user': {'has_paid_topup': True}, 'list_devices': [device],
                      'user_is_blocked': False, 'flag_on': False, 'user_billing_paused': False,
                      'mark_paid_topup': None, 'log_billing_event': None, 'mark_devices_billed': None}
            for name, value in values.items():
                stack.enter_context(patch.object(db, name, AsyncMock(return_value=value)))
            stack.enter_context(patch.object(db, 'add_balance_rub', credit))
            stack.enter_context(patch.object(db, 'spend_balance_rub', spend))
            stack.enter_context(patch.object(live, 'paid'))
            stack.enter_context(patch.object(referrals, 'maybe_reward_referrer', AsyncMock()))
            stack.enter_context(patch.object(referrals, 'maybe_reward_invitee', AsyncMock()))
            async def debit(*args):
                self.assertTrue(lock.locked())
                credit.assert_awaited_once_with(123, 100)
                return True
            spend.side_effect = debit
            await billing.grant_plan(123, 'topup', rw)
        return rw, credit, spend

    async def test_disabled_device_activated_before_payment_returns(self):
        rw, credit, spend = await self.scenario()
        rw.extend_panel_user.assert_awaited_once()
        spend.assert_awaited_once_with(123, 6)

    async def test_already_paid_day_is_not_charged_again(self):
        rw, credit, spend = await self.scenario(already_paid=True)
        spend.assert_not_awaited()
        rw.extend_panel_user.assert_not_awaited()

    async def test_activation_outage_does_not_fail_credited_payment(self):
        rw, credit, spend = await self.scenario(panel_failure=True)
        credit.assert_awaited_once_with(123, 100)

    async def test_duplicate_order_does_not_credit_or_activate_again(self):
        with patch.object(db, 'get_rollypay_order', AsyncMock(return_value={'status': 'granted'})), patch.object(billing, 'grant_plan', AsyncMock()) as grant:
            await billing.fulfill_rollypay_order('already-paid', SimpleNamespace())
        grant.assert_not_awaited()

    async def test_panel_rejection_refunds_daily_charge_but_keeps_topup(self):
        rw, credit, spend = await self.scenario(panel_error=RemnawaveError('panel unavailable'))
        self.assertEqual(credit.await_args_list, [call(123, 100), call(123, 6)])
        spend.assert_awaited_once_with(123, 6)
