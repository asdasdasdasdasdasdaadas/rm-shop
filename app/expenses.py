"""«Затраты»: the service's regular bills — hosting, domains, servers — and reminders to pay them.

Every bill has the date of its next payment and a period: month, quarter, year, or once.
«Оплачено» in the admin logs the payment and moves the date one period on (a one-off bill is closed instead).
Nothing moves by itself: until a payment is marked, the bill stays due and then shows as overdue, because the
service cannot know whether the card was really charged.

Monthly dates keep their day: a bill on the 31st is paid on Feb 28 and then on Mar 31 again (anchor_day).

Reminders (switch on the «Затраты» page, app_flags «expenses_notify»): after 10:00 Moscow time, to the live
channel (or to each admin in private when no channel is set), N days before the date and on the day itself
(«expenses_remind_days», default 3 and 0), and once the day after when the payment is still not marked.
Each (bill, date, stage) is claimed in expense_reminders first, so a restart or two bots never send it twice.
If the bot was down on the stage day, the nearest missed stage still goes out once («через 1 день»).
"""
from __future__ import annotations

import asyncio
import calendar
import logging
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any, Iterable

from app import db

logger = logging.getLogger("rm-shop.expenses")

MSK = timezone(timedelta(hours=3))
PERIODS = {"month": "Раз в месяц", "quarter": "Раз в квартал", "year": "Раз в год", "once": "Разово"}
MONTHS_IN = {"month": 1, "quarter": 3, "year": 12}
CURRENCIES = {"RUB": "₽", "USD": "$", "EUR": "€"}
NOTIFY_FLAG = "expenses_notify"
DAYS_KEY = "expenses_remind_days"
DEFAULT_DAYS = (3, 0)
OVERDUE_STAGE = -1
SEND_HOUR_MSK = 10
UPCOMING = 6


def today_msk(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(MSK).date()


def as_day(value: Any) -> date | None:
    """DATE from asyncpg (date), PGlite (ISO string at midnight UTC) or the admin form (YYYY-MM-DD)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def add_period(day: date, period: str, anchor: int | None = None) -> date | None:
    """The next payment date one period after `day`; None for a one-off bill."""
    months = MONTHS_IN.get(period)
    if not months:
        return None
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    want = int(anchor or day.day)
    return date(year, month, min(want, calendar.monthrange(year, month)[1]))


def occurrences(item: dict, start: date, end: date) -> list[date]:
    """Payment dates of an open bill within [start, end], from its next date on."""
    day = as_day(item.get("next_date"))
    found = []
    while day is not None and day <= end and len(found) < 400:
        if day >= start:
            found.append(day)
        day = add_period(day, item["period"], item.get("anchor_day"))
    return found


def monthly(item: dict) -> float:
    months = MONTHS_IN.get(item["period"])
    return float(item["amount"]) / months if months else 0.0


def _add(totals: dict, currency: str, amount: float) -> None:
    totals[currency] = round(totals.get(currency, 0.0) + amount, 2)


def summarize(items: Iterable[dict], paid: Iterable[dict], today: date) -> dict:
    """What to pay and when. Sums are kept per currency: rates are not guessed."""
    open_items = [x for x in items if x.get("done_at") is None and as_day(x.get("next_date"))]
    first = today.replace(day=1)
    last = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    soon_end = today + timedelta(days=29)
    month_due, month_paid, next30, overdue, per_month = {}, {}, {}, {}, {}
    overdue_n = 0
    upcoming = []
    for item in open_items:
        amount, cur = float(item["amount"]), item["currency"]
        due = as_day(item["next_date"])
        if due < today:
            overdue_n += 1
            _add(overdue, cur, amount)
            _add(next30, cur, amount)
        for day in occurrences(item, first, last):
            _add(month_due, cur, amount)
        for day in occurrences(item, today, soon_end):
            _add(next30, cur, amount)
        if monthly(item):
            _add(per_month, cur, monthly(item))
        upcoming.append({"id": item["id"], "title": item["title"], "amount": amount, "currency": cur,
                         "date": due.isoformat(), "days_left": (due - today).days, "url": item.get("url") or ""})
    for row in paid:
        if first <= as_day(row["paid_on"]) <= last:
            _add(month_paid, row["currency"], float(row["amount"]))
    upcoming.sort(key=lambda x: (x["date"], x["title"].lower()))
    return {
        "today": today.isoformat(),
        "month_label": f"{_MONTHS[today.month - 1]} {today.year}",
        "month_due": month_due,
        "month_paid": month_paid,
        "next_30": next30,
        "overdue": overdue,
        "overdue_count": overdue_n,
        "per_month": per_month,
        "per_year": {k: round(v * 12, 2) for k, v in per_month.items()},
        "upcoming": upcoming[:UPCOMING],
    }


_MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


# ---- validation ----

def _clean_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 500:
        raise ValueError("Ссылка длиннее 500 символов")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", text, re.I):
        if re.match(r"^[a-z][a-z0-9+.-]*:(?!\d)", text, re.I):   # javascript:, mailto: — not a page to open
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        text = "https://" + text
    from urllib.parse import urlsplit
    parts = urlsplit(text)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc or re.search(r"\s", text):
        raise ValueError("Ссылка должна начинаться с http:// или https://")
    return text


def clean(body: Any) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Некорректный запрос")
    title = str(body.get("title") or "").strip()
    if not title:
        raise ValueError("Укажите наименование")
    if len(title) > 120:
        raise ValueError("Наименование длиннее 120 символов")
    try:
        amount = Decimal(str(body.get("amount") or "").replace(",", ".").replace(" ", ""))
    except InvalidOperation:
        raise ValueError("Сумма должна быть числом") from None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000"):
        raise ValueError("Сумма должна быть больше нуля")
    currency = str(body.get("currency") or "RUB").upper()
    if currency not in CURRENCIES:
        raise ValueError("Валюта: RUB, USD или EUR")
    period = str(body.get("period") or "month")
    if period not in PERIODS:
        raise ValueError("Некорректный период")
    try:
        next_date = as_day(body.get("next_date"))
    except ValueError:
        raise ValueError("Некорректная дата") from None
    if next_date is None:
        raise ValueError("Укажите дату оплаты")
    if not date(2000, 1, 1) <= next_date <= date(2100, 1, 1):
        raise ValueError("Некорректная дата")
    description = str(body.get("description") or "").strip()
    if len(description) > 2000:
        raise ValueError("Описание длиннее 2000 символов")
    return {"title": title, "amount": amount.quantize(Decimal("0.01")), "currency": currency, "period": period,
            "next_date": next_date, "url": _clean_url(body.get("url")), "description": description}


def parse_days(value: Any) -> list[int]:
    """«3, 0» → [3, 0]: how many days before the date to remind. 0 is the day itself."""
    items = value if isinstance(value, list) else re.split(r"[\s,;]+", str(value or "").strip())
    days = set()
    for raw in items:
        if raw == "" or raw is None:
            continue
        try:
            n = int(raw)
        except (TypeError, ValueError):
            raise ValueError("Дни напоминания: числа через запятую, например 3, 0") from None
        if not 0 <= n <= 60:
            raise ValueError("Дни напоминания: от 0 до 60")
        days.add(n)
    if not days:
        raise ValueError("Укажите хотя бы один день напоминания")
    if len(days) > 6:
        raise ValueError("Не больше 6 напоминаний")
    return sorted(days, reverse=True)


# ---- storage ----

def _row(r: Any) -> dict:
    x = dict(r)
    x["amount"] = float(x["amount"])
    for key in ("next_date",):
        x[key] = as_day(x.get(key))
    return x


def _iso(v: Any) -> Any:
    if v is None or isinstance(v, str):
        return v
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v.isoformat()


async def list_items() -> list[dict]:
    rows = await db._pool_req().fetch(
        "SELECT * FROM service_expenses ORDER BY done_at IS NOT NULL, next_date, lower(title)")
    return [_row(r) for r in rows]


async def get(expense_id: int) -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM service_expenses WHERE id=$1", int(expense_id))
    return _row(row) if row else None


async def create(data: dict) -> int:
    return int(await db._pool_req().fetchval(
        """INSERT INTO service_expenses (title, amount, currency, period, next_date, anchor_day, url, description)
           VALUES ($1, $2::text::numeric, $3, $4, $5::date, $6, $7, $8) RETURNING id""",
        data["title"], str(data["amount"]), data["currency"], data["period"], data["next_date"],
        data["next_date"].day, data["url"], data["description"]))


async def update(expense_id: int, data: dict) -> bool:
    """Editing a closed one-off bill with a new date opens it again."""
    return bool(await db._pool_req().fetchval(
        """UPDATE service_expenses SET title=$2, amount=$3::text::numeric, currency=$4, period=$5,
               anchor_day = CASE WHEN next_date IS DISTINCT FROM $6::date OR period <> $5 THEN $7 ELSE anchor_day END,
               done_at = CASE WHEN next_date IS DISTINCT FROM $6::date THEN NULL ELSE done_at END,
               next_date=$6::date, url=$8, description=$9, updated_at=NOW()
           WHERE id=$1 RETURNING id""",
        int(expense_id), data["title"], str(data["amount"]), data["currency"], data["period"], data["next_date"],
        data["next_date"].day, data["url"], data["description"]))


async def delete(expense_id: int) -> bool:
    return bool(await db._pool_req().fetchval("DELETE FROM service_expenses WHERE id=$1 RETURNING id", int(expense_id)))


async def mark_paid(expense_id: int, today: date | None = None) -> dict:
    """Log the payment and move the date one period on (close a one-off bill)."""
    item = await get(expense_id)
    if not item:
        raise LookupError("Затрата не найдена")
    if item.get("done_at") is not None:
        raise ValueError("Эта разовая затрата уже оплачена")
    due = item["next_date"]
    nxt = add_period(due, item["period"], item.get("anchor_day"))
    pool = db._pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO service_expense_payments (expense_id, title, amount, currency, due_date, paid_on)
                   VALUES ($1, $2, $3::text::numeric, $4, $5::date, $6::date)""",
                item["id"], item["title"], f'{item["amount"]:.2f}', item["currency"], due, today or today_msk())
            if nxt is None:
                await conn.execute(
                    "UPDATE service_expenses SET done_at=NOW(), last_paid_at=NOW(), updated_at=NOW() WHERE id=$1", item["id"])
            else:
                await conn.execute(
                    "UPDATE service_expenses SET next_date=$2::date, last_paid_at=NOW(), updated_at=NOW() WHERE id=$1",
                    item["id"], nxt)
    return {"next_date": nxt.isoformat() if nxt else None, "closed": nxt is None}


async def notify_settings() -> dict:
    raw = await db.get_kv(DAYS_KEY)
    try:
        days = parse_days(raw) if raw.strip() else list(DEFAULT_DAYS)
    except ValueError:
        days = list(DEFAULT_DAYS)
    from app.config import get_settings
    from app.live import _chat_id
    chat = _chat_id()
    admins = len(get_settings().admin_id_set)
    target = "канал событий" if chat else (f"админам в личку ({admins})" if admins else "")
    return {"enabled": await db.flag_on(NOTIFY_FLAG), "days": days, "target": target, "hour": SEND_HOUR_MSK}


async def save_notify(body: Any) -> None:
    if not isinstance(body, dict):
        raise ValueError("Некорректный запрос")
    if "days" in body:
        await db.set_kv(DAYS_KEY, ", ".join(str(d) for d in parse_days(body.get("days"))))
    if "enabled" in body:
        await db.set_flag(NOTIFY_FLAG, bool(body.get("enabled")))


async def overview(today: date | None = None) -> dict:
    today = today or today_msk()
    items = await list_items()
    first = today.replace(day=1)
    paid = [dict(r) for r in await db._pool_req().fetch(
        "SELECT amount, currency, paid_on FROM service_expense_payments WHERE paid_on >= $1::date", first)]
    for p in paid:
        p["amount"] = float(p["amount"])
    history = [dict(r) for r in await db._pool_req().fetch(
        "SELECT id, expense_id, title, amount, currency, due_date, paid_on FROM service_expense_payments "
        "ORDER BY paid_on DESC, id DESC LIMIT 20")]
    out_items = []
    for x in items:
        due = x["next_date"]
        out_items.append({
            "id": x["id"], "title": x["title"], "amount": x["amount"], "currency": x["currency"],
            "period": x["period"], "period_label": PERIODS.get(x["period"], x["period"]),
            "next_date": due.isoformat() if due else None, "url": x.get("url") or "",
            "description": x.get("description") or "", "done": x.get("done_at") is not None,
            "days_left": (due - today).days if due and x.get("done_at") is None else None,
            "monthly": round(monthly(x), 2), "last_paid_at": _iso(x.get("last_paid_at")),
        })
    return {
        "items": out_items,
        "summary": summarize(items, paid, today),
        "history": [{**h, "amount": float(h["amount"]), "due_date": _iso(as_day(h["due_date"])),
                     "paid_on": _iso(as_day(h["paid_on"]))} for h in history],
        "notify": await notify_settings(),
        "periods": PERIODS,
        "currencies": CURRENCIES,
    }


# ---- reminders ----

def stage_for(due: date, today: date, days: list[int]) -> int | None:
    """Which reminder is due today: the nearest stage not later than today, or the overdue one the day after."""
    left = (due - today).days
    if left < 0:
        return OVERDUE_STAGE if left >= -7 else None
    reached = [d for d in days if d >= left]
    return min(reached) if reached else None


def fmt_money(amount: float, currency: str) -> str:
    whole = abs(amount - round(amount)) < 0.005
    text = f"{amount:,.0f}" if whole else f"{amount:,.2f}"
    return text.replace(",", " ").replace(".", ",") + " " + CURRENCIES.get(currency, currency)


def _when(left: int) -> str:
    if left < 0:
        n = -left
        return f"просрочено на {n} {_plural(n, 'день', 'дня', 'дней')}"
    if left == 0:
        return "сегодня"
    if left == 1:
        return "завтра"
    return f"через {left} {_plural(left, 'день', 'дня', 'дней')}"


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    return {1: one, 2: few, 3: few, 4: few}.get(n % 10, many)


def format_reminder(rows: list[dict], today: date) -> str:
    lines = ["💳 <b>Скоро оплата сервисов</b>" if any((r["next_date"] - today).days >= 0 for r in rows)
             else "⚠️ <b>Оплата сервисов просрочена</b>", ""]
    totals: dict = {}
    for r in sorted(rows, key=lambda x: (x["next_date"], x["title"].lower())):
        left = (r["next_date"] - today).days
        title = escape(r["title"])
        if r.get("url"):
            title = f'<a href="{escape(r["url"], quote=True)}">{title}</a>'
        mark = "🔴" if left <= 0 else "🟡"
        lines.append(f"{mark} {title} — <b>{fmt_money(r['amount'], r['currency'])}</b>, "
                     f"{r['next_date'].strftime('%d.%m.%Y')} ({_when(left)})")
        if r.get("description"):
            lines.append(f"<i>{escape(r['description'][:200])}</i>")
        _add(totals, r["currency"], float(r["amount"]))
    if len(rows) > 1:
        lines += ["", "Итого: " + " + ".join(fmt_money(v, k) for k, v in totals.items())]
    if any((r["next_date"] - today).days < 0 for r in rows):
        lines += ["", "Если уже оплачено — отметьте «Оплачено» в админке, в разделе «Затраты»."]
    return "\n".join(lines)


CLAIM_SQL = """INSERT INTO expense_reminders (expense_id, due_date, stage) VALUES ($1, $2::date, $3)
               ON CONFLICT DO NOTHING RETURNING expense_id"""


async def due_reminders(today: date, days: list[int]) -> list[dict]:
    """Claim today's reminders; each (bill, date, stage) only once."""
    claimed = []
    for item in await list_items():
        if item.get("done_at") is not None or not item.get("next_date"):
            continue
        stage = stage_for(item["next_date"], today, days)
        if stage is None:
            continue
        if await db._pool_req().fetchval(CLAIM_SQL, item["id"], item["next_date"], stage):
            claimed.append(item)
    return claimed


async def send_due(bot, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    if now.astimezone(MSK).hour < SEND_HOUR_MSK or not await db.flag_on(NOTIFY_FLAG):
        return 0
    from app.stuck_alert import _targets
    targets = await _targets()
    if not targets:
        return 0
    today = today_msk(now)
    rows = await due_reminders(today, (await notify_settings())["days"])
    if not rows:
        return 0
    text = format_reminder(rows, today)
    for chat in targets:
        try:
            await bot.send_message(chat, text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            logger.warning("Напоминание об оплате сервисов не ушло в %s", chat, exc_info=True)
    return len(rows)


async def expenses_loop(bot) -> None:
    await asyncio.sleep(60)
    while True:
        try:
            await send_due(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Напоминания об оплате сервисов")
        await asyncio.sleep(600)
