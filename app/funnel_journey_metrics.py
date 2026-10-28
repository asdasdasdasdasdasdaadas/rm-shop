"""Comparable seven-day stage conversions for consecutive signup cohorts."""
from datetime import timedelta
from statistics import median

STAGES = ('gift', 'device', 'online', 'paid', 'repeat_paid')
LABELS = ('Подарок → устройство', 'Устройство → первый онлайн',
          'Первый онлайн → первая оплата', 'Первая → повторная оплата')

SQL = '''
WITH paid_events AS (
 SELECT telegram_id, created_at AS paid_at FROM payments
 UNION ALL
 SELECT telegram_id, paid_at FROM rollypay_orders
 WHERE status='granted' AND paid_at IS NOT NULL
), ranked AS (
 SELECT telegram_id, paid_at, ROW_NUMBER() OVER (PARTITION BY telegram_id ORDER BY paid_at) AS n
 FROM paid_events
), paid AS (
 SELECT telegram_id, MIN(paid_at) FILTER (WHERE n=1) AS paid,
 MIN(paid_at) FILTER (WHERE n=2) AS repeat_paid FROM ranked GROUP BY telegram_id
)
SELECT CASE WHEN u.ad_link_id IS NOT NULL THEN 'ads'
            WHEN u.referred_by IS NOT NULL THEN 'referral' ELSE 'organic' END AS acquisition_source,
 u.bot_started_at AS started, u.gift_claimed_at AS gift,
 (SELECT MIN(d.created_at) FROM devices d WHERE d.telegram_id=u.telegram_id
  AND COALESCE(d.kind,'') <> 'router') AS device,
 u.first_online_at AS online, p.paid, p.repeat_paid, u.bot_blocked_at AS blocked
FROM users u LEFT JOIN paid p USING (telegram_id)
WHERE u.bot_started_at >= $1 AND u.bot_started_at < $2
'''


def summarize(rows, now, *, include_sources=True):
    result = []
    for period, start, end in [('previous', now-timedelta(days=60), now-timedelta(days=30)),
                               ('current', now-timedelta(days=30), now)]:
        cohort = [r for r in rows if start <= r['started'] < end]
        transitions = []
        for source, target, label in zip(STAGES, STAGES[1:], LABELS):
            # Exclude immature entrants even when they already converted: identical observation windows.
            eligible = [r for r in cohort if r.get(source) is not None and
                        r['started'] <= r[source] <= now-timedelta(days=7)]
            hours = [(r[target]-r[source]).total_seconds()/3600 for r in eligible
                     if r.get(target) is not None and r[source] <= r[target] <= r[source]+timedelta(days=7)]
            transitions.append(dict(label=label, eligible=len(eligible), converted=len(hours),
                                    rate=round(100*len(hours)/len(eligible),1) if eligible else None,
                                    median_hours=round(median(hours),1) if hours else None))
        mature = [r for r in cohort if r['started'] <= now-timedelta(days=7)]
        blocked = sum(r.get('blocked') is not None and r['started'] <= r['blocked'] <= r['started']+timedelta(days=7) for r in mature)
        outcomes = []
        for key, label in [('online', 'Первый онлайн'), ('paid', 'Первая оплата'), ('repeat_paid', 'Повторная оплата')]:
            count = sum(r.get(key) is not None and r['started'] <= r[key] <= r['started']+timedelta(days=7) for r in mature)
            outcomes.append(dict(key=key, label=label, users=count, eligible=len(mature),
                                 rate=round(100*count/len(mature),1) if mature else None))
        result.append(dict(period=period, users=len(cohort), transitions=transitions, outcomes=outcomes,
                           block_eligible=len(mature), blocked=blocked,
                           block_rate=round(100*blocked/len(mature),1) if mature else None))
    sources = []
    if include_sources:
        for source, label in [('ads', 'Реклама'), ('referral', 'Рекомендации'), ('organic', 'Органика')]:
            subset = [r for r in rows if r.get('acquisition_source', 'organic') == source]
            sources.append(dict(source=source, label=label, items=summarize(subset, now, include_sources=False)['items']))
    return {'items': result, 'sources': sources, 'window_days': 7,
            'sources_note': 'Источник: рекламная метка имеет приоритет, затем реферальная ссылка, иначе органика. Итоги — за первые 7 дней после запуска бота, только для пользователей с полными 7 днями наблюдения. Это категории по сохранённым меткам, не доказательство влияния рекламы.',
            'note': 'Когорты по запуску бота: последние и предыдущие 30 дней. Каждый переход — за 7 дней; свежие входы исключены. Медиана — среди перешедших. Блокировки — зарегистрированные за первые 7 дней, не доказанное следствие рассылки. Удалённые устройства и снятые блокировки могут не сохраниться в истории.'}


async def metrics(pool, now):
    rows = await pool.fetch(SQL, now-timedelta(days=60), now)
    return summarize(rows, now)
