"""Read-only finance dashboard: successful payments and paid-client renewals."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app import db
from app.config import get_settings

PAYMENTS_SQL = '''WITH events AS (
 SELECT 'rollypay:'||o.order_id AS id,o.telegram_id,o.plan_code,
 COALESCE(o.paid_at,o.created_at) AS at,'RUB' AS currency,r.amount::bigint AS amount
 FROM rollypay_orders o LEFT JOIN payment_receipts r ON r.payment_key='rollypay:'||o.order_id
 WHERE o.status='granted'
 UNION ALL
 SELECT 'stars:'||p.telegram_payment_id,p.telegram_id,p.plan_code,p.created_at,'XTR',p.stars::bigint
 FROM payments p
), ranked AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY telegram_id ORDER BY at,id) AS payment_number FROM events
)
SELECT e.*,u.first_name,u.username FROM ranked e LEFT JOIN users u USING(telegram_id)
WHERE e.at >= $1 AND e.at < $2 ORDER BY e.at DESC,e.id DESC'''

DUE_SQL = '''WITH candidates AS (
 SELECT u.telegram_id,u.first_name,u.username,COALESCE(u.balance_rub,0) AS balance_rub,
 u.router_expire_at,dev.device_count,
 (u.billing_paused_at IS NULL AND dev.device_count>0
  AND COALESCE(u.balance_rub,0) <= $1 * dev.device_count * $2) AS balance_low,
 (u.router_expire_at IS NOT NULL AND u.router_expire_at <= NOW()+$2::int*INTERVAL '1 day'
  AND EXISTS(SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id AND d.kind='router')) AS router_due
 FROM users u CROSS JOIN LATERAL (
 SELECT COUNT(*)::int AS device_count FROM devices d
 WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router') dev
 WHERE u.blocked_at IS NULL AND (
 EXISTS(SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id) OR
 EXISTS(SELECT 1 FROM rollypay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted'))
)
SELECT * FROM candidates WHERE balance_low OR router_due
ORDER BY balance_rub,router_expire_at NULLS LAST,telegram_id'''


def payment_report(rows, start_day, days, settings):
    series={ (start_day+timedelta(days=i)).isoformat():dict(rub=0,stars=0,payments=0,star_payments=0,first=0,repeat=0) for i in range(days)}
    items=[];payers=set();estimated=0
    for row in rows:
        item=dict(row)
        if item['currency']=='RUB' and item['amount'] is None:
            item['amount']=settings.topup_rub_for_code(item['plan_code'])
            item['estimated']=True
            estimated+=1
        else:
            item['estimated']=False
        item['amount']=int(item['amount'] or 0)
        point=series[item['at'].astimezone(ZoneInfo('Europe/Moscow')).date().isoformat()]
        rub=item['currency']=='RUB'
        point['rub' if rub else 'stars']+=item['amount']
        point['payments' if rub else 'star_payments']+=1
        point['first' if item['payment_number']==1 else 'repeat']+=1
        payers.add(item['telegram_id'])
        item['at']=item['at'].isoformat();items.append(item)
    totals={key:sum(p[key] for p in series.values()) for key in ('rub','stars','payments','star_payments','first','repeat')}
    totals['payers']=len(payers)
    totals['average_rub']=round(totals['rub']/totals['payments'],2) if totals['payments'] else 0
    return dict(series=[dict(day=k,**v) for k,v in series.items()],totals=totals,items=items,estimated=estimated)


async def overview(days=30,page=1,horizon=3,due_page=1):
    if days not in {7,30,90,365} or horizon not in {1,3,7,14} or page<1 or due_page<1:
        raise ValueError('Некорректный период или страница')
    now=db._utc_now();msk=ZoneInfo('Europe/Moscow')
    start_day=now.astimezone(msk).date()-timedelta(days=days-1)
    start=datetime.combine(start_day,datetime.min.time(),msk)
    settings=get_settings();pool=db._pool_req()
    report=payment_report(await pool.fetch(PAYMENTS_SQL,start,now),start_day,days,settings)
    items=report.pop('items');report['history']={'items':items[(page-1)*30:page*30],'total':len(items),'page':page}
    price=max(1,int(settings.vpn_day_price_rub))
    rows=await pool.fetch(DUE_SQL,price,horizon)
    due=[]
    due_series={(now.astimezone(msk).date()+timedelta(days=i)).isoformat():0 for i in range(horizon+1)}
    for row in rows:
        item=dict(row)
        count=int(item['device_count'])
        item['balance_days']=round(max(0,int(item['balance_rub']))/(price*count),1) if count else None
        remaining=[]
        if item['balance_low']:
            remaining.append(int(item['balance_days'] or 0))
        if item['router_due']:
            remaining.append(max(0,(item['router_expire_at'].astimezone(msk).date()-now.astimezone(msk).date()).days))
        bucket=(now.astimezone(msk).date()+timedelta(days=min(horizon,min(remaining)))).isoformat()
        due_series[bucket]+=1
        item['router_expire_at']=item['router_expire_at'].isoformat() if item['router_expire_at'] else None
        due.append(item)
    report['due']={'items':due[(due_page-1)*30:due_page*30],'total':len(due),'page':due_page,'horizon':horizon,'series':[dict(day=k,renewals=v) for k,v in due_series.items()]}
    return dict(report,days=days,day_price=price)
