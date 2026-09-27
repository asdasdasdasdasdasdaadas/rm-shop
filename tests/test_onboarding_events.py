import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db, web

class OnboardingEventsTest(unittest.IsolatedAsyncioTestCase):
    async def test_client_can_record_only_allowed_stages_for_authenticated_user(self):
        for stage, status in [('gift_view',200),('wizard_4',200),('channel_passed',400),('connected',400),([],400)]:
            with self.subTest(stage=stage), patch.object(web,'_require_tg',AsyncMock(return_value=(123,None))), patch.object(db,'record_onboarding_event',AsyncMock()) as save:
                response=await web.api_onboarding_event(SimpleNamespace(json=AsyncMock(return_value={'stage':stage,'telegram_id':999})))
                self.assertEqual(response.status,status)
                if status == 200: save.assert_awaited_once_with(123,stage)
                else: save.assert_not_awaited()

    async def test_event_is_first_observation_only_and_tracking_failure_is_nonblocking(self):
        pool=SimpleNamespace(execute=AsyncMock())
        with patch.object(db,'_pool_req',return_value=pool):
            await db.record_onboarding_event(1,'cabinet')
            self.assertIn('ON CONFLICT (telegram_id,stage) DO NOTHING', pool.execute.call_args.args[0])
            pool.execute.side_effect=RuntimeError('offline')
            await db.record_onboarding_event(1,'cabinet')
