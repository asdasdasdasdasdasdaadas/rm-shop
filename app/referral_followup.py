"""Invitation follow-ups: after recorded interest (never inferred sharing), a second invite when the first one
brought nobody, a reminder to whoever invited a friend who has not connected VPN yet (that is when the inviter's
50 ₽ is paid), and «invite one more» a few days after a friend's reward."""
import copy
import logging

logger = logging.getLogger(__name__)

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


# A friend who came by the link but has not connected VPN in the last 14 days, the newest one first.
_STUCK = """FROM users f WHERE f.referred_by=u.telegram_id AND f.telegram_id<>u.telegram_id
    AND f.first_online_at IS NULL AND f.bot_blocked_at IS NULL AND f.blocked_at IS NULL
    AND f.created_at > NOW() - INTERVAL '14 days'"""
# Connect rewards: rows that existed when the column appeared carry 'epoch', not a real time.
_REWARDED_AT = """(SELECT MAX(f.referral_connect_bonus_at) FROM users f WHERE f.referred_by=u.telegram_id
    AND f.referral_connect_bonus_at > TIMESTAMPTZ '2001-01-01')"""

EXTRA_CONDITIONS = (
    {'id': 'invite_silent', 'label': 'Приглашали, друзей пока нет', 'anchor': 'u.first_online_at', 'gate': 'referral',
     'where': """NOT EXISTS (SELECT 1 FROM users friend WHERE friend.referred_by=u.telegram_id)
        AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id
            AND d.last_online_at >= NOW() - INTERVAL '7 days')""",
     'hint': 'Первое приглашение уже было, по ссылке никто не пришёл, VPN используется. Второе и последнее напоминание.'},
    {'id': 'friend_stuck', 'label': 'Друг пришёл, но не подключил VPN', 'gate': 'referral', 'max_hours': 24 * 14,
     'anchor': f'(SELECT MAX(f.created_at) {_STUCK})',
     'where': f'EXISTS (SELECT 1 {_STUCK})',
     'hint': 'Пишем тому, кто пригласил: друг открыл бота по ссылке, но VPN не подключил. Награда пригласившему — '
             'после подключения друга. Новый такой друг — новое напоминание.'},
    {'id': 'friend_rewarded', 'label': 'Друг подключился — позвать ещё', 'gate': 'referral', 'max_hours': 24 * 10,
     'anchor': _REWARDED_AT,
     'where': f'{_REWARDED_AT} IS NOT NULL',
     'hint': 'Через несколько дней после награды за друга предлагаем позвать следующего. Повторяется после каждой новой награды.'},
)
EXTRA_KINDS = {
    'invite_silent': 'nudge_invite_again',
    'friend_stuck': 'nudge_friend_stuck',
    'friend_rewarded': 'nudge_invite_more',
}
# A new stuck friend or a new reward is a new reason to write.
EXTRA_CYCLE = {'friend_stuck', 'friend_rewarded'}

INVITE_SILENT_TEXT = (
    '👥 <b>{name}, VPN нужен и вашим друзьям</b>\n\n'
    '{when}\n\n'
    'Отправьте ссылку тем, у кого не открываются сайты или тормозит видео:\n{link}'
)
FRIEND_STUCK_TEXT = (
    '⏳ <b>Друг пришёл по вашей ссылке, но VPN ещё не подключил</b>\n\n'
    'Напомните ему: настройка занимает пару минут, в боте есть пошаговая инструкция. '
    'Как только друг подключит VPN, вам начислим {reward}.'
)
FRIEND_REWARDED_TEXT = (
    '🎉 <b>{name}, спасибо, что зовёте друзей!</b>\n\n'
    'За каждого нового друга — ещё {reward} вам и {reward} ему. Ссылка та же:\n{link}'
)


def extra_steps(step):
    """The second invite goes into «Пригласить друга» after invite-1; two branches of their own for the rest."""
    return (
        step('invite-2', 'invite_silent', 24 * 7, INVITE_SILENT_TEXT, ['share', 'copy', 'menu'], 'previous'),
        [
            {'id': 'friend-stuck', 'title': 'Друг не подключился → напомнить пригласившему', 'steps': [
                step('friend-stuck-1', 'friend_stuck', 48, FRIEND_STUCK_TEXT,
                     [{'action': 'share', 'text': 'Напомнить другу'}, 'menu']),
            ]},
            {'id': 'invite-more', 'title': 'Друг подключился → позвать ещё', 'steps': [
                step('invite-more-1', 'friend_rewarded', 72, FRIEND_REWARDED_TEXT, ['share', 'copy', 'menu']),
            ]},
        ],
    )
