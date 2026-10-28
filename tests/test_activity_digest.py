import unittest
from datetime import datetime, date, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app import activity_digest as digest, live

class DigestTest(unittest.IsolatedAsyncioTestCase):
    def connection(self, day):
        conn=MagicMock()
        conn.transaction.return_value.__aenter__=AsyncMock()
        conn.transaction.return_value.__aexit__=AsyncMock(return_value=False)
        conn.fetchval=AsyncMock(side_effect=[True,day,2])
        conn.fetch=AsyncMock(return_value=[{'action':'share','events':5,'users':2}])
        conn.execute=AsyncMock()
        pool=MagicMock()
        pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__=AsyncMock(return_value=False)
        return pool,conn

    async def test_moscow_schedule_and_success(self):
        pool,conn=self.connection(date(2026,10,26))
        bot=AsyncMock()
        with patch.object(live,'_chat_id',return_value=-100123), patch.object(digest.db,'_pool_req',return_value=pool):
            self.assertFalse(await digest.send_due(bot,datetime(2026,10,27,5,59,tzinfo=timezone.utc)))
            pool.acquire.assert_not_called()
            self.assertTrue(await digest.send_due(bot,datetime(2026,10,27,6,tzinfo=timezone.utc)))
        self.assertIn('26.10.2026',bot.send_message.call_args.args[1])
        self.assertIn('людей: <b>2</b>',bot.send_message.call_args.args[1])
        conn.execute.assert_awaited_once_with('INSERT INTO admin_activity_digests(day) VALUES ($1)',date(2026,10,26))

    async def test_failure_is_not_marked_sent(self):
        pool,conn=self.connection(date(2026,10,26))
        bot=AsyncMock();bot.send_message.side_effect=TimeoutError()
        with patch.object(live,'_chat_id',return_value=-100123), patch.object(digest.db,'_pool_req',return_value=pool):
            with self.assertRaises(TimeoutError):
                await digest.send_due(bot,datetime(2026,10,27,6,tzinfo=timezone.utc))
        conn.execute.assert_not_awaited()

    async def test_no_pending_day_does_not_send(self):
        pool,conn=self.connection(None);bot=AsyncMock()
        with patch.object(live,'_chat_id',return_value=-100123), patch.object(digest.db,'_pool_req',return_value=pool):
            self.assertFalse(await digest.send_due(bot,datetime(2026,10,27,6,tzinfo=timezone.utc)))
        bot.send_message.assert_not_called()
