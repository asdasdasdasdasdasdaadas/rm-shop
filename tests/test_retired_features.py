import unittest
from unittest.mock import AsyncMock, patch

class RetiredFeaturesTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_promo_send_even_when_forced(self):
        from app.winback import send_due
        bot=AsyncMock()
        self.assertEqual(await send_due(bot,force=True),(0,[]))
        bot.send_message.assert_not_called()

    async def test_no_promo_redemption(self):
        from app import db
        with patch.object(db,'_pool_req',side_effect=AssertionError('Must not touch balance')):
            with self.assertRaises(ValueError): await db.redeem_promo_code(123,'TEST')
