import unittest
from unittest.mock import patch

from aiohttp import web as aiohttp_web
from app import db, web
from app.config import Settings
from app.keyboards import profile_keyboard, share_keyboard, story_webapp_button


class RemovedStoriesTest(unittest.IsolatedAsyncioTestCase):
    async def test_old_api_and_media_are_gone(self):
        self.assertEqual((await web.api_story_share(None)).status, 410)
        with self.assertRaises(aiohttp_web.HTTPGone):
            await web.webapp_story(None)

    async def test_pending_requests_cannot_credit_balance(self):
        with patch.object(db, '_pool_req') as pool:
            self.assertIsNone(await db.approve_story_reward(123, 150))
            self.assertFalse(await db.start_story_check(123))
            pool.assert_not_called()

    @patch("app.keyboards.get_settings", return_value=Settings.model_construct(balance_enabled=True, bot_username="test_bot", story_reward_enabled=True))
    @patch("app.keyboards.mini_app_url", return_value="https://example.com/app")
    def test_legacy_keyboard_request_never_shows_story(self, *_mocks):
        self.assertIsNone(story_webapp_button(story_offer=True))
        for markup in (profile_keyboard(trial_available=True, has_access=True, story_offer=True),
                       share_keyboard('test_bot',123,story_offer=True)):
            for row in markup.inline_keyboard:
                for button in row:
                    self.assertNotIn('Истори',button.text)
