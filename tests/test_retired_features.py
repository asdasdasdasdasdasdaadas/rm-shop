import unittest
from unittest.mock import AsyncMock, patch

class RetiredFeaturesTest(unittest.IsolatedAsyncioTestCase):
    def test_no_promo_step_in_funnel(self):
        from app import funnel_board
        self.assertNotIn('winback', funnel_board.CONDITION_IDS)
        self.assertIn('winback', funnel_board.RETIRED_CONDITIONS)

    async def test_no_promo_redemption(self):
        from app import db
        with patch.object(db,'_pool_req',side_effect=AssertionError('Must not touch balance')):
            with self.assertRaises(ValueError): await db.redeem_promo_code(123,'TEST')
