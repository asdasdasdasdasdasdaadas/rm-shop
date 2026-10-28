import unittest
from unittest.mock import AsyncMock, patch
from app import live, activity_digest

class LiveActionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_records_actions_without_immediate_message(self):
        for action in live._ACTION_TITLES:
            with self.subTest(action=action), patch.object(live, '_chat_id', return_value=-100123), patch.object(activity_digest, 'record', AsyncMock()) as record, patch.object(live, 'post') as post:
                await live.user_action({'telegram_id':123}, action)
                record.assert_awaited_once_with(123, action, 'bot')
                post.assert_not_called()

    async def test_disabled_channel_and_unknown_action(self):
        with patch.object(activity_digest, 'record', AsyncMock()) as record, patch.object(live, '_chat_id', return_value=None):
            await live.web_user_action(123, 'share')
            record.assert_not_awaited()
        with patch.object(activity_digest, 'record', AsyncMock()) as record:
            await live.user_action({}, 'unknown')
            record.assert_not_awaited()

    async def test_record_failure_does_not_break_user_action(self):
        with patch.object(live, '_chat_id', return_value=-100123), patch.object(activity_digest, 'record', AsyncMock(side_effect=RuntimeError())):
            await live.web_user_action(123, 'copy')

    async def test_web_source_and_identity(self):
        with patch.object(live, '_chat_id', return_value=-100123), patch.object(activity_digest, 'record', AsyncMock()) as record:
            await live.web_user_action(123, 'share')
            record.assert_awaited_once_with(123, 'share', 'web')
