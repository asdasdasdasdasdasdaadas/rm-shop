import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,MagicMock,patch
from datetime import datetime,timedelta,timezone
from app import web,gram

class GramApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_order_status_is_scoped_to_authenticated_customer(self):
        pool=SimpleNamespace(fetchrow=AsyncMock(return_value=None))
        request=SimpleNamespace(match_info={'order_id':'other-order'})
        with patch.object(web,'_require_tg',AsyncMock(return_value=(42,None))),patch.object(web.db,'_pool_req',return_value=pool):
            response=await web.api_gram_order(request)
        self.assertEqual(response.status,404)
        self.assertEqual(pool.fetchrow.call_args.args[1:],('other-order',42))
        self.assertIn('telegram_id=$2',pool.fetchrow.call_args.args[0])

    async def test_quote_unavailable_never_returns_payment_details(self):
        request=SimpleNamespace(json=AsyncMock(return_value={'plan':'topup_100','method':'gram'}))
        with patch.object(web,'_require_tg',AsyncMock(return_value=(42,None))),patch.object(web,'get_settings',return_value=SimpleNamespace(plan_by_code=lambda c:{'topup_rub':100})),patch.object(web,'public_pay_methods',return_value=[{'id':'gram'}]),patch.object(gram,'create_order',AsyncMock(side_effect=RuntimeError('rate unavailable'))),patch.object(web.logger,'exception'):
            response=await web.api_invoice(request)
        self.assertEqual(response.status,503)
        self.assertNotIn('gram_order',json.loads(response.text))

    async def test_quote_uses_server_price_and_reuses_unexpired_order(self):
        from decimal import Decimal
        from app import pay_methods
        from test_gram import WALLET
        conn=MagicMock();conn.fetchval=AsyncMock(side_effect=[42,0,42]);conn.execute=AsyncMock()
        saved={}
        async def fetchrow(sql,*args):
            if sql.startswith('SELECT'):return saved or None
            saved.update(id=args[0],telegram_id=args[1],plan_code=args[2],amount_rub=args[3],
                         nano_amount=args[4],rate_rub=args[5],rate_at=args[6],wallet=args[7],comment=args[8],
                         status='pending',expires_at=datetime.now(timezone.utc)+timedelta(minutes=10))
            return saved
        conn.fetchrow=AsyncMock(side_effect=fetchrow)
        conn.transaction.return_value.__aenter__=AsyncMock()
        conn.transaction.return_value.__aexit__=AsyncMock(return_value=False)
        pool=MagicMock();pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__=AsyncMock(return_value=False)
        settings=SimpleNamespace(gram_wallet=WALLET,plan_by_code=lambda c:{'topup_rub':300})
        with patch.object(gram,'get_settings',return_value=settings),patch.object(gram,'current_rate',AsyncMock(side_effect=[(Decimal('100'),100),(Decimal('200'),101)])),patch.object(pay_methods,'public_pay_methods',return_value=[{'id':'gram'}]),patch.object(gram.db,'_pool_req',return_value=pool):
            first=await gram.create_order(42,'topup_300')
            second=await gram.create_order(42,'topup_300')
        self.assertEqual(first,second)
        self.assertEqual(first['rub'],300)
        self.assertEqual(first['gram'],'3')
        self.assertIn('amount=3',first['telegram_wallet_url'])
        self.assertNotIn('wallet_url',first)
        self.assertEqual(sum(call.args[0].startswith('INSERT INTO gram_orders') for call in conn.fetchrow.call_args_list),1)
