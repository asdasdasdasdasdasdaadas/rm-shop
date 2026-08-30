from __future__ import annotations


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


def minutes_text(n: int) -> str:
    return f"{int(n)} {ru_plural(n, 'минуту', 'минуты', 'минут')}"
