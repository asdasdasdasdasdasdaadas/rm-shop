"""The bot's automatic messages: built-in journeys of steps, each sent once when its condition holds."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html import escape

from app.funnel_gifts import ACTION as GIFT_ACTION, gift_label

logger = logging.getLogger("rm-shop.funnel")

STEP_LIMIT = 20
RUN_LIMIT = 80
SCAN_PAGES = 10
_scan_cursors: dict[str, int] = {}
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
    "trial_nudge", "trial_resume_channel",
    "invite_nudge", "info_nudge", "vpn_quality_check",
    "device_setup_nudge", "device_nudge_1",
    "nodevice_1", "nodevice_2", "unpaid_1", "unpaid_2",
})

ACTIONS = (
    {"id": "cabinet", "label": "Личный кабинет", "button": "Личный кабинет"},
    {"id": "gift", "label": "Экран подарка", "button": "Забрать подарок и подключиться"},
    {"id": "connect", "label": "Подключение", "button": "Подключить VPN"},
    {"id": "topup", "label": "Пополнение баланса", "button": "Пополнить баланс"},
    {"id": "topup_quick", "label": "Пополнение: две кнопки с готовой суммой (минимум и месяц)", "button": "Пополнить"},
    {"id": "topup_return", "label": "Пополнение с бонусом за возвращение: «200 ₽ → 240 ₽»", "button": "Пополнить другую сумму"},
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
    {"id": "promise", "label": "Обещанный платёж (видна, только когда он доступен)", "button": "🤝 Обещанный платёж"},
    {"id": "claim_gift", "label": "Забрать подарочные дни (личный подарок, не чаще раза в 14 дней)",
     "button": f"🎁 Забрать {gift_label()}"},
)
ACTION_IDS = {row["id"] for row in ACTIONS}

CONDITIONS = (
    {"id": "unpaid_invoice", "label": "Неоплаченный счёт", "special": "invoice",
     "hint": "Уходит примерно через 10 минут после счёта. Пауза на карточке здесь не используется. Не тратит дневной лимит. Кнопка «Продолжить оплату счёта» открывает этот счёт."},
    {"id": "balance_low", "label": "Баланс заканчивается", "special": "balance",
     "hint": "За 3 дня до конца (тем, кто уже платил) и когда осталось меньше суток — по разу, пока баланс снова не вырастет. Приходит и тем, кто выключил напоминания. Пауза на карточке здесь не используется. К тексту добавляется остаток и на сколько его хватит. Не тратит дневной лимит."},
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
        AND NOT EXISTS (SELECT 1 FROM pay_orders o WHERE o.telegram_id = u.telegram_id AND o.status = 'granted')
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
)
from app.recovery_funnel import CONDITIONS as RECOVERY_CONDITIONS
from app.referral_followup import CONDITION as REFERRAL_FOLLOWUP_CONDITION
from app.referral_followup import (EXTRA_CONDITIONS as REFERRAL_EXTRA, EXTRA_CYCLE as REFERRAL_CYCLE,
                                   EXTRA_KINDS as REFERRAL_KINDS)
from app.extra_journeys import CONDITIONS as EXTRA_CONDITIONS, CYCLE as EXTRA_CYCLE, KINDS as EXTRA_KINDS
CONDITIONS = CONDITIONS + RECOVERY_CONDITIONS + (REFERRAL_FOLLOWUP_CONDITION,) + REFERRAL_EXTRA + EXTRA_CONDITIONS
CONDITION_IDS = {row["id"]: row for row in CONDITIONS}
SPECIAL_ONCE = {"unpaid_invoice", "balance_low"}
# Removed features: boards saved earlier may still name them, so they are dropped on load.
RETIRED_CONDITIONS = {"winback", "ambassador_earn", "ambassador_active"}
RETIRED_ACTIONS = {"ambassador"}


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


RETURN_BONUS_STEP = "recovery-recover-topup-4"


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
        emoji = str(item.get("emoji") or "").strip()
        if emoji:
            if not re.fullmatch(r"[0-9]{1,30}", emoji):
                raise ValueError("Выберите эмодзи из набора Telegram")
            button["emoji"] = emoji
        if action == "url":
            url = str(item.get("url") or "").strip()
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or len(url) > 2048:
                raise ValueError("Для ссылки нужен полный HTTPS-адрес")
            button["url"] = url
        clean.append(button)
    return clean


def markup(button_ids: list[str], telegram_id: int, token: str | None = None, gift_id: int | None = None,
           promise: bool = False, gift_days: int | None = None, bonus: tuple[int, int] | None = None):
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    from app.config import get_settings
    from app.keyboards import invite_copy_text, mini_app_url, referral_share_button

    def emoji_id(item) -> str | None:
        if not isinstance(item, dict):
            return None
        value = str(item.get("emoji") or "").strip()
        return value or None

    def press(label: str, item, **kwargs):
        return InlineKeyboardButton(text=label, icon_custom_emoji_id=emoji_id(item), **kwargs)

    def screen(label: str, name: str | None, item, **params):
        url = mini_app_url()
        if not url:
            return press(label, item, callback_data="help:connect")
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        if name:
            query["screen"] = name
        query.update({k: str(v) for k, v in params.items()})
        return press(
            label, item, style="success" if name in {None, "gift", "connect", "topup"} else None,
            web_app=WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query)))),
        )

    ids = {item if isinstance(item, str) else item["action"] for item in button_ids}
    if {"feedback_ok", "feedback_help"}.issubset(ids) and "feedback_terms" not in ids:
        button_ids = [*button_ids, "feedback_terms"]
    rows = []
    for item in button_ids:
        action_id = item if isinstance(item, str) else item["action"]
        label = _button(action_id)["button"] if isinstance(item, str) else item["text"]
        if action_id == "url":
            rows.append([press(label, item, url=item["url"])])
            continue
        if action_id == "cabinet":
            rows.append([screen(label, None, item)])
        elif action_id == "gift":
            rows.append([screen(label, "gift", item)])
        elif action_id == "connect":
            rows.append([screen(label, "connect", item)])
        elif action_id == "topup":
            if bonus:
                # The person can still get «+N% к первому пополнению»: the button opens the top-up on the threshold.
                rows.append([screen(f"🎁 Пополнить {bonus[0]} ₽ · +{bonus[1]}%", "topup", item, amount=bonus[0])])
            else:
                rows.append([screen(label, "topup", item)])
        elif action_id == "topup_quick":
            # Two ready amounts side by side; the cabinet opens on the top-up with it chosen (card, SBP, Stars).
            if bonus:
                # «+3 дня за первую оплату» is on: the second button is the bonus amount.
                low, (need, pct) = quick_amounts()[0], bonus
                rows.append([screen(f"Пополнить {low} ₽", "topup", item, amount=low)] if low < need else [])
                rows[-1].append(screen(f"🎁 {need} ₽ · +{pct}%", "topup", item, amount=need))
            else:
                rows.append([screen(f"Пополнить {amount} ₽", "topup", item, amount=amount) for amount in quick_amounts()])
        elif action_id == "topup_return":
            # «Возвращайтесь с бонусом»: the threshold and the next step up, each showing what lands on the balance.
            from app import return_bonus
            t = return_bonus.terms()
            if t:
                need, pct, _days = t
                step = max(1, int(get_settings().balance_topup_step or 50))
                amounts = [need, -(-(need + 100) // step) * step]
                rows.append([screen(f"{a} ₽ → {a + return_bonus.bonus_rub(a, pct)} ₽", "topup", item, amount=a) for a in amounts])
            rows.append([screen(label, "topup", item)])
        elif action_id == "help":
            rows.append([press(label, item, callback_data="help:connect")])
        elif action_id == "welcome":
            rows.append([press(label, item, callback_data="welcome:continue")])
        elif action_id == "channel":
            url = (get_settings().required_channel_url or "").strip()
            if url:
                rows.append([press(label, item, url=url)])
            if isinstance(item, str) and get_settings().required_channel_enabled:
                rows.append([InlineKeyboardButton(text="Проверить подписку", callback_data="check_sub")])
        elif action_id == "feedback_ok":
            rows.append([press(label, item, callback_data="vpn_feedback:ok")])
        elif action_id == "feedback_help":
            rows.append([press(label, item, callback_data="vpn_feedback:help")])
        elif action_id == "feedback_terms":
            rows.append([press(label, item, callback_data="vpn_feedback:terms")])
        elif action_id == "feedback_later":
            rows.append([press(label, item, callback_data="vpn_feedback:later")])
        elif action_id == "share":
            button = referral_share_button(int(telegram_id))
            rows.append([button.model_copy(update={
                "text": label,
                "icon_custom_emoji_id": emoji_id(item) or button.icon_custom_emoji_id,
            })])
        elif action_id == "copy":
            username = get_settings().bot_username
            rows.append([press(
                label, item, copy_text=CopyTextButton(text=invite_copy_text(int(telegram_id), username)),
            )])
        elif action_id == "resume_pay":
            if token:
                rows.append([press(label, item, callback_data=f"resume_pay:{token}")])
            else:
                rows.append([screen(label, "topup", item)])
        elif action_id in {"about", "invite"}:
            rows.append([press(label, item, callback_data="about_service" if action_id == "about" else "share")])
        elif action_id == "menu":
            rows.append([press(label, item, callback_data="profile")])
        elif action_id == "promise":
            # Shown only to people who can take a promised payment right now (see trust.promise_available).
            if promise and mini_app_url():
                rows.append([screen(label, "promise", item)])
        elif action_id == GIFT_ACTION:
            # Without an issued gift (preview, cooldown) the button would promise nothing: leave it out.
            if gift_id:
                if gift_days and isinstance(item, str):
                    label = f"🎁 Забрать {gift_label(gift_days)}"
                rows.append([press(label, item, callback_data=f"fgift:{int(gift_id)}", style="success")])
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def with_first_bonus(body: str, bonus: tuple[int, int] | None) -> str:
    """Fills {bonus_min}, {bonus_pct}, {bonus_total} when the text names them, otherwise adds the bonus line."""
    if not bonus:
        return body
    need, pct = bonus
    if "{bonus_" in body:
        return (body.replace("{bonus_min}", f"{need} ₽").replace("{bonus_pct}", str(pct))
                .replace("{bonus_total}", f"{need + need * pct // 100} ₽"))
    return body + f"\n\n🎁 Пополните от {need} ₽ до конца подарка — и получите +{pct}% к сумме на баланс."


async def first_bonus_for(uid: int, buttons) -> tuple[int, int] | None:
    """(threshold, percent) when this person can still get «+N% к первому пополнению» and the step offers a top-up."""
    if not any((b if isinstance(b, str) else b.get("action")) in {"topup_quick", "topup"} for b in buttons):
        return None
    from app import db, first_bonus
    from app.config import get_settings
    local = await db.get_user(uid)
    if not first_bonus.eligible(local) or int((local or {}).get("balance_rub") or 0) <= 0:
        return None
    s = get_settings()
    return int(s.first_bonus_min_rub), int(s.first_bonus_percent)


def quick_amounts() -> list[int]:
    """The minimum top-up and about a month for one device, rounded up to the top-up step: 50 and 200 ₽ at 6 ₽/day."""
    from app.config import get_settings
    s = get_settings()
    low = max(1, int(s.balance_topup_min or 50))
    step = max(1, int(s.balance_topup_step or 50))
    month = -(-max(1, int(s.vpn_day_price_rub or 1)) * 30 // step) * step
    month = min(max(month, low), int(s.balance_topup_max or month))
    return [low] if month <= low else [low, month]


def render_text(text: str, telegram_id: int, first_name: str | None, *, gift_days: int | None = None) -> str:
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
        "reward": "50 ₽",
        "when": when,
        "gift_days": gift_label(gift_days),
        "min_topup": f"{max(1, int(settings.balance_topup_min or 50))} ₽",
        "month": rub_text(max(1, int(settings.vpn_day_price_rub)) * 30),
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
    return {"branches": clean}


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
    from app.notices import notice_text
    from app.nudge import trial_nudge_text

    def tx(key: str, **kwargs) -> str:
        try:
            value = notice_text(key, **kwargs).strip()
        except Exception:
            value = ""
        return value or "Напишите текст сообщения."

    try:
        gift_text = trial_nudge_text("{name}", already_granted=False)
    except Exception:
        gift_text = tx("trial_nudge")
    pay_on = await _flag("payment_nudge", True)
    trial_on = await _flag("trial_nudge", True)
    invite_on = await _flag("invite_nudge", True)
    branches = [
        {"id": "invoice", "title": "Неоплаченный счёт", "steps": [
            _step("pay-1", "unpaid_invoice", 0, tx("payment_nudge"), ["resume_pay", "menu"], enabled=pay_on),
        ]},
        {"id": "balance", "title": "Баланс заканчивается", "steps": [
            _step("balance-1", "balance_low", 0, tx("balance_ending_nudge"), ["topup_quick", "menu"]),
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
    from app.referral_followup import extra_steps
    invite_second, referral_branches = extra_steps(_step)
    branches.extend([
        {"id": "friends", "title": "Пригласить друга", "steps": [
            _step("invite-1", "invite", 48, tx("invite_nudge"), ["share", "copy", "menu"], enabled=invite_on),
            {**invite_second, "enabled": invite_on},
        ]},
        {"id": "gift", "title": "Подарок не забран", "steps": [
            _step("trial-1", "trial", 24, gift_text, ["gift", "help"], enabled=trial_on),
        ]},
        *[{**b, "steps": [{**st, "enabled": invite_on} for st in b["steps"]]} for b in referral_branches],
    ])
    from app.recovery_funnel import upgrade
    from app.referral_followup import upgrade as upgrade_referrals
    from app.extra_journeys import upgrade as upgrade_extra
    return validate(upgrade_extra(upgrade_referrals(upgrade({"branches": branches}))))


async def _ensure_tables() -> None:
    from app.db import _pool_req
    await _pool_req().execute("""
        CREATE TABLE IF NOT EXISTS funnel_step_sends (
            telegram_id BIGINT NOT NULL,
            step_id TEXT NOT NULL,
            sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (telegram_id, step_id)
        )
    """)


def _kept_button(button) -> bool:
    action = button if isinstance(button, str) else button.get("action") if isinstance(button, dict) else None
    return action not in RETIRED_ACTIONS


def without_retired_branches(graph):
    """Drop steps and buttons of removed features, so boards saved before the removal still load."""
    graph = json.loads(json.dumps(graph))
    if not isinstance(graph, dict) or not isinstance(graph.get('branches'), list):
        return graph
    for branch in graph['branches']:
        if not isinstance(branch, dict) or not isinstance(branch.get('steps'), list):
            continue
        branch['steps'] = [s for s in branch['steps'] if not isinstance(s, dict) or s.get('condition') not in RETIRED_CONDITIONS]
        for step in branch['steps']:
            if isinstance(step, dict):
                step['buttons'] = [button for button in step.get('buttons') or [] if _kept_button(button)]
    graph['branches'] = [b for b in graph['branches'] if not isinstance(b, dict) or b.get('steps')]
    return graph


_unburned = False


async def _unburn_gift_steps(graph) -> None:
    """Once: gift steps used to be marked as sent without a message when a recent gift (often the «+3 дня всем»
    broadcast) blocked the offer, so those people never got it. Forget such marks: no message logged for the step,
    and not an A/B control group (that one is skipped on purpose)."""
    global _unburned
    if _unburned:
        return
    from app.db import _pool_req, get_kv, set_kv
    if await get_kv("funnel_gift_unburn_v1"):
        _unburned = True
        return
    ids = [s["id"] for b in graph["branches"] for s in b["steps"]
           if any((x if isinstance(x, str) else x.get("action")) == GIFT_ACTION for x in s["buttons"])]
    if ids:
        result = await _pool_req().execute(
            """DELETE FROM funnel_step_sends s
               WHERE s.step_id = ANY($1::text[])
                 AND NOT EXISTS (SELECT 1 FROM message_log m WHERE m.telegram_id = s.telegram_id
                     AND m.status = 'sent' AND m.extra->>'step_id' = s.step_id)
                 AND NOT EXISTS (SELECT 1 FROM funnel_experiment_users eu
                     JOIN funnel_experiments e ON e.id = eu.experiment_id
                     WHERE eu.telegram_id = s.telegram_id AND e.step_id = s.step_id AND eu.arm = 'control')""",
            ids)
        logger.info("Воронка: вернули шаги с подарком, отмеченные без сообщения: %s", result)
    await set_kv("funnel_gift_unburn_v1", "1")
    _unburned = True


async def load() -> dict:
    """The journeys built into the code. The admin-panel editor is gone, so an old saved copy is not read."""
    await _ensure_tables()
    graph = without_retired_branches(await default_graph())
    try:
        await _unburn_gift_steps(graph)
    except Exception:
        logger.exception("Воронка: не удалось вернуть шаги с подарком")
    return graph


async def _gate(condition: str) -> bool:
    if condition in RETIRED_CONDITIONS:
        return False
    spec = CONDITION_IDS[condition]
    gate = spec.get("gate")
    if gate == "trial":
        from app.config import get_settings
        return bool(get_settings().trial_enabled)
    if gate == "referral":
        from app.config import get_settings
        return bool(get_settings().referral_program_enabled)
    return True


def is_setup_assist(step, prev_id):
    return not prev_id and step['condition'] in {'recover_setup','recover_online'} and step.get('wait_from') == 'anchor'


async def _due(step: dict, prev_id: str | None, limit: int, skip: list[int], *, after_id: int = 0) -> list[dict]:
    from app.config import get_settings
    from app.db import _pool_req, _ACCESS_EXHAUSTED
    spec = CONDITION_IDS[step["condition"]]
    if spec.get("special"):
        return []
    price = max(1, int(get_settings().vpn_day_price_rub)) * 3
    where = spec["where"].replace("{price}", str(price)).replace("{day}", str(max(1, int(get_settings().vpn_day_price_rub))))
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
    if step['condition'] in {'recover_idle', 'recover_online', 'recover_late', 'recover_topup', *EXTRA_CYCLE, *REFERRAL_CYCLE}:
        cycle_anchor = SEEN if step['condition'] in {'recover_idle', 'recover_late'} else anchor
        cycle_clause = f" AND s.sent_at >= {cycle_anchor}"
        time_sql = time_sql.replace("p.step_id = $5", f"p.step_id = $5 AND p.sent_at >= {cycle_anchor}")
    args = [int(limit), [int(item) for item in skip], step["id"], hours]
    if prev:
        args.append(prev)
    base_where = BASE_WHERE
    if step["condition"] == "terms_offer":
        base_where = base_where.replace("NOT IN ('help','terms')", "<> 'help'")
    rows = await _pool_req().fetch(
        f"""SELECT u.telegram_id, u.first_name
            FROM users u
            WHERE {base_where}
              AND {where}
              AND {time_sql}
              AND NOT EXISTS (
                  SELECT 1 FROM funnel_step_sends s
                  WHERE s.telegram_id = u.telegram_id AND s.step_id = $3 {cycle_clause}
              )
              AND u.telegram_id > {int(after_id)}
              AND NOT (u.telegram_id = ANY($2::bigint[]))
            ORDER BY u.telegram_id
            LIMIT $1""",
        *args,
    )
    return [dict(row) for row in rows]


async def _candidates(step, prev_id, skip, touched):
    # Bound work per tick, but continue past throttled users on the next tick.
    key = step['id']
    for _ in range(SCAN_PAGES):
        rows = await _due(step, prev_id, STEP_LIMIT, skip + touched,
                          after_id=_scan_cursors.get(key, 0))
        if not rows:
            _scan_cursors.pop(key, None)
            return
        for row in rows:
            _scan_cursors[key] = int(row['telegram_id'])
            yield row
        if len(rows) < STEP_LIMIT:
            _scan_cursors.pop(key, None)
            return


async def _send_step(bot, step: dict, prev_id: str | None, skip: list[int]) -> tuple[int, list[int]]:
    from app import db
    from app.nudge import _deliver_unbudgeted
    sent = 0
    touched: list[int] = []
    if not await _gate(step["condition"]):
        return 0, touched
    from app.recovery_funnel import KINDS
    kind = "nudge_setup_assist" if is_setup_assist(step, prev_id) else (
        KINDS.get(step["condition"]) or REFERRAL_KINDS.get(step["condition"])
        or EXTRA_KINDS.get(step["condition"], "nudge_board"))
    from app import funnel_gifts
    wants_gift = any((b if isinstance(b, str) else b.get("action")) == GIFT_ACTION for b in step["buttons"])
    wants_promise = any((b if isinstance(b, str) else b.get("action")) == "promise" for b in step["buttons"])
    from app import experiments
    try:
        exp = (await experiments.running()).get(step["id"])
    except Exception:
        logger.exception("Тесты сообщений не прочитались")
        exp = None
    async for row in _candidates(step, prev_id, skip, touched):
        uid = int(row["telegram_id"])
        if wants_gift and not await funnel_gifts.can_issue(uid):
            # A gift went out recently: do not promise another one now. The step waits for the cooldown to end
            # (and is dropped by its own conditions if the person comes back meanwhile), it is not marked as sent.
            touched.append(uid)
            continue
        slot = await (db.reserve_setup_assistance(uid) if kind == "nudge_setup_assist" else db.reserve_optional_message(uid, kind))
        if slot is None:
            touched.append(uid)
            continue
        arm = "a"
        if exp:
            try:
                arm = await experiments.assign(exp, uid)
            except Exception:
                logger.exception("Не удалось распределить в тест %s", uid)
        if arm == "control":
            # The control group gets nothing; the journey goes on as if the step was sent.
            await db.finish_optional_message(slot, False)
            await db._pool_req().execute(
                """INSERT INTO funnel_step_sends (telegram_id, step_id) VALUES ($1, $2)
                   ON CONFLICT (telegram_id,step_id) DO UPDATE SET sent_at=NOW()""", uid, step["id"])
            touched.append(uid)
            continue
        text, gift_days = experiments.variant(step, exp, arm)
        delivered = False
        gift_id = None
        try:
            if wants_gift:
                gift_id = await funnel_gifts.issue(uid, step["id"], days=gift_days)
                if gift_id is None:
                    continue
            body = render_text(text, uid, row.get('first_name'), gift_days=gift_days)
            promise = False
            if wants_promise:
                from app.trust import promise_available
                promise = await promise_available(uid)
            buttons = step['buttons']
            if step['condition'] == 'recover_idle':
                funded = await db.has_funded_access(uid)
                body += "\n\n" + ("Доступ ещё действует — можно включить VPN." if funded else "Доступ закончился. В кабинете можно пополнить баланс и вернуться к VPN.")
                buttons = [(
                    {'action':'connect' if funded else 'topup','text':'Подключить VPN' if funded else 'Пополнить баланс', **({'emoji': b['emoji']} if isinstance(b, dict) and b.get('emoji') else {})}
                    if (b if isinstance(b, str) else b.get('action')) in {'cabinet','connect','topup'} else b
                ) for b in buttons]
            if step["id"] == RETURN_BONUS_STEP:
                from app import return_bonus
                filled = return_bonus.fill(body)
                if filled is None:
                    continue  # the bonus is off: the step has nothing to offer
                body = filled
            bonus = await first_bonus_for(uid, buttons)
            if step["condition"] == "first_bonus" and not bonus:
                continue  # the bonus is off or no longer applies: the step has nothing to say
            body = with_first_bonus(body, bonus)
            delivered = await _deliver_unbudgeted(
                bot, kind=kind, telegram_id=uid, first_name=row.get("first_name"),
                title=CONDITION_IDS[step["condition"]]["label"],
                body=body,
                reply_markup=markup(buttons, uid, gift_id=gift_id, promise=promise, gift_days=gift_days, bonus=bonus), preserve=True,
                extra={"step_id": step["id"], **({"gift_id": gift_id} if gift_id else {})},
            )
        except Exception:
            logger.exception("Шаг воронки %s не ушёл %s", step["id"], uid)
        finally:
            await db.finish_optional_message(slot, delivered)
            if gift_id and not delivered:
                await funnel_gifts.cancel(gift_id)
        touched.append(uid)
        if not delivered:
            continue
        if exp:
            await experiments.mark_delivered(exp, uid)
        await db._pool_req().execute(
            """INSERT INTO funnel_step_sends (telegram_id, step_id)
               VALUES ($1, $2) ON CONFLICT (telegram_id,step_id) DO UPDATE SET sent_at=NOW()""",
            uid, step["id"],
        )
        if step["condition"] == "terms_offer":
            # The offer answered «условия не подошли»: let the regular funnel speak to this person again.
            await db._pool_req().execute(
                "UPDATE users SET vpn_feedback=NULL WHERE telegram_id=$1 AND vpn_feedback='terms'", uid)
        sent += 1
        if sent >= STEP_LIMIT:
            break
    return sent, touched


async def send_due(bot, rp=None, skip_ids: list[int] | None = None,
                   optional_skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    """skip_ids: never write to them this run. optional_skip_ids: muted for reminders (quiet mode, «не нужен»),
    but still told that their paid balance is running out."""
    from app import db
    from app import nudge
    if await db.flag_on("maintenance"):
        return 0, []
    try:
        graph = await load()
    except Exception:
        logger.exception("Доска воронки не прочиталась")
        return 0, []
    hard_skip = [int(item) for item in (skip_ids or [])]
    skip = hard_skip + [int(item) for item in (optional_skip_ids or [])]
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
    # Balance warnings are about money already paid: only the hard skips and people written to this run.
    if balance and balance["enabled"] and sent < RUN_LIMIT:
        count, ids = await nudge.send_due_trial_end_nudges(
            bot, hard_skip + touched, body=balance["text"], button_ids=balance["buttons"],
        )
        sent += count
        touched.extend(ids)
        skip.extend(ids)
    # Reminders and offers wait for daytime in Moscow; the money warnings above go out any time.
    if not reminder_hours():
        return sent, touched
    terms_ids = set(await db.terms_feedback_ids())
    marketing = await db.marketing_suppressed_ids()
    skip.extend(marketing)
    skip.extend(await db.nudge_suppressed_ids(hours=24))
    # People who only answered «условия не подошли» stay reachable for the terms offer;
    # its slot reservation still applies the daily and weekly caps.
    for branch in graph["branches"]:
        prev = None
        enabled = [step for step in branch["steps"] if step["enabled"]]
        for step in enabled:
            if sent >= RUN_LIMIT:
                return sent, touched
            spec = CONDITION_IDS[step["condition"]]
            if not spec.get("special") and not is_setup_assist(step, prev):
                count, ids = await _send_step(bot, step, prev, _terms_skip(skip, terms_ids, touched) if step["condition"] == "terms_offer" else skip)
                sent += count
                touched.extend(ids)
                skip.extend(ids)
            if not spec.get("special"):
                prev = step["id"]
    return sent, touched


REMINDER_HOURS_MSK = (10, 21)
_MSK = timezone(timedelta(hours=3))  # Moscow has no daylight saving time.


def reminder_hours(now: datetime | None = None) -> bool:
    """10:00–21:00 by Moscow time: the window for reminders and offers."""
    start, end = REMINDER_HOURS_MSK
    hour = (now or datetime.now(timezone.utc)).astimezone(_MSK).hour
    return start <= hour < end


def _terms_skip(skip: list[int], terms_ids: set[int], touched: list[int]) -> list[int]:
    done = set(touched)
    return [uid for uid in skip if uid not in terms_ids or uid in done]


def _first(graph: dict, condition: str) -> dict | None:
    for branch in graph["branches"]:
        for step in branch["steps"]:
            if step["condition"] == condition:
                return step
    return None
