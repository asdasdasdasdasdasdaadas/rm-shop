import unittest
from unittest.mock import AsyncMock, patch
from app.interface_editor import editor_catalog

class RetiredFeaturesTest(unittest.IsolatedAsyncioTestCase):
    def test_editor_has_no_removed_destinations(self):
        catalog=editor_catalog()
        retired={'promo','referrals','ambassador','settings'}
        self.assertFalse(retired & {s['id'] for s in catalog['screens']})
        self.assertFalse(retired & {a['id'] for a in catalog['actions']})
        self.assertFalse({'device_setup','connect_check'} & {f['key'] for f in catalog['fields']})

    async def test_no_promo_send_even_when_forced(self):
        from app.winback import send_due
        bot=AsyncMock()
        self.assertEqual(await send_due(bot,force=True),(0,[]))
        bot.send_message.assert_not_called()

    async def test_no_promo_redemption(self):
        from app import db
        with patch.object(db,'_pool_req',side_effect=AssertionError('Must not touch balance')):
            with self.assertRaises(ValueError): await db.redeem_promo_code(123,'TEST')

    async def test_no_ambassador_recruitment(self):
        from app.nudge import send_due_ambassador_nudges
        self.assertEqual(await send_due_ambassador_nudges(AsyncMock()),(0,[]))
