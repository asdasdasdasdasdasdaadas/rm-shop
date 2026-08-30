from __future__ import annotations

from html import escape


def ru_plural(n: int, one: str, few: str, many: str) -> str:
    absn = abs(int(n))
    mod10 = absn % 10
    mod100 = absn % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and (mod100 < 12 or mod100 > 14):
        return few
    return many


def days_text(n: int) -> str:
    return f"{int(n)} {ru_plural(n, 'день', 'дня', 'дней')}"


def rub_text(n: int) -> str:
    return f"{int(n)} {ru_plural(n, 'рубль', 'рубля', 'рублей')}"


def subscription_reissued_text(items: list[tuple[str, str]]) -> str:
    parts = [
        "Ссылка подписки обновлена. Старая больше не работает.",
        "",
        "Откройте кабинет и заново добавьте подписку в приложение.",
    ]
    shown = [(title, url) for title, url in items if url]
    if len(shown) == 1:
        title, url = shown[0]
        if title:
            parts.extend(["", title])
        parts.append(f"<code>{escape(url)}</code>")
    elif shown:
        for title, url in shown:
            parts.append("")
            parts.append(title or "Устройство")
            parts.append(f"<code>{escape(url)}</code>")
    return "\n".join(parts)


def minutes_text(n: int) -> str:
    return f"{int(n)} {ru_plural(n, 'минуту', 'минуты', 'минут')}"
