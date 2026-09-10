from __future__ import annotations

from typing import Any

from app.config import shop_overlay

DEFAULT_NOTICES: dict[str, str] = {
    "welcome": (
        "Добро пожаловать в <b>{brand}</b>.\n\n"
        "Чтобы пользоваться ботом, подпишитесь на канал и нажмите «Проверить подписку»."
    ),
    "welcome_intro_hi": (
        "Привет, {name}.\n\n"
        "Вот вам {days} бесплатно."
    ),
    "welcome_intro_hi_plain": "Привет, {name}.",
    "welcome_intro_hello": (
        "Это <b>{brand}</b>. Держим YouTube, Instagram и всё, что без VPN не открывается. "
        "Без резких обрывов и без возни с настройками."
    ),
    "welcome_intro_try": (
        "Давай попробуем: {days} уже на балансе.\n\n"
        "Открой кабинет, добавь устройство — займёт минуту. "
        "Пока VPN не включится, ничего не спишется."
    ),
    "welcome_intro_try_no_trial": (
        "Открой кабинет и добавь устройство — займёт минуту. "
        "Дальше всё из приложения, без переписки с ботом."
    ),
    "welcome_intro_channel": (
        "Чтобы начать, подпишись на канал и нажми «Проверить подписку». "
        "Дальше сразу откроем кабинет."
    ),
    "welcome_intro_legal": (
        "Остался один тап: оферта и политика. Документы по ссылкам ниже."
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
        "{when}\n\n"
        "Ваша ссылка:\n{link}"
    ),
    "broadcast_invite": (
        "Вы пользуетесь VPN. Пригласите друзей и получите баланс.\n\n"
        "За каждого, кто придёт по вашей ссылке, начислим {reward}.\n\n"
        "Ваша ссылка:\n{link}"
    ),
    "broadcast_unused": (
        "Вы так и не воспользовались VPN.\n\n"
        "Может, дадите нам шанс? Откройте кабинет и добавьте устройство. "
        "Пока устройств нет, баланс не списывается."
    ),
    "info_nudge": (
        "Как устроен кабинет.\n\n"
        "Сутки VPN списываются только с добавленных устройств, по {price} за каждое в день. "
        "Пока устройств нет, баланс не тратится.\n\n"
        "Кабинет всегда можно открыть из бота, даже если VPN вдруг отключится."
        "{story}"
    ),
    "story_nudge": (
        "VPN уже работает. Выложите историю в Telegram — за это начислим {amount} на баланс.\n\n"
        "Кнопка откроет кабинет, оттуда можно сразу выложить. Награда один раз, после проверки."
    ),
    "first_device_thanks": (
        "Все готово. Спасибо, что решили попробовать.\n\n"
        "Если что-то не заработает — напишите в поддержку из кабинета."
    ),
    "first_online_nudge": (
        "VPN уже работал. Всё ли в порядке?\n\n"
        "Если да — пополните баланс в кабинете, чтобы не отключилось. "
        "Осталось примерно {days}."
    ),
    "trial_end_nudge": (
        "До отключения примерно сутки. VPN ещё работает.\n\n"
        "Пополните баланс сейчас — потом Telegram может быть недоступен. "
        "Если не успеваете, в кабинете можно взять обещанный платёж."
    ),
    "device_nudge_1": (
        "Вы заглянули к нам, но устройство ещё не создано. "
        "Без него VPN не включится. Откройте кабинет — займёт меньше минуты."
    ),
    "device_nudge_2": (
        "Напоминаем: устройство всё ещё не добавлено. "
        "Пока его нет, VPN не работает, баланс не списывается. "
        "Откройте кабинет и подключитесь."
    ),
    "device_nudge_3": (
        "Последнее напоминание: без устройства VPN не запустится. "
        "Откройте кабинет, когда будете готовы."
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
    "referral_referrer_paid": (
        "<b>Поздравляем</b>\n\n"
        "Друг {name} первый раз оплатил VPN по вашей ссылке.\n"
        "Вам начислено <b>{amount}</b> на баланс. Это реферальные: их можно вывести при накоплении порога."
    ),
    "referral_referrer_paid_days": (
        "<b>Поздравляем</b>\n\n"
        "Друг {name} первый раз оплатил VPN по вашей ссылке.\n"
        "Вам начислено <b>{days}</b> подписки.\n\n"
        "Действует до: <b>{expire}</b>{sub_block}"
    ),
    "referral_payout_submitted": (
        "Заявка на вывод <b>{amount}</b> принята. "
        "Администратор переведёт деньги по указанным реквизитам."
    ),
    "referral_payout_paid": "Реферальные <b>{amount}</b> выплачены.",
    "referral_payout_rejected": (
        "Заявку на вывод <b>{amount}</b> отклонили. Сумма вернулась на баланс."
    ),
    "referral_clawback": (
        "Друг {name} заблокировал бота и не взял бесплатный период. "
        "С баланса списано <b>{amount}</b>."
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
    {"key": "welcome", "title": "Приветствие: нет подписки на канал", "hint": "{brand}"},
    {"key": "welcome_intro_hi", "title": "Первый запуск: привет", "hint": "{name} {days}"},
    {"key": "welcome_intro_hi_plain", "title": "Первый запуск: привет без триала", "hint": "{name}"},
    {"key": "welcome_intro_hello", "title": "Первый запуск: кто мы", "hint": "{brand}"},
    {"key": "welcome_intro_try", "title": "Первый запуск: попробуй", "hint": "{days}"},
    {"key": "welcome_intro_try_no_trial", "title": "Первый запуск: попробуй без триала", "hint": ""},
    {"key": "welcome_intro_channel", "title": "Первый запуск: подписка на канал", "hint": ""},
    {"key": "welcome_intro_legal", "title": "Первый запуск: оферта", "hint": ""},
    {"key": "legal", "title": "Оферта и политика", "hint": ""},
    {"key": "profile_balance", "title": "Профиль (режим баланса)", "hint": "{name} {balance} {price}"},
    {"key": "profile_days", "title": "Профиль (режим подписки)", "hint": "{name}"},
    {"key": "low_balance", "title": "Не хватает денег на сутки", "hint": "{price}"},
    {"key": "cabinet_link", "title": "Ссылка на кабинет без VPN", "hint": "{url}"},
    {"key": "trust_collect", "title": "Списание обещанного платежа", "hint": "{amount}"},
    {"key": "trial_nudge", "title": "Напоминание взять триал", "hint": "{name} {extra}"},
    {"key": "invite_nudge", "title": "Пригласить друга", "hint": "{name} {reward} {when} {link}"},
    {"key": "broadcast_invite", "title": "Рассылка: пользуются VPN", "hint": "{reward} {link}"},
    {"key": "broadcast_unused", "title": "Рассылка: не подключались", "hint": ""},
    {"key": "info_nudge", "title": "Как устроен кабинет", "hint": "{price} {story}"},
    {"key": "story_nudge", "title": "Выложить историю", "hint": "{amount}"},
    {"key": "first_device_thanks", "title": "После первого устройства", "hint": ""},
    {"key": "first_online_nudge", "title": "После первого онлайна", "hint": "{days}"},
    {"key": "trial_end_nudge", "title": "За сутки до отключения (триал)", "hint": ""},
    {"key": "device_nudge_1", "title": "Нет устройства: 30 минут", "hint": ""},
    {"key": "device_nudge_2", "title": "Нет устройства: сутки после первого", "hint": ""},
    {"key": "device_nudge_3", "title": "Нет устройства: ещё сутки", "hint": ""},
    {"key": "referral_referrer_balance", "title": "Реферал: пригласившему (триал)", "hint": "{name} {amount}"},
    {"key": "referral_invitee_balance", "title": "Реферал: другу (триал)", "hint": "{amount}"},
    {"key": "referral_referrer_days", "title": "Реферал: пригласившему дни (триал)", "hint": "{name} {days} {expire} {sub_block}"},
    {"key": "referral_referrer_paid", "title": "Реферал: пригласившему (оплата)", "hint": "{name} {amount}"},
    {"key": "referral_referrer_paid_days", "title": "Реферал: пригласившему дни (оплата)", "hint": "{name} {days} {expire} {sub_block}"},
    {"key": "referral_payout_submitted", "title": "Реферал: заявка на вывод", "hint": "{amount}"},
    {"key": "referral_payout_paid", "title": "Реферал: выплата прошла", "hint": "{amount}"},
    {"key": "referral_payout_rejected", "title": "Реферал: выплата отклонена", "hint": "{amount}"},
    {"key": "referral_clawback", "title": "Реферал: возврат за блок бота", "hint": "{name} {amount}"},
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
