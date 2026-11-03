"""Native GRAM deposits on TON mainnet. No private keys or transaction signing."""
from __future__ import annotations
import asyncio
import base64
import binascii
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from urllib.parse import urlencode
import httpx
from app import db
from app.config import get_settings

logger=logging.getLogger(__name__)
COIN_ID='the-open-network'
NANO=Decimal(10**9)
_cache=None
_rate_lock=asyncio.Lock()


def address_raw(value):
    value=str(value).strip()
    if re.fullmatch(r'0:[0-9a-fA-F]{64}',value):
        return value.lower()
    try:
        data=base64.b64decode(value+'='*((-len(value))%4),altchars=b'-_',validate=True)
        if len(data)!=36 or data[0] not in (0x11,0x51) or data[1]!=0:
            raise ValueError()
        if binascii.crc_hqx(data[:34],0).to_bytes(2,'big')!=data[34:]:
            raise ValueError()
        return '0:'+data[2:34].hex()
    except Exception as exc:
        raise ValueError('Нужен корректный адрес кошелька TON mainnet') from exc


def friendly_address(value):
    raw=address_raw(value)
    data=bytes([0x51,0])+bytes.fromhex(raw[2:])
    return base64.urlsafe_b64encode(data+binascii.crc_hqx(data,0).to_bytes(2,'big')).decode().rstrip('=')


def nano_amount(rubles,rate):
    rate=Decimal(str(rate));rubles=Decimal(str(rubles))
    if not rate.is_finite() or rate<=0 or not rubles.is_finite() or rubles<=0:
        raise ValueError('Некорректный курс или сумма')
    value=int((rubles/rate*NANO).to_integral_value(rounding=ROUND_CEILING))
    if not 0<value<2**63:
        raise ValueError('Сумма вне допустимого диапазона')
    return value


def validate_rate(payload,now):
    row=payload[COIN_ID]
    rate=Decimal(str(row['rub']))
    stamp=int(row['last_updated_at'])
    if not rate.is_finite() or rate<=0 or not -30<=now-stamp<=180:
        raise ValueError('Курс устарел или недоступен. Попробуйте позже.')
    return rate,stamp


async def current_rate():
    global _cache
    async with _rate_lock:
        now=time.time()
        if _cache and now-_cache[2]<60 and now-_cache[1]<=180:
            return _cache[:2]
        key=get_settings().gram_coingecko_api_key.strip()
        headers={'x-cg-demo-api-key':key} if key else {}
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.get('https://api.coingecko.com/api/v3/simple/price',
                params={'ids':COIN_ID,'vs_currencies':'rub','include_last_updated_at':'true'},headers=headers)
            response.raise_for_status()
            rate,stamp=validate_rate(response.json(),now)
        _cache=(rate,stamp,now)
        return rate,stamp


def public_order(order):
    address=friendly_address(order['wallet'])
    telegram_query=urlencode({
        'to': address,
        'amount': format(Decimal(order['nano_amount'])/NANO, 'f'),
    })
    return dict(id=order['id'],status=order['status'],rub=order['amount_rub'],
        gram=format(Decimal(order['nano_amount'])/NANO,'f'),rate=str(order['rate_rub']),
        address=address,comment=order['comment'],expires_at=order['expires_at'].isoformat(),
        telegram_wallet_url=f'https://t.me/sendgrams?{telegram_query}')


async def create_order(uid,code):
    from app.pay_methods import public_pay_methods
    settings=get_settings()
    if not any(m['id']=='gram' for m in public_pay_methods()):
        raise ValueError('Оплата GRAM недоступна')
    plan=settings.plan_by_code(code)
    if not plan or plan.get('router') or not plan.get('topup_rub'):
        raise ValueError('GRAM доступен для пополнения баланса')
    wallet=address_raw(settings.gram_wallet)
    rate,stamp=await current_rate()
    amount=int(plan['topup_rub']);nano=nano_amount(amount,rate)
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await conn.fetchval('SELECT telegram_id FROM users WHERE telegram_id=$1 FOR UPDATE',uid)
            row=await conn.fetchrow("SELECT * FROM gram_orders WHERE telegram_id=$1 AND plan_code=$2 AND wallet=$3 AND status='pending' AND expires_at>NOW()+INTERVAL '30 seconds' ORDER BY created_at DESC LIMIT 1",uid,code,wallet)
            if row:
                return public_order(dict(row))
            count=await conn.fetchval("SELECT COUNT(*) FROM gram_orders WHERE telegram_id=$1 AND created_at>NOW()-INTERVAL '10 minutes'",uid)
            if count>=10:
                raise ValueError('Слишком много счетов. Подождите несколько минут.')
            oid=uuid.uuid4().hex
            row=await conn.fetchrow('''INSERT INTO gram_orders
                (id,telegram_id,plan_code,amount_rub,nano_amount,rate_rub,rate_at,wallet,comment,expires_at)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW()+INTERVAL '10 minutes') RETURNING *''',
                oid,uid,code,amount,nano,rate,datetime.fromtimestamp(stamp,timezone.utc),wallet,'gram_'+oid)
            await conn.execute('''INSERT INTO gram_wallet_cursors(wallet,started_at) VALUES($1,NOW()) ON CONFLICT DO NOTHING''',wallet)
    return public_order(dict(row))


def text_comment(body):
    from tonsdk.boc import Cell
    if not isinstance(body,str) or len(body)>4096:
        return ''
    try:
        cell=Cell.one_from_boc(base64.b64decode(body,validate=True)).begin_parse()
        if len(cell.bits)<32 or cell.read_uint(32)!=0:
            return ''
        parts=[]
        for _ in range(4):
            if len(cell.bits)%8: return ''
            parts.append(cell.read_bytes(len(cell.bits)//8))
            if not cell.refs: return b''.join(parts).decode('utf-8')
            if len(cell.refs)!=1: return ''
            cell=cell.read_ref().begin_parse()
    except Exception:
        return ''
    return ''


def incoming(tx,wallet,masterchain_seqno):
    """Only indexed, finalized, successful native incoming transfers with plain text."""
    desc=tx.get('description') or {};msg=tx.get('in_msg') or {}
    if tx.get('finality') not in (None,'finalized'):
        raise ValueError('Transaction finality pending')
    if tx.get('emulated') is True or desc.get('aborted') is not False:
        return None
    seq=tx.get('mc_block_seqno')
    if not isinstance(seq,int) or seq>masterchain_seqno or seq<=0:
        raise ValueError('Transaction is not finalized')
    if desc.get('type')!='ord' or (desc.get('compute_ph') or {}).get('success') is not True:
        return None
    if desc.get('action') is not None and desc['action'].get('success') is not True:
        return None
    if msg.get('bounced') is not False or not msg.get('source'):
        return None
    if address_raw(tx.get('account',''))!=wallet or address_raw(msg.get('destination',''))!=wallet:
        return None
    comment=text_comment((msg.get('message_content') or {}).get('body'))
    value=int(msg.get('value') or 0)
    if value<=0:
        return None
    txhash=tx.get('hash','')
    # Indexer transaction hashes are base64 (32 bytes); canonicalize for deduplication.
    if re.fullmatch(r'[0-9a-fA-F]{64}',txhash):
        txhash=txhash.lower()
    else:
        data=base64.b64decode(txhash,validate=True)
        if len(data)!=32: raise ValueError('Invalid transaction hash')
        txhash=data.hex()
    return dict(hash=txhash,comment=comment,nano=value,
                at=datetime.fromtimestamp(int(tx['now']),timezone.utc))


async def observe(conn,wallet,deposit):
    if not deposit:
        return
    order=await conn.fetchrow('SELECT * FROM gram_orders WHERE wallet=$1 AND comment=$2 FOR UPDATE',wallet,deposit['comment'])
    reason='unmatched'
    if order:
        reason='duplicate' if order['status'] in ('confirmed','granted') else 'review'
        if order['status'] in ('pending','expired') and order['created_at'].replace(microsecond=0)<=deposit['at']<=order['expires_at'] and deposit['nano']>=order['nano_amount']:
            reason='accepted'
    inserted=await conn.fetchval('''INSERT INTO gram_deposits(tx_hash,wallet,order_id,nano_amount,paid_at,reason)
        VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING RETURNING tx_hash''',
        deposit['hash'],wallet,order['id'] if order else None,deposit['nano'],deposit['at'],reason)
    if not inserted or not order:
        return
    if reason=='accepted':
        await conn.execute("UPDATE gram_orders SET status='confirmed',tx_hash=$2,paid_at=$3 WHERE id=$1",order['id'],deposit['hash'],deposit['at'])
    elif reason=='review' and order['status'] not in ('confirmed','granted'):
        await conn.execute("UPDATE gram_orders SET status='review' WHERE id=$1",order['id'])


async def scan_wallet(client,wallet):
    # Durable cursor is advanced atomically with deposit/order recording; resume after downtime.
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            cursor=await conn.fetchrow('SELECT * FROM gram_wallet_cursors WHERE wallet=$1 FOR UPDATE SKIP LOCKED',wallet)
            if not cursor: return
            response=await client.get('https://toncenter.com/api/v3/masterchainInfo')
            response.raise_for_status();seq=int(response.json()['last']['seqno'])
            params={'account':wallet,'sort':'asc','limit':100,'start_lt':str(int(cursor['last_lt'])+1)}
            if not cursor['last_lt']:
                params['start_utime']=int(cursor['started_at'].timestamp())-60
            response=await client.get('https://toncenter.com/api/v3/transactions',params=params)
            response.raise_for_status()
            rows=response.json()['transactions']
            for tx in rows:
                lt=int(tx['lt'])
                if lt<=int(cursor['last_lt']): raise ValueError('Out of order transaction page')
                deposit=incoming(tx,wallet,seq)
                await observe(conn,wallet,deposit)
                await conn.execute('UPDATE gram_wallet_cursors SET last_lt=$2,checked_at=NOW() WHERE wallet=$1',wallet,lt)
                cursor=dict(cursor,last_lt=lt)


async def settle(rw,bot):
    from app.billing import apply_payment_effects
    from app.payment_notice import deliver_payment_notice
    from app.live import paid
    rows=await db._pool_req().fetch("SELECT * FROM gram_orders WHERE status='confirmed' ORDER BY created_at LIMIT 100")
    for row in rows:
        receipt=await db.credit_payment_once(row['telegram_id'],row['plan_code'],'gram:'+row['id'],row['amount_rub'])
        if receipt:
            # Effects and notice are already in durable retry queues.
            try:
                await apply_payment_effects(receipt,rw,bot)
                await deliver_payment_notice(bot,receipt)
                paid(await db.get_user(row['telegram_id']),amount=row['amount_rub'],title='GRAM',repeat=not receipt['first_payment'])
            except Exception:
                logger.exception('GRAM credited; effects will retry: %s',row['id'])


async def payment_loop(rw,bot):
    while True:
        try:
            headers={}
            if get_settings().gram_toncenter_api_key:
                headers['X-API-Key']=get_settings().gram_toncenter_api_key
            async with httpx.AsyncClient(timeout=20,headers=headers) as client:
                wallets=await db._pool_req().fetch('SELECT wallet FROM gram_wallet_cursors')
                for row in wallets:
                    try:
                        await scan_wallet(client,row['wallet'])
                    except Exception:
                        logger.exception('GRAM wallet scan will retry')
            await settle(rw,bot)
            await db._pool_req().execute("UPDATE gram_orders SET status='expired' WHERE status='pending' AND expires_at<NOW()")
        except Exception:
            logger.exception('GRAM processing will retry')
        await asyncio.sleep(15)
