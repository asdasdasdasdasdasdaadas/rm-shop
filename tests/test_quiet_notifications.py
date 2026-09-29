import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db, web as webapp

class QuietNotificationsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn=sqlite3.connect(':memory:'); self.conn.row_factory=sqlite3.Row
        self.conn.executescript('''CREATE TABLE users (telegram_id INTEGER PRIMARY KEY,has_paid_topup BOOLEAN,quiet_notifications BOOLEAN DEFAULT FALSE);
          INSERT INTO users (telegram_id,has_paid_topup) VALUES (1,TRUE),(2,FALSE);''')
        self.addCleanup(self.conn.close)
        async def fetchrow(sql,*args): return self.conn.execute(sql,{str(i):a for i,a in enumerate(args,1)}).fetchone()
        async def fetchval(sql,*args):
            row=await fetchrow(sql,*args)
            return row[0] if row else None
        self.pool=SimpleNamespace(fetchrow=fetchrow,fetchval=fetchval)

    async def test_only_paid_user_can_change_and_reenable(self):
        with patch.object(db,'_pool_req',return_value=self.pool):
            self.assertFalse(await db.set_quiet_notifications(2,True))
            self.assertTrue(await db.set_quiet_notifications(1,True))
            for kind in ('broadcast','nudge_idle','nudge_invite','nudge_payment','referral_campaign_start','first_device_thanks'):
                self.assertFalse(await db.notification_allowed(1,kind))
            for kind in ('low_balance','nudge_trial_end','topup','support_reply','device_reissued'):
                self.assertTrue(await db.notification_allowed(1,kind))
            self.assertTrue(await db.set_quiet_notifications(1,False))
            self.assertTrue(await db.notification_allowed(1,'broadcast'))

    async def test_confirmation_required_and_identity_from_session(self):
        request=SimpleNamespace(json=AsyncMock(return_value={'quiet':True,'telegram_id':999}))
        with patch.object(webapp,'_require_tg',AsyncMock(return_value=(1,None))), patch.object(db,'set_quiet_notifications',AsyncMock(return_value=True)) as save:
            self.assertEqual((await webapp.api_notification_settings(request)).status,400)
            save.assert_not_awaited()
            request.json.return_value['confirmed']=True
            self.assertEqual((await webapp.api_notification_settings(request)).status,200)
            save.assert_awaited_once_with(1,True)
