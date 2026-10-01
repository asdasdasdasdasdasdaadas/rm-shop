from __future__ import annotations

from html import escape

from app.config import get_settings, referral_is_payout, shop_overlay
from app.texts import days_text, rub_text
from app.referral_terms import referral_terms


def faq_items(*, trial_days: int | None = None) -> list[dict[str, str]]:
    custom = shop_overlay().get("faq_items")
    if custom is not None:
        return [dict(item) for item in custom]
    return default_faq_items(trial_days=trial_days)


def default_faq_items(*, trial_days: int | None = None) -> list[dict[str, str]]:
    settings = get_settings()
    price = rub_text(settings.vpn_day_price_rub)
    trial = days_text(trial_days if trial_days is not None else settings.trial_days)
    items: list[dict[str, str]] = [
        {
            "q": "VPN не включается. Что сделать?",
            "a": (
                "Нажмите «Открыть кабинет», добавьте устройство и вставьте ссылку в приложение. "
                "Пока устройства нет, подключения не будет — это не поломка."
            ),
        },
    ]
    if settings.trial_enabled and settings.trial_days > 0:
        items.append(
            {
                "q": "Пробный период закончится — и всё отключится?",
                "a": (
                    f"Да, когда баланс кончится. Сейчас на старте обычно {trial}. "
                    "Пополните заранее, не дожидаясь нуля: так проще не потерять доступ. "
                    "Бот открывается даже без VPN."
                ),
            }
        )
    items.extend(
        [
            {
                "q": "Когда списывается баланс?",
                "a": (
                    f"Только с устройств, которые вы сами добавили. "
                    f"Сутки одного устройства — {price}. "
                    "Роутер в этот счёт не входит: у него отдельная оплата на срок. "
                    "Пока устройства нет, деньги лежат. "
                    "Лишние гаджеты лучше не держать — уйдёт быстрее."
                ),
            },
            {
                "q": "Отключился и пропал доступ к мессенджеру. Как зайти?",
                "a": (
                    "Бот открывается без VPN — так и задумано. "
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
        ]
    )
    items.append(
        {
            "q": "Сменил телефон или переустановил приложение.",
            "a": (
                "Откройте то же устройство в кабинете и заново добавьте подписку. "
                "Если ссылка не берётся — обновите её там же."
            ),
        }
    )
    why = (
        "Устройства, оплата и поддержка в одном месте. "
        "Бот открывается, даже если VPN уже выключен. "
    )
    why += "Платите только за те устройства, которые сами добавили."
    items.append({"q": "Как у нас всё устроено?", "a": why})
    if settings.router_enabled:
        router_days = days_text(settings.router_days)
        router_price = rub_text(settings.router_rub)
        items.append(
            {
                "q": "Подписка на роутер: как оплатить и подключить?",
                "a": (
                    f"Это отдельная подписка, не суточный баланс телефонов и компьютеров. "
                    f"Слот стоит {router_price} за {router_days}. Пока он оплачен, роутер работает; "
                    "когда срок кончится, остановится только он, гаджеты не заденет.\n\n"
                    "С баланса устройств ничего не списывается, лимит телефонов слот не занимает. "
                    "На аккаунт — один роутер.\n\n"
                    "На главной откройте плашку «Роутер», оплатите слот, затем создайте устройство. "
                    "Ссылку подписки вставьте в Keenetic, OpenWrt или другой клиент. "
                    "Продлить можно там же, пока срок не вышел или сразу после."
                ),
            }
        )
    terms = referral_terms(settings)
    items.extend([
        {"q": "Как пригласить друга?", "a": "Откройте раздел «Пригласить друга» и нажмите «Поделиться реферальной ссылкой». Друг должен запустить бота по вашей ссылке. " + terms["note"]},
        {"q": "Когда начислят за приглашённого друга?", "a": terms["when"]},
        {"q": "Сколько дают за друга?", "a": terms["how"] + (" " + terms["friend"] if terms["friend"] else "")},
    ])
    if referral_is_payout():
        items.append({"q": "Можно вывести уже начисленные награды?", "a": f"Вывести можно от {rub_text(settings.referral_payout_min)} доступных реферальных средств. Заявка оформляется в кабинете."})
    if settings.trial_enabled and settings.trial_days > 0:
        items.append(
            {
                "q": "Можно сначала попробовать и уйти?",
                "a": (
                    f"Да. На старте обычно {trial} на балансе. "
                    "Пока устройства нет, ничего не списывается. "
                    "Если не зайдёт — просто не пополняйте."
                ),
            }
        )
    items.append(
        {
            "q": "Где писать, если что-то не так?",
            "a": (
                "В поддержку — кнопка рядом. Можно прикрепить скриншот. "
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
