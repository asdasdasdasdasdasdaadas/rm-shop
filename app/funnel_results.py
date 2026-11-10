"""Observed outcomes, not causal lift: seven-day last delivered message attribution."""
from datetime import timedelta
from app import db

SQL = r'''WITH messages AS (
 SELECT m.*, COALESCE(NULLIF(m.extra->>'step_id',''),m.kind) AS step,
 CASE WHEN m.status='sent' THEN LEAST(m.created_at+INTERVAL '7 days',$2,
   COALESCE((SELECT n.created_at FROM message_log n WHERE n.telegram_id=m.telegram_id
     AND n.source='auto' AND n.kind LIKE 'nudge_%' AND n.status='sent'
     AND (n.created_at,n.id)>(m.created_at,m.id) ORDER BY n.created_at,n.id LIMIT 1),$2)) END AS until
 FROM message_log m WHERE m.source='auto' AND m.kind LIKE 'nudge_%'
 AND m.created_at >= $1 AND m.created_at < $2
), payments AS (
 SELECT o.telegram_id,COALESCE(o.paid_at,o.created_at) AS at,r.amount,'RUB' AS currency
 FROM pay_orders o LEFT JOIN payment_receipts r ON r.payment_key='order:'||o.order_id
 WHERE o.status='granted' AND COALESCE(o.paid_at,o.created_at)>=$1 AND COALESCE(o.paid_at,o.created_at)<$2
 UNION ALL SELECT telegram_id,created_at,stars,'XTR' FROM payments WHERE created_at >=$1 AND created_at<$2
), outcomes AS (
 SELECT m.*, u.first_online_at,
 EXISTS (SELECT 1 FROM reminder_deliveries rd WHERE m.status='sent' AND rd.telegram_id=m.telegram_id
   AND COALESCE(rd.step_id,rd.kind)=m.step AND rd.status='sent'
   -- message_log stores timezone('utc', now()), deliveries NOW(): allow for a server time zone offset.
   AND rd.created_at BETWEEN m.created_at-INTERVAL '1 day' AND m.created_at+INTERVAL '1 day'
   AND rd.clicked_at IS NOT NULL AND rd.clicked_at<=rd.created_at+INTERVAL '7 days') AS clicked,
 COALESCE(p.payments,0) AS payments,COALESCE(p.rub,0) AS rub,COALESCE(p.stars,0) AS stars,
 COALESCE(p.unknown,0) AS unknown
 FROM messages m LEFT JOIN users u USING(telegram_id)
 LEFT JOIN LATERAL (
 SELECT COUNT(*) AS payments,SUM(amount) FILTER(WHERE currency='RUB') AS rub,
 SUM(amount) FILTER(WHERE currency='XTR') AS stars,
 COUNT(*) FILTER(WHERE currency='RUB' AND amount IS NULL) AS unknown
 FROM payments p WHERE m.status='sent' AND p.telegram_id=m.telegram_id
 AND p.at>m.created_at AND p.at<=m.until
 ) p ON TRUE
)
SELECT step,MAX(title) AS title,COUNT(*)::int AS attempts,
 COUNT(*) FILTER(WHERE status='sent')::int AS sent,
 COUNT(*) FILTER(WHERE status='failed')::int AS failed,
 COUNT(DISTINCT telegram_id) FILTER(WHERE status='sent')::int AS recipients,
 COUNT(DISTINCT telegram_id) FILTER(WHERE status='sent' AND created_at<=$2-INTERVAL '7 days')::int AS mature_recipients,
 COUNT(DISTINCT telegram_id) FILTER(WHERE clicked)::int AS clickers,
 COUNT(DISTINCT telegram_id) FILTER(WHERE status='sent' AND first_online_at>created_at AND first_online_at<=until)::int AS connected,
 COUNT(DISTINCT telegram_id) FILTER(WHERE payments>0)::int AS payers,
 SUM(payments)::int AS payments,SUM(rub)::bigint AS rub,SUM(stars)::bigint AS stars,SUM(unknown)::int AS unknown,
 COUNT(DISTINCT telegram_id) FILTER(WHERE status='failed' AND
 (COALESCE(extra->>'error','')||' '||COALESCE(extra->>'error_raw','')) ~* '(blocked by the user|пользователь заблокировал бота)')::int AS blocked,
 COUNT(DISTINCT telegram_id)::int AS attempted_users
FROM outcomes GROUP BY step ORDER BY sent DESC,step'''


async def report(days=30):
    if days not in {7,30,90}:
        raise ValueError('Некорректный период')
    now=db._utc_now()
    rows=await db._pool_req().fetch(SQL,now-timedelta(days=days),now)
    items=[]
    for row in rows:
        item=dict(row)
        item['payment_rate']=round(100*item['payers']/item['recipients'],1) if item['recipients'] else None
        item['click_rate']=round(100*item['clickers']/item['recipients'],1) if item['recipients'] else None
        item['blocked_rate']=round(100*item['blocked']/item['attempted_users'],1) if item['attempted_users'] else None
        items.append(item)
    return {'items':items,'days':days,'window_days':7}
