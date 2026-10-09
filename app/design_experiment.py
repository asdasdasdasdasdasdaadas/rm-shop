"""Account-stable cabinet experiment; successful payments come from server records."""
import hashlib
from app import db
from app.config import get_settings

EXPERIMENT = 'cabinet_dark_v2'


def variant_for(telegram_id: int) -> str:
    digest = hashlib.sha256(f'{EXPERIMENT}:{telegram_id}'.encode()).digest()
    return 'modern' if int.from_bytes(digest[:8], 'big') % 2 else 'classic'


async def enabled() -> bool:
    return await db.get_kv(EXPERIMENT + '_enabled') != '0'


async def assignment(telegram_id: int) -> dict:
    if telegram_id in get_settings().admin_id_set or not await enabled():
        return {'active': False}
    row = await db._pool_req().fetchrow('''INSERT INTO design_exposures
        (experiment,telegram_id,variant,existing_customer,connection_eligible)
        SELECT $1,telegram_id,$3,has_paid_topup,first_online_at IS NULL FROM users WHERE telegram_id=$2
        ON CONFLICT (experiment,telegram_id) DO UPDATE SET telegram_id=EXCLUDED.telegram_id
        RETURNING variant''', EXPERIMENT, telegram_id, variant_for(telegram_id))
    return {'active': bool(row), 'id': EXPERIMENT, 'variant': row['variant'] if row else 'classic'}


async def record(telegram_id: int, stage: str, variant: str) -> None:
    if not await enabled():
        return
    pool = db._pool_req()
    if stage == 'exposure':
        await pool.execute('''UPDATE design_exposures e SET exposed_at=NOW(),
            existing_customer=u.has_paid_topup,connection_eligible=u.first_online_at IS NULL
            FROM users u WHERE e.telegram_id=u.telegram_id AND e.telegram_id=$2
            AND experiment=$1 AND variant=$3 AND exposed_at IS NULL''', EXPERIMENT, telegram_id, variant)
    else:
        await pool.execute('''INSERT INTO design_events(experiment,telegram_id,stage)
            SELECT experiment,telegram_id,$3 FROM design_exposures
            WHERE experiment=$1 AND telegram_id=$2 AND variant=$4 AND exposed_at IS NOT NULL
            ON CONFLICT DO NOTHING''', EXPERIMENT, telegram_id, stage, variant)


async def statistics() -> dict:
    rows = await db._pool_req().fetch('''WITH cohort AS (
        SELECT e.*, u.first_online_at,
        EXISTS(SELECT 1 FROM design_events d WHERE d.experiment=e.experiment AND d.telegram_id=e.telegram_id
            AND d.stage='topup' AND d.created_at < e.exposed_at+INTERVAL '7 days') AS topup,
        EXISTS(SELECT 1 FROM design_events d WHERE d.experiment=e.experiment AND d.telegram_id=e.telegram_id
            AND d.stage='wizard' AND d.created_at < e.exposed_at+INTERVAL '7 days') AS wizard,
        (EXISTS(SELECT 1 FROM payments p WHERE p.telegram_id=e.telegram_id
            AND p.created_at>=e.exposed_at AND p.created_at<e.exposed_at+INTERVAL '7 days')
         OR EXISTS(SELECT 1 FROM rollypay_orders p WHERE p.telegram_id=e.telegram_id AND p.status='granted'
            AND p.paid_at>=e.exposed_at AND p.paid_at<e.exposed_at+INTERVAL '7 days')) AS paid
        FROM design_exposures e JOIN users u ON u.telegram_id=e.telegram_id
        WHERE e.experiment=$1 AND e.exposed_at IS NOT NULL
    ) SELECT variant,existing_customer,COUNT(*)::int AS exposed,
        COUNT(*) FILTER(WHERE topup)::int AS topup,
        COUNT(*) FILTER(WHERE wizard)::int AS wizard,
        COUNT(*) FILTER(WHERE exposed_at<=NOW()-INTERVAL '7 days')::int AS mature,
        COUNT(*) FILTER(WHERE exposed_at<=NOW()-INTERVAL '7 days' AND paid)::int AS paid,
        COUNT(*) FILTER(WHERE exposed_at<=NOW()-INTERVAL '7 days' AND connection_eligible)::int AS connection_base,
        COUNT(*) FILTER(WHERE exposed_at<=NOW()-INTERVAL '7 days' AND connection_eligible
          AND first_online_at>=exposed_at AND first_online_at<exposed_at+INTERVAL '7 days')::int AS connected
        FROM cohort GROUP BY variant,existing_customer ORDER BY existing_customer,variant''', EXPERIMENT)
    return {'ok': True, 'active': await enabled(), 'experiment': EXPERIMENT, 'rows': [dict(r) for r in rows]}
