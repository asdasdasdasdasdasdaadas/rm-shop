from __future__ import annotations

from typing import Any

from app.config import shop_overlay

DEFAULT_NOTICES: dict[str, str] = {
    "welcome": (
        "Добро пожаловать в <b>{brand}</b>.\n\n"
        "Чтобы пользоваться ботом, подпишитесь на канал и нажмите «Проверить подписку»."
    ),
    "legal": (
        "Перед использованием примите оферту и политику конфиденциальности. "
        "Документы открываются по ссылкам ниже."
    ),
    "profile_balance": (
        "Привет, {name}.\n\n"
        "Баланс: <b>{balance}</b>\n"
        "Сутки VPN на одно устройство: <b>{price}</b>\n\n"
        "Чтобы включить VPN, нажмите «Открыть кабинет» внизу и добавьте устройство. "
        "Пока устройств нет, баланс не списывается."
    ),
    "profile_days": (
        "Привет, {name}.\n"
        "Выберите действие. Кабинет внизу — там подписка и подключение."
    ),
    "low_balance": (
        "На балансе не хватает средств на сутки VPN. "
        "Стоимость: {price} за устройство в день. "
        "Пополните баланс."
    ),
    "cabinet_link": (
        "Баланса хватит меньше чем на двое суток. "
        "Если VPN отключится, Telegram может быть недоступен.\n\n"
        "Кабинет из браузера, без VPN. Ссылка действует 10 дней:\n"
        "{url}"
    ),
    "trust_collect": (
        "Списан обещанный платёж: {amount}. "
        "Если баланс ушёл в минус, пополните его."
    ),
    "trial_nudge": (
        "{name}, вы запустили бота, но ещё не пробовали VPN.\n\n"
        "Давайте попробуем: {extra} "
        "Если не зайдёт — просто не продлевайте."
    ),
    "invite_nudge": (
        "{name}, за друга можно получить {reward}.\n\n"
        "Когда человек перейдёт по вашей ссылке и нажмёт «Попробовать бесплатно», "
        "бонус придёт вам обоим.\n\n"
        "Ваша ссылка:\n{link}"
    ),
    "info_nudge": (
        "Как устроен кабинет.\n\n"
        "Сутки VPN списываются только с добавленных устройств, по {price} за каждое в день. "
        "Пока устройств нет, баланс не тратится.\n\n"
        "Кабинет всегда можно открыть из бота, даже если VPN вдруг отключится."
        "{story}"
    ),
    "referral_referrer_balance": (
        "<b>Поздравляем</b>\n\n"
        "Друг {name} попробовал VPN бесплатно по вашей ссылке.\n"
        "Вам начислено <b>{amount}</b> на баланс."
    ),
    "referral_invitee_balance": "За переход по ссылке на баланс начислено <b>{amount}</b>",
    "referral_referrer_days": (
        "<b>Поздравляем</b>\n\n"
        "Друг {name} попробовал VPN бесплатно по вашей ссылке.\n"
        "Вам начислено <b>{days}</b> подписки.\n\n"
        "Действует до: <b>{expire}</b>{sub_block}"
    ),
    "topup_ok": "Баланс пополнен на {amount}.",
    "subscription_issued": (
        "<b>{title}</b>\n\n"
        "Действует до: <b>{expire}</b>{sub_block}"
    ),
    "sub_reissued": (
        "Ссылка подписки обновлена. Старая больше не работает.\n\n"
        "Откройте кабинет и заново добавьте подписку в приложение.{links}"
    ),
    "blocked": "Доступ ограничен. Если это ошибка, напишите в поддержку.",
    "payment_unknown": "Платёж получен, но тариф неизвестен. Напишите в поддержку.",
    "payment_duplicate": "Этот платёж уже обработан.",
    "payment_panel_error": "Оплата прошла, но панель не ответила: {error}\nНапишите в поддержку.",
}

NOTICE_FIELDS: list[dict[str, str]] = [
    {"key": "welcome", "title": "Приветствие", "hint": "{brand}"},
    {"key": "legal", "title": "Оферта и политика", "hint": ""},
    {"key": "profile_balance", "title": "Профиль (режим баланса)", "hint": "{name} {balance} {price}"},
    {"key": "profile_days", "title": "Профиль (режим подписки)", "hint": "{name}"},
    {"key": "low_balance", "title": "Не хватает денег на сутки", "hint": "{price}"},
    {"key": "cabinet_link", "title": "Ссылка на кабинет без VPN", "hint": "{url}"},
    {"key": "trust_collect", "title": "Списание обещанного платежа", "hint": "{amount}"},
    {"key": "trial_nudge", "title": "Напоминание взять триал", "hint": "{name} {extra}"},
    {"key": "invite_nudge", "title": "Пригласить друга", "hint": "{name} {reward} {link}"},
    {"key": "info_nudge", "title": "Как устроен кабинет", "hint": "{price} {story}"},
    {"key": "referral_referrer_balance", "title": "Реферал: пригласившему (баланс)", "hint": "{name} {amount}"},
    {"key": "referral_invitee_balance", "title": "Реферал: другу (баланс)", "hint": "{amount}"},
    {"key": "referral_referrer_days", "title": "Реферал: пригласившему (дни)", "hint": "{name} {days} {expire} {sub_block}"},
    {"key": "topup_ok", "title": "Баланс пополнен", "hint": "{amount}"},
    {"key": "subscription_issued", "title": "Подписка оформлена", "hint": "{title} {expire} {sub_block}"},
    {"key": "sub_reissued", "title": "Ссылка подписки перевыпущена", "hint": "{links}"},
    {"key": "blocked", "title": "Пользователь заблокирован", "hint": ""},
    {"key": "payment_unknown", "title": "Оплата: неизвестный тариф", "hint": ""},
    {"key": "payment_duplicate", "title": "Оплата: повтор", "hint": ""},
    {"key": "payment_panel_error", "title": "Оплата: панель не ответила", "hint": "{error}"},
]


class _SafeMap(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def public_notices() -> dict[str, str]:
    raw = shop_overlay().get("notices")
    overlay = raw if isinstance(raw, dict) else {}
    out: dict[str, str] = {}
    for key, default in DEFAULT_NOTICES.items():
        val = overlay.get(key)
        text = str(val).strip() if isinstance(val, str) else ""
        out[key] = text or default
    return out


def notice_text(key: str, **kwargs: Any) -> str:
    tpl = public_notices().get(key) or DEFAULT_NOTICES.get(key) or ""
    data = {k: "" if v is None else v for k, v in kwargs.items()}
    try:
        return tpl.format_map(_SafeMap(data))
    except Exception:
        return tpl


def validate_notices(raw: Any) -> dict[str, str]:
    src = raw if isinstance(raw, dict) else {}
    out: dict[str, str] = {}
    for key in DEFAULT_NOTICES:
        val = src.get(key)
        text = str(val) if val is not None else ""
        if len(text) > 3500:
            raise ValueError(f"Уведомление «{key}»: слишком длинный текст")
        out[key] = text
    return out


def sub_block(url: str | None) -> str:
    link = (url or "").strip()
    if not link:
        return ""
    return f"\n\nСсылка подписки:\n<code>{link}</code>"
