"""Admin-only previews: never run payment, reward or reminder tracking actions."""
from html import escape
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.config import get_settings
from app.keyboards import (cabinet_keyboard, onboarding_keyboard, payment_nudge_keyboard,
                           share_keyboard, vpn_feedback_keyboard, support_welcome_keyboard, channel_keyboard)
from app.notices import notice_text
from app.nudge import trial_nudge_text, invite_nudge_text, info_nudge_text, _idle_notice_key
from app.texts import days_text, rub_text
from app.referrals import topup_ok_text


def catalog(telegram_id: int, ambassador_cfg=None) -> list[dict]:
    s = get_settings()
    from app.winback import message as winback_message, keyboard as winback_keyboard
    rows = []
    def add(key, group, title, condition, body, markup):
        from app.funnel_ui import funnel_body, funnel_keyboard
        body, markup = funnel_body(body), funnel_keyboard(markup)
        rows.append(dict(id=key, group=group, title=title, condition=condition, body=body, markup=markup))
    add('welcome', 'start', 'Приветствие с подарком', 'Первый запуск; пробный доступ доступен',
        notice_text('welcome_intro_hi', name='Тестовый пользователь', days=days_text(s.trial_days)), None)
    add('intro', 'start', 'Знакомство с сервисом', 'После приветствия',
        notice_text('welcome_intro_hello', name='Тестовый пользователь', brand=escape(s.brand_name)), None)
    add('support', 'start', 'Согласие помочь сервису', 'Перед продолжением регистрации',
        notice_text('support_welcome', brand=escape(s.brand_name)), support_welcome_keyboard())
    add('gift', 'start', 'Подарок ещё не забрали', 'Напоминание о пробном доступе; подарок не получен',
        trial_nudge_text('Тестовый пользователь', already_granted=False), onboarding_keyboard(gift=True))
    add('resume_welcome', 'start', 'Не завершил приветствие', 'Через 24 часа; не нажал «Я помогу»',
        notice_text('trial_resume_welcome'), support_welcome_keyboard())
    add('resume_channel', 'start', 'Не подписался на канал', 'Через 24 часа; приветствие завершено, подписка на канал не подтверждена',
        notice_text('trial_resume_channel'), channel_keyboard())
    add('gift_claimed', 'start', 'Подарок получен, устройства нет', 'Альтернативная ветка: подарок уже на балансе',
        trial_nudge_text('Тестовый пользователь', already_granted=True), onboarding_keyboard(gift=True))
    add('device', 'start', 'Устройство добавлено', 'Сразу после добавления устройства',
        notice_text('device_created_next_step'), onboarding_keyboard(has_device=True))
    add('setup', 'start', 'Нет первого подключения', 'Устройство есть, но пользователь ещё не вышел онлайн',
        notice_text('device_setup_nudge'), onboarding_keyboard(has_device=True))
    add('quality', 'start', 'Проверка качества VPN', 'От 20 часов до 7 дней после первого онлайна; ещё не ответил на опрос',
        notice_text('vpn_quality_check'), vpn_feedback_keyboard())
    add('ending', 'payment', 'Баланс заканчивается', 'Пользователь подходит к концу оплаченного доступа',
        notice_text('balance_ending_nudge'), payment_nudge_keyboard(label='Пополнить баланс'))
    add('empty', 'payment', 'Не хватает на сутки', 'Баланс меньше стоимости суток устройства',
        notice_text('low_balance', price=rub_text(s.vpn_day_price_rub)), payment_nudge_keyboard(label='Пополнить баланс'))
    add('invoice', 'payment', 'Счёт не оплачен', 'Через 10 минут после создания неоплаченного счёта',
        notice_text('payment_nudge'), payment_nudge_keyboard('test'))
    add('paid', 'payment', 'Успешное пополнение', 'Пример: подтверждён платёж 100 ₽; реального зачисления нет',
        topup_ok_text(rub_text(100), can_share=False, local={'balance_rub':100}), cabinet_keyboard())
    add('winback', 'winback', 'Персональный промокод: 5 дней',
        'Пользовался — через 48 часов без баланса; не подключился — сразу. Не чаще раза в 2 месяца. Это образец, код не создаётся.',
        winback_message('TEST-ONLY-CODE', 1, 5*s.vpn_day_price_rub), winback_keyboard())
    add('invite', 'referral', 'Приглашение друзей', 'Через 48 часов после первого онлайна; положительный отзыв или повторное использование; программа включена',
        invite_nudge_text(telegram_id, 'Тестовый пользователь'), share_keyboard(s.bot_username, telegram_id))
    add('info', 'referral', 'Как устроен сервис', 'Через 96 часов после первого онлайна; пользовался за последние 7 дней; нет нерешённой проблемы',
        info_nudge_text(), cabinet_keyboard())
    for days in (7, 10, 15, 20, 45):
        for segment, label in [('setup', 'не подключился'), ('topup', 'закончились деньги'), ('return', 'баланс есть')]:
            markup = onboarding_keyboard(gift=True) if segment == 'setup' else payment_nudge_keyboard(label='Пополнить баланс') if segment == 'topup' else vpn_feedback_keyboard(returning=True)
            key = _idle_notice_key(segment, days)
            add(f'{segment}_{days}', f'return_{segment}', f'Возврат: {label}, {days} дней',
                f'{days} дней без использования; ветка «{label}». Шаги идут по порядку: 7, 10, 15, 20 и 45 дней.', notice_text(key), markup)
    add('nodevice_1', 'nodevice', 'Без устройства',
        'Сутки после запуска бота, устройства нет. Повтор через 7 дней.',
        notice_text('nodevice_1'), onboarding_keyboard(gift=True))
    add('nodevice_2', 'nodevice', 'Без устройства, повтор',
        'Прошла неделя после первого напоминания, устройства всё ещё нет.',
        notice_text('nodevice_2'), onboarding_keyboard(gift=True))
    add('unpaid_1', 'unpaid', 'Без первой оплаты',
        'Двое суток после запуска. Есть устройство, был онлайн или уже пройдены оба напоминания про устройство. Оплат нет.',
        notice_text('unpaid_1'), payment_nudge_keyboard(label='Пополнить баланс'))
    add('unpaid_2', 'unpaid', 'Без первой оплаты, повтор',
        'Прошла неделя после первого напоминания, оплаты всё ещё нет.',
        notice_text('unpaid_2'), payment_nudge_keyboard(label='Пополнить баланс'))
    from app.ambassadors import invitation_text
    from app.keyboards import ambassador_keyboard
    cfg = ambassador_cfg or dict(first_percent=100,first_cap=500,recurring_percent=5,payout_min=2000,hold_days=14)
    add('ambassador','ambassador','Приглашение в амбассадоры',
        'Платил, подключился не менее 7 дней назад и был онлайн за последние 3 дня. Только при открытом наборе, начислениях и доступном бюджете.',
        invitation_text(cfg), ambassador_keyboard())
    from app.ambassadors import invitation_followup_text, invitation_earn_text, invitation_earn_followup_text
    add('ambassador_2','ambassador','Приглашение в амбассадоры, повтор',
        'Через 7 дней после первого приглашения, если заявки всё ещё нет и условия те же.',
        invitation_followup_text(cfg), ambassador_keyboard())
    add('ambassador_earn','ambassador_earn','Заработок: баланс кончился или оплаты не было',
        'Двое суток после запуска. Человек не платил или баланс уже закончился. Набор открыт.',
        invitation_earn_text(cfg), ambassador_keyboard())
    add('ambassador_earn_2','ambassador_earn','Заработок: повтор',
        'Через 7 дней, если заявки всё ещё нет.',
        invitation_earn_followup_text(cfg), ambassador_keyboard())
    for row in rows:
        kind = MESSAGE_KINDS.get(row['id'])
        row['kind'] = kind
        row['exclusions'] = (
            'Тишина, незакрытый тикет, оплата в последние 20 минут, недавнее сообщение; максимум 1 в сутки и 3 за неделю.'
            if kind and (kind.startswith('nudge_') and kind not in {'nudge_trial_end', 'nudge_payment'})
            else 'Финансовые и запрошенные действия не расходуют лимит рекламных сообщений.'
        )
        if row['id'] == 'gift_claimed':
            row['condition'] = 'Только пример текста. Отдельное автоматическое напоминание этого типа не отправляется.'
    return rows


MESSAGE_KINDS = {
    'ambassador': 'nudge_ambassador', 'ambassador_2': 'nudge_ambassador',
    'ambassador_earn': 'nudge_ambassador', 'ambassador_earn_2': 'nudge_ambassador',
    'winback': 'nudge_winback',
    'welcome': 'welcome_intro', 'intro': 'welcome_intro', 'support': 'welcome_intro',
    'resume_welcome': 'nudge_trial', 'resume_channel': 'nudge_trial', 'gift': 'nudge_trial', 'device': 'first_device_thanks', 'setup': 'nudge_device',
    'quality': 'nudge_first_online', 'ending': 'nudge_trial_end', 'empty': 'low_balance',
    'invoice': 'nudge_payment', 'invite': 'nudge_invite', 'info': 'nudge_info',
    **{f'{segment}_{day}': 'nudge_idle' for segment in ('setup','topup','return') for day in (7,10,15,20,45)},
    'nodevice_1': 'nudge_nodevice', 'nodevice_2': 'nudge_nodevice',
    'unpaid_1': 'nudge_unpaid', 'unpaid_2': 'nudge_unpaid',
}


SCENARIOS = {
    'ambassador': ('Амбассадорство', ['ambassador', 'ambassador_2']),
    'ambassador_earn': ('Заработок на рекомендациях', ['ambassador_earn', 'ambassador_earn_2']),
    'winback': ('Возвращение с промокодом', ['winback']),
    'start': ('Первое подключение', ['welcome', 'intro', 'support', 'gift', 'device', 'setup', 'quality']),
    'payment': ('Баланс и неоплаченный счёт', ['ending', 'empty', 'invoice', 'paid']),
    'referral': ('Приглашение друзей', ['invite']),
    'return_setup': ('Возврат: не подключился', ['setup_7', 'setup_10', 'setup_15', 'setup_20', 'setup_45']),
    'return_topup': ('Возврат: нет денег', ['topup_7', 'topup_10', 'topup_15', 'topup_20', 'topup_45']),
    'return_return': ('Возврат: баланс есть', ['return_7', 'return_10', 'return_15', 'return_20', 'return_45']),
    'nodevice': ('Без устройства', ['nodevice_1', 'nodevice_2']),
    'unpaid': ('Без первой оплаты', ['unpaid_1', 'unpaid_2']),
}


def test_keyboard(markup):
    if not markup:
        return None
    # All actions are inert, including web apps, payment links and copied referral texts.
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=button.text, style=button.style, callback_data='funnel_test:click')
        for button in row] for row in markup.inline_keyboard])
