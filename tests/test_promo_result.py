import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from app import web


class PromoResultTest(unittest.IsolatedAsyncioTestCase):
    async def test_response_uses_actual_credited_amount_and_balance(self):
        request=SimpleNamespace(app={'rw':object()},json=AsyncMock(return_value={'code':'GIFT'}))
        with patch.object(web,'_if_down',AsyncMock(return_value=None)), \
             patch.object(web,'_require_tg',AsyncMock(return_value=(42,None))), \
             patch.object(web,'get_settings',return_value=SimpleNamespace(promo_enabled=True,balance_enabled=True,vpn_day_price_rub=6)), \
             patch.object(web.db,'claim_promo_code',AsyncMock(return_value=9)), \
             patch.object(web.db,'add_balance_rub',AsyncMock(return_value=180)) as credit:
            response=await web.api_promo(request)
        credit.assert_awaited_once_with(42,54)
        self.assertEqual(json.loads(response.text),{'ok':True,'days':9,'credited_rub':54,'balance_rub':180})
