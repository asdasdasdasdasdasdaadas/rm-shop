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


ADMIN_MAX_RUB = 1_000_000


def is_admin(telegram_id: int | None) -> bool:
    return telegram_id is not None and int(telegram_id) in get_settings().admin_id_set


def limits(telegram_id: int | None = None) -> tuple[int, int]:
    """Gift amount limits; an admin gifts any amount (the cap only guards against a typo)."""
    if is_admin(telegram_id):
        return 1, ADMIN_MAX_RUB
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


def public_base() -> str:
    """https://host of the cabinet, where the gift page and card picture live; '' when there is none."""
    from urllib.parse import urlsplit

    from app.keyboards import mini_app_url

    parts = urlsplit(mini_app_url() or "")
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme == "https" and parts.netloc else ""


def share_link(code: str) -> str:
    """The link people forward: our gift page (it unfurls into a card with a picture), or the bot link without one."""
    base = public_base()
    return f"{base}/g/{code}" if base else gift_link(code)


def card_image() -> str:
    base = public_base()
    return f"{base}/icons/gift-card.jpg" if base else ""


def giver_name(row: dict | None) -> str:
    name = str((row or {}).get("first_name") or "").strip()
    return name[:40] or "Друг"


MAX_COUNT = 100

# Money a gift took from the giver: everything for one still waiting or opened, only the opened part of one
# taken back. Admin gifts are free and do not count.
_GIFTABLE_SQL = """
    SELECT GREATEST(0, LEAST(COALESCE(u.balance_rub, 0),
        COALESCE((SELECT SUM(amount) FROM billing_events
                  WHERE telegram_id=u.telegram_id AND kind='topup' AND source='pay'), 0)
      - COALESCE((SELECT SUM(amount_rub * CASE WHEN status='returned' THEN claimed_count ELSE count END)
                  FROM friend_gifts WHERE from_telegram_id=u.telegram_id AND NOT from_admin), 0)))::int
    FROM users u WHERE u.telegram_id=$1
"""


async def giftable_rub(telegram_id: int, conn=None) -> int:
    """How much of the balance can be gifted: the balance, but not more than the user paid in themselves."""
    if is_admin(telegram_id):
        return ADMIN_MAX_RUB
    q = conn or db._pool_req()
    return int(await q.fetchval(_GIFTABLE_SQL, telegram_id) or 0)


async def create_gift(telegram_id: int, amount: int, count: int = 1) -> dict:
    """One gift, or a giveaway of `count` equal gifts behind one link (first come, one each)."""
    lo, hi = limits(telegram_id)
    admin = is_admin(telegram_id)
    if not get_settings().gifts_enabled:
        raise GiftError("Подарки сейчас недоступны")
    if not isinstance(count, int) or count < 1 or count > MAX_COUNT:
        raise GiftError(f"Подарков может быть от 1 до {MAX_COUNT}")
    if not isinstance(amount, int) or amount < lo:
        raise GiftError(f"Минимальный подарок — {lo} ₽")
    total = amount * count
    if total > hi:
        raise GiftError(f"Всего можно подарить до {hi} ₽ за раз" if count > 1 else f"Максимальный подарок — {hi} ₽")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow("SELECT balance_rub FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id)
            if not user:
                raise GiftError("Пользователь не найден")
            can = await giftable_rub(telegram_id, conn)
            if not admin and total > can:
                raise GiftError(
                    f"Можно подарить до {can} ₽ — это деньги, которые вы сами внесли на баланс"
                    if can else "Сначала пополните баланс — подарить можно только свои деньги"
                )
            code = secrets.token_urlsafe(9)
            gift = await conn.fetchrow(
                """INSERT INTO friend_gifts (code, from_telegram_id, amount_rub, count, from_admin)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id, code, amount_rub, count, status, created_at""",
                code, telegram_id, amount, count, admin,
            )
            what = f"{count} × {amount} ₽" if count > 1 else f"{amount} ₽"
            if admin:
                # An admin's gift is not paid from their balance; the event only records it.
                balance = user["balance_rub"]
                await conn.execute(
                    """INSERT INTO billing_events (telegram_id, kind, source, amount, balance_after, note)
                       VALUES ($1, 'gift_sent', 'admin', 0, $2, $3)""",
                    telegram_id, balance, f"Подарок {what} от администратора, без списания",
                )
            else:
                balance = await conn.fetchval(
                    "UPDATE users SET balance_rub=COALESCE(balance_rub,0)-$2 WHERE telegram_id=$1 RETURNING balance_rub",
                    telegram_id, total,
                )
                await conn.execute(
                    """INSERT INTO billing_events (telegram_id, kind, source, amount, balance_after, note)
                       VALUES ($1, 'gift_sent', 'user', $2, $3, $4)""",
                    telegram_id, -total, balance, "Подарки в группу: " + what if count > 1 else "Подарок другу",
                )
    out = dict(gift)
    out["balance_rub"] = int(balance or 0)
    return out


async def get_gift(code: str, viewer: int | None = None) -> dict | None:
    """The gift with its giver's name; with `viewer`, also whether they took one and said thanks."""
    clean = clean_code(code)
    if not clean:
        return None
    row = await db._pool_req().fetchrow(
        """SELECT g.*, u.first_name AS from_first_name,
                  c.telegram_id IS NOT NULL AS taken_by_viewer, c.thanked_at AS viewer_thanked_at
           FROM friend_gifts g
           LEFT JOIN users u ON u.telegram_id=g.from_telegram_id
           LEFT JOIN friend_gift_claims c ON c.gift_id=g.id AND c.telegram_id=$2
           WHERE g.code=$1""",
        clean, viewer,
    )
    return dict(row) if row else None


async def claim_gift(telegram_id: int, code: str) -> dict:
    """Credit one gift to the friend: once per person, while any are left. Raises GiftError with a text for the user."""
    clean = clean_code(code)
    if not clean:
        raise GiftError("Подарок не найден")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            gift = await conn.fetchrow("SELECT * FROM friend_gifts WHERE code=$1 FOR UPDATE", clean)
            if not gift:
                raise GiftError("Подарок не найден")
            many = int(gift["count"]) > 1
            if int(gift["from_telegram_id"]) == telegram_id:
                raise GiftError("Это ваши подарки — отправьте их друзьям" if many else "Это ваш подарок — отправьте его другу")
            if await conn.fetchval("SELECT 1 FROM friend_gift_claims WHERE gift_id=$1 AND telegram_id=$2", gift["id"], telegram_id):
                raise GiftError("Вы уже забрали свой подарок" if many else "Вы уже открыли этот подарок")
            if gift["status"] == "claimed":
                raise GiftError("Подарки уже разобрали" if many else "Этот подарок уже открыли")
            if gift["status"] != "active":
                raise GiftError("Подарок отменён — даритель забрал его обратно")
            user = await conn.fetchrow(
                "SELECT balance_rub, bot_started_at FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id
            )
            if not user or user["bot_started_at"] is None:
                raise GiftError("Сначала откройте бота по ссылке на подарок")
            amount = int(gift["amount_rub"])
            await conn.execute(
                "INSERT INTO friend_gift_claims (gift_id, telegram_id, amount_rub) VALUES ($1, $2, $3)",
                gift["id"], telegram_id, amount,
            )
            taken = int(gift["claimed_count"]) + 1
            last = taken >= int(gift["count"])
            await conn.execute(
                """UPDATE friend_gifts SET claimed_count=$2,
                   status=CASE WHEN $3 THEN 'claimed' ELSE status END,
                   claimed_at=CASE WHEN $3 THEN NOW() ELSE claimed_at END,
                   claimed_by=CASE WHEN count=1 THEN $4 ELSE claimed_by END
                   WHERE id=$1""",
                gift["id"], taken, last, telegram_id,
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
        "gift_id": int(gift["id"]),
        "amount_rub": amount,
        "balance_rub": int(balance or 0),
        "from_telegram_id": int(gift["from_telegram_id"]),
        "from_name": giver_name(dict(giver) if giver else None),
        "count": int(gift["count"]),
        "claimed_count": taken,
        "last": last,
    }


async def claimer_names(gift_id: int) -> list[str]:
    rows = await db._pool_req().fetch(
        """SELECT u.first_name FROM friend_gift_claims c LEFT JOIN users u ON u.telegram_id=c.telegram_id
           WHERE c.gift_id=$1 ORDER BY c.claimed_at""",
        gift_id,
    )
    return [giver_name(dict(r)) for r in rows]


async def return_gift(telegram_id: int, code: str) -> dict:
    """The giver takes back what nobody has opened yet: a whole gift, or the rest of a giveaway."""
    clean = clean_code(code)
    if not clean:
        raise GiftError("Подарок не найден")
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            gift = await conn.fetchrow("SELECT * FROM friend_gifts WHERE code=$1 FOR UPDATE", clean)
            if not gift or int(gift["from_telegram_id"]) != telegram_id:
                raise GiftError("Подарок не найден")
            if gift["status"] == "claimed":
                raise GiftError("Подарки уже разобрали" if int(gift["count"]) > 1 else "Друг уже открыл этот подарок")
            if gift["status"] != "active":
                raise GiftError("Подарок уже вернулся на ваш баланс")
            user = await conn.fetchrow("SELECT balance_rub FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id)
            left = int(gift["count"]) - int(gift["claimed_count"])
            amount = int(gift["amount_rub"]) * left
            await conn.execute(
                "UPDATE friend_gifts SET status='returned', returned_at=NOW() WHERE id=$1", gift["id"]
            )
            if gift["from_admin"]:
                # Nothing was taken from the admin's balance, so nothing goes back: the gift is simply cancelled.
                return {"amount_rub": 0, "left": left, "balance_rub": int(user["balance_rub"] or 0) if user else 0}
            balance = await conn.fetchval(
                """UPDATE users SET balance_rub=COALESCE(balance_rub,0)+$2, low_balance_notified_at=NULL
                   WHERE telegram_id=$1 RETURNING balance_rub""",
                telegram_id, amount,
            )
            await conn.execute(
                """INSERT INTO billing_events (telegram_id, kind, source, amount, balance_after, note)
                   VALUES ($1, 'gift_return', 'user', $2, $3, $4)""",
                telegram_id, amount, balance,
                f"Не забрали {left} из {gift['count']} — вернули на баланс" if int(gift["count"]) > 1
                else "Подарок не открыли — вернули на баланс",
            )
    return {"amount_rub": amount, "left": left, "balance_rub": int(balance or 0)}


async def mark_thanked(telegram_id: int, code: str) -> dict | None:
    """Each friend says thanks once; returns the gift when this is their first «спасибо»."""
    clean = clean_code(code)
    if not clean:
        return None
    row = await db._pool_req().fetchrow(
        """UPDATE friend_gift_claims c SET thanked_at=NOW()
           FROM friend_gifts g
           WHERE g.code=$1 AND c.gift_id=g.id AND c.telegram_id=$2 AND c.thanked_at IS NULL
           RETURNING g.from_telegram_id, g.amount_rub""",
        clean, telegram_id,
    )
    return dict(row) if row else None


async def list_sent(telegram_id: int, limit: int = 20) -> list[dict]:
    rows = await db._pool_req().fetch(
        """SELECT g.code, g.amount_rub, g.count, g.claimed_count, g.status, g.created_at, g.claimed_at,
                  u.first_name AS friend_name
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
            "url": share_link(r["code"]),
            "amount_rub": int(r["amount_rub"]),
            "count": int(r.get("count") or 1),
            "claimed_count": int(r.get("claimed_count") or 0),
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


def open_button(code: str, text: str = "🎁 Открыть подарок"):
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
    return InlineKeyboardButton(text=text, style="success",
                                web_app=WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query)))))


def _gifts_word(n: int) -> str:
    return _plural(n, "подарок", "подарка", "подарков")


def share_text(name: str, amount: int, count: int = 1) -> str:
    if count > 1:
        return (f"🎁 {name} раздаёт {count} {_gifts_word(count)} по {amount} ₽ на VPN — это ≈ {days_text(amount)} каждому. "
                "Кто первый — того и подарок!")
    return f"🎁 {name} дарит вам {amount} ₽ на VPN — это ≈ {days_text(amount)}. Откройте подарок, пока он не остыл!"


async def prepare_share(bot, telegram_id: int, code: str, amount: int, name: str, count: int = 1) -> str | None:
    """A ready card for Telegram's «share» sheet (WebApp.shareMessage). None when Telegram refuses."""
    from aiogram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        InlineQueryResultArticle,
        InlineQueryResultPhoto,
        InputTextMessageContent,
    )

    if bot is None:
        return None
    try:
        title = f"{count} {_gifts_word(count)} по {amount} ₽ на VPN" if count > 1 else f"Подарок {amount} ₽ на VPN"
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎁 Забрать подарок" if count > 1 else "🎁 Открыть подарок", url=gift_link(code)),
        ]])
        picture = card_image()
        # The card: the gift picture with the text under it and one button; a plain text card without a public URL.
        result = InlineQueryResultPhoto(
            id=f"gift-{code}"[:64], photo_url=picture, thumbnail_url=picture, photo_width=1200, photo_height=630,
            title=title, caption=share_text(name, amount, count), reply_markup=markup,
        ) if picture else InlineQueryResultArticle(
            id=f"gift-{code}"[:64], title=title,
            description=f"≈ {days_text(amount)} VPN {'каждому ' if count > 1 else ''}от {name}",
            input_message_content=InputTextMessageContent(message_text=share_text(name, amount, count)),
            reply_markup=markup,
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

    me = message.from_user.id
    gift = await get_gift(code, me)
    if not gift:
        await message.answer("Этот подарок не найден. Попросите друга прислать ссылку ещё раз.")
        return False
    name = giver_name({"first_name": gift.get("from_first_name")})
    amount, count = int(gift["amount_rub"]), int(gift.get("count") or 1)
    left = count - int(gift.get("claimed_count") or 0)
    if int(gift["from_telegram_id"]) == me:
        text = (f"🎁 Это ваши подарки: {count} × {amount} ₽, осталось {left}. Отправьте ссылку в группу — друзья заберут по одному."
                if count > 1 else f"🎁 Это ваш подарок на {amount} ₽. Отправьте ссылку другу — он откроет его у себя.")
    elif gift.get("taken_by_viewer"):
        text = "🎁 Вы уже забрали свой подарок — деньги на балансе."
    elif gift["status"] == "claimed":
        text = "Подарки уже разобрали — вы не успели." if count > 1 else "Этот подарок уже открыли."
    elif gift["status"] != "active":
        text = "Этот подарок отменён: даритель забрал его обратно."
    elif count > 1:
        text = (f"🎁 <b>{_html(name)}</b> раздаёт подарки: <b>{amount} ₽</b> на VPN каждому — это ≈ {days_text(amount)}.\n\n"
                f"Осталось {left} из {count}. Заберите свой, пока не разобрали!")
    else:
        text = f"🎁 <b>{_html(name)}</b> дарит вам <b>{amount} ₽</b> на VPN — это ≈ {days_text(amount)}.\n\nОткройте подарок, и деньги сразу лягут на баланс."
    show = gift["status"] == "active" or gift.get("taken_by_viewer")
    btn = open_button(gift["code"], "🎁 Забрать подарок" if count > 1 else "🎁 Открыть подарок") if show else None
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


async def notify_giveaway_done(bot, giver_id: int, gift_id: int, count: int, amount: int) -> None:
    """A giveaway sends one message when the last gift is taken, not one per friend."""
    if bot is None:
        return
    names = await claimer_names(gift_id)
    shown = ", ".join(_html(n) for n in names[:5]) + (f" и ещё {len(names) - 5}" if len(names) > 5 else "")
    try:
        await bot.send_message(
            giver_id,
            f"🎁 <b>Все {count} {_gifts_word(count)} разобрали!</b>\n\nЗабрали: {shown}.\n"
            f"По {amount} ₽ на баланс каждому — всего {amount * count} ₽.\n\nСпасибо, что делитесь ❤️",
            parse_mode="HTML",
        )
    except Exception:
        logger.info("Giveaway summary not delivered to %s", giver_id, exc_info=True)


def landing_html(gift: dict | None, code: str) -> str:
    """/g/CODE: a page whose preview in a chat is the gift card; opening it goes on to the bot."""
    import html

    bot = gift_link(code)
    if gift:
        name = giver_name({"first_name": gift.get("from_first_name")})
        amount, count = int(gift["amount_rub"]), int(gift.get("count") or 1)
        title = (f"🎁 {name} раздаёт {count} {_gifts_word(count)} по {amount} ₽ на VPN" if count > 1
                 else f"🎁 {name} дарит вам {amount} ₽ на VPN")
        desc = f"Это ≈ {days_text(amount)} VPN{' каждому' if count > 1 else ''}. Нажмите, чтобы забрать подарок."
    else:
        title, desc = "🎁 Подарок на VPN", "Нажмите, чтобы открыть подарок в Telegram."
    e = lambda t: html.escape(t, quote=True)  # noqa: E731
    img = card_image()
    meta = "".join(f'<meta property="{k}" content="{e(v)}">' for k, v in (
        ("og:type", "website"), ("og:title", title), ("og:description", desc), ("og:image", img),
        ("og:image:width", "1200"), ("og:image:height", "630")) if v)
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>{meta}
<meta name="twitter:card" content="summary_large_image"><meta http-equiv="refresh" content="0;url={e(bot)}">
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#111215;color:#fff;
font-family:-apple-system,system-ui,sans-serif;text-align:center}}a{{display:inline-block;margin-top:18px;padding:14px 26px;border-radius:99px;
background:#fff;color:#1d2340;font-weight:700;text-decoration:none}}</style></head>
<body><div><div style="font-size:64px">🎁</div><div style="font-size:22px;font-weight:700">{e(title)}</div>
<a href="{e(bot)}">Открыть в Telegram</a></div></body></html>"""
