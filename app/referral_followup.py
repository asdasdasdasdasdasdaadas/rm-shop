"""One invitation follow-up after recorded interest, never inferred sharing."""
import copy
import json
import logging

logger = logging.getLogger(__name__)

VERSION = 'referral_followup_v1'
CONDITION = {
    'id': 'invite_no_registration',
    'label': 'Приглашение без регистрации',
    'anchor': 'u.invite_opened_at',
    'gate': 'referral',
    'max_hours': 24 * 14,
    'where': """NOT EXISTS (SELECT 1 FROM users friend WHERE friend.referred_by=u.telegram_id)
        AND (u.idle_snoozed_at IS NULL OR u.invite_opened_at > u.idle_snoozed_at)
        AND NOT EXISTS (SELECT 1 FROM message_log m WHERE m.telegram_id=u.telegram_id
            AND m.status='sent' AND (m.kind LIKE 'nudge_%' OR m.kind IN ('broadcast','low_balance'))
            AND m.created_at > NOW()-INTERVAL '48 hours')""",
    'hint': 'Открыл приглашение, поделился или скопировал ссылку; друзей по ней ещё нет. Одно напоминание через 72 часа, не позднее 14 дней. Отправка ссылки другу не подтверждена.',
}

async def record_interest(telegram_id):
    from app.db import _pool_req
    await _pool_req().execute('''UPDATE users SET invite_opened_at=NOW()
        WHERE telegram_id=$1 AND (invite_opened_at IS NULL
            OR invite_opened_at <= idle_snoozed_at)''', int(telegram_id))


def upgrade(graph):
    from app.funnel_board import _step
    result = copy.deepcopy(graph)
    if any(s['condition'] == CONDITION['id'] for b in result['branches'] for s in b['steps']):
        return result
    if len(result['branches']) >= 32:
        return result
    # Branch and step IDs share a namespace with administrator-created entries.
    used = {b['id'] for b in result['branches']}
    used.update(s['id'] for b in result['branches'] for s in b['steps'])
    def available(base):
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f'{base}-{suffix}'
            suffix += 1
        used.add(candidate)
        return candidate
    branch_id = available('invite-followup')
    step_id = available('invite-followup-1')
    result['branches'].append({
        'id': branch_id, 'title': 'Приглашение без регистрации',
        'steps': [_step(step_id, CONDITION['id'], 72,
            '<tg-emoji emoji-id="5258513401784573443">👥</tg-emoji> <b>Поделитесь VPN с другом</b>\n\n'
            '<blockquote>С другом проще поделиться готовым приглашением. Нажмите кнопку ниже, '
            'выберите друга и отправьте свою ссылку.</blockquote>\n\n'
            'Текст и ваша личная ссылка уже подготовлены.',
            [{'action': 'share', 'text': 'Отправить приглашение'}, 'copy', 'menu'])],
    })
    return result


async def migrate(pool, graph):
    from app.recovery_funnel import migrate as migrate_recovery
    from app.funnel_board import validate
    graph = await migrate_recovery(pool, graph)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(73619429)')
            row = await conn.fetchrow('SELECT graph FROM funnel_graphs WHERE id=1 FOR UPDATE')
            raw = row['graph'] if row else graph
            if isinstance(raw, str):
                raw = json.loads(raw)
            if await conn.fetchval('SELECT value FROM app_flags WHERE key=$1', VERSION):
                return validate(raw)
            updated = validate(upgrade(raw))
            if not any(s['condition'] == CONDITION['id'] for b in updated['branches'] for s in b['steps']):
                # Keep all existing journeys running; retry after an admin frees a slot.
                logger.warning('Referral follow-up migration deferred: funnel has 32 branches')
                return updated
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2) ON CONFLICT DO NOTHING',
                               VERSION+'_backup', json.dumps(raw, ensure_ascii=False))
            await conn.execute('UPDATE funnel_graphs SET graph=$1::jsonb,updated_at=NOW() WHERE id=1',
                               json.dumps(updated, ensure_ascii=False))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2)', VERSION, '1')
            return updated
