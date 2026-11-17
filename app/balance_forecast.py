"""When the VPN will actually switch off, from each device's next daily charge and the balance,
and whether the «баланс на исходе» warning should go out now so it does not land at night or too late."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.remnawave import parse_dt

DAY = timedelta(hours=24)
MSK = timezone(timedelta(hours=3))  # Moscow has no daylight saving time.
DAY_START, DAY_END = 10, 22  # Moscow hours when a warning may wake nobody up.


def off_at(balance: int, billed: list, price: int, now: datetime | None = None) -> datetime | None:
    """The first moment a device's daily charge finds less than a day's price on the balance; None without devices."""
    now = now or datetime.now(timezone.utc)
    price = max(1, int(price))
    queue = sorted(max(at + DAY, now) for at in (parse_dt(x) for x in billed or []) if at)
    if not queue:
        return None
    money = max(0, int(balance))
    for _ in range(400):
        at = queue.pop(0)
        if money < price:
            return at
        money -= price
        queue.append(at + DAY)
        queue.sort()
    return None


def _morning(after: datetime) -> datetime:
    """The next DAY_START in Moscow after this moment."""
    local = after.astimezone(MSK)
    start = local.replace(hour=DAY_START, minute=0, second=0, microsecond=0)
    if start <= local:
        start += DAY
    return start.astimezone(timezone.utc)


def warn_now(off: datetime, now: datetime | None = None) -> bool:
    """A day ahead, but not in the middle of the night: a warning due at night waits for 10:00 Moscow time,
    unless the VPN would already be off by then (or soon after)."""
    now = now or datetime.now(timezone.utc)
    hour = now.astimezone(MSK).hour
    if not (DAY_START <= hour < DAY_END):
        return off <= _morning(now) + timedelta(hours=2)
    return off - now <= DAY


def when_label(off: datetime, now: datetime | None = None) -> str:
    """«сегодня около 18:40», «завтра около 7:00», «25 ноября около 9:10» (Moscow time, down to 10 minutes)."""
    now = now or datetime.now(timezone.utc)
    local, today = off.astimezone(MSK), now.astimezone(MSK).date()
    clock = f"{local.hour}:{local.minute // 10 * 10:02d}"
    days = (local.date() - today).days
    if days <= 0:
        day = "сегодня"
    elif days == 1:
        day = "завтра"
    else:
        from app.return_bonus import MONTHS
        day = f"{local.day} {MONTHS[local.month - 1]}"
    return f"{day} около {clock}"
