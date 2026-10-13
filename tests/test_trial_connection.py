import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db, balance, web, live
from app.remnawave import panel_online_at

class Context:
    def __init__(self,value): self.value=value
    async def __aenter__(self): return self.value
    async def __aexit__(self,*args): return False

class TrialConnectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_subscription_view_is_not_connection(self):
        panel={'id':4,'subLastOpenedAt':'2026-10-13T10:00:00Z'}
        self.assertIsNone(panel_online_at(panel))
        with patch.object(db,'claim_first_online',AsyncMock(return_value=None)) as claim:
            await live.note_panel_online(1,panel)
            claim.assert_not_awaited()
            await live.note_panel_online(1,{**panel,'userTraffic':{'usedTrafficBytes':100}})
            claim.assert_awaited_once_with(1)
        self.assertIsNotNone(panel_online_at({'onlineAt':'2026-10-13T10:00:00Z'}))

    async def test_waiting_gift_is_not_charged_by_manual_sync(self):
        rw=SimpleNamespace(enable_panel_user=AsyncMock())
        with patch.object(db,'get_user',AsyncMock(return_value={'trial_waiting_connection':True})), \
             patch.object(db,'spend_balance_rub',AsyncMock()) as spend, \
             patch.object(db,'mark_devices_billed',AsyncMock()) as mark:
            result=await balance._bill_due_device(rw,None,{'id':1,'telegram_id':2,'remnawave_id':3},6,False,set())
            self.assertEqual(result,'extended');spend.assert_not_awaited()
            self.assertFalse(mark.call_args.kwargs['touch_billed'])

    async def test_first_connection_arms_billing_once_without_recrediting(self):
        conn=SimpleNamespace(fetchval=AsyncMock(side_effect=[7,None]),execute=AsyncMock())
        conn.transaction=lambda:Context(conn)
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(acquire=lambda:Context(conn))):
            await db.activate_connected_trial(7);await db.activate_connected_trial(7)
        conn.execute.assert_awaited_once()
        self.assertIn('last_billed_at=NULL',conn.execute.call_args.args[0])
        self.assertNotIn('balance_rub',conn.execute.call_args.args[0])

    async def test_gift_device_creation_does_not_spend_or_refund(self):
        rw=SimpleNamespace(create_user=AsyncMock(return_value={'id':9,'subscriptionUrl':'https://sub.test/9'}))
        request=SimpleNamespace(app={'rw':rw},json=AsyncMock(return_value={'platform':'ios'}))
        with patch.object(web,'_if_down',AsyncMock(return_value=None)), \
             patch.object(web,'_require_tg',AsyncMock(return_value=(7,None))), \
             patch.object(web,'get_settings',return_value=SimpleNamespace(max_devices=6,vpn_day_price_rub=6,remnawave_hwid_limit=1)), \
             patch.object(db,'billable_device_count',AsyncMock(return_value=0)), \
             patch.object(db,'get_user',AsyncMock(return_value={'trial_waiting_connection':True})), \
             patch.object(db,'spend_balance_rub',AsyncMock()) as spend, \
             patch.object(db,'add_balance_rub',AsyncMock()) as refund, \
             patch.object(db,'add_device',AsyncMock()), \
             patch.object(db,'save_device_subscription',AsyncMock()), \
             patch.object(db,'mark_first_device_thanks_pending',AsyncMock()):
            response=await web._api_add_device_locked(request)
            self.assertEqual(response.status,200);spend.assert_not_awaited();refund.assert_not_awaited()
            with patch.object(db,'billable_device_count',AsyncMock(return_value=1)):
                response=await web._api_add_device_locked(request)
                self.assertEqual(response.status,400)
            rw.create_user.assert_awaited_once()
