import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app import config, shop_config


class ReferralSettingsTest(unittest.IsolatedAsyncioTestCase):
    async def test_toggle_persists_and_survives_reload_without_other_settings(self):
        previous = config.shop_overlay().copy()
        self.addCleanup(config.set_shop_overlay, previous)
        stored = {'brand_name':'VPN','admin_live_chat_id':'@unavailable_channel','plan_1m_rub':0,
                  'notices':{'welcome':'Custom message'}}
        async def read(key): return json.dumps(stored)
        async def write(key,value):
            stored.clear()
            stored.update(json.loads(value))
        with patch.object(shop_config,'get_settings',return_value=SimpleNamespace(balance_enabled=True)), \
             patch.object(shop_config.db,'get_kv',AsyncMock(side_effect=read)), \
             patch.object(shop_config.db,'set_kv',AsyncMock(side_effect=write)), \
             patch.object(shop_config.db,'migrate_legacy_promo_codes',AsyncMock()), \
             patch.object(shop_config,'validate_shop',side_effect=AssertionError('Unrelated validation')):
            for enabled in (True,False):
                response = await shop_config.save_referral_settings({'referral_program_enabled':enabled,
                    'referral_mode':'classic','referral_invitee_reward_rub':'30','referral_payout_min':'2000'})
                self.assertEqual(response['values']['referral_program_enabled'],enabled)
                self.assertEqual(config.shop_overlay()['referral_program_enabled'],enabled)
                config.set_shop_overlay({})
                await shop_config.load_shop_overlay()
                self.assertEqual(config.shop_overlay()['referral_program_enabled'],enabled)
                self.assertEqual(stored['notices'],{'welcome':'Custom message'})
                self.assertEqual(stored['admin_live_chat_id'],'@unavailable_channel')
                self.assertEqual(stored['plan_1m_rub'],0)

    async def test_bad_values_do_not_write(self):
        with patch.object(shop_config,'get_settings',return_value=SimpleNamespace(balance_enabled=True)), \
             patch.object(shop_config.db,'set_kv',AsyncMock()) as write:
            for body in ({'referral_program_enabled':'false'},
                         {'referral_program_enabled':True,'referral_payout_min':-1}):
                with self.assertRaises(ValueError):
                    await shop_config.save_referral_settings(body)
            write.assert_not_awaited()
