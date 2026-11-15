import unittest
from unittest.mock import AsyncMock, patch

from app import db
from app.tg_err import is_user_blocked_bot, is_user_deactivated, telegram_fail_reason


class DeletedAccounts(unittest.IsolatedAsyncioTestCase):
    def test_deactivated_is_not_a_block(self):
        err = Exception("Telegram server says - Forbidden: user is deactivated")
        self.assertTrue(is_user_deactivated(err))
        self.assertFalse(is_user_blocked_bot(err))
        self.assertTrue(is_user_deactivated(extra={"error": telegram_fail_reason(err)}))
        self.assertFalse(is_user_deactivated(Exception("Forbidden: bot was blocked by the user")))

    async def test_failed_delivery_marks_the_account(self):
        pool = AsyncMock()
        with patch.object(db, "_pool_req", return_value=pool), \
             patch.object(db, "mark_tg_deleted", AsyncMock()) as deleted, \
             patch.object(db, "mark_bot_blocked", AsyncMock()) as blocked:
            await db.log_bot_message(kind="broadcast", telegram_id=7, title="t", body="b", status="failed",
                                     extra={"error_raw": "Forbidden: user is deactivated"})
            deleted.assert_awaited_once_with(7)
            blocked.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
