"""Кейсы с лягушкой: a case drops one of 48 frog models, by rarity; the one picked lives on the home card.

Where cases come from:
  topup        — a real-money top-up of at least case_topup_min_rub gives one (0 turns it off);
  subscription — each successful monthly autopay charge gives case_subscription_count;
  admin        — given by hand in the admin, with an optional message in the bot.
Opening one draws the frog on the server. A frog the person already has gives case_dup_bonus_rub to the balance instead.
"""
from __future__ import annotations

import logging
import secrets

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.frog-cases")

# rarity: (label, chance in %)
RARITY = {"l": ("Легендарная", 1), "e": ("Эпическая", 5), "r": ("Редкая", 12), "u": ("Необычная", 27), "c": ("Обычная", 55)}
RARITY_ORDER = ("l", "e", "r", "u", "c")
# model number (webapp/icons/frog/pNN.json) -> (name, rarity)
SKINS: dict[int, tuple[str, str]] = {
    32: ("Королевская", "l"), 35: ("Громовая", "l"), 39: ("Лотосовая", "l"), 44: ("Снежная", "l"),
    19: ("Призрачная", "e"), 20: ("Сияющая", "e"), 33: ("Пиратская", "e"), 38: ("Звездочёт", "e"),
    40: ("Ядовитая", "e"), 42: ("Колдовская", "e"), 43: ("Рогатая", "e"), 45: ("Вулканная", "e"),
    25: ("Фея", "r"), 26: ("Цветочная", "r"), 27: ("Тортик", "r"), 30: ("Мухомор", "r"), 31: ("Земляника", "r"),
    37: ("Рыцарская", "r"), 41: ("Пчелиная", "r"), 46: ("Мороженка", "r"), 49: ("Дождевая", "r"),
    7: ("Радужная", "u"), 10: ("Пятнистая", "u"), 11: ("Космическая", "u"), 14: ("Ягодная", "u"), 15: ("Неоновая", "u"),
    16: ("Аметистовая", "u"), 17: ("Панда", "u"), 21: ("Огненная", "u"), 22: ("Ледяная", "u"), 23: ("Фиалковая", "u"),
    28: ("Мечтательная", "u"), 29: ("Болотная", "u"), 34: ("Апельсиновая", "u"),
    0: ("Закатная", "c"), 1: ("Сиреневая", "c"), 2: ("Медовая", "c"), 3: ("Мятная", "c"), 4: ("Небесная", "c"),
    5: ("Клубничная", "c"), 6: ("Лавандовая", "c"), 8: ("Шоколадная", "c"), 9: ("Сапфировая", "c"), 12: ("Карамельная", "c"),
    13: ("Серебряная", "c"), 18: ("Ночная", "c"), 24: ("Лимонная", "c"), 36: ("Глиняная", "c"),
}
KINDS = ("topup", "subscription", "admin")
MAX_GIVE = 50
_rng = secrets.SystemRandom()


def case_word(n: int) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return "кейс"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "кейса"
    return "кейсов"


def roll(rng=_rng) -> int:
    """One frog: first the rarity by its chance, then any model of that rarity."""
    x = rng.random() * 100
    rarity = "c"
    for key in RARITY_ORDER:
        if x < RARITY[key][1]:
            rarity = key
            break
        x -= RARITY[key][1]
    pool = sorted(k for k, (_, r) in SKINS.items() if r == rarity)
    return pool[rng.randrange(len(pool))]


def _iso(value) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value else None)


def enabled() -> bool:
    return bool(get_settings().cases_enabled)


async def view(telegram_id: int) -> dict | None:
    """What the cabinet shows: {left, owned: {model: count}, skin, gift}; None while cases are off."""
    if not enabled():
        return None
    pool = db._pool_req()
    row = await pool.fetchrow("SELECT cases_left, skin, gift_count, gift_note, gift_at FROM frog_case_users WHERE telegram_id=$1",
                              int(telegram_id))
    owned = await pool.fetch("SELECT skin, count FROM frog_case_skins WHERE telegram_id=$1", int(telegram_id))
    s = get_settings()
    gift = None
    if row and row["gift_count"]:
        gift = {"count": int(row["gift_count"]), "note": row["gift_note"] or "", "at": _iso(row["gift_at"])}
    return {
        "left": int(row["cases_left"]) if row else 0,
        "owned": {str(r["skin"]): int(r["count"]) for r in owned},
        "skin": int(row["skin"]) if row and row["skin"] is not None else None,
        "gift": gift,
        "topup_min": int(s.case_topup_min_rub or 0),
        "per_month": int(s.case_subscription_count or 0),
        "dup_bonus": int(s.case_dup_bonus_rub or 0),
    }


async def skin(telegram_id: int) -> int | None:
    """The frog the person put on the home card, if cases are on."""
    if not enabled():
        return None
    value = await db._pool_req().fetchval("SELECT skin FROM frog_case_users WHERE telegram_id=$1", int(telegram_id))
    return int(value) if value is not None else None


async def grant(telegram_id: int, count: int, kind: str, *, note: str = "", notify: bool = False, ref: str = "") -> int:
    """Adds cases; returns how many now wait. With notify the cabinet shows the gift once and the caller messages the bot.

    ref makes a grant happen once (a payment id): a second call with the same kind and ref adds nothing."""
    if kind not in KINDS:
        raise ValueError("Неизвестный источник кейса")
    count = int(count)
    if not 1 <= count <= MAX_GIVE:
        raise ValueError(f"От 1 до {MAX_GIVE} кейсов")
    note = str(note or "").strip()[:300]
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            if ref:
                done = await conn.fetchval(
                    "INSERT INTO frog_case_log (telegram_id, kind, delta, ref, note) VALUES ($1,$2,$3,$4,$5) "
                    "ON CONFLICT (kind, ref) WHERE ref <> '' DO NOTHING RETURNING id",
                    int(telegram_id), kind, count, ref, note)
                if not done:
                    return int(await conn.fetchval("SELECT COALESCE(MAX(cases_left),0) FROM frog_case_users WHERE telegram_id=$1",
                                                   int(telegram_id)))
            else:
                await conn.execute("INSERT INTO frog_case_log (telegram_id, kind, delta, note) VALUES ($1,$2,$3,$4)",
                                   int(telegram_id), kind, count, note)
            left = await conn.fetchval(
                """INSERT INTO frog_case_users (telegram_id, cases_left, gift_count, gift_note, gift_at)
                   VALUES ($1, $2, CASE WHEN $3 THEN $2 ELSE 0 END, CASE WHEN $3 THEN $4 ELSE '' END, CASE WHEN $3 THEN NOW() END)
                   ON CONFLICT (telegram_id) DO UPDATE SET cases_left = frog_case_users.cases_left + $2,
                     gift_count = CASE WHEN $3 THEN frog_case_users.gift_count + $2 ELSE frog_case_users.gift_count END,
                     gift_note = CASE WHEN $3 THEN $4 ELSE frog_case_users.gift_note END,
                     gift_at = CASE WHEN $3 THEN NOW() ELSE frog_case_users.gift_at END,
                     updated_at = NOW()
                   RETURNING cases_left""",
                int(telegram_id), count, bool(notify), note)
    return int(left)


async def open_case(telegram_id: int) -> dict:
    """Spends one case and draws a frog: {skin, name, rarity, dup, bonus, left}."""
    if not enabled():
        raise ValueError("Кейсы сейчас выключены")
    bonus_rub = int(get_settings().case_dup_bonus_rub or 0)
    model = roll()
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            left = await conn.fetchval(
                "UPDATE frog_case_users SET cases_left = cases_left - 1, updated_at = NOW() "
                "WHERE telegram_id=$1 AND cases_left > 0 RETURNING cases_left", int(telegram_id))
            if left is None:
                raise ValueError("Кейсов нет — следующий придёт с пополнением")
            count = await conn.fetchval(
                """INSERT INTO frog_case_skins (telegram_id, skin) VALUES ($1, $2)
                   ON CONFLICT (telegram_id, skin) DO UPDATE SET count = frog_case_skins.count + 1
                   RETURNING count""", int(telegram_id), model)
            dup = int(count) > 1
            bonus = bonus_rub if dup else 0
            await conn.execute("INSERT INTO frog_case_log (telegram_id, kind, delta, skin, note) VALUES ($1,'open',-1,$2,$3)",
                               int(telegram_id), model, f"+{bonus} ₽ за повтор" if bonus else "")
    if bonus:
        total = await db.add_balance_rub(int(telegram_id), bonus)
        await db.log_billing_event(int(telegram_id), "case_bonus", source="case", amount=bonus, balance_after=total,
                                   note=f"Кейс с лягушкой: повтор «{SKINS[model][0]}»")
    name, rarity = SKINS[model]
    return {"skin": model, "name": name, "rarity": rarity, "dup": dup, "bonus": bonus, "left": int(left)}


async def set_skin(telegram_id: int, model: int) -> None:
    model = int(model)
    if model not in SKINS:
        raise ValueError("Такой лягушки нет")
    pool = db._pool_req()
    if not await pool.fetchval("SELECT 1 FROM frog_case_skins WHERE telegram_id=$1 AND skin=$2", int(telegram_id), model):
        raise ValueError("Этой лягушки пока нет в коллекции")
    await pool.execute("UPDATE frog_case_users SET skin=$2, updated_at=NOW() WHERE telegram_id=$1", int(telegram_id), model)


async def gift_seen(telegram_id: int) -> None:
    await db._pool_req().execute(
        "UPDATE frog_case_users SET gift_count=0, gift_note='', updated_at=NOW() WHERE telegram_id=$1", int(telegram_id))


async def admin_view(telegram_id: int) -> dict:
    pool = db._pool_req()
    row = await pool.fetchrow("SELECT cases_left, skin FROM frog_case_users WHERE telegram_id=$1", int(telegram_id))
    owned = await pool.fetchval("SELECT COUNT(*) FROM frog_case_skins WHERE telegram_id=$1", int(telegram_id))
    log = await pool.fetch(
        "SELECT kind, delta, skin, note, created_at FROM frog_case_log WHERE telegram_id=$1 ORDER BY id DESC LIMIT 8", int(telegram_id))
    model = int(row["skin"]) if row and row["skin"] is not None else None
    return {
        "enabled": enabled(),
        "left": int(row["cases_left"]) if row else 0,
        "owned_count": int(owned or 0),
        "total": len(SKINS),
        "skin": model,
        "skin_name": SKINS[model][0] if model is not None else None,
        "history": [{"kind": r["kind"], "delta": int(r["delta"]), "skin": SKINS.get(r["skin"], ("", ""))[0] if r["skin"] is not None else "",
                     "note": r["note"] or "", "at": _iso(r["created_at"])} for r in log],
    }


def gift_text(count: int, note: str = "") -> str:
    n = int(count)
    head = "🎁 Вам подарили кейс с лягушкой!" if n == 1 else f"🎁 Вам подарили {n} {case_word(n)} с лягушкой!"
    note = str(note or "").strip()
    return head + (f"\n\n{note}" if note else "") + "\n\nВнутри одна из 48 лягушек — бывают легендарные."


async def send_gift(bot, telegram_id: int, count: int, note: str = "") -> str:
    """The bot message about a gift with the button that opens the case; returns "" or why it was not sent."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from app.keyboards import mini_app_screen
    from app.tg_err import telegram_fail_reason
    app = mini_app_screen("case")
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть кейс 🎁", web_app=app)]]) if app else None
    try:
        await bot.send_message(int(telegram_id), gift_text(count, note), reply_markup=markup)
    except Exception as exc:
        logger.warning("Case gift message not sent to %s: %s", telegram_id, exc)
        try:
            return telegram_fail_reason(exc) or "не доставлено"
        except Exception:
            return "не доставлено"
    return ""
