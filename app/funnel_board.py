"""Editable board that replaces the automatic marketing funnel."""
from __future__ import annotations

import json
import logging
import re
from html import escape

logger = logging.getLogger("rm-shop.funnel")

STEP_LIMIT = 20
RUN_LIMIT = 80
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
LAST_SEEN = (
    "COALESCE((SELECT MAX(d.last_online_at) FROM devices d "
    "WHERE d.telegram_id = u.telegram_id), u.first_online_at, u.bot_started_at)"
)
BASE_WHERE = """
u.blocked_at IS NULL
AND u.bot_blocked_at IS NULL
AND u.bot_started_at IS NOT NULL
AND u.billing_paused_at IS NULL
AND NOT COALESCE(u.quiet_notifications, FALSE)
AND (u.marketing_pause_until IS NULL OR u.marketing_pause_until <= NOW())
AND COALESCE(u.vpn_feedback,'') NOT IN ('help','terms')
AND NOT EXISTS (
    SELECT 1 FROM tickets t
    WHERE t.telegram_id = u.telegram_id AND t.status <> 'closed'
)
"""

OWNED_NOTICE_KEYS = frozenset({
    "paid_setup_nudge", "winback_promo", "payment_nudge", "balance_ending_nudge",
    "trial_nudge", "trial_resume_welcome", "trial_resume_channel",
    "invite_nudge", "info_nudge", "vpn_quality_check",
    "return_check", "return_last", "device_setup_nudge", "device_nudge_1",
    "nodevice_1", "nodevice_2", "unpaid_1", "unpaid_2", "idle_comeback",
    *(f"idle_setup_{day}" for day in (7, 10, 15, 20)),
    *(f"idle_topup_{day}" for day in (7, 10, 15, 20)),
    *(f"idle_return_{day}" for day in (7, 10, 15, 20)),
})

ACTIONS = (
    {"id": "cabinet", "label": "Личный кабинет", "button": "Личный кабинет"},
    {"id": "gift", "label": "Экран подарка", "button": "Забрать подарок и подключиться"},
    {"id": "connect", "label": "Подключение", "button": "Подключить VPN"},
    {"id": "topup", "label": "Пополнение баланса", "button": "Пополнить баланс"},
    {"id": "ambassador", "label": "Раздел амбассадора", "button": "Стать амбассадором"},
    {"id": "help", "label": "Нужна помощь с подключением", "button": "Нужна помощь"},
    {"id": "welcome", "label": "Продолжить знакомство", "button": "Я помогу"},
    {"id": "channel", "label": "Подписка на канал", "button": "Подписаться на канал"},
    {"id": "feedback_ok", "label": "Всё работает", "button": "Всё работает"},
    {"id": "feedback_help", "label": "Помощь с VPN", "button": "Нужна помощь"},
    {"id": "feedback_terms", "label": "Не подошли условия", "button": "Не подошли условия"},
    {"id": "feedback_later", "label": "Пока не нужен", "button": "Пока не нужен"},
    {"id": "share", "label": "Поделиться ссылкой", "button": "Поделиться ссылкой"},
    {"id": "copy", "label": "Скопировать приглашение", "button": "Скопировать текст"},
    {"id": "resume_pay", "label": "Продолжить оплату счёта", "button": "Продолжить оплату"},
    {"id": "about", "label": "О сервисе", "button": "О сервисе"},
    {"id": "invite", "label": "Пригласить друга", "button": "Пригласить"},
    {"id": "menu", "label": "Главное меню", "button": "В главное меню"},
)
ACTION_IDS = {row["id"] for row in ACTIONS}

CONDITIONS = (
    {"id": "unpaid_invoice", "label": "Неоплаченный счёт", "special": "invoice",
     "hint": "Уходит примерно через 10 минут после счёта. Пауза на карточке здесь не используется. Не тратит дневной лимит. Кнопка «Продолжить оплату счёта» открывает этот счёт."},
    {"id": "balance_low", "label": "Баланс заканчивается", "special": "balance",
     "hint": "Один раз, пока баланс снова не пополнят. Пауза на карточке здесь не используется. К тексту добавляются баланс, число устройств и расход. Не тратит дневной лимит."},
    {"id": "no_device", "label": "Нет устройства", "anchor": "u.bot_started_at",
     "where": "NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)",
     "hint": "Бот запущен, устройство не добавлено. Срок считается от запуска бота."},
    {"id": "no_online", "label": "Устройство не выходило в сеть", "anchor": "COALESCE(u.gift_claimed_at, u.bot_started_at)",
     "where": """u.first_online_at IS NULL
        AND COALESCE(u.gift_claimed_at, u.bot_started_at) <= timezone('utc', now()) - INTERVAL '30 minutes'
        AND (EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)
             OR u.gift_claimed_at IS NOT NULL OR COALESCE(u.has_paid_topup, FALSE))""",
     "hint": "Подарок или устройство уже есть, но VPN ещё ни разу не подключался. Не раньше чем через 30 минут."},
    {"id": "unpaid", "label": "Не было первой оплаты", "anchor": "u.bot_started_at",
     "where": """NOT COALESCE(u.has_paid_topup, FALSE)
        AND NOT EXISTS (SELECT 1 FROM rollypay_orders o WHERE o.telegram_id = u.telegram_id AND o.status = 'granted')
        AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id = u.telegram_id)
        AND u.first_online_at IS NOT NULL AND NOT u.trial_waiting_connection
        AND COALESCE(u.balance_rub,0) <= 0
        AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id
          AND d.last_billed_at > NOW() - INTERVAL '24 hours')""",
     "hint": "Был подтверждённый онлайн, доступ закончился, оплаты ещё не было. Пока подарок действует — предложение оплаты не отправляется."},
    {"id": "quality", "label": "Первые дни после подключения", "anchor": "u.first_online_at", "max_hours": 168,
     "where": """u.vpn_feedback_at IS NULL
        AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)""",
     "hint": "Спрашиваем в окне от выбранной паузы до 7 дней после первого онлайна, если человек ещё не ответил."},
    {"id": "idle_setup", "label": "Давно не заходил и не был онлайн", "anchor": LAST_SEEN,
     "where": f"u.first_online_at IS NULL AND (u.idle_snoozed_at IS NULL OR {LAST_SEEN} > u.idle_snoozed_at)",
     "hint": "Срок — сколько человек не появлялся. Шаги одной ветки идут по порядку."},
    {"id": "idle_topup", "label": "Давно не заходил, баланс пуст", "anchor": LAST_SEEN,
     "where": f"""u.first_online_at IS NOT NULL AND COALESCE(u.balance_rub, 0) <= 0
        AND (u.idle_snoozed_at IS NULL OR {LAST_SEEN} > u.idle_snoozed_at)""",
     "hint": "Был онлайн, баланс на нуле или ниже. Срок — сколько человек не появлялся."},
    {"id": "idle_return", "label": "Давно не заходил, баланс есть", "anchor": LAST_SEEN,
     "where": f"""u.first_online_at IS NOT NULL AND COALESCE(u.balance_rub, 0) > 0
        AND (u.idle_snoozed_at IS NULL OR {LAST_SEEN} > u.idle_snoozed_at)""",
     "hint": "Был онлайн и на балансе ещё есть деньги. Срок — сколько человек не появлялся."},
    {"id": "trial", "label": "Подарок не забран", "anchor": "u.bot_started_at", "gate": "trial",
     "where": """NOT COALESCE(u.has_paid_topup, FALSE) AND NOT COALESCE(u.trial_used, FALSE)
        AND u.gift_claimed_at IS NULL""",
     "hint": "Подарок включён, человек его не забрал и не оплачивал."},
    {"id": "ambassador_earn", "label": "Амбассадор: ещё не зарабатывает", "anchor": "u.bot_started_at", "gate": "ambassador",
     "where": """NOT EXISTS (SELECT 1 FROM ambassadors a WHERE a.telegram_id = u.telegram_id)
        AND (NOT COALESCE(u.has_paid_topup, FALSE)
             OR (COALESCE(u.balance_rub, 0) <= 0
                 AND (u.balance_exhausted_at IS NOT NULL OR u.trial_used OR u.gift_claimed_at IS NOT NULL)))""",
     "hint": "Набор амбассадоров открыт. Человек без оплаты или с уже пустым балансом."},
    {"id": "ambassador_active", "label": "Амбассадор: стабильно пользуется", "anchor": "u.first_online_at", "gate": "ambassador",
     "where": """COALESCE(u.has_paid_topup, FALSE)
        AND u.balance_rub >= {price} * GREATEST(1, (SELECT COUNT(*) FROM devices d
            WHERE d.telegram_id = u.telegram_id AND COALESCE(d.kind, '') <> 'router'))
        AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
            AND d.last_online_at > timezone('utc', now()) - INTERVAL '3 days')
        AND NOT EXISTS (SELECT 1 FROM ambassadors a WHERE a.telegram_id = u.telegram_id)""",
     "hint": "Набор открыт. Была оплата, хватает баланса на 3 дня и устройство было онлайн за последние 3 дня."},
    {"id": "invite", "label": "Можно пригласить друга", "anchor": "u.first_online_at", "gate": "referral",
     "where": """(u.vpn_feedback = 'ok' OR EXISTS (
            SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
            AND d.last_online_at >= u.first_online_at + INTERVAL '24 hours'
            AND d.last_online_at >= timezone('utc', now()) - INTERVAL '7 days'))""",
     "hint": "Реферальная программа включена, VPN уже поработал. В тексте можно оставить {name} и {link}."},
    {"id": "info", "label": "Кабинет уже пользовали", "anchor": "u.first_online_at",
     "where": """EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
        AND d.last_online_at > timezone('utc', now()) - INTERVAL '7 days')""",
     "hint": "Устройство было онлайн за последнюю неделю. В тексте можно оставить {price}."},
    {"id": "winback", "label": "Промокод на 5 дней", "special": "winback",
     "hint": "Личный код, когда баланс уже пуст. Срок задаёт сам промокод, пауза на карточке здесь не используется. Условия кода добавляются к тексту. Можно оставить {code}, {devices} и {amount}."},
)
from app.recovery_funnel import CONDITIONS as RECOVERY_CONDITIONS
CONDITIONS = CONDITIONS + RECOVERY_CONDITIONS
CONDITION_IDS = {row["id"]: row for row in CONDITIONS}
SPECIAL_ONCE = {"unpaid_invoice", "balance_low", "winback"}


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def conditions_public() -> list[dict]:
    return [{"id": row["id"], "label": row["label"], "hint": row["hint"]} for row in CONDITIONS if row["id"] not in {"winback","ambassador_earn","ambassador_active"}]


def actions_public() -> list[dict]:
    return [{"id": row["id"], "label": row["label"], "button": row["button"]} for row in ACTIONS if row["id"] != "ambassador"]


def _button(action_id: str) -> dict:
    return next(row for row in ACTIONS if row["id"] == action_id)


def validate_buttons(buttons):
    from urllib.parse import urlsplit
    if not isinstance(buttons, list) or len(buttons) > 6:
        raise ValueError("Можно добавить до 6 кнопок")
    clean = []
    for item in buttons:
        if isinstance(item, str):
            if item not in ACTION_IDS or item in clean:
                raise ValueError("Выберите действие кнопки")
            clean.append(item)
            continue
        if not isinstance(item, dict):
            raise ValueError("Некорректная кнопка")
        action = str(item.get("action") or "")
        label = str(item.get("text") or "").strip()
        if action not in ACTION_IDS | {"url"} or not label or len(label) > 64:
            raise ValueError("Выберите действие и название кнопки до 64 символов")
        button = {"action": action, "text": label}
        if action == "url":
            url = str(item.get("url") or "").strip()
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or len(url) > 2048:
                raise ValueError("Для ссылки нужен полный HTTPS-адрес")
            button["url"] = url
        clean.append(button)
    return clean


def default_menu():
    from app.notices import public_notices
    text = public_notices()["profile_balance"]
    text = text.replace("«Открыть кабинет» внизу", "«Личный кабинет»").replace("«Открыть кабинет»", "«Личный кабинет»")
    return {"text": text,
            "buttons": ["cabinet", {"action": "channel", "text": "Новостной канал"}, "invite", "about"]}


def validate_menu(menu):
    if not isinstance(menu, dict):
        raise ValueError("Некорректное главное меню")
    text = str(menu.get("text") or "").strip()
    if not text or len(text) > 3500:
        raise ValueError("Текст меню — от 1 до 3500 символов")
    buttons = validate_buttons(menu.get("buttons"))
    if not buttons:
        raise ValueError("Добавьте хотя бы одну кнопку меню")
    return {"text": text, "buttons": buttons}


async def menu_content(first_name, balance_rub, telegram_id):
    try:
        graph = await load()
    except Exception:
        logger.exception("Не удалось загрузить главное меню, используем стандартное")
        return None
    menu = graph.get("main_menu")
    if not menu:
        return None
    from app.texts import rub_text
    body = render_text(menu["text"].replace("{balance}", rub_text(balance_rub)), telegram_id, first_name)
    return body, main_menu_markup(menu["buttons"], telegram_id)


def main_menu_markup(button_ids, telegram_id):
    keyboard = markup(button_ids, telegram_id)
    if not keyboard:
        return keyboard
    rows = []
    pair = []
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.callback_data == "check_sub":
                continue
            if button.callback_data in {"share", "about_service"}:
                pair.append(button)
            else:
                rows.append([button])
    if pair:
        rows.append(pair)
    return keyboard.model_copy(update={"inline_keyboard": rows})


def markup(button_ids: list[str], telegram_id: int, token: str | None = None):
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    from app.config import get_settings
    from app.keyboards import invite_copy_text, mini_app_url, referral_share_button

    def screen(label: str, name: str | None):
        url = mini_app_url()
        if not url:
            return InlineKeyboardButton(text=label, callback_data="help:connect")
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        if name:
            query["screen"] = name
        return InlineKeyboardButton(
            text=label, style="success" if name is None or label == "Личный кабинет" else None,
            web_app=WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query)))),
        )

    ids = {item if isinstance(item, str) else item["action"] for item in button_ids}
    if {"feedback_ok", "feedback_help"}.issubset(ids) and "feedback_terms" not in ids:
        button_ids = [*button_ids, "feedback_terms"]
    rows = []
    for item in button_ids:
        action_id = item if isinstance(item, str) else item["action"]
        if action_id == "ambassador":
            continue
        label = _button(action_id)["button"] if isinstance(item, str) else item["text"]
        if action_id == "url":
            rows.append([InlineKeyboardButton(text=label, url=item["url"])])
            continue
        if action_id == "cabinet":
            rows.append([screen(label, None)])
        elif action_id == "gift":
            rows.append([screen(label, "gift")])
        elif action_id == "connect":
            rows.append([screen(label, "connect")])
        elif action_id == "topup":
            rows.append([screen(label, "topup")])
        elif action_id == "ambassador":
            rows.append([screen(label, "ambassador")])
        elif action_id == "help":
            rows.append([InlineKeyboardButton(text=label, callback_data="help:connect")])
        elif action_id == "welcome":
            rows.append([InlineKeyboardButton(text=label, callback_data="welcome:continue")])
        elif action_id == "channel":
            url = get_settings().required_channel_url
            if url:
                rows.append([InlineKeyboardButton(text=label, url=url)])
            if isinstance(item, str):
                rows.append([InlineKeyboardButton(text="Проверить подписку", callback_data="check_sub")])
        elif action_id == "feedback_ok":
            rows.append([InlineKeyboardButton(text=label, callback_data="vpn_feedback:ok")])
        elif action_id == "feedback_help":
            rows.append([InlineKeyboardButton(text=label, callback_data="vpn_feedback:help")])
        elif action_id == "feedback_terms":
            rows.append([InlineKeyboardButton(text=label, callback_data="vpn_feedback:terms")])
        elif action_id == "feedback_later":
            rows.append([InlineKeyboardButton(text=label, callback_data="vpn_feedback:later")])
        elif action_id == "share":
            rows.append([referral_share_button(int(telegram_id)).model_copy(update={"text": label})])
        elif action_id == "copy":
            username = get_settings().bot_username
            rows.append([InlineKeyboardButton(
                text=label, copy_text=CopyTextButton(text=invite_copy_text(int(telegram_id), username)),
            )])
        elif action_id == "resume_pay":
            if token:
                rows.append([InlineKeyboardButton(text=label, callback_data=f"resume_pay:{token}")])
            else:
                rows.append([screen(label, "topup")])
        elif action_id in {"about", "invite"}:
            rows.append([InlineKeyboardButton(text=label, callback_data="about_service" if action_id == "about" else "share")])
        elif action_id == "menu":
            rows.append([InlineKeyboardButton(text=label, callback_data="profile")])
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_text(text: str, telegram_id: int, first_name: str | None) -> str:
    from app.config import get_settings
    from app.texts import rub_text

    settings = get_settings()
    when = ""
    try:
        from app.referral_terms import referral_terms
        terms = referral_terms(settings)
        when = terms.get("when") or ""
        if terms.get("friend"):
            when = (when + " " + terms["friend"]).strip()
    except Exception:
        logger.debug("Условия рефералки не подставились", exc_info=True)
    name = escape(first_name or "").replace("{", "").replace("}", "")
    values = _Safe({
        "name": name,
        "link": f"https://t.me/{settings.bot_username}?start=ref_{int(telegram_id)}",
        "price": rub_text(settings.vpn_day_price_rub),
        "reward": "50 ₽ + 5% с каждого пополнения",
        "when": when,
    })
    try:
        return str(text or "").format_map(values)
    except Exception:
        return str(text or "")


def validate(graph) -> dict:
    if not isinstance(graph, dict):
        raise ValueError("Воронка должна быть доской с ветками")
    branches = graph.get("branches")
    if not isinstance(branches, list) or len(branches) > 32:
        raise ValueError("Веток может быть от 0 до 32")
    clean = []
    seen = set()
    specials = set()
    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError("Ветка устроена неверно")
        bid = str(branch.get("id") or "")
        title = str(branch.get("title") or "").strip()
        if not _ID.match(bid) or bid in seen:
            raise ValueError("У ветки должен быть свой короткий id")
        if not title or len(title) > 80:
            raise ValueError("Название ветки — до 80 символов")
        seen.add(bid)
        steps_in = branch.get("steps")
        if not isinstance(steps_in, list) or len(steps_in) > 8:
            raise ValueError(f"В ветке «{title}» может быть от 0 до 8 шагов")
        steps = []
        for step in steps_in:
            if not isinstance(step, dict):
                raise ValueError("Шаг устроен неверно")
            sid = str(step.get("id") or "")
            if not _ID.match(sid) or sid in seen:
                raise ValueError("У шага должен быть свой короткий id")
            seen.add(sid)
            condition = str(step.get("condition") or "")
            if condition not in CONDITION_IDS:
                raise ValueError("Выберите условие из списка")
            if condition in SPECIAL_ONCE:
                if condition in specials:
                    raise ValueError(f"Условие «{CONDITION_IDS[condition]['label']}» можно поставить один раз")
                specials.add(condition)
            raw_hours = step.get("wait_hours")
            if isinstance(raw_hours, bool) or not isinstance(raw_hours, (int, str)) or not re.fullmatch(r"[0-9]+", str(raw_hours)):
                raise ValueError("Укажите паузу целым числом часов. Для отправки сразу введите 0")
            hours = int(raw_hours)
            if hours < 0 or hours > 24 * 365:
                raise ValueError("Пауза шага — от 0 часов до года")
            wait_from = str(step.get("wait_from") or "")
            if wait_from not in {"anchor", "previous"}:
                raise ValueError("Пауза считается от события или от предыдущего шага")
            text = str(step.get("text") or "").strip()
            if not text or len(text) > 3500:
                raise ValueError("Текст шага — от 1 до 3500 символов")
            picked = validate_buttons(step.get("buttons", []))
            steps.append({
                "id": sid,
                "condition": condition,
                "wait_hours": hours,
                "wait_from": wait_from,
                "text": text,
                "buttons": picked,
                "enabled": bool(step.get("enabled", True)),
            })
        clean.append({"id": bid, "title": title, "steps": steps})
    result = {"branches": clean}
    if "main_menu" in graph:
        result["main_menu"] = validate_menu(graph["main_menu"])
    return result


def _step(sid, condition, hours, text, buttons, wait_from="anchor", enabled=True):
    return {
        "id": sid, "condition": condition, "wait_hours": int(hours), "wait_from": wait_from,
        "text": (text or "Напишите текст сообщения.").strip()[:3500],
        "buttons": list(buttons), "enabled": bool(enabled),
    }


async def _flag(name: str, default: bool) -> bool:
    from app import db
    try:
        return bool(await db.flag_on(name, default=default))
    except Exception:
        return default


async def default_graph() -> dict:
    from app import ambassadors
    from app.notices import notice_text
    from app.nudge import _idle_notice_key, trial_nudge_text

    def tx(key: str, **kwargs) -> str:
        try:
            value = notice_text(key, **kwargs).strip()
        except Exception:
            value = ""
        return value or "Напишите текст сообщения."

    try:
        cfg = await ambassadors.settings()
        active = ambassadors.invitation_text(cfg)
        active_next = ambassadors.invitation_followup_text(cfg)
        earn = ambassadors.invitation_earn_text(cfg)
        earn_next = ambassadors.invitation_earn_followup_text(cfg)
    except Exception:
        logger.debug("Текст амбассадоров для доски не собрался", exc_info=True)
        active = active_next = earn = earn_next = "Расскажите, как можно зарабатывать на рекомендациях."
    try:
        gift_text = trial_nudge_text("{name}", already_granted=False)
    except Exception:
        gift_text = tx("trial_nudge")
    pay_on = await _flag("payment_nudge", True)
    trial_on = await _flag("trial_nudge", True)
    invite_on = await _flag("invite_nudge", True)
    info_on = await _flag("info_nudge", True)
    win_on = await _flag("winback_promo", True)
    idle_buttons = {
        "setup": ["connect", "help"],
        "topup": ["topup", "menu"],
        "return": ["feedback_ok", "feedback_help", "feedback_later"],
    }
    idle_titles = {
        "setup": "Не подключался",
        "topup": "Баланс пуст",
        "return": "Есть баланс",
    }
    branches = [
        {"id": "invoice", "title": "Неоплаченный счёт", "steps": [
            _step("pay-1", "unpaid_invoice", 0, tx("payment_nudge"), ["resume_pay", "menu"], enabled=pay_on),
        ]},
        {"id": "balance", "title": "Баланс заканчивается", "steps": [
            _step("balance-1", "balance_low", 0, tx("balance_ending_nudge"), ["topup", "menu"]),
        ]},
        {"id": "nodevice", "title": "Нет устройства", "steps": [
            _step("nodevice-1", "no_device", 24, tx("nodevice_1"), ["gift", "help"]),
            _step("nodevice-2", "no_device", 168, tx("nodevice_2"), ["gift", "help"], "previous"),
        ]},
        {"id": "online", "title": "Нет первого подключения", "steps": [
            _step("device-1", "no_online", 0, tx("device_nudge_1"), ["connect", "help"]),
        ]},
        {"id": "unpaid", "title": "Нет первой оплаты", "steps": [
            _step("unpaid-1", "unpaid", 48, tx("unpaid_1"), ["topup", "menu"]),
            _step("unpaid-2", "unpaid", 168, tx("unpaid_2"), ["topup", "menu"], "previous"),
        ]},
        {"id": "quality", "title": "Как работает VPN", "steps": [
            _step("quality-1", "quality", 20, tx("vpn_quality_check"), ["feedback_ok", "feedback_help", "feedback_terms"]),
        ]},
    ]
    for segment, title in idle_titles.items():
        steps = []
        for days, hours in ((7, 168), (10, 240), (15, 360), (20, 480), (45, 1080)):
            steps.append(_step(
                f"idle-{segment}-{days}", "idle_" + segment, hours,
                tx(_idle_notice_key(segment, days)), idle_buttons[segment],
            ))
        branches.append({"id": f"idle-{segment}", "title": title, "steps": steps})
    branches.extend([
        {"id": "earn", "title": "Заработок на VPN", "steps": [
            _step("earn-1", "ambassador_earn", 48, earn, ["ambassador", "menu"]),
            _step("earn-2", "ambassador_earn", 168, earn_next, ["ambassador", "menu"], "previous"),
        ]},
        {"id": "active", "title": "Приглашение амбассадора", "steps": [
            _step("active-1", "ambassador_active", 168, active, ["ambassador", "menu"]),
            _step("active-2", "ambassador_active", 168, active_next, ["ambassador", "menu"], "previous"),
        ]},
        {"id": "friends", "title": "Пригласить друга", "steps": [
            _step("invite-1", "invite", 48, tx("invite_nudge"), ["share", "copy", "menu"], enabled=invite_on),
        ]},
        {"id": "cabinet", "title": "Как устроен кабинет", "steps": [
            _step("info-1", "info", 96, tx("info_nudge"), ["cabinet", "menu"], enabled=info_on),
        ]},
        {"id": "gift", "title": "Подарок не забран", "steps": [
            _step("trial-1", "trial", 24, gift_text, ["gift", "help"], enabled=trial_on),
        ]},
        {"id": "return", "title": "Промокод на возвращение", "steps": [
            _step("winback-1", "winback", 0, tx("winback_promo"), ["cabinet", "menu"], enabled=win_on),
        ]},
    ])
    from app.recovery_funnel import upgrade
    return validate(upgrade({"branches": branches}))


def preview(graph: dict, telegram_id: int) -> tuple[list[dict], list[tuple]]:
    rows = []
    scenarios = []
    for branch in graph.get("branches") or []:
        ids = []
        for step in branch.get("steps") or []:
            if not step.get("enabled", True):
                continue
            ids.append(step["id"])
            spec = CONDITION_IDS.get(step["condition"], {})
            rows.append({
                "id": step["id"],
                "title": branch.get("title") or "Шаг",
                "condition": spec.get("label") or step["condition"],
                "body": render_text(step.get("text") or "", telegram_id, "Администратор").replace("{code}", "TEST-ONLY").replace("{devices}", "1").replace("{amount}", "30"),
                "kind": "nudge_board",
                "markup": markup(step.get("buttons") or [], telegram_id),
            })
        if ids:
            scenarios.append((branch["id"], branch.get("title") or "Ветка", ids))
    return rows, scenarios


async def _ensure_tables() -> None:
    from app.db import _pool_req
    pool = _pool_req()
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS funnel_graphs (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            graph JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS funnel_step_sends (
            telegram_id BIGINT NOT NULL,
            step_id TEXT NOT NULL,
            sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (telegram_id, step_id)
        )
    """)


def _parse(raw) -> dict:
    if isinstance(raw, str):
        raw = json.loads(raw)
    return validate(raw)


def without_retired_branches(graph):
    graph = json.loads(json.dumps(graph))
    for branch in graph['branches']:
        branch['steps'] = [s for s in branch['steps'] if s['condition'] not in {'winback','ambassador_earn','ambassador_active'}]
    graph['branches'] = [b for b in graph['branches'] if b['steps']]
    return graph


async def load() -> dict:
    from app.db import _pool_req
    await _ensure_tables()
    pool = _pool_req()
    row = await pool.fetchrow("SELECT graph FROM funnel_graphs WHERE id = 1")
    if row:
        from app.recovery_funnel import migrate
        return without_retired_branches(await migrate(pool, _parse(row["graph"])))
    graph = await default_graph()
    inserted = await pool.fetchrow(
        "INSERT INTO funnel_graphs (id, graph) VALUES (1, $1::jsonb) ON CONFLICT DO NOTHING RETURNING id",
        json.dumps(graph, ensure_ascii=False),
    )
    if inserted:
        try:
            await _backfill()
        except Exception:
            logger.exception("Старые шаги воронки не отмечены")
        from app.recovery_funnel import migrate
        return without_retired_branches(await migrate(pool, graph))
    row = await pool.fetchrow("SELECT graph FROM funnel_graphs WHERE id = 1")
    from app.recovery_funnel import migrate
    return without_retired_branches(await migrate(pool, _parse(row["graph"])))


async def save(graph: dict) -> None:
    from app.db import _pool_req
    clean = validate(graph)
    await _ensure_tables()
    await _pool_req().execute(
        """INSERT INTO funnel_graphs (id, graph) VALUES (1, $1::jsonb)
           ON CONFLICT (id) DO UPDATE SET graph = EXCLUDED.graph, updated_at = NOW()""",
        json.dumps(clean, ensure_ascii=False),
    )


async def _backfill() -> None:
    from app.db import _pool_req
    pairs = [
        ("nodevice_nudge_step >= 1", "nodevice-1"),
        ("nodevice_nudge_step >= 2", "nodevice-2"),
        ("unpaid_nudge_step >= 1", "unpaid-1"),
        ("unpaid_nudge_step >= 2", "unpaid-2"),
        ("trial_nudge_sent_at IS NOT NULL", "trial-1"),
        ("invite_nudge_sent_at IS NOT NULL", "invite-1"),
        ("info_nudge_sent_at IS NOT NULL", "info-1"),
        ("device_nudge_at IS NOT NULL", "device-1"),
        ("first_online_nudge_at IS NOT NULL", "quality-1"),
        ("ambassador_invite_step >= 1", "active-1"),
        ("ambassador_invite_step >= 2", "active-2"),
        ("ambassador_invite_step >= 1", "earn-1"),
        ("ambassador_invite_step >= 2", "earn-2"),
    ]
    for days in (7, 10, 15, 20, 45):
        for segment in ("setup", "topup", "return"):
            pairs.append((f"idle_nudge_step >= {int(days)}", f"idle-{segment}-{days}"))
    pool = _pool_req()
    for where, step_id in pairs:
        await pool.execute(
            f"""INSERT INTO funnel_step_sends (telegram_id, step_id)
                SELECT telegram_id, $1 FROM users WHERE {where}
                ON CONFLICT DO NOTHING""",
            step_id,
        )


async def _gate(condition: str) -> bool:
    if condition in {"ambassador_earn", "ambassador_active", "winback"}:
        return False
    spec = CONDITION_IDS[condition]
    gate = spec.get("gate")
    if gate == "trial":
        from app.config import get_settings
        return bool(get_settings().trial_enabled)
    if gate == "referral":
        from app.config import get_settings
        return bool(get_settings().referral_program_enabled)
    if gate == "ambassador":
        from app.ambassadors import recruitment_offer
        return bool(await recruitment_offer())
    return True


def is_setup_assist(step, prev_id):
    return not prev_id and step['condition'] in {'recover_setup','recover_online'} and step.get('wait_from') == 'anchor'


async def _due(step: dict, prev_id: str | None, limit: int, skip: list[int]) -> list[dict]:
    from app.config import get_settings
    from app.db import _pool_req, _ACCESS_EXHAUSTED
    spec = CONDITION_IDS[step["condition"]]
    if spec.get("special"):
        return []
    price = max(1, int(get_settings().vpn_day_price_rub)) * 3
    where = spec["where"].replace("{price}", str(price))
    if step["condition"] == "unpaid":
        where = where.replace("COALESCE(u.balance_rub,0) <= 0", _ACCESS_EXHAUSTED.replace("{price}", str(max(1, int(get_settings().vpn_day_price_rub)))))
    from app.recovery_funnel import SEEN
    if step["condition"].startswith("recover_"):
        where = where.replace("{exhausted}", _ACCESS_EXHAUSTED.replace("{price}", str(max(1, int(get_settings().vpn_day_price_rub)))))
        snooze_anchor = spec["anchor"] if step["condition"] == "recover_online" else SEEN
        where += f" AND (u.idle_snoozed_at IS NULL OR {snooze_anchor} > u.idle_snoozed_at)"
        if not is_setup_assist(step, prev_id):
            where += " AND NOT EXISTS (SELECT 1 FROM message_log m WHERE m.telegram_id=u.telegram_id AND m.status='sent' AND m.kind LIKE 'nudge_recover_%' AND m.created_at > NOW()-INTERVAL '48 hours')"

    anchor = spec["anchor"]
    hours = int(step["wait_hours"])
    prev = prev_id or ""
    if prev and step.get("wait_from") == "previous":
        time_sql = """EXISTS (
            SELECT 1 FROM funnel_step_sends p
            WHERE p.telegram_id = u.telegram_id AND p.step_id = $5
              AND p.sent_at <= NOW() - ($4::int * INTERVAL '1 hour')
        )"""
    else:
        time_sql = (
            f"{anchor} IS NOT NULL AND {anchor} <= NOW() - ($4::int * INTERVAL '1 hour')"
        )
        if spec.get("max_hours"):
            time_sql += (
                f" AND {anchor} >= NOW() - ({int(spec['max_hours'])} * INTERVAL '1 hour')"
            )
        if prev:
            time_sql += """ AND EXISTS (
                SELECT 1 FROM funnel_step_sends p
                WHERE p.telegram_id = u.telegram_id AND p.step_id = $5
            )"""
    cycle_clause = ""
    if step['condition'] in {'recover_idle', 'recover_online'}:
        cycle_anchor = SEEN if step['condition'] == 'recover_idle' else anchor
        cycle_clause = f" AND s.sent_at >= {cycle_anchor}"
        time_sql = time_sql.replace("p.step_id = $5", f"p.step_id = $5 AND p.sent_at >= {cycle_anchor}")
    args = [int(limit), [int(item) for item in skip], step["id"], hours]
    if prev:
        args.append(prev)
    rows = await _pool_req().fetch(
        f"""SELECT u.telegram_id, u.first_name
            FROM users u
            WHERE {BASE_WHERE}
              AND {where}
              AND {time_sql}
              AND NOT EXISTS (
                  SELECT 1 FROM funnel_step_sends s
                  WHERE s.telegram_id = u.telegram_id AND s.step_id = $3 {cycle_clause}
              )
              AND NOT (u.telegram_id = ANY($2::bigint[]))
            ORDER BY u.telegram_id
            LIMIT $1""",
        *args,
    )
    return [dict(row) for row in rows]


async def _send_step(bot, step: dict, prev_id: str | None, skip: list[int]) -> tuple[int, list[int]]:
    from app import db
    from app.nudge import _deliver_unbudgeted
    sent = 0
    touched: list[int] = []
    if not await _gate(step["condition"]):
        return 0, touched
    from app.recovery_funnel import KINDS
    kind = "nudge_setup_assist" if is_setup_assist(step, prev_id) else KINDS.get(step["condition"], "nudge_board")
    for row in await _due(step, prev_id, STEP_LIMIT, skip + touched):
        uid = int(row["telegram_id"])
        slot = await (db.reserve_setup_assistance(uid) if kind == "nudge_setup_assist" else db.reserve_optional_message(uid, kind))
        if slot is None:
            touched.append(uid)
            continue
        delivered = False
        try:
            body = render_text(step['text'], uid, row.get('first_name'))
            buttons = step['buttons']
            if step['condition'] == 'recover_idle':
                funded = await db.has_funded_access(uid)
                body += "\n\n" + ("Доступ ещё действует — можно включить VPN." if funded else "Доступ закончился. В кабинете можно пополнить баланс и вернуться к VPN.")
                buttons = [({'action':'connect' if funded else 'topup','text':'Личный кабинет'}
                            if (b if isinstance(b,str) else b.get('action')) in {'cabinet','connect','topup'} else b) for b in buttons]
            delivered = await _deliver_unbudgeted(
                bot, kind=kind, telegram_id=uid, first_name=row.get("first_name"),
                title=CONDITION_IDS[step["condition"]]["label"],
                body=body,
                reply_markup=markup(buttons, uid), preserve=True,
                extra={"step_id": step["id"]},
            )
        except Exception:
            logger.exception("Шаг воронки %s не ушёл %s", step["id"], uid)
        finally:
            await db.finish_optional_message(slot, delivered)
        touched.append(uid)
        if not delivered:
            continue
        await db._pool_req().execute(
            """INSERT INTO funnel_step_sends (telegram_id, step_id)
               VALUES ($1, $2) ON CONFLICT (telegram_id,step_id) DO UPDATE SET sent_at=NOW()""",
            uid, step["id"],
        )
        if step["condition"] in {"ambassador_active", "ambassador_earn"}:
            try:
                from app import ambassadors
                await ambassadors.mark_invitation_sent(uid, 1 if not prev_id else 2)
            except Exception:
                logger.exception("Приглашение амбассадора не отмечено %s", uid)
        sent += 1
        if sent >= STEP_LIMIT:
            break
    return sent, touched


async def send_due(bot, rp=None, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    from app import db
    from app import nudge
    from app.winback import send_due as send_winback
    if await db.flag_on("maintenance"):
        return 0, []
    try:
        graph = await load()
    except Exception:
        logger.exception("Доска воронки не прочиталась")
        return 0, []
    skip = [int(item) for item in (skip_ids or [])]
    sent = 0
    touched: list[int] = []
    invoice = _first(graph, "unpaid_invoice")
    balance = _first(graph, "balance_low")
    if invoice and invoice["enabled"]:
        count, ids = await nudge.send_due_payment_nudges(
            bot, rp, skip, body=invoice["text"], button_ids=invoice["buttons"], honor_flag=False,
        )
        sent += count
        touched.extend(ids)
        skip.extend(ids)
    # Event-related setup help has its own small budget, before marketing suppression.
    for branch in graph['branches']:
        first = next((step for step in branch['steps'] if step['enabled']), None)
        if first and is_setup_assist(first, None) and sent < RUN_LIMIT:
            count, ids = await _send_step(bot, first, None, skip)
            sent += count
            touched.extend(ids)
            skip.extend(ids)
    skip.extend(await db.nudge_suppressed_ids(hours=6))
    if balance and balance["enabled"] and sent < RUN_LIMIT:
        count, ids = await nudge.send_due_trial_end_nudges(
            bot, skip, body=balance["text"], button_ids=balance["buttons"],
        )
        sent += count
        touched.extend(ids)
        skip.extend(ids)
    skip.extend(await db.marketing_suppressed_ids())
    skip.extend(await db.nudge_suppressed_ids(hours=24))
    winback_done = False
    for branch in graph["branches"]:
        prev = None
        enabled = [step for step in branch["steps"] if step["enabled"]]
        for step in enabled:
            if sent >= RUN_LIMIT:
                return sent, touched
            spec = CONDITION_IDS[step["condition"]]
            if spec.get("special") == "winback" and not winback_done:
                count, ids = await send_winback(
                    bot, skip, custom=step["text"], force=True, button_ids=step["buttons"],
                )
                sent += count
                touched.extend(ids)
                skip.extend(ids)
                winback_done = True
            elif not spec.get("special") and not is_setup_assist(step, prev):
                count, ids = await _send_step(bot, step, prev, skip)
                sent += count
                touched.extend(ids)
                skip.extend(ids)
            if not spec.get("special"):
                prev = step["id"]
    return sent, touched


def _first(graph: dict, condition: str) -> dict | None:
    for branch in graph["branches"]:
        for step in branch["steps"]:
            if step["condition"] == condition:
                return step
    return None
