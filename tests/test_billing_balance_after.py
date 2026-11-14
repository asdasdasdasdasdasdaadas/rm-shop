import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db, balance

class Context:
    def __init__(self, value): self.value=value
    async def __aenter__(self): return self.value
    async def __aexit__(self, *args): return False

class BillingBalanceAfterTest(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_is_calculated_from_locked_balance_and_propagated_per_device(self):
        marked=[{'id':1,'prev_at':None,'prev_on':None},{'id':2,'prev_at':'yesterday','prev_on':None}]
        conn=SimpleNamespace(fetchrow=AsyncMock(return_value={'bal':15}),execute=AsyncMock(),fetch=AsyncMock(return_value=marked))
        conn.transaction=lambda: Context(conn)
        pool=SimpleNamespace(acquire=lambda: Context(conn))
        devices=[{'id':i,'telegram_id':1,'remnawave_id':i,'title':str(i)} for i in [1,2,3]]
        with patch.object(db,'_pool_req',return_value=pool):
            ext,dis=await balance._decide_user_devices(devices,6,False)
        self.assertEqual([d['charge_balance_after'] for d in ext],[9,3])
        self.assertEqual([d['id'] for d in dis],[3])
        self.assertNotIn('charge_balance_after',devices[0])
        self.assertIn('FOR UPDATE',conn.fetchrow.call_args.args[0])
        self.assertEqual(conn.execute.call_args.args[1:],(1,12))
        # The two paid devices are marked billed inside the same transaction as the charge.
        self.assertEqual(conn.fetch.call_args.args[1],[1,2])
        self.assertEqual(ext[1]['prev_billed'],('yesterday',None))
        rw=SimpleNamespace(bulk_refresh_lease=AsyncMock())
        with patch.object(db,'mark_devices_billed',AsyncMock()), patch.object(db,'log_billing_events',AsyncMock()) as log:
            await balance._commit_extends(rw,ext,price=6,paused=False,source='cron',chunk=100)
        self.assertEqual([r['balance_after'] for r in log.call_args.args[0]],[9,3])

    async def test_single_device_fallback_keeps_charge_snapshot(self):
        rw=SimpleNamespace(extend_panel_user=AsyncMock())
        with patch.object(db,'mark_devices_billed',AsyncMock()), patch.object(db,'log_billing_event',AsyncMock()) as log:
            await balance._extend_already_charged(rw,{'telegram_id':1,'id':2,'remnawave_id':3,'charge_balance_after':0},6,False,'cron')
        self.assertEqual(log.call_args.kwargs['balance_after'],0)

    async def test_panel_refusal_refunds_and_reopens_the_day(self):
        from app.remnawave import RemnawaveError
        rw=SimpleNamespace(extend_panel_user=AsyncMock(side_effect=RemnawaveError('down')))
        item={'telegram_id':1,'id':2,'remnawave_id':3,'charge_balance_after':0,'prev_billed':('t',None)}
        with patch.object(db,'add_balance_rub',AsyncMock()) as refund, \
                patch.object(db,'restore_device_billed',AsyncMock()) as restore, \
                patch.object(db,'log_billing_event',AsyncMock()):
            self.assertFalse(await balance._extend_already_charged(rw,item,6,False,'cron'))
        refund.assert_awaited_once_with(1,6)
        restore.assert_awaited_once_with(2,('t',None))
