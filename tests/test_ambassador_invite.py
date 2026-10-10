import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from app import ambassadors as amb, db, nudge, keyboards, config

CFG=dict(recruitment=True,accruing=True,budget=10000,max_members=20,first_percent=100,first_cap=500,recurring_percent=5,payout_min=2000,hold_days=14)
class AmbassadorInviteTest(unittest.IsolatedAsyncioTestCase):
    async def test_closed_paused_full_and_exhausted_do_not_recruit(self):
        for update,capacity in [({'recruitment':False},{}),({'accruing':False},{}),({},dict(members=20,spent=0)),({},dict(members=1,spent=1000000))]:
            pool=SimpleNamespace(fetchrow=AsyncMock(return_value=capacity))
            with patch.object(db,'_pool_req',return_value=pool):
                self.assertIsNone(await amb.recruitment_offer({**CFG,**update}))
        with patch.object(db,'_pool_req',return_value=SimpleNamespace(fetchrow=AsyncMock(return_value=dict(members=1,spent=0)))):
            self.assertEqual(await amb.recruitment_offer(CFG),CFG)

    async def test_marks_only_success_and_uses_marketing_sender(self):
        for success in [False,True]:
            pool=SimpleNamespace(execute=AsyncMock())
            with patch.object(db,'flag_on',AsyncMock(return_value=False)),patch.object(amb,'recruitment_offer',AsyncMock(return_value=CFG)),patch.object(amb,'due_invitations',AsyncMock(return_value=[dict(telegram_id=42,first_name='Иван')])),patch.object(nudge,'_deliver',AsyncMock(return_value=success)) as deliver,patch.object(db,'_pool_req',return_value=pool),patch.object(keyboards,'ambassador_keyboard',return_value=None):
                sent,ids=await nudge.send_due_ambassador_nudges(None,[])
                self.assertEqual(sent,int(success));self.assertEqual(ids,[42])
                self.assertEqual(deliver.call_args.kwargs['kind'],'nudge_ambassador')
                self.assertEqual(pool.execute.await_count,int(success))
                self.assertTrue(db.is_marketing_message('nudge_ambassador'))

    def test_keyboard_opens_program_with_required_navigation(self):
        with patch.object(keyboards,'mini_app_url',return_value='https://example.org/?a=1'):
            markup=keyboards.ambassador_keyboard()
        self.assertIn('screen=ambassador',markup.inline_keyboard[0][0].web_app.url)
        self.assertEqual(markup.inline_keyboard[0][0].style,'success')
        self.assertEqual(markup.inline_keyboard[1][0].callback_data,'profile')
        self.assertIn('500 ₽',amb.invitation_text(CFG))

import os
@unittest.skipUnless(os.environ.get('PGLITE_MODULE'), 'Requires PostgreSQL test engine')
class AmbassadorAudienceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests.test_funnel_integration import FunnelPostgresTest
        await FunnelPostgresTest.asyncSetUp(self)
        p=patch.object(amb,'get_settings',return_value=self.settings);p.start();self.addCleanup(p.stop)
    async def asyncTearDown(self):
        self.proc.stdin.close();await self.proc.wait()
    async def test_audience_and_once_only_marker(self):
        await self.pool.query('''INSERT INTO users(telegram_id,bot_started_at,has_paid_topup,first_online_at,balance_rub)
            SELECT id,NOW()-INTERVAL '10 days',TRUE,NOW()-INTERVAL '8 days',100 FROM generate_series(3,10) id;
            INSERT INTO devices(telegram_id,title,last_online_at) SELECT id,'Телефон',NOW() FROM generate_series(3,10) id;
            UPDATE users SET quiet_notifications=TRUE WHERE telegram_id=4;
            INSERT INTO tickets(telegram_id) VALUES(5);
            UPDATE users SET ambassador_invite_sent_at=NOW() WHERE telegram_id=6;
            INSERT INTO ambassadors(telegram_id,application,token) VALUES(7,'Мой канал','pending-seven');
            UPDATE devices SET last_online_at=NOW()-INTERVAL '4 days' WHERE telegram_id=8;
            UPDATE users SET has_paid_topup=FALSE WHERE telegram_id=9;
            UPDATE users SET balance_rub=1 WHERE telegram_id=10;''',script=True)
        self.assertEqual([r['telegram_id'] for r in await amb.due_invitations(80,[])],[3])
        self.assertEqual(await amb.due_invitations(80,[3]),[])
        await self.pool.execute('UPDATE users SET ambassador_invite_sent_at=NOW() WHERE telegram_id=3')
        self.assertEqual(await amb.due_invitations(80,[]),[])
