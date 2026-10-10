import json
import unittest
from unittest.mock import AsyncMock, patch
from app import config, db, shop_config


class RouterOfferTest(unittest.IsolatedAsyncioTestCase):
    def test_new_install_default_is_disabled(self):
        self.assertFalse(config.Settings.model_fields['router_enabled'].default)

    async def load(self, store):
        async def get(key): return store.get(key, '')
        async def put(key, value): store[key] = value
        with patch.object(db, 'get_kv', side_effect=get), patch.object(db, 'set_kv', side_effect=put), patch.object(db, 'migrate_legacy_promo_codes', AsyncMock()), patch.object(shop_config, 'set_shop_overlay') as apply:
            await shop_config.load_shop_overlay()
        return apply.call_args.args[0]

    async def test_offer_stays_disabled(self):
        store = {shop_config.KV_KEY: json.dumps({'router_enabled': True, 'router_rub': 500})}
        first = await self.load(store)
        self.assertNotIn('router_enabled', first)
        self.assertNotIn('router_rub', first)
        first['router_enabled'] = True
        store[shop_config.KV_KEY] = json.dumps(first)
        self.assertNotIn('router_enabled', await self.load(store))

    async def test_empty_install_records_migration(self):
        store = {}
        self.assertFalse((await self.load(store)).get('router_enabled', False))
        self.assertEqual(store['router_offer_hidden_v1'], '1')

    async def test_device_limit_upgrade_preserves_later_admin_changes(self):
        store = {shop_config.KV_KEY: json.dumps({'max_devices': 12})}
        first = await self.load(store)
        self.assertEqual(first['max_devices'], 6)
        first['max_devices'] = 15
        store[shop_config.KV_KEY] = json.dumps(first)
        self.assertEqual((await self.load(store))['max_devices'], 15)
