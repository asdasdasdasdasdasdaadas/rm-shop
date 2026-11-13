import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin, db


class ScheduledBroadcastTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.kv = {}

        async def get_kv(key):
            return self.kv.get(key, "")

        async def set_kv(key, value):
            self.kv[key] = value

        for name, mock in [('get_kv', get_kv), ('set_kv', set_kv),
                           ('broadcast_audience_counts', AsyncMock(return_value={'all': 2})),
                           ('list_broadcast_ids', AsyncMock(return_value=[1, 2]))]:
            p = patch.object(db, name, mock)
            p.start()
            self.addCleanup(p.stop)
        for p in [patch.object(admin, '_need_auth', return_value=None),
                  patch.object(admin, 'get_settings', return_value=SimpleNamespace(referral_program_enabled=True))]:
            p.start()
            self.addCleanup(p.stop)
        self.app = {}

    def request(self, body):
        return SimpleNamespace(method='POST', app=self.app, json=AsyncMock(return_value=body))

    async def test_schedule_then_send_when_due(self):
        at = datetime.now(timezone.utc) + timedelta(hours=2)
        with patch.object(admin, '_start_broadcast_job') as start:
            response = await admin.api_broadcast(self.request(
                {'template': 'gift3', 'text': 'Дарим', 'scheduled_at': at.isoformat()}))
            self.assertEqual(response.status, 200)
            start.assert_not_called()
            stored = json.loads(self.kv[admin.SCHEDULE_KV])
            self.assertEqual([(x['template'], x['text']) for x in stored], [('gift3', 'Дарим')])

            await admin.run_due_broadcasts(self.app)  # not due yet
            start.assert_not_called()

            stored[0]['at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            self.kv[admin.SCHEDULE_KV] = json.dumps(stored)
            await admin.run_due_broadcasts(self.app)
            start.assert_called_once_with(self.app, 'Дарим', None, 'gift3', None, {'template': 'gift3', 'text': 'Дарим', 'audience': 'all'})
            self.assertEqual(json.loads(self.kv[admin.SCHEDULE_KV]), [])

    async def test_waits_while_another_broadcast_runs(self):
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.kv[admin.SCHEDULE_KV] = json.dumps([{'id': 'a', 'at': past, 'template': '', 'text': 'Hi', 'audience': 'all'}])
        self.app['broadcast_job'] = {**admin._new_bc_job(), 'running': True}
        with patch.object(admin, '_start_broadcast_job') as start:
            await admin.run_due_broadcasts(self.app)
        start.assert_not_called()
        self.assertEqual(len(json.loads(self.kv[admin.SCHEDULE_KV])), 1)

    async def test_rejects_past_time_and_cancels(self):
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        response = await admin.api_broadcast(self.request({'text': 'Hi', 'scheduled_at': past}))
        self.assertEqual(response.status, 400)
        at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = await admin.api_broadcast(self.request({'text': 'Hi', 'scheduled_at': at}))
        item_id = json.loads(response.body)['planned']['id']
        response = await admin.api_broadcast(self.request({'cancel_scheduled': item_id}))
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(self.kv[admin.SCHEDULE_KV]), [])
