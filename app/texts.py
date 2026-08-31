from __future__ import annotations

from html import escape

from app.notices import notice_text


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
    shown = [(title, url) for title, url in items if url]
    extra: list[str] = []
    if len(shown) == 1:
        title, url = shown[0]
        extra.append("")
        if title:
            extra.append(title)
        extra.append(f"<code>{escape(url)}</code>")
    elif shown:
        for title, url in shown:
            extra.append("")
            extra.append(title or "Устройство")
            extra.append(f"<code>{escape(url)}</code>")
    links = "\n".join(extra)
    return notice_text("sub_reissued", links=links)


def minutes_text(n: int) -> str:
    return f"{int(n)} {ru_plural(n, 'минуту', 'минуты', 'минут')}"
