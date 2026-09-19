import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app import admin


class WhitelistBroadcastTest(unittest.IsolatedAsyncioTestCase):
    async def test_whitelist_uses_saved_text_and_all_users(self):
        request = SimpleNamespace(app={}, method='POST', json=AsyncMock(
            return_value={'template': 'whitelist', 'audience': 'unused'}))
        with patch.object(admin, '_need_auth', return_value=None), \
             patch.object(admin.db, 'broadcast_audience_counts', AsyncMock(return_value={'all': 2})), \
             patch.object(admin.db, 'list_broadcast_ids', AsyncMock(return_value=[1, 2])) as targets, \
             patch.object(admin, '_broadcast_template_preview', return_value='Сохранённый текст') as preview, \
             patch.object(admin, '_start_broadcast_job', return_value={'running': True}) as start:
            response = await admin.api_broadcast(request)
        self.assertEqual(response.status, 200)
        targets.assert_awaited_once_with('all')
        preview.assert_called_once_with('whitelist')
        start.assert_called_once_with(request.app, 'Сохранённый текст', [1, 2], 'whitelist')

    async def test_running_job_prevents_duplicate(self):
        request = SimpleNamespace(app={'broadcast_job': {'running': True}}, method='POST')
        with patch.object(admin, '_need_auth', return_value=None), \
             patch.object(admin, '_start_broadcast_job') as start:
            response = await admin.api_broadcast(request)
        self.assertEqual(response.status, 409)
        start.assert_not_called()

    def test_payload_keeps_snapshot_and_cabinet_button(self):
        with patch.object(admin, 'cabinet_keyboard', return_value='keyboard'):
            self.assertEqual(admin._broadcast_payload('whitelist', 'Сохранённый текст', 1, None, None),
                             ('Сохранённый текст', 'keyboard'))

    def test_preview_uses_editable_notice(self):
        with patch.object(admin, 'get_settings'), \
             patch.object(admin, 'notice_text', return_value='Новый текст') as notice:
            self.assertEqual(admin._broadcast_template_preview('whitelist'), 'Новый текст')
        notice.assert_called_once_with('broadcast_whitelist')
