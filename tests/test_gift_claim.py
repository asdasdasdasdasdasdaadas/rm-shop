"""Only explicit cabinet acceptance may credit the gift."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.handlers import profile
from app import web


class GiftClaimTest(unittest.IsolatedAsyncioTestCase):
    async def test_old_bot_trial_button_only_invites_to_cabinet(self):
        cb = SimpleNamespace(from_user=SimpleNamespace(id=123),
                             message=SimpleNamespace(edit_text=AsyncMock()))
        with patch.object(profile, 'gate_or_continue', AsyncMock(return_value=True)), \
             patch.object(profile, 'ack', AsyncMock()), \
             patch.object(profile, 'trial_is_available', return_value=True), \
             patch.object(profile, 'back_profile_keyboard', return_value=None), \
             patch.object(profile.db, 'get_user', AsyncMock(return_value={'trial_used': False})), \
             patch.object(profile.db, 'claim_trial_balance', AsyncMock()) as grant, \
             patch.object(profile.db, 'mark_trial_used', AsyncMock()) as used:
            await profile.activate_trial(cb, AsyncMock())
            grant.assert_not_awaited()
            used.assert_not_awaited()
            self.assertIn('Принять подарок', cb.message.edit_text.call_args.args[0])

    async def test_cabinet_claim_credits_once_even_with_concurrent_requests(self):
        request = SimpleNamespace(app={'rw': AsyncMock()})
        settings = SimpleNamespace(balance_enabled=True, trial_days=3)
        with patch.object(web, '_require_tg', AsyncMock(return_value=(123, None))), \
             patch.object(web, 'get_settings', return_value=settings), \
             patch.object(web, 'trial_is_available', return_value=True), \
             patch.object(web, 'trial_grant_rub', return_value=18), \
             patch.object(web.db, 'get_user', AsyncMock(return_value={'trial_used': False})), \
             patch.object(web.db, 'claim_trial_balance', AsyncMock(side_effect=[18, None])) as grant, \
             patch.object(web.db, 'log_billing_event', AsyncMock()) as log:
            first = await web.api_trial(request)
            second = await web.api_trial(request)
            self.assertEqual(first.status, 200)
            self.assertEqual(second.status, 400)
            self.assertEqual(grant.await_count, 2)
            log.assert_awaited_once()
            self.assertEqual(log.call_args.kwargs['source'], 'user')
