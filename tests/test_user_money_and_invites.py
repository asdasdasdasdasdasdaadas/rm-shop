import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app import db


class ReferralVisitTest(unittest.IsolatedAsyncioTestCase):
    async def run_upsert(self, ref, attached_to):
        pool = MagicMock()
        pool.fetchrow = AsyncMock(return_value={'telegram_id': 5, 'username': None, 'first_name': 'x',
                                                'referred_by': attached_to, 'referral_attached': False})
        pool.execute = AsyncMock()
        with patch.object(db, '_pool_req', return_value=pool):
            await db.upsert_user(5, None, 'x', referred_by=ref)
        return pool.execute

    async def test_visit_of_an_existing_user_is_an_attempt(self):
        execute = await self.run_upsert(1, None)
        self.assertIn('referral_link_visits', execute.await_args.args[0])
        self.assertEqual(execute.await_args.args[1:], (1, 5, False))

    async def test_new_friend_is_attached(self):
        execute = await self.run_upsert(1, 1)
        self.assertEqual(execute.await_args.args[1:], (1, 5, True))

    async def test_no_link_and_own_link_are_not_recorded(self):
        (await self.run_upsert(None, None)).assert_not_awaited()
        (await self.run_upsert(5, None)).assert_not_awaited()


class UserListSqlTest(unittest.TestCase):
    def test_sorts_by_real_money_and_friends(self):
        self.assertIn('payment_receipts', db._admin_users_order({'sort': 'paid_desc'}))
        self.assertIn('invited_count', db._admin_users_order({'sort': 'invited_desc'}))


if __name__ == '__main__':
    unittest.main()
