"""«Выгрузить в Excel»: every statistics screen of the admin panel in one .xlsx to send to someone.

The screens' own handlers are called with the admin's request, so the numbers match the panel exactly;
their JSON is laid out as tables (lists) and «показатель — значение» blocks (everything else). Gifts,
messages, buttons and funnel steps get sheets of their own, built from the tables directly.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone

from aiohttp import web

from app import db, xlsx

logger = logging.getLogger(__name__)

PERIODS = {7, 30, 90, 365, 0}  # 0 — за всё время

# Readable names for the keys that recur across screens; anything else becomes «key name».
KEYS = {
    "users_total": "Пользователей всего", "users": "Пользователи", "total": "Всего", "count": "Количество",
    "sent": "Отправлено", "failed": "Не доставлено", "skipped": "Пропущено", "recipients": "Получателей",
    "clicked": "Нажали кнопку", "clicks": "Нажатий", "connected": "Подключили VPN", "paid": "Оплатили",
    "first_paid": "Первая оплата", "paid_rub": "Оплачено, ₽", "opened": "Открыли кабинет",
    "devices": "Устройства", "device_count": "Устройств", "amount": "Сумма", "amount_rub": "Сумма, ₽",
    "revenue_rub": "Выручка, ₽", "rub": "₽", "stars": "Звёзды", "new_1d": "Новых за сутки",
    "new_7d": "Новых за 7 дней", "new_30d": "Новых за 30 дней", "active": "Активных", "trial_used": "Взяли пробный",
    "referred": "Пришли по приглашению", "referral_rewarded": "Награда за друга выдана", "legal_ok": "Приняли условия",
    "title": "Название", "label": "Название", "name": "Имя", "kind": "Тип", "status": "Статус", "source": "Источник",
    "created_at": "Создано", "finished_at": "Завершено", "updated_at": "Обновлено", "day": "День", "date": "Дата",
    "rate": "Конверсия, %", "eligible": "В выборке", "converted": "Перешли", "median_hours": "Медиана, ч",
    "period": "Период", "telegram_id": "Telegram ID", "username": "Username", "first_name": "Имя",
    "balance_rub": "Баланс, ₽", "earned": "Заработано", "pending": "Ожидает", "available": "Доступно",
    "invited": "Пригласили", "invited_count": "Пригласил", "code": "Код", "uses": "Использований",
    "scope": "Аудитория", "template": "Шаблон", "body": "Текст", "error": "Ошибка", "note": "Примечание",
    "days": "Дней", "income": "Доход", "expenses": "Расходы", "profit": "Прибыль", "orders": "Заказы",
    "payments": "Платежи", "visits": "Переходы", "starts": "Запуски бота", "online": "Вышли в сеть",
    "blocked": "Заблокировали бота", "block_rate": "Блокировки, %", "outcomes": "Итоги", "transitions": "Переходы",
    "items": "Список", "rows": "Строки", "summary": "Итого", "share": "Поделились", "copy": "Скопировали",
    "groups": "По типам", "recent": "Последние", "compare": "Сравнение", "from": "С", "to": "По",
    "sources": "По источникам", "clicked_at": "Нажал", "connected_at": "Подключил", "paid_after": "Оплатил после",
    "current": "Текущий период", "previous": "Прошлый период", "1d": "Сутки", "7d": "7 дней", "30d": "30 дней",
    "90d": "90 дней", "all": "Всё время", "series": "По дням", "totals": "Итого", "window_days": "Окно, дней",
    "sources_note": "Про источники", "id": "ID", "value": "Значение", "share_rate": "Доля, %",
    # Summary and jobs
    "promo_uses": "Использований промокодов", "stars_payments": "Оплат звёздами", "vpn_reports": "Жалоб на VPN",
    "tickets_open": "Открытых обращений", "broadcast_users": "Получатели рассылок",
    "broadcast_using": "Пользуются VPN", "broadcast_unused": "Не пользуются VPN", "checkout_feedback": "Ответы после брошенной оплаты",
    "bot_blocked": "Заблокировали бота", "bot_blocked_idle": "Заблокировали, не пользовались",
    "payouts_pending": "Выплат ожидает", "paying_users": "Платящие клиенты", "new_today": "Новых сегодня",
    "granted": "Оплачено", "plans": "Пополнения по суммам", "billing_today": "Списания сегодня", "charges": "Списаний",
    "errors": "Ошибок", "credited": "Начислено", "week": "Неделя", "week_prev": "Прошлая неделя",
    "month": "Месяц", "month_prev": "Прошлый месяц", "day_prev": "Прошлые сутки", "pay_soon": "Скоро платить",
    "day_price_rub": "Цена дня, ₽", "day_price": "Цена дня, ₽", "low_balance": "Мало баланса", "trust": "Обещанный платёж",
    "people": "Люди", "trust_open": "Обещанный платёж открыт", "trust_amount": "Обещанный платёж, ₽",
    "due_at": "Срок", "days_left": "Дней осталось", "reason": "Причина", "reasons": "Причины",
    "exit_feedback": "Отзывы при удалении устройства", "answered": "Ответили", "key": "Ключ", "topups": "Пополнения",
    "last_paid_at": "Последняя оплата", "jobs": "Фоновые задачи", "billing": "Списания", "panel_sync": "Синхронизация с панелью",
    "extended": "Продлено", "disabled": "Отключено", "revived": "Включено снова", "extend_mode": "Режим продления",
    "disable_mode": "Режим отключения", "revive_mode": "Режим включения", "paused": "На паузе",
    "maintenance": "Техработы", "seconds": "Секунд", "at": "Когда", "mode": "Режим", "pages": "Страниц",
    "seen": "Просмотрено", "applied": "Применено", "partial": "Частично", "browser_logins": "Входы через браузер",
    "snapshot": "Сейчас", "traffic_bytes": "Трафик, байт", "devices_total": "Устройств всего",
    "registered": "Зарегистрировались", "started": "Запустили бота", "promo": "Промокоды",
    "star_payments": "Оплат звёздами", "invitation_card": "Карточка приглашения", "share_users": "Поделились, людей",
    "copy_users": "Скопировали, людей",
    # Finance and forecast
    "estimated": "Оценка", "first": "Первые оплаты", "repeat": "Повторные оплаты", "payers": "Плательщиков",
    "average_rub": "Средний платёж, ₽", "history": "Платежи", "page": "Страница", "limit": "На странице",
    "plan_code": "Сумма пополнения", "currency": "Валюта", "payment_number": "Номер оплаты клиента",
    "due": "Скоро продление", "horizon": "Горизонт, дней", "router_expire_at": "Роутер до",
    "balance_low": "Мало баланса", "router_due": "Продление роутера", "balance_days": "Хватит на дней",
    "renewals": "Продлений", "sample_intervals": "Интервалов в выборке", "repeat_amounts": "Повторных сумм",
    "average_repeat_rub": "Средний повторный платёж, ₽", "periods": "Периоды", "clients": "Клиентов",
    "covered": "С историей", "expected_payments": "Ожидаемых платежей",
    # Funnel
    "entered": "Пришли", "from_ref": "По приглашению", "from_ad": "По рекламе", "organic": "Сами",
    "legal": "Приняли условия", "trial": "Взяли подарок", "device": "Добавили устройство", "checkout": "Открыли оплату",
    "repeat_paid": "Оплатили повторно", "paid_stars": "Оплатили звёздами",
    "device_no_online": "Устройство без онлайна", "checkout_drop": "Бросили оплату", "no_legal": "Не приняли условия",
    "no_gift": "Не взяли подарок", "gift_no_online": "Подарок есть, онлайна нет", "online_no_paid": "Пользуются, не платили",
    "paid_no_repeat": "Платили один раз", "paid_empty": "Платили, баланс пуст",
    "progress_paid_empty": "Сдвинулись: платили, баланс пуст", "progress_no_gift": "Сдвинулись: без подарка",
    "progress_gift_no_online": "Сдвинулись: подарок без онлайна", "progress_device_no_online": "Сдвинулись: устройство без онлайна",
    "progress_checkout_drop": "Сдвинулись: брошенная оплата", "progress_online_no_paid": "Сдвинулись: пользуются, не платили",
    "progress_paid_no_repeat": "Сдвинулись: платили один раз", "unpaid_help": "Не платили: нужна помощь",
    "unpaid_terms": "Не платили: не подошли условия", "unpaid_ok": "Не платили: всё работает",
    "unpaid_no_feedback": "Не платили: без ответа", "trial_transition": "Переход: подарок",
    "device_transition": "Переход: устройство", "connected_transition": "Переход: подключили VPN",
    "checkout_transition": "Переход: открыли оплату", "paid_transition": "Переход: оплатили",
    "repeat_paid_transition": "Переход: оплатили повторно", "inv_entered": "Приглашённые: пришли",
    "inv_legal": "Приглашённые: приняли условия", "inv_trial": "Приглашённые: взяли подарок",
    "inv_device": "Приглашённые: добавили устройство", "inv_connected": "Приглашённые: подключили VPN",
    "inv_checkout": "Приглашённые: открыли оплату", "inv_paid": "Приглашённые: оплатили",
    "gift_claimed": "Забрали подарок", "median_minutes": "Медиана, минут", "stages": "Этапы", "cabinet": "Кабинет",
    "channel_passed": "Подписались на канал", "wizard_1": "Мастер: шаг 1", "wizard_2": "Мастер: шаг 2",
    "wizard_3": "Мастер: шаг 3", "wizard_4": "Мастер: шаг 4", "welcome_continue": "Продолжили знакомство",
    "gift_view": "Открыли подарок", "started_at": "Начало", "ends": "Конец", "online_mature": "Онлайн: в выборке",
    "online_success": "Онлайн: перешли", "paid_mature": "Оплата: в выборке", "paid_success": "Оплата: перешли",
    "online_pending": "Онлайн: ждём", "online_rate": "Онлайн, %", "paid_pending": "Оплата: ждём", "paid_rate": "Оплата, %",
    "block_eligible": "В выборке блокировок",
    # Referrals, win-back, A/B, ads, promos, stories
    "invitee_id": "Друг (ID)", "invitee_username": "Друг (username)", "invitee_name": "Друг (имя)",
    "invitee_at": "Друг пришёл", "referrer_id": "Пригласил (ID)", "referrer_username": "Пригласил (username)",
    "referrer_name": "Пригласил (имя)", "activated": "Активировали", "activated_at": "Активировал",
    "mature": "Срок вышел", "observing": "Наблюдаем", "expired": "Истекло", "gift_rub": "Подарок, ₽",
    "debt_rub": "Долг, ₽", "debt_repaid_rub": "Долг погашен, ₽", "unknown_debt": "Долг неизвестен",
    "paid_credit_rub": "Оплачено после, ₽", "promo_id": "Промокод (ID)", "sent_at": "Отправлено",
    "retry_at": "Повтор", "attempts": "Попыток", "expires_at": "Истекает", "max_holdout": "Макс. контрольная группа, %",
    "steps": "Шаги", "branch": "Ветка", "n": "№", "condition": "Условие", "wait_hours": "Пауза, ч", "text": "Текст",
    "gift": "Подарок", "step_id": "Шаг", "holdout_pct": "Контрольная группа, %", "b_pct": "Вариант B, %",
    "b_text": "Текст B", "b_gift_days": "Подарок B, дней", "stopped_at": "Остановлен", "running": "Идёт",
    "step": "Шаг", "arms": "Группы", "matured": "Срок вышел", "delivered": "Доставлено", "first_payers": "Первых плательщиков",
    "arm": "Группа", "conversion": "Конверсия, %", "rub_per_user": "₽ на человека", "comparisons": "Сравнения",
    "against": "Против", "payers_pp": "Разница плательщиков, п.п.", "rub_per_100": "₽ на 100 человек",
    "p_value": "p-value", "sure": "Надёжно", "verdict": "Вывод", "tracked": "Отслеживается", "state": "Состояние",
    "slug": "Метка", "url": "Ссылка", "partner": "Партнёр", "archived": "В архиве", "links": "Ссылок",
    "revoked": "Отозван", "recipient_telegram_id": "Кому (ID)", "max_uses": "Макс. использований",
    "used_count": "Использовано", "remaining": "Осталось", "enabled": "Включён", "shared": "Поделились",
    "rewarded": "Награждены", "story_pending_at": "Сторис на проверке", "story_rewarded_at": "Сторис награждена",
}

# The users funnel counts people: «paid_rub» there is «paid in rubles», not an amount.
FUNNEL_KEYS = {"paid_rub": "Оплатили рублями", "paid": "Оплатили"}


def _label(key: str, extra: dict | None = None) -> str:
    key = str(key)
    if extra and key in extra:
        return extra[key]
    if re.fullmatch(r"b\d+", key):
        return f"Пополнение {key[1:]} ₽"
    if key in KEYS or key.lower() in KEYS:
        return KEYS.get(key) or KEYS[key.lower()]
    if not key.isascii():
        return key  # already a readable column name from our own queries
    text = key.replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def _value(v):
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d %H:%M") if isinstance(v, datetime) else v.isoformat()
    s = str(v)
    if len(s) >= 19 and s[4] == "-" and s[10] in "T " and s[13] == ":":
        return s[:16].replace("T", " ")
    return s


def _scalar(v) -> bool:
    return not isinstance(v, (dict, list))


def _table(title: str, items: list[dict], kinds: dict | None = None, keys: dict | None = None) -> list[list]:
    cols: list[str] = []
    for item in items:
        for k, v in item.items():
            if k not in cols and _scalar(v):
                cols.append(k)
    if not cols:
        return []
    rows = [[(title, "title")], [(_label(c, keys), "head") for c in cols]]
    for item in items:
        row = []
        for c in cols:
            v = item.get(c)
            if c == "kind" and kinds and isinstance(v, str):
                v = kinds.get(v, v)
            row.append(_value(v))
        rows.append(row)
    rows.append([])
    return rows


def layout(data, title: str = "", kinds: dict | None = None, keys: dict | None = None) -> list[list]:
    """JSON → rows: scalars as «показатель — значение», lists of objects as tables, nested objects recursively."""
    out: list[list] = []
    if isinstance(data, list):
        if data and all(isinstance(x, dict) for x in data):
            out += _table(title or "Список", data, kinds, keys)
            for i, item in enumerate(data):
                for k, v in item.items():
                    if isinstance(v, (dict, list)) and v and not (isinstance(v, list) and all(_scalar(x) for x in v)):
                        name = item.get("label") or item.get("title") or item.get("name") or item.get("id") or i + 1
                        out += layout(v, f"{title} · {name} · {_label(k, keys)}".strip(" ·"), kinds, keys)
        elif data:
            out += [[(title, "title")], *[[_value(x)] for x in data], []]
        return out
    if not isinstance(data, dict):
        return [[(title, "title")], [_value(data)], []] if title else [[_value(data)]]
    flat = [(k, v) for k, v in data.items() if k != "ok" and (_scalar(v) or (isinstance(v, list) and all(_scalar(x) for x in v)))]
    if flat:
        if title:
            out.append([(title, "title")])
        out.append([("Показатель", "head"), ("Значение", "head")])
        for k, v in flat:
            out.append([_label(k, keys), _value(", ".join(map(str, v)) if isinstance(v, list) else v)])
        out.append([])
    for k, v in data.items():
        if k == "ok" or k in dict(flat):
            continue
        out += layout(v, f"{title} · {_label(k, keys)}" if title else _label(k, keys), kinds, keys)
    return out


async def _call(request: web.Request, handler, path: str, query: dict | None = None) -> dict:
    sub = request.clone(method="GET", rel_url=request.rel_url.with_path(path).with_query(query or {}))
    resp = await handler(sub)
    data = json.loads(resp.body if isinstance(resp.body, (bytes, bytearray)) else resp.text)
    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(data.get("error") or f"HTTP {resp.status}")
    return data


def _dig(data: dict, path: tuple[str, ...]):
    for part in path:
        data = data.get(part) if isinstance(data, dict) else None
    return data


async def _call_all(request: web.Request, handler, path: str, query: dict | None, lists: list[tuple[tuple[str, ...], str]],
                    size: dict | None = None) -> dict:
    """A paged screen in full: every page of each listed list (data path, page parameter) is fetched and joined."""
    query = {**(query or {}), **(size or {})}
    data = await _call(request, handler, path, query)
    for where, param in lists:
        box = _dig(data, where[:-1]) if len(where) > 1 else data
        items = _dig(data, where)
        if not isinstance(box, dict) or not isinstance(items, list) or not items:
            continue
        total = int(box.get("total") or 0)
        page, per = 1, len(items)
        while len(items) < total and page < 300:
            page += 1
            more = _dig(await _call(request, handler, path, {**query, param: str(page)}), where) or []
            if not more:
                break
            items.extend(more)
            if len(more) < per:
                break
        box.pop("page", None)
        box.pop("limit", None)
    return data


def _since(days: int) -> str:
    return "NOW() - INTERVAL '100 years'" if not days else f"NOW() - INTERVAL '{int(days)} days'"


async def _rows(sql: str, *args) -> list[dict]:
    return [dict(r) for r in await db._pool_req().fetch(sql, *args)]


async def gifts_sheet(days: int, kinds: dict) -> list[list]:
    since = _since(days)
    out: list[list] = []
    out += _table("Подарки друзьям: итоги", await _rows(f"""
        SELECT CASE WHEN g.from_admin THEN 'Админ или безлимит' ELSE 'Пользователи' END AS "Кто дарил",
               CASE g.status WHEN 'active' THEN 'ждёт' WHEN 'claimed' THEN 'забран' WHEN 'returned' THEN 'возвращён' ELSE g.status END AS "Статус", COUNT(*)::int AS "Подарков", COALESCE(SUM(g.count),0)::int AS "Мест",
               COALESCE(SUM(g.claimed_count),0)::int AS "Забрали",
               COALESCE(SUM(g.amount_rub * g.count),0)::bigint AS "Подарено, ₽",
               COALESCE(SUM(g.amount_rub * g.claimed_count),0)::bigint AS "Забрали, ₽"
        FROM friend_gifts g WHERE g.created_at >= {since}
        GROUP BY 1, 2 ORDER BY 1, 2"""))
    out += _table("Подарки друзьям: каждый подарок", await _rows(f"""
        SELECT g.created_at AS "Создан", g.from_telegram_id AS "От (ID)", u.first_name AS "От (имя)",
               u.username AS "Username", CASE WHEN g.from_admin THEN 'да' ELSE 'нет' END AS "Без списания",
               g.amount_rub AS "Сумма, ₽", g.count AS "Мест", g.claimed_count AS "Забрали", CASE g.status WHEN 'active' THEN 'ждёт' WHEN 'claimed' THEN 'забран' WHEN 'returned' THEN 'возвращён' ELSE g.status END AS "Статус",
               g.claimed_at AS "Забран", g.returned_at AS "Возвращён"
        FROM friend_gifts g LEFT JOIN users u ON u.telegram_id = g.from_telegram_id
        WHERE g.created_at >= {since} ORDER BY g.created_at DESC LIMIT 5000"""))
    out += _table("Подарочные дни (воронка и рассылки)", await _rows(f"""
        SELECT step_id AS "Шаг или рассылка", COUNT(*)::int AS "Выдано", COUNT(claimed_at)::int AS "Забрали",
               COALESCE(SUM(days) FILTER (WHERE claimed_at IS NOT NULL),0)::int AS "Дней забрали",
               COALESCE(SUM(gift_rub),0)::bigint AS "На сумму, ₽"
        FROM funnel_gifts WHERE created_at >= {since} GROUP BY 1 ORDER BY 2 DESC"""))
    out += _table("Начисления от администратора: итоги", await _rows(f"""
        SELECT kind AS kind, COUNT(*)::int AS "Операций", COUNT(DISTINCT telegram_id)::int AS "Людей",
               COALESCE(SUM(amount) FILTER (WHERE amount > 0),0)::bigint AS "Начислено, ₽",
               COALESCE(SUM(amount) FILTER (WHERE amount < 0),0)::bigint AS "Списано, ₽"
        FROM billing_events WHERE created_at >= {since} AND kind IN ('admin_grant','admin_balance')
        GROUP BY 1 ORDER BY 1"""), kinds)
    out += _table("Начисления от администратора: каждое", await _rows(f"""
        SELECT b.created_at AS "Когда", b.telegram_id AS "Telegram ID", u.first_name AS "Имя", b.kind AS kind,
               b.amount AS "Сумма, ₽", b.balance_after AS "Баланс после, ₽", b.note AS "Примечание"
        FROM billing_events b LEFT JOIN users u ON u.telegram_id = b.telegram_id
        WHERE b.created_at >= {since} AND b.kind IN ('admin_grant','admin_balance')
        ORDER BY b.created_at DESC LIMIT 5000"""), kinds)
    out += _table("Бонусы и подарки на баланс", await _rows(f"""
        SELECT kind AS kind, source AS "Источник", COUNT(*)::int AS "Операций",
               COUNT(DISTINCT telegram_id)::int AS "Людей", COALESCE(SUM(amount),0)::bigint AS "Сумма, ₽"
        FROM billing_events WHERE created_at >= {since}
          AND kind IN ('referral','promo','trial','trust','gift_sent','gift_received','gift_return','story')
        GROUP BY 1, 2 ORDER BY 1, 2"""), kinds)
    out += _table("Безлимит подарков выдан", await _rows("""
        SELECT telegram_id AS "Telegram ID", first_name AS "Имя", username AS "Username"
        FROM users WHERE gift_unlimited ORDER BY telegram_id"""))
    return out


async def messages_sheet(days: int, kinds: dict) -> list[list]:
    since = _since(days)
    out: list[list] = []
    out += _table("Сообщения бота по типам", await _rows(f"""
        SELECT kind AS kind, CASE source WHEN 'manual' THEN 'вручную' ELSE 'автоматически' END AS "Как",
               COUNT(*) FILTER (WHERE status = 'sent')::int AS "Отправлено",
               COUNT(*) FILTER (WHERE status = 'failed')::int AS "Не доставлено",
               COUNT(DISTINCT telegram_id) FILTER (WHERE status = 'sent')::int AS "Получателей"
        FROM message_log WHERE created_at >= {since} GROUP BY 1, 2 ORDER BY 3 DESC"""), kinds)
    out += _table("Сообщения по дням", await _rows(f"""
        SELECT (created_at AT TIME ZONE 'Europe/Moscow')::date AS "День",
               COUNT(*) FILTER (WHERE status = 'sent')::int AS "Отправлено",
               COUNT(*) FILTER (WHERE status = 'failed')::int AS "Не доставлено",
               COUNT(DISTINCT telegram_id) FILTER (WHERE status = 'sent')::int AS "Получателей"
        FROM message_log WHERE created_at >= {since} GROUP BY 1 ORDER BY 1 DESC"""))
    out += _table("Почему не доставлено", await _rows(f"""
        SELECT COALESCE(NULLIF(extra->>'error',''), LEFT(extra->>'error_raw', 120), 'без причины') AS "Причина",
               COUNT(*)::int AS "Сообщений", COUNT(DISTINCT telegram_id)::int AS "Людей"
        FROM message_log WHERE created_at >= {since} AND status = 'failed' GROUP BY 1 ORDER BY 2 DESC LIMIT 50"""))
    out += _table("Рассылки", await _rows(f"""
        SELECT created_at AS "Запущена", title AS "Название", template AS "Шаблон", scope AS "Аудитория",
               total AS "Всего", sent AS "Отправлено", failed AS "Не доставлено", skipped AS "Пропущено",
               finished_at AS "Завершена"
        FROM broadcast_runs WHERE created_at >= {since} ORDER BY created_at DESC LIMIT 1000"""))
    return out


async def buttons_sheet(days: int, kinds: dict) -> list[list]:
    since = _since(days)
    out: list[list] = []
    out += _table("Кнопки в сообщениях: кто нажал и что сделал дальше", await _rows(f"""
        SELECT d.kind AS kind, COALESCE(d.step_id, '') AS "Шаг воронки",
               COUNT(*) FILTER (WHERE d.status = 'sent')::int AS "Отправлено",
               COUNT(*) FILTER (WHERE d.status = 'sent' AND d.clicked_at IS NOT NULL)::int AS "Нажали",
               COALESCE(SUM(c.n),0)::int AS "Нажатий всего",
               COUNT(*) FILTER (WHERE d.cabinet_opened_at IS NOT NULL)::int AS "Открыли кабинет",
               COUNT(*) FILTER (WHERE d.device_added_at IS NOT NULL)::int AS "Добавили устройство",
               COUNT(*) FILTER (WHERE d.connected_at IS NOT NULL)::int AS "Подключили VPN",
               ROUND(100.0 * COUNT(*) FILTER (WHERE d.status = 'sent' AND d.clicked_at IS NOT NULL)
                     / NULLIF(COUNT(*) FILTER (WHERE d.status = 'sent'), 0), 1)::float AS "Нажали, %"
        FROM reminder_deliveries d
        LEFT JOIN (SELECT token, COUNT(*) AS n FROM reminder_clicks GROUP BY token) c ON c.token = d.token
        WHERE d.created_at >= {since} GROUP BY 1, 2 ORDER BY 3 DESC"""), kinds)
    out += _table("Приглашения: «Поделиться» и «Скопировать»", await _rows(f"""
        SELECT CASE action WHEN 'share' THEN 'Поделиться' ELSE 'Скопировать' END AS "Кнопка",
               COUNT(*)::int AS "Нажатий", COUNT(DISTINCT telegram_id)::int AS "Людей"
        FROM invitation_card_events WHERE created_at >= {since} GROUP BY 1 ORDER BY 2 DESC"""))
    out += _table("После брошенной оплаты: ответы", await _rows(f"""
        SELECT CASE reason WHEN 'broken' THEN 'Не получилось оплатить' WHEN 'price' THEN 'Дорого'
                           WHEN 'payment' THEN 'Нет удобного способа' ELSE 'Позже' END AS "Ответ",
               COUNT(*)::int AS "Людей"
        FROM checkout_feedback WHERE created_at >= {since} GROUP BY 1 ORDER BY 2 DESC"""))
    out += _table("Шаги знакомства (кабинет и бот)", await _rows(f"""
        SELECT stage AS "Этап", COUNT(*)::int AS "Людей"
        FROM onboarding_events WHERE created_at >= {since} GROUP BY 1 ORDER BY 2 DESC"""))
    return out


async def funnel_sheet(days: int, stats: dict) -> list[list]:
    from app import funnel_board
    since = _since(days)
    graph = await funnel_board.load()
    sends = {r["step_id"]: r for r in await _rows(f"""
        SELECT step_id, COUNT(*)::int AS total, COUNT(*) FILTER (WHERE sent_at >= {since})::int AS period
        FROM funnel_step_sends GROUP BY 1""")}
    clicks = {r["step_id"]: r for r in await _rows(f"""
        SELECT step_id, COUNT(*) FILTER (WHERE status = 'sent')::int AS sent,
               COUNT(*) FILTER (WHERE status = 'sent' AND clicked_at IS NOT NULL)::int AS clicked,
               COUNT(*) FILTER (WHERE connected_at IS NOT NULL)::int AS connected
        FROM reminder_deliveries WHERE step_id IS NOT NULL AND created_at >= {since} GROUP BY 1""")}
    steps = []
    for branch in graph.get("branches", []):
        for st in branch.get("steps", []):
            spec = funnel_board.CONDITION_IDS.get(st["condition"], {})
            buttons = [b.get("text") or b.get("action") if isinstance(b, dict) else _button_label(funnel_board, b)
                       for b in st.get("buttons", [])]
            s, c = sends.get(st["id"], {}), clicks.get(st["id"], {})
            steps.append({
                "Ветка": branch.get("title"), "Шаг": st["id"], "Условие": spec.get("label") or st["condition"],
                "Пауза, ч": st.get("wait_hours"),
                "Отсчёт": "от предыдущего шага" if st.get("wait_from") == "previous" else "от события",
                "Включён": bool(st.get("enabled")), "Кнопки": ", ".join(map(str, buttons)),
                "Отправлено за период": s.get("period", 0), "Отправлено всего": s.get("total", 0),
                "Нажали кнопку": c.get("clicked", 0), "Подключили VPN": c.get("connected", 0),
                "Текст": st.get("text"),
            })
    out = _table("Шаги воронки", steps)
    for key, title in (("funnel", "Воронка пользователей"), ("onboarding_steps", "Шаги онбординга"),
                       ("cohort_outcomes", "Когорты"), ("journey_comparison", "Сравнение путей")):
        if stats.get(key):
            out += layout(stats.pop(key), title, keys=FUNNEL_KEYS if key == "funnel" else None)
    return out


async def build(request: web.Request, days: int, labels: dict | None = None) -> bytes:
    from app import admin
    labels = labels or {}
    kinds = {**(labels.get("messages") or {}), **(labels.get("billing") or {})}
    q = {"days": str(days or 365)}
    when = datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")
    period = "за всё время" if not days else f"за {days} дн."
    sheets: list[tuple[str, list[list]]] = []

    async def section(title: str, make):
        try:
            rows = await make()
        except Exception as exc:
            logger.exception("Выгрузка: раздел «%s» не собрался", title)
            rows = [[(title, "title")], [f"Не удалось собрать: {type(exc).__name__}: {exc}"]]
        sheets.append((title, rows or [[(title, "title")], ["Нет данных за период"]]))

    stats: dict = {}
    try:
        stats = await _call(request, admin.api_stats, "/admin/api/stats")
    except Exception:
        logger.exception("Выгрузка: сводка не собралась")
    reminders = stats.pop("reminder_results", None)

    async def overview():
        head = [[(f"Статистика сервиса — выгрузка {when}", "title")],
                [(f"Период для разделов с датами: {period}. Сводка — на момент выгрузки.", "note")], []]
        return head + layout({k: v for k, v in stats.items() if k not in
                              ("funnel", "onboarding_steps", "cohort_outcomes", "journey_comparison")}, "", kinds)

    funnel_rows = await _safe(funnel_sheet(days, stats))
    await section("Сводка", overview)
    await section("Статистика", lambda: _layout_call(request, admin.api_statistics, "/admin/api/statistics", q, kinds))
    await section("Финансы", lambda: _layout_all(request, admin.api_finance, "/admin/api/finance", q, kinds,
                                                 [(("history", "items"), "page"), (("due", "items"), "due_page")]))
    await section("Прогноз выручки", lambda: _layout_call(request, admin.api_revenue_forecast, "/admin/api/revenue-forecast", None, kinds))
    await section("Воронка", lambda: _const(funnel_rows))
    await section("Сообщения", lambda: messages_sheet(days, kinds))

    async def buttons():
        rows = await buttons_sheet(days, kinds)
        return rows + (layout(reminders, "Напоминания: результаты", kinds) if reminders else [])
    await section("Кнопки и клики", buttons)
    await section("Подарки", lambda: gifts_sheet(days, kinds))
    await section("Рефералы", lambda: _layout_all(request, admin.api_referrals, "/admin/api/referrals", None, kinds,
                                                  [(("items",), "page")], {"limit": "100"}))
    await section("Возврат клиентов", lambda: _layout_all(request, admin.api_winback_statistics, "/admin/api/statistics/winback",
                                                          q, kinds, [(("items",), "page")]))
    await section("Рассылки и тесты", lambda: _layout_all(request, admin.api_broadcast_results, "/admin/api/broadcast-results",
                                                          None, kinds, [(("items",), "page")]))
    await section("A-B тесты", lambda: _layout_call(request, admin.api_experiments, "/admin/api/experiments", None, kinds))
    await section("Реклама", lambda: _layout_call(request, admin.api_ad_links, "/admin/api/ads", None, kinds))
    await section("Партнёры", lambda: _layout_call(request, admin.api_partners, "/admin/api/partners", None, kinds))
    await section("Промокоды", lambda: _layout_call(request, admin.api_promo_codes, "/admin/api/promos", None, kinds))
    await section("Истории", lambda: _layout_call(request, admin.api_story_stats, "/admin/api/story-stats", None, kinds))
    return xlsx.build(sheets)


def _button_label(funnel_board, action: str) -> str:
    try:
        return funnel_board._button(action).get("button") or action
    except Exception:
        return action


async def _safe(coro):
    try:
        return await coro
    except Exception as exc:
        logger.exception("Выгрузка: воронка не собралась")
        return [[("Воронка", "title")], [f"Не удалось собрать: {type(exc).__name__}: {exc}"]]


async def _const(rows):
    return rows


async def _layout_all(request, handler, path, query, kinds, lists, size=None):
    return layout(await _call_all(request, handler, path, query, lists, size), "", kinds)


async def _layout_call(request, handler, path, query, kinds):
    return layout(await _call(request, handler, path, query), "", kinds)
