import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse, parse_qs
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage
from app import campaigns


class CampaignAnnouncementTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.row = dict(campaign_id=7,telegram_id=123,attempts=1,reward_rub=540)
        self.bot = AsyncMock()
        self.finish = AsyncMock()
        self.log = AsyncMock()
        for target,value in [('finish_campaign_message',self.finish),('log_bot_message',self.log)]:
            p=patch.object(campaigns.db,target,value);p.start();self.addCleanup(p.stop)
        p=patch.object(campaigns,'invite_url',return_value='https://t.me/test_bot?start=ref_123')
        p.start();self.addCleanup(p.stop)

    async def test_success_has_personal_share_button_and_no_preview(self):
        await campaigns.deliver_campaign_message(self.bot,self.row)
        args=self.bot.send_message.call_args
        self.assertIn('540 ₽',args.args[1])
        self.assertIn('впервые',args.args[1])
        self.assertTrue(args.kwargs['link_preview_options'].is_disabled)
        button=args.kwargs['reply_markup'].inline_keyboard[0][0]
        self.assertEqual(parse_qs(urlparse(button.url).query)['url'],['https://t.me/test_bot?start=ref_123'])
        self.finish.assert_awaited_once_with(7,123,error=None,retry_seconds=None,retryable=False)

    async def test_rate_limit_requeues_and_pauses_worker(self):
        self.bot.send_message.side_effect=TelegramRetryAfter(method=SendMessage(chat_id=123,text='x'),message='limited',retry_after=8)
        pause=await campaigns.deliver_campaign_message(self.bot,self.row)
        self.assertEqual(pause,8)
        self.assertEqual(self.finish.call_args.kwargs['retry_seconds'],8)

    async def test_blocked_user_is_not_retried(self):
        self.bot.send_message.side_effect=TelegramForbiddenError(method=SendMessage(chat_id=123,text='x'),message='blocked')
        await campaigns.deliver_campaign_message(self.bot,self.row)
        self.assertIsNone(self.finish.call_args.kwargs['retry_seconds'])
        self.assertIsNotNone(self.finish.call_args.kwargs['error'])

    async def test_temporary_failure_retries_but_stops_after_three_attempts(self):
        self.bot.send_message.side_effect=OSError('network')
        await campaigns.deliver_campaign_message(self.bot,self.row)
        self.assertEqual(self.finish.call_args.kwargs['retry_seconds'],60)
        self.row['attempts']=3
        await campaigns.deliver_campaign_message(self.bot,self.row)
        self.assertIsNone(self.finish.call_args.kwargs['retry_seconds'])

    async def test_logging_failure_does_not_requeue_delivered_message(self):
        self.log.side_effect=OSError('audit unavailable')
        with self.assertLogs(campaigns.logger,level='ERROR'):
            await campaigns.deliver_campaign_message(self.bot,self.row)
        self.finish.assert_awaited_once_with(7,123,error=None,retry_seconds=None,retryable=False)

    def test_moscow_input_is_converted_to_utc(self):
        value=campaigns.parse_campaign_moscow_time('2030-01-02T18:30')
        self.assertEqual(value.isoformat(),'2030-01-02T15:30:00+00:00')
        for value in (None, '', '2030-01-02T18:30Z', '2030-02-31T12:00'):
            with self.assertRaises(ValueError): campaigns.parse_campaign_moscow_time(value)
