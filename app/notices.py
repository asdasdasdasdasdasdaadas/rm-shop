from __future__ import annotations

from typing import Any

from app.config import shop_overlay

DEFAULT_NOTICES: dict[str, str] = {
    "welcome": (
        "Добро пожаловать в <b>{brand}</b>.\n\n"
        "Чтобы начать, подпишитесь на канал и нажмите «Проверить подписку»."
    ),
    "welcome_intro_hi": (
        "Здравствуйте, {name}.\n\n"
        "Вот Вам {days} бесплатно."
    ),
    "welcome_intro_hi_plain": "Здравствуйте, {name}.",
    "welcome_intro_hello": (
        "Это <b>{brand}</b>. Добавьте устройство — откроются YouTube, Instagram "
        "и то, что без VPN не грузится."
    ),
    "welcome_intro_try": (
        "Давайте попробуем: {days} уже на балансе.\n\n"
        "Нажмите «Открыть кабинет» и добавьте устройство — займёт минуту. "
        "Пока устройства нет, ничего не спишется."
    ),
    "welcome_intro_try_no_trial": (
        "Нажмите «Открыть кабинет» и добавьте устройство — займёт минуту. "
        "Ссылка, устройства и поддержка будут рядом, без переписки."
    ),
    "welcome_intro_channel": (
        "Чтобы начать, подпишитесь на канал и нажмите «Проверить подписку». "
        "Дальше сразу откроем доступ."
    ),
    "welcome_intro_legal": (
        "Остался один шаг: оферта и политика. Документы по ссылкам ниже."
    ),
    "legal": (
        "Перед использованием примите оферту и политику конфиденциальности. "
        "Документы открываются по ссылкам ниже."
    ),
    "profile_balance": (
        "Здравствуйте, {name}.\n\n"
        "Баланс: <b>{balance}</b>\n"
        "Сутки VPN на одно устройство: <b>{price}</b>\n\n"
        "Чтобы включить VPN, нажмите «Открыть кабинет» и добавьте устройство. "
        "Пока устройств нет, баланс не списывается. "
        "Сюда можно зайти даже если VPN уже не работает."
    ),
    "profile_days": (
        "Здравствуйте, {name}.\n"
        "Выберите действие. Кнопка «Открыть кабинет» внизу — там подписка и подключение."
    ),
    "low_balance": (
        "На балансе не хватает средств на сутки VPN. "
        "Стоимость: {price} за устройство в день. "
        "Пополните баланс."
    ),
    "cabinet_link": (
        "Баланса хватит меньше чем на двое суток. "
        "Если VPN отключится, мессенджер может быть недоступен.\n\n"
        "Запасная ссылка без VPN, действует 10 дней:\n"
        "{url}"
    ),
    "trust_collect": (
        "Списан обещанный платёж: {amount}. "
        "Если баланс ушёл в минус, пополните его."
    ),
    "trial_nudge": (
        "{name}, Вы заглянули к нам, но VPN ещё не пробовали.\n\n"
        "Давайте попробуем: {extra} "
        "Платите только за свои устройства. Если не зайдёт — просто не продлевайте."
    ),
    "invite_nudge": (
        "{name}, за друга можно получить {reward}.\n\n"
        "{when} "
        "Друг подключится по вашей ссылке.\n\n"
        "Ваша ссылка:\n{link}"
    ),
    "broadcast_invite": (
        "Вы уже с нами. Пригласите друзей по своей ссылке.\n\n"
        "За каждого, кто первый раз оплатит по вашей ссылке, начислим {reward}. "
        "Другу за переход эти деньги не даём, после его первой оплаты ему тоже капнет на баланс.\n\n"
        "Ваша ссылка:\n{link}"
    ),
    "broadcast_unused": (
        "Вы так и не воспользовались VPN.\n\n"
        "Нажмите «Открыть кабинет» и добавьте одно устройство. Пока его нет, баланс не списывается."
    ),
    "info_nudge": (
        "Как у нас устроено.\n\n"
        "Сутки VPN списываются только с добавленных устройств, по {price} за каждое в день. "
        "Пока устройств нет, баланс не тратится.\n\n"
        "Сюда всегда можно зайти из бота, даже если VPN вдруг отключится. "
        "Поддержка тоже здесь."
        "{story}"
    ),
    "story_nudge": (
        "VPN уже работает. Если удобно, выложите историю: коротко расскажите, "
        "что подключились у нас. После проверки начислим {amount} на баланс.\n\n"
        "Это один раз. Кнопка ниже откроет редактор — можно сразу добавить картинку и подпись."
    ),
    "first_device_thanks": (
        "Всё готово. Спасибо, что решили попробовать.\n\n"
        "Если держит — удобно остаться: ссылку можно обновить в кабинете, "
        "поддержка тоже там."
    ),
    "first_online_nudge": (
        "VPN уже работал. Всё ли в порядке?\n\n"
        "Если да — пополните баланс, чтобы не отключилось. "
        "Осталось примерно {days}. "
        "Сюда можно зайти из бота даже без VPN.\n\n"
        "Если VPN уже нужен — отправьте ссылку другу. Награда придёт после его первой оплаты."
    ),
    "trial_end_nudge": (
        "До отключения примерно сутки. VPN ещё работает.\n\n"
        "Пополните баланс сейчас — потом мессенджер может быть недоступен. "
        "Если не успеваете, можно взять обещанный платёж.\n\n"
        "Можно также пригласить друга: награда после его первой оплаты."
    ),
    "device_nudge_1": (
        "Вижу — Вы ещё не подключаетесь.\n\n"
        "Давайте разберёмся, какая у Вас проблема?"
    ),
    "device_nudge_2": (
        "Всё ещё не получается подключиться.\n\n"
        "Давайте разберёмся, какая у Вас проблема?"
    ),
    "device_nudge_3": (
        "Последнее напоминание: VPN так и не включился.\n\n"
        "Давайте разберёмся, какая у Вас проблема?"
    ),
    "help_connect_no_device": (
        "Без устройства VPN не включится. Обычно хватает трёх шагов:\n\n"
        "1. Нажмите «Открыть кабинет»\n"
        "2. Добавьте устройство\n"
        "3. Откройте ссылку в Happ или Incy\n\n"
        "Займёт минуту. Если застрянете — напишите, разберёмся."
    ),
    "help_connect_has_device": (
        "Устройство уже есть. Чаще всего помогает заново добавить ссылку в приложение:\n\n"
        "1. Откройте кабинет и то же устройство\n"
        "2. Если ссылка не открывается — обновите её там\n"
        "3. Вставьте в Happ или Incy ещё раз\n\n"
        "Если не поможет — напишите, посмотрим вместе."
    ),
    "help_other": (
        "Обращение открыто. Напишите сюда, что случилось. "
        "Можно прислать скриншот. Ответ придёт в этот чат."
    ),
    "idle_nudge_7": (
        "Неделю VPN не подключался. Если что-то сломалось — напишите в поддержку, разберёмся.\n\n"
        "Сюда можно зайти из бота даже без VPN. Можно пополнить баланс или проверить устройство."
    ),
    "idle_nudge_10": (
        "Уже десять дней без подключения. Если VPN всё ещё нужен, зайдите и проверьте устройство.\n\n"
        "Бот открывается, даже когда сеть недоступна. Ссылку можно обновить в кабинете."
    ),
    "idle_nudge_15": (
        "Пятнадцать дней без онлайна. Мы на месте: баланс, устройства и поддержка.\n\n"
        "Если понадобится снова — зайдите из бота и подключитесь."
    ),
    "idle_nudge_20": (
        "Двадцать дней без подключения. Это последнее напоминание на этой паузе.\n\n"
        "Когда понадобится VPN — зайдите и подключитесь снова."
    ),
    "referral_referrer_balance": (
        "<b>Поздравляем</b>\n\n"
        "Друг {name} первый раз оплатил VPN по вашей ссылке.\n"
        "Вам начислено <b>{amount}</b> на баланс."
    ),
    "referral_invitee_balance": "За переход по ссылке на баланс начислено <b>{amount}</b>",
    "referral_invitee_paid": (
        "За первую оплату по ссылке друга на баланс ещё <b>{amount}</b>."
    ),
    "referral_referrer_days": (
        "<b>Поздравляем</b>\n\n"
        "Друг {name} первый раз оплатил VPN по вашей ссылке.\n"
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
    "router_ok": (
        "Роутер оплачен на {days} дн., до {expire}. "
        "Создайте устройство в кабинете и вставьте ссылку в настройки роутера. "
        "С баланса телефонов эта сумма не списывается."
    ),
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
    {"key": "cabinet_link", "title": "Запасная ссылка без VPN", "hint": "{url}"},
    {"key": "trust_collect", "title": "Списание обещанного платежа", "hint": "{amount}"},
    {"key": "trial_nudge", "title": "Напоминание взять триал", "hint": "{name} {extra}"},
    {"key": "invite_nudge", "title": "Пригласить друга", "hint": "{name} {reward} {when} {link}"},
    {"key": "broadcast_invite", "title": "Рассылка: пользуются VPN", "hint": "{reward} {link}"},
    {"key": "broadcast_unused", "title": "Рассылка: не подключались", "hint": ""},
    {"key": "info_nudge", "title": "Как у нас устроено", "hint": "{price} {story}"},
    {"key": "story_nudge", "title": "Выложить историю", "hint": "{amount}"},
    {"key": "first_device_thanks", "title": "После первого устройства", "hint": ""},
    {"key": "first_online_nudge", "title": "После первого онлайна", "hint": "{days}"},
    {"key": "trial_end_nudge", "title": "За сутки до отключения (триал)", "hint": ""},
    {"key": "device_nudge_1", "title": "Нет устройства: 30 минут", "hint": ""},
    {"key": "device_nudge_2", "title": "Нет устройства: сутки после первого", "hint": ""},
    {"key": "device_nudge_3", "title": "Нет устройства: ещё сутки", "hint": ""},
    {"key": "help_connect_no_device", "title": "Не получается подключиться: нет устройства", "hint": ""},
    {"key": "help_connect_has_device", "title": "Не получается подключиться: устройство есть", "hint": ""},
    {"key": "help_other", "title": "Другая проблема", "hint": ""},
    {"key": "idle_nudge_7", "title": "Не пользуется: 7 дней", "hint": ""},
    {"key": "idle_nudge_10", "title": "Не пользуется: 10 дней", "hint": ""},
    {"key": "idle_nudge_15", "title": "Не пользуется: 15 дней", "hint": ""},
    {"key": "idle_nudge_20", "title": "Не пользуется: 20 дней", "hint": ""},
    {"key": "referral_referrer_balance", "title": "Реферал: пригласившему (оплата, баланс)", "hint": "{name} {amount} {nxt}"},
    {"key": "referral_invitee_balance", "title": "Реферал: другу (устарело)", "hint": "{amount}"},
    {"key": "referral_invitee_paid", "title": "Реферал: другу за первую оплату", "hint": "{amount}"},
    {"key": "referral_referrer_days", "title": "Реферал: пригласившему дни (оплата)", "hint": "{name} {days} {expire} {sub_block}"},
    {"key": "referral_referrer_paid", "title": "Реферал: пригласившему (оплата)", "hint": "{name} {amount} {nxt}"},
    {"key": "referral_referrer_paid_days", "title": "Реферал: пригласившему дни (оплата)", "hint": "{name} {days} {expire} {sub_block}"},
    {"key": "referral_payout_submitted", "title": "Реферал: заявка на вывод", "hint": "{amount}"},
    {"key": "referral_payout_paid", "title": "Реферал: выплата прошла", "hint": "{amount}"},
    {"key": "referral_payout_rejected", "title": "Реферал: выплата отклонена", "hint": "{amount}"},
    {"key": "referral_clawback", "title": "Реферал: возврат за блок бота", "hint": "{name} {amount}"},
    {"key": "topup_ok", "title": "Баланс пополнен", "hint": "{amount}"},
    {"key": "router_ok", "title": "Роутер оплачен", "hint": "{amount} {days} {expire}"},
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
