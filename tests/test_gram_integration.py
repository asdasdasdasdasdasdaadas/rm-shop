import asyncio
from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from test_funnel_integration import PgPool
from app import gram,db
from app.config import Settings
from test_gram import WALLET

@unittest.skipUnless(os.environ.get('PGLITE_MODULE'),'PostgreSQL integration')
class GramIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.proc=await asyncio.create_subprocess_exec('node',str(Path(__file__).parent/'support/pglite_bridge.mjs'),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE)
        self.pool=PgPool(self.proc)
        await self.pool.query(db.SCHEMA_PATH.read_text(),script=True)
        patcher=patch.object(db,'_pool_req',return_value=self.pool);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(db,'get_settings',return_value=Settings.model_construct(referral_program_enabled=False));patcher.start();self.addCleanup(patcher.stop)
        await self.pool.execute('INSERT INTO users(telegram_id) VALUES(1)')
        self.now=datetime.now(timezone.utc)
        self.wallet=gram.address_raw(WALLET)
        await self.pool.execute('''INSERT INTO gram_orders(id,telegram_id,plan_code,amount_rub,nano_amount,rate_rub,rate_at,wallet,comment,created_at,expires_at)
            VALUES('one',1,'topup_100',100,1000000000,100,NOW(),$1,'gram_one',$2,$3)''',self.wallet,self.now-timedelta(minutes=1),self.now+timedelta(minutes=9))

    async def asyncTearDown(self):
        self.proc.stdin.close();await self.proc.wait()

    async def deposit(self,amount=10**9,at=None,hash='a'*64,comment='gram_one'):
        # Bridge dates are strings; wrap record for production asyncpg semantics.
        async with self.pool.acquire() as conn:
            original=conn.fetchrow
            async def fetchrow(sql,*args):
                row=await original(sql,*args)
                if row and 'expires_at' in row:
                    for key in ('created_at','expires_at'):row[key]=datetime.fromisoformat(row[key].replace('Z','+00:00'))
                return row
            conn.fetchrow=fetchrow
            async with conn.transaction():
                await gram.observe(conn,self.wallet,dict(hash=hash,nano=amount,at=at or self.now,comment=comment))

    async def test_credit_is_atomic_and_idempotent_and_uses_locked_rubles(self):
        with self.assertRaises(ValueError):await db.credit_payment_once(1,'topup_100','gram:one',100)
        await self.deposit()
        with self.assertRaises(ValueError):await db.credit_payment_once(1,'topup_100','gram:one',999)
        results=await asyncio.gather(*[db.credit_payment_once(1,'topup_100','gram:one',100) for _ in range(3)])
        self.assertEqual(sum(r is not None for r in results),1)
        self.assertEqual(await self.pool.fetchval('SELECT balance_rub FROM users WHERE telegram_id=1'),100)
        self.assertEqual(await self.pool.fetchval("SELECT status FROM gram_orders WHERE id='one'"),'granted')
        await self.deposit()
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM gram_deposits'),1)
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM payment_receipts'),1)

    async def test_late_underpaid_and_unknown_are_not_credited(self):
        await self.deposit(amount=1)
        self.assertEqual(await self.pool.fetchval("SELECT status FROM gram_orders WHERE id='one'"),'review')
        with self.assertRaises(ValueError):await db.credit_payment_once(1,'topup_100','gram:one',100)
        await self.pool.execute("UPDATE gram_orders SET status='pending' WHERE id='one'")
        await self.deposit(at=self.now+timedelta(hours=1),hash='b'*64)
        self.assertEqual(await self.pool.fetchval("SELECT status FROM gram_orders WHERE id='one'"),'review')
        await self.deposit(comment='missing',hash='c'*64)
        self.assertEqual(await self.pool.fetchval("SELECT reason FROM gram_deposits WHERE tx_hash=$1",'c'*64),'unmatched')
        self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM payment_receipts'),0)

    async def test_delayed_indexing_credits_in_time_transfer_even_after_expiration(self):
        await self.pool.execute("UPDATE gram_orders SET status='expired' WHERE id='one'")
        await self.deposit()
        self.assertEqual(await self.pool.fetchval("SELECT status FROM gram_orders WHERE id='one'"),'confirmed')

    async def test_scanner_rolls_back_cursor_and_recovers_after_provider_pending(self):
        from contextlib import asynccontextmanager
        from types import SimpleNamespace
        from test_funnel_integration import PgConnection
        from test_gram import transaction
        import httpx
        await self.pool.execute('INSERT INTO gram_wallet_cursors(wallet,started_at) VALUES($1,NOW())',self.wallet)
        @asynccontextmanager
        async def acquire():
            async with self.pool.lock:
                conn=PgConnection(self.pool)
                original=conn.fetchrow
                async def fetchrow(sql,*args):
                    row=await original(sql,*args)
                    if row:
                        for key in ('started_at','created_at','expires_at'):
                            if isinstance(row.get(key),str): row[key]=datetime.fromisoformat(row[key].replace('Z','+00:00'))
                    return row
                conn.fetchrow=fetchrow
                yield conn
        tx=transaction('gram_one');tx['now']=int(self.now.timestamp());tx['lt']='100'
        later=transaction('unknown');later['lt']='200';later['hash']='ab'*32;later['finality']='pending'
        def respond(request):
            if 'masterchainInfo' in request.url.path:return httpx.Response(200,json={'last':{'seqno':10}})
            start=int(request.url.params['start_lt'])
            return httpx.Response(200,json={'transactions':[t for t in (tx,later) if int(t['lt'])>=start]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch.object(db,'_pool_req',return_value=SimpleNamespace(acquire=acquire)):
                with self.assertRaises(ValueError):await gram.scan_wallet(client,self.wallet)
            self.assertEqual(await self.pool.fetchval('SELECT last_lt FROM gram_wallet_cursors'),0)
            self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM gram_deposits'),0)
            later['finality']='finalized'
            with patch.object(db,'_pool_req',return_value=SimpleNamespace(acquire=acquire)):
                await gram.scan_wallet(client,self.wallet)
                await gram.scan_wallet(client,self.wallet)
            self.assertEqual(int(await self.pool.fetchval('SELECT last_lt FROM gram_wallet_cursors')),200)
            self.assertEqual(await self.pool.fetchval('SELECT COUNT(*) FROM gram_deposits'),2)
            self.assertEqual(await self.pool.fetchval("SELECT status FROM gram_orders WHERE id='one'"),'confirmed')
