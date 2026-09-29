import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import db, web as webapp


class TicketRatingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function('now', 0, lambda: '2026-09-29')
        self.conn.create_function('timezone', 2, lambda zone, value: value)
        self.conn.execute('CREATE TABLE tickets (id INTEGER PRIMARY KEY, telegram_id INTEGER, status TEXT, closed_at TEXT, support_rating INTEGER, rated_at TEXT)')
        self.conn.execute("INSERT INTO tickets VALUES (1, 123, 'open', NULL, NULL, NULL)")
        async def fetchrow(query, *args):
            return self.conn.execute(query, {str(i): arg for i, arg in enumerate(args, 1)}).fetchone()
        self.pool = SimpleNamespace(fetchrow=fetchrow)

    def tearDown(self): self.conn.close()

    async def test_only_owner_can_close_and_rate_once_after_closure(self):
        with patch.object(db, '_pool_req', return_value=self.pool):
            self.assertIsNone(await db.close_user_ticket(999, 1))
            self.assertIsNone(await db.rate_user_ticket(123, 1, 5))
            self.assertEqual((await db.close_user_ticket(123, 1))['status'], 'closed')
            self.assertIsNone(await db.close_user_ticket(123, 1))
            self.assertIsNone(await db.rate_user_ticket(999, 1, 5))
            self.assertEqual((await db.rate_user_ticket(123, 1, 4))['support_rating'], 4)
            self.assertIsNone(await db.rate_user_ticket(123, 1, 1))
            for bad in (0, 6, True, '5', None):
                with self.assertRaises(ValueError): await db.rate_user_ticket(123, 1, bad)

    async def test_endpoint_rejects_other_users_ticket(self):
        request = SimpleNamespace(match_info={'ticket_id':'1'}, json=AsyncMock(return_value={'action':'close'}))
        with patch.object(webapp, '_require_tickets', AsyncMock(return_value=(999,None))), patch.object(db, 'get_ticket', AsyncMock(return_value={'id':1, 'telegram_id':123})), patch.object(db, 'close_user_ticket', AsyncMock()) as close:
            response = await webapp.api_ticket_action(request)
        self.assertEqual(response.status, 404)
        close.assert_not_awaited()

    async def test_endpoint_requires_auth(self):
        from aiohttp import web
        request = SimpleNamespace()
        with patch.object(webapp, '_require_tickets', AsyncMock(return_value=(None, web.json_response({'ok':False},status=401)))), patch.object(db, 'get_ticket', AsyncMock()) as fetch:
            response = await webapp.api_ticket_action(request)
        self.assertEqual(response.status, 401)
        fetch.assert_not_awaited()
