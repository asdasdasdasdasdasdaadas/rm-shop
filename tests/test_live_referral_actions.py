import unittest
from unittest.mock import AsyncMock, patch

from app import db, live


class LiveReferralActionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for p in [patch.object(live, '_chat_id', return_value=-100123),
                  patch('app.referral_followup.record_interest', AsyncMock()),
                  patch('app.activity_digest.record', AsyncMock())]:
            p.start()
            self.addCleanup(p.stop)

    async def test_bot_invite_click_is_posted_at_once(self):
        with patch.object(live, 'post') as post:
            await live.user_action({'telegram_id': 5, 'first_name': 'Аня', 'username': 'anya'}, 'invite')
        text = post.call_args.args[0]
        self.assertIn('Пригласить друзей', text)
        self.assertIn('@anya', text)
        self.assertIn('в боте', text)

    async def test_web_copy_click_loads_the_user_name(self):
        with patch.object(live, 'post') as post, \
                patch.object(db, 'get_user', AsyncMock(return_value={'telegram_id': 7, 'first_name': 'Петя', 'username': None})):
            await live.web_user_action(7, 'copy')
        text = post.call_args.args[0]
        self.assertIn('Скопировать приглашение', text)
        self.assertIn('Петя', text)
        self.assertIn('в личном кабинете', text)

    async def test_other_actions_stay_in_the_digest_only(self):
        with patch.object(live, 'post') as post:
            await live.user_action({'telegram_id': 5}, 'about')
        post.assert_not_called()
