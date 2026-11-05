from __future__ import annotations

from html import escape

from app.config import get_settings, shop_overlay
from app.texts import days_text
from app.referral_terms import referral_terms


def tariff_faq_items() -> list[dict[str, str]]:
    """Price, billing model and minimum top-up. Always shown, even with a custom FAQ from the admin panel."""
    settings = get_settings()
    price = max(1, int(settings.vpn_day_price_rub or 1))
    minimum = max(1, int(settings.balance_topup_min or 1))
    return [
        {
            "q": "Сколько стоит VPN?",
            "a": (
                f"{price} ₽ в день за одно устройство. Телефон и ноутбук — это два устройства, "
                f"то есть {price * 2} ₽ в день. Других платежей нет."
            ),
        },
        {
            "q": "Это подписка?",
            "a": (
                "Нет, это баланс. Вы пополняете его сами, а раз в сутки с него списывается "
                f"{price} ₽ за каждое добавленное устройство. Автоплатежей с карты нет: "
                "деньги берутся только с баланса."
            ),
        },
        {
            "q": "Какое минимальное пополнение?",
            "a": (
                f"От {minimum} ₽. Этого хватит на {days_text(minimum // price)} для одного устройства. "
                "Сумму выбираете сами, остаток не сгорает."
            ),
        },
        {
            "q": "Когда списываются деньги?",
            "a": (
                "Списания начинаются, когда вы добавляете устройство, и идут каждые 24 часа — "
                "даже если VPN выключен в приложении. Пока устройств нет, ничего не списывается."
            ),
        },
        {
            "q": "Что будет, когда баланс закончится?",
            "a": (
                "VPN на устройствах отключится. Пополните баланс — и он снова заработает, "
                "устройства добавлять заново не нужно."
            ),
        },
        {
            "q": "Как перестать платить?",
            "a": (
                "Удалите устройства в кабинете — со следующих суток списаний не будет. "
                "Деньги на балансе останутся."
            ),
        },
    ]


def faq_items(*, trial_days: int | None = None) -> list[dict[str, str]]:
    custom = shop_overlay().get("faq_items")
    if custom is None:
        items = default_faq_items(trial_days=trial_days)
    else:
        asked = {str(item.get("q", "")).strip().lower() for item in custom}
        items = [item for item in tariff_faq_items() if item["q"].lower() not in asked] + [dict(item) for item in custom]
    return [
        item for item in items
        if "роутер" not in f"{item.get('q', '')} {item.get('a', '')}".lower()
    ]


def default_faq_items(*, trial_days: int | None = None) -> list[dict[str, str]]:
    settings = get_settings()
    trial = days_text(trial_days if trial_days is not None else settings.trial_days)
    items: list[dict[str, str]] = [*tariff_faq_items(),
        {
            "q": "VPN не включается. Что сделать?",
            "a": (
                "Нажмите «Открыть кабинет», добавьте устройство и вставьте ссылку в приложение. "
                "Затем включите VPN в приложении. Если не получится — напишите нам."
            ),
        },
    ]
    if settings.trial_enabled and settings.trial_days > 0:
        items.append(
            {
                "q": "Пробный период закончится — и всё отключится?",
                "a": (
                    f"Подарка хватит на {trial} для одного устройства. "
                    "Для дальнейшей работы VPN пополните баланс. "
                    "Сохраните запасную ссылку на кабинет заранее."
                ),
            }
        )
    items.extend(
        [
            {
                "q": "Отключился и пропал доступ к мессенджеру. Как зайти?",
                "a": (
                    "Используйте заранее сохранённую ссылку на кабинет. "
                    "Пополните баланс заранее, "
                    "пока мессенджер ещё работает."
                ),
            },
        ]
    )
    items.append(
        {
            "q": "Сменил телефон или переустановил приложение.",
            "a": (
                "Откройте то же устройство в кабинете и заново добавьте подписку. "
                "Если ссылка не работает, напишите в поддержку."
            ),
        }
    )
    why = (
        "Устройства, оплата и поддержка в одном месте. "
        "Сохраните ссылку на кабинет, чтобы вернуться к нему позже. "
    )
    why += "Платите только за те устройства, которые сами добавили."
    items.append({"q": "Как у нас всё устроено?", "a": why})
    terms = referral_terms(settings)
    items.extend([
        {"q": "Как пригласить друга?", "a": "Откройте раздел «Пригласить друга» и нажмите «Поделиться ссылкой». Друг должен запустить бота по вашей ссылке. " + terms["note"]},
        {"q": "Когда начислят за приглашённого друга?", "a": terms["when"]},
        {"q": "Сколько дают за друга?", "a": terms["how"] + (" " + terms["friend"] if terms["friend"] else "")},
    ])
    if settings.trial_enabled and settings.trial_days > 0:
        items.append(
            {
                "q": "Можно сначала попробовать и уйти?",
                "a": (
                    f"Да. На старте обычно {trial} на балансе. "
                    "Пока устройства нет, ничего не списывается. "
                    "Если VPN не нужен, удалите устройства — списания остановятся."
                ),
            }
        )
    items.append(
        {
            "q": "Где писать, если что-то не так?",
            "a": (
                "Нажмите «Поддержка» в кабинете. Можно прикрепить скриншот. "
                "Ответ придёт и сюда, и в чат бота — не нужно искать отдельный канал."
            ),
        }
    )
    return items


def faq_html() -> str:
    lines = ["<b>Частые вопросы</b>", ""]
    for item in faq_items():
        lines.append(f"<b>{escape(item['q'])}</b>")
        lines.append(escape(item["a"]))
        lines.append("")
    lines.append("Если не помогло — напишите в поддержку.")
    return "\n".join(lines).strip()


def validate_faq(value):
    if value is None:
        return None
    if not isinstance(value, list) or len(value) > 25:
        raise ValueError("Частые вопросы: максимум 25 вопросов")
    result = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("q"), str) or not isinstance(item.get("a"), str):
            raise ValueError("Укажите вопрос и ответ")
        q, a = item["q"].strip(), item["a"].strip()
        if not q or not a or len(q) > 150 or len(a) > 1200:
            raise ValueError("Вопрос: 1–150 символов. Ответ: 1–1200 символов.")
        result.append({"q": q, "a": a})
    return result


def faq_pages() -> list[str]:
    header = "<b>Частые вопросы</b>"
    pages, current = [], header
    for item in faq_items():
        block = f"\n\n<b>{escape(item['q'])}</b>\n{escape(item['a'])}"
        if len((current + block).encode('utf-16-le')) // 2 > 3800:
            pages.append(current)
            current = header
        current += block
    pages.append(current + "\n\nЕсли не помогло — напишите в поддержку.")
    return pages
