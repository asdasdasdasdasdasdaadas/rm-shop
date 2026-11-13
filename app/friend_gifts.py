"""«Подарить другу»: a user gives part of their balance to a friend as a gift link.

The giver pays from the balance, but only with money they topped up themselves (trial, referral and promo
credits cannot be passed on, otherwise fresh accounts could farm them). The friend opens the link in the
bot, then the gift in the cabinet; the amount lands on their balance in one transaction. Until it is opened,
the giver can take the gift back.
"""
from __future__ import annotations

import logging
import re
import secrets

from app import db
from app.config import get_settings

logger = logging.getLogger(__name__)

START_PREFIX = "present_"
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{8,32}$")


class GiftError(ValueError):
    pass


def limits() -> tuple[int, int]:
    s = get_settings()
    lo = max(1, int(s.gift_min_rub or 1))
    return lo, max(lo, int(s.gift_max_rub or lo))


def clean_code(code: str | None) -> str | None:
    raw = (code or "").strip()
    return raw if _CODE_RE.match(raw) else None


def code_from_start(payload: str | None) -> str | None:
    raw = (payload or "").strip()
    if raw.startswith("/start"):
        parts = raw.split(maxsplit=1)
        raw = parts[1] if len(parts) > 1 else ""
    if not raw.startswith(START_PREFIX):
        return None
    return clean_code(raw.removeprefix(START_PREFIX))


def gift_link(code: str) -> str:
    return f"https://t.me/{get_settings().bot_username.lstrip('@')}?start={START_PREFIX}{code}"


def giver_name(row: dict | None) -> str:
    name = str((row or {}).get("first_name") or "").strip()
    return name[:40] or "Друг"


_GIFTABLE_SQL = """
    SELECT GREATEST(0, LEAST(COALESCE(u.balance_rub, 0),
        COALESCE((SELECT SUM(amount) FROM billing_events
                  WHERE telegram_id=u.telegram_id AND kind='topup' AND source='pay'), 0)
      - COALESCE((SELECT SUM(amount_rub) FROM friend_gifts
                  WHERE from_telegram_id=u.telegram_id AND status IN ('active','claimed')), 0)))::int
    FROM users u WHERE u.telegram_id=$1
"""


async def giftable_rub(telegram_id: int, conn=None) -> int:
    """How much of the balance can be gifted: the balance, but not more than the user paid in themselves."""
    q = conn or db._pool_req()
    return int(await q.fetchval(_GIFTABLE_SQL, telegram_id) or 0)


async def create_gift(telegram_id: int, amount: int) -> dict:
    lo, hi = limits()
    if not get_settings().gifts_enabled:
        raise GiftError("Подарки сейчас недоступны")
    if not isinstance(amount, int) or amount < lo:
        raise GiftError(f"Минимальный подарок — {lo} ₽")
    if amount > hi:
        raise GiftError(f"Максимальный подарок — {hi} ₽")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow("SELECT balance_rub FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id)
            if not user:
                raise GiftError("Пользователь не найден")
            can = await giftable_rub(telegram_id, conn)
            if amount > can:
                raise GiftError(
                    f"Можно подарить до {can} ₽ — это деньги, которые вы сами внесли на баланс"
                    if can else "Сначала пополните баланс — подарить можно только свои деньги"
                )
            code = secrets.token_urlsafe(9)
            gift = await conn.fetchrow(
                """INSERT INTO friend_gifts (code, from_telegram_id, amount_rub)
                   VALUES ($1, $2, $3) RETURNING id, code, amount_rub, status, created_at""",
                code, telegram_id, amount,
            )
            balance = await conn.fetchval(
                "UPDATE users SET balance_rub=COALESCE(balance_rub,0)-$2 WHERE telegram_id=$1 RETURNING balance_rub",
                telegram_id, amount,
            )
            await conn.execute(
                """INSERT INTO billing_events (telegram_id, kind, source, amount, balance_after, note)
                   VALUES ($1, 'gift_sent', 'user', $2, $3, $4)""",
                telegram_id, -amount, balance, "Подарок другу",
            )
    out = dict(gift)
    out["balance_rub"] = int(balance or 0)
    return out


async def get_gift(code: str) -> dict | None:
    clean = clean_code(code)
    if not clean:
        return None
    row = await db._pool_req().fetchrow(
        """SELECT g.*, u.first_name AS from_first_name
           FROM friend_gifts g LEFT JOIN users u ON u.telegram_id=g.from_telegram_id
           WHERE g.code=$1""",
        clean,
    )
    return dict(row) if row else None


async def claim_gift(telegram_id: int, code: str) -> dict:
    """Credit the gift to the friend exactly once. Raises GiftError with a text for the user."""
    clean = clean_code(code)
    if not clean:
        raise GiftError("Подарок не найден")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            gift = await conn.fetchrow("SELECT * FROM friend_gifts WHERE code=$1 FOR UPDATE", clean)
            if not gift:
                raise GiftError("Подарок не найден")
            if int(gift["from_telegram_id"]) == telegram_id:
                raise GiftError("Это ваш подарок — отправьте его другу")
            if gift["status"] == "claimed":
                if gift["claimed_by"] is not None and int(gift["claimed_by"]) == telegram_id:
                    raise GiftError("Вы уже открыли этот подарок")
                raise GiftError("Этот подарок уже открыли")
            if gift["status"] != "active":
                raise GiftError("Подарок отменён — даритель забрал его обратно")
            user = await conn.fetchrow(
                "SELECT balance_rub, bot_started_at FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id
            )
            if not user or user["bot_started_at"] is None:
                raise GiftError("Сначала откройте бота по ссылке на подарок")
            amount = int(gift["amount_rub"])
            await conn.execute(
                "UPDATE friend_gifts SET status='claimed', claimed_by=$2, claimed_at=NOW() WHERE id=$1",
                gift["id"], telegram_id,
            )
            balance = await conn.fetchval(
                """UPDATE users SET balance_rub=COALESCE(balance_rub,0)+$2,
                   low_balance_notified_at=NULL, trial_end_nudge_at=NULL
                   WHERE telegram_id=$1 RETURNING balance_rub""",
                telegram_id, amount,
            )
            giver = await conn.fetchrow("SELECT first_name FROM users WHERE telegram_id=$1", gift["from_telegram_id"])
            await conn.execute(
                """INSERT INTO billing_events (telegram_id, kind, source, amount, balance_after, note)
                   VALUES ($1, 'gift_received', 'user', $2, $3, $4)""",
                telegram_id, amount, balance, f"От {giver_name(dict(giver) if giver else None)}",
            )
    return {
        "amount_rub": amount,
        "balance_rub": int(balance or 0),
        "from_telegram_id": int(gift["from_telegram_id"]),
        "from_name": giver_name(dict(giver) if giver else None),
    }


async def return_gift(telegram_id: int, code: str) -> dict:
    """The giver takes back a gift nobody has opened yet."""
    clean = clean_code(code)
    if not clean:
        raise GiftError("Подарок не найден")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            gift = await conn.fetchrow("SELECT * FROM friend_gifts WHERE code=$1 FOR UPDATE", clean)
            if not gift or int(gift["from_telegram_id"]) != telegram_id:
                raise GiftError("Подарок не найден")
            if gift["status"] == "claimed":
                raise GiftError("Друг уже открыл этот подарок")
            if gift["status"] != "active":
                raise GiftError("Подарок уже вернулся на ваш баланс")
            await conn.fetchrow("SELECT 1 FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id)
            amount = int(gift["amount_rub"])
            await conn.execute(
                "UPDATE friend_gifts SET status='returned', returned_at=NOW() WHERE id=$1", gift["id"]
            )
            balance = await conn.fetchval(
                """UPDATE users SET balance_rub=COALESCE(balance_rub,0)+$2, low_balance_notified_at=NULL
                   WHERE telegram_id=$1 RETURNING balance_rub""",
                telegram_id, amount,
            )
            await conn.execute(
                """INSERT INTO billing_events (telegram_id, kind, source, amount, balance_after, note)
                   VALUES ($1, 'gift_return', 'user', $2, $3, $4)""",
                telegram_id, amount, balance, "Подарок не открыли — вернули на баланс",
            )
    return {"amount_rub": amount, "balance_rub": int(balance or 0)}


async def mark_thanked(telegram_id: int, code: str) -> dict | None:
    """The friend says thanks once; returns the gift when this is the first «спасибо»."""
    clean = clean_code(code)
    if not clean:
        return None
    row = await db._pool_req().fetchrow(
        """UPDATE friend_gifts SET thanked_at=NOW()
           WHERE code=$1 AND claimed_by=$2 AND status='claimed' AND thanked_at IS NULL
           RETURNING from_telegram_id, amount_rub""",
        clean, telegram_id,
    )
    return dict(row) if row else None


async def list_sent(telegram_id: int, limit: int = 20) -> list[dict]:
    rows = await db._pool_req().fetch(
        """SELECT g.code, g.amount_rub, g.status, g.created_at, g.claimed_at, u.first_name AS friend_name
           FROM friend_gifts g LEFT JOIN users u ON u.telegram_id=g.claimed_by
           WHERE g.from_telegram_id=$1 ORDER BY g.created_at DESC LIMIT $2""",
        telegram_id, limit,
    )
    return [dict(r) for r in rows]


def public_sent(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({
            "code": r["code"],
            "url": gift_link(r["code"]),
            "amount_rub": int(r["amount_rub"]),
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "claimed_at": r["claimed_at"].isoformat() if r.get("claimed_at") else None,
            "friend_name": (str(r.get("friend_name") or "").strip()[:40] or None) if r["status"] == "claimed" else None,
        })
    return out


# ---------- bot side ----------
def days_for(amount: int) -> int:
    return int(amount) // max(1, int(get_settings().vpn_day_price_rub or 1))


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    m = n % 10
    return many if 10 < n < 20 else one if m == 1 else few if 1 < m < 5 else many


def days_text(amount: int) -> str:
    d = days_for(amount)
    return f"{d} {_plural(d, 'день', 'дня', 'дней')}"


def open_button(code: str):
    """«Открыть подарок»: the cabinet straight on the gift screen; None without a mini app URL."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    from aiogram.types import InlineKeyboardButton, WebAppInfo

    from app.keyboards import mini_app_url

    url = mini_app_url()
    if not url:
        return None
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update(screen="present", code=code)
    return InlineKeyboardButton(text="🎁 Открыть подарок", style="success",
                                web_app=WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query)))))


def share_text(name: str, amount: int) -> str:
    return f"🎁 {name} дарит вам {amount} ₽ на VPN — это ≈ {days_text(amount)}. Откройте подарок, пока он не остыл!"


async def prepare_share(bot, telegram_id: int, code: str, amount: int, name: str) -> str | None:
    """A ready card for Telegram's «share» sheet (WebApp.shareMessage). None when Telegram refuses."""
    from aiogram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        InlineQueryResultArticle,
        InputTextMessageContent,
    )

    if bot is None:
        return None
    try:
        result = InlineQueryResultArticle(
            id=f"gift-{code}"[:64],
            title=f"Подарок {amount} ₽ на VPN",
            description=f"≈ {days_text(amount)} VPN от {name}",
            input_message_content=InputTextMessageContent(message_text=share_text(name, amount)),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🎁 Открыть подарок", url=gift_link(code)),
            ]]),
        )
        prepared = await bot.save_prepared_inline_message(
            user_id=telegram_id, result=result, allow_user_chats=True, allow_group_chats=True,
        )
        return prepared.id
    except Exception:
        logger.warning("Gift share card was not prepared for %s", telegram_id, exc_info=True)
        return None


async def send_gift_card(message, code: str) -> bool:
    """/start present_CODE: the friend sees whose gift it is and a button that opens it."""
    from aiogram.types import InlineKeyboardMarkup

    gift = await get_gift(code)
    if not gift:
        await message.answer("Этот подарок не найден. Попросите друга прислать ссылку ещё раз.")
        return False
    name = giver_name({"first_name": gift.get("from_first_name")})
    amount = int(gift["amount_rub"])
    if int(gift["from_telegram_id"]) == message.from_user.id:
        text = f"🎁 Это ваш подарок на {amount} ₽. Отправьте ссылку другу — он откроет его у себя."
    elif gift["status"] == "claimed":
        text = ("🎁 Вы уже открыли этот подарок — деньги на балансе."
                if gift.get("claimed_by") == message.from_user.id else "Этот подарок уже открыли.")
    elif gift["status"] != "active":
        text = "Этот подарок отменён: даритель забрал его обратно."
    else:
        text = f"🎁 <b>{_html(name)}</b> дарит вам <b>{amount} ₽</b> на VPN — это ≈ {days_text(amount)}.\n\nОткройте подарок, и деньги сразу лягут на баланс."
    btn = open_button(gift["code"]) if gift["status"] in ("active", "claimed") else None
    await message.answer(text, parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn]]) if btn else None)
    return True


def _html(text: str) -> str:
    import html

    return html.escape(text or "", quote=False)


async def notify_giver_claimed(bot, giver_id: int, friend_name: str, amount: int) -> None:
    if bot is None:
        return
    try:
        await bot.send_message(
            giver_id,
            f"🎁 Ваш подарок открыт! {amount} ₽ теперь на балансе у <b>{_html(friend_name)}</b>. Спасибо, что делитесь!",
            parse_mode="HTML",
        )
    except Exception:
        logger.info("Gift claim notice not delivered to %s", giver_id, exc_info=True)


async def notify_giver_thanks(bot, giver_id: int, friend_name: str) -> None:
    if bot is None:
        return
    try:
        await bot.send_message(giver_id, f"❤️ <b>{_html(friend_name)}</b> говорит спасибо за подарок!", parse_mode="HTML")
    except Exception:
        logger.info("Gift thanks not delivered to %s", giver_id, exc_info=True)
