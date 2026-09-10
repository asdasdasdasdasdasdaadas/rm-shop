from __future__ import annotations

from html import escape

from app.config import get_settings
from app.texts import days_text, rub_text


def faq_items(*, trial_days: int | None = None) -> list[dict[str, str]]:
    settings = get_settings()
    price = rub_text(settings.vpn_day_price_rub)
    trial = days_text(trial_days if trial_days is not None else settings.trial_days)
    items: list[dict[str, str]] = [
        {
            "q": "VPN не включается. Что сделать?",
            "a": (
                "Откройте кабинет и добавьте устройство, затем вставьте ссылку в приложение. "
                "Пока устройства нет, подключения не будет — это не поломка."
            ),
        },
        {
            "q": "Когда списывается баланс?",
            "a": (
                f"Только после того, как устройство реально вышло в сеть. "
                f"Сутки одного устройства — {price}. "
                "Пока не подключились, деньги лежат."
            ),
        },
        {
            "q": "Отключился и пропал Telegram. Как зайти?",
            "a": (
                "Бот и кабинет открываются без VPN. "
                "За сутки до конца лучше пополнить или взять обещанный платёж, "
                "пока мессенджер ещё работает."
            ),
        },
        {
            "q": "Можно и телефон, и компьютер?",
            "a": (
                "Да, это разные устройства. Каждое списывает свои сутки. "
                "Не добавляйте лишние — иначе баланс уйдёт быстрее."
            ),
        },
        {
            "q": "Сменил телефон или переустановил приложение.",
            "a": (
                "Откройте то же устройство в кабинете и заново добавьте подписку. "
                "Если ссылка не берётся — перевыпустите её там же."
            ),
        },
    ]
    if settings.balance_enabled and settings.trial_enabled and settings.trial_days > 0:
        items.insert(
            1,
            {
                "q": "Пробный период закончится — и всё отключится?",
                "a": (
                    f"Да, когда баланс кончится. Сейчас на старте обычно {trial}. "
                    "Пополните заранее, не дожидаясь нуля: так проще не потерять доступ."
                ),
            },
        )
    if not settings.balance_enabled:
        items = [items[0], items[-2], items[-1]]
        items.insert(
            1,
            {
                "q": "Как не остаться без доступа?",
                "a": "Продлите подписку до даты окончания. Кабинет открывается из бота даже если VPN уже не работает.",
            },
        )
    return items


def faq_html() -> str:
    lines = ["<b>Частые вопросы</b>", ""]
    for item in faq_items():
        lines.append(f"<b>{escape(item['q'])}</b>")
        lines.append(escape(item["a"]))
        lines.append("")
    lines.append("Если не помогло — напишите в поддержку из кабинета.")
    return "\n".join(lines).strip()
