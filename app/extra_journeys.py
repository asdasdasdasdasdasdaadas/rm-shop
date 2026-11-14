"""Three journeys the funnel was missing: a second touch on an abandoned checkout, an early «gift is ending»
for those who never paid, and upsells (a second device, a month ahead) for paying customers.

They are built-in steps of the funnel board (app/funnel_board.py): same daily and weekly caps, Moscow daytime,
quiet mode, open tickets and the A/B tests in «A/B-тесты». {day} in a condition is the price of one day.
"""
import copy

from app.recovery_funnel import PAID

# Non-router devices, at least one, for «price × devices» limits.
_DEVICES = ("(SELECT GREATEST(COUNT(*),1) FROM devices d WHERE d.telegram_id=u.telegram_id "
            "AND COALESCE(d.kind,'') <> 'router')")
_ANY_DEVICE = "EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router')"
_RECEIPTS = "(SELECT COUNT(*) FROM payment_receipts p WHERE p.telegram_id=u.telegram_id AND p.router_days=0)"
_FIRST_PAID_AT = "(SELECT MIN(p.created_at) FROM payment_receipts p WHERE p.telegram_id=u.telegram_id)"
_LAST_PAID_AT = "(SELECT MAX(p.created_at) FROM payment_receipts p WHERE p.telegram_id=u.telegram_id)"

CONDITIONS = (
    {"id": "checkout_again", "label": "Брошенный счёт: второе напоминание", "anchor": "u.checkout_started_at",
     "max_hours": 72,
     "where": """u.checkout_nudge_at IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM payment_receipts p WHERE p.telegram_id=u.telegram_id
            AND p.created_at >= u.checkout_started_at)
        AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id
            AND p.created_at >= u.checkout_started_at)
        AND NOT EXISTS (SELECT 1 FROM pay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted'
            AND o.paid_at >= u.checkout_started_at)""",
     "hint": "Человек открыл счёт, первое напоминание уже было, оплаты нет. Через сутки после счёта, не позже 3 дней. "
             "Новый счёт начинает отсчёт заново."},
    {"id": "gift_ending_soon", "label": "Подарок скоро закончится (не платил)", "anchor": "u.first_online_at",
     "where": f"""NOT {PAID} AND u.first_online_at IS NOT NULL AND {_ANY_DEVICE}
        AND COALESCE(u.balance_rub,0) > {{day}} * {_DEVICES}
        AND COALESCE(u.balance_rub,0) <= {{day}} * 2 * {_DEVICES}""",
     "hint": "Пользуется VPN на подарке, ни разу не платил, осталось от 1 до 2 дней. Один раз. "
             "Последние сутки закрывает «Баланс заканчивается»."},
    {"id": "upsell_device", "label": "Платит: второе устройство", "anchor": _FIRST_PAID_AT, "max_hours": 24 * 30,
     "where": f"""{PAID}
        AND (SELECT COUNT(*) FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router') = 1
        AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id
            AND d.last_online_at > NOW() - INTERVAL '3 days')
        AND COALESCE(u.balance_rub,0) > {{day}} * 5""",
     "hint": "Платил, одно устройство, VPN работает, денег больше чем на 5 дней. Через 3 дня после первой оплаты. Один раз."},
    {"id": "upsell_month", "label": "Платит понемногу: пополнить на месяц", "anchor": _LAST_PAID_AT, "max_hours": 24 * 7,
     "where": f"""{_RECEIPTS} >= 2
        AND (SELECT MAX(p.amount) FROM (SELECT amount FROM payment_receipts p WHERE p.telegram_id=u.telegram_id
            AND p.router_days=0 ORDER BY created_at DESC LIMIT 2) p) < {{day}} * 20 * {_DEVICES}
        AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id
            AND d.last_online_at > NOW() - INTERVAL '7 days')""",
     "hint": "Два последних пополнения меньше чем на 20 дней каждое, VPN используется. Через сутки после пополнения. Один раз."},
)
KINDS = {
    "checkout_again": "nudge_checkout_again",
    "gift_ending_soon": "nudge_gift_ending",
    "upsell_device": "nudge_upsell_device",
    "upsell_month": "nudge_upsell_month",
}
# Steps that may go out again: a new checkout is a new reason.
CYCLE = {"checkout_again"}

CHECKOUT_TEXT = (
    '💳 <b>Оплата так и не прошла</b>\n\n'
    'Вчера вы начали пополнение, но деньги не поступили. Если что-то не получилось — попробуйте другой способ: '
    'в кабинете есть карта, СБП и оплата в Telegram. Новый счёт создаётся за минуту.\n\n'
    'Если деньги списались, а баланс не пополнился, нажмите «Нужна помощь» — разберёмся.'
)
GIFT_ENDING_TEXT = (
    '⏳ <b>Подарок закончится примерно через 2 дня</b>\n\n'
    'Чтобы VPN не выключился, пополните баланс заранее — от {min_topup}. '
    'Настраивать заново ничего не придётся: всё продолжит работать на тех же устройствах.'
)
UPSELL_DEVICE_TEXT = (
    '💻 <b>VPN и на втором устройстве</b>\n\n'
    'Ноутбук, планшет или телевизор подключаются за минуту в кабинете. '
    'Каждое устройство — {price} в день, с того же баланса. Можно отключить в любой момент.'
)
UPSELL_MONTH_TEXT = (
    '📅 <b>Пополните сразу на месяц</b>\n\n'
    'Месяц VPN — {month} на одно устройство. Так не придётся вспоминать об оплате каждые пару недель, '
    'и VPN не выключится в неподходящий момент.'
)

TOPUP = {"action": "topup", "text": "Пополнить баланс"}


def branches():
    from app.funnel_board import _step
    return [
        {"id": "checkout-again", "title": "Брошенный счёт → второе напоминание", "steps": [
            _step("checkout-again-1", "checkout_again", 24, CHECKOUT_TEXT, [TOPUP, "help", "menu"]),
        ]},
        {"id": "gift-ending", "title": "Подарок заканчивается → первая оплата", "steps": [
            _step("gift-ending-1", "gift_ending_soon", 0, GIFT_ENDING_TEXT, [TOPUP, "menu"]),
        ]},
        {"id": "upsell-device", "title": "Допродажа: второе устройство", "steps": [
            _step("upsell-device-1", "upsell_device", 72, UPSELL_DEVICE_TEXT,
                  [{"action": "connect", "text": "Добавить устройство"}, "menu"]),
        ]},
        {"id": "upsell-month", "title": "Допродажа: пополнить на месяц", "steps": [
            _step("upsell-month-1", "upsell_month", 24, UPSELL_MONTH_TEXT, [TOPUP, "menu"]),
        ]},
    ]


def upgrade(graph):
    result = copy.deepcopy(graph)
    ids = {b["id"] for b in result["branches"]}
    for branch in branches():
        if branch["id"] not in ids and len(result["branches"]) < 32:
            result["branches"].append(branch)
    return result
