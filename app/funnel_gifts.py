"""Gift days inside funnel messages: one tap credits N days of VPN for the user's devices."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app import db
from app.config import get_settings
from app.texts import days_text, rub_text

logger = logging.getLogger(__name__)

GIFT_DAYS = 3
VALID_DAYS = 7
COOLDOWN_DAYS = 14
ACTION = "claim_gift"

router = Router()


def gift_label() -> str:
    return days_text(GIFT_DAYS)


async def can_issue(telegram_id: int) -> bool:
    """At most one gift per user per cooldown, claimed or not."""
    return not await db._pool_req().fetchval(
        "SELECT EXISTS (SELECT 1 FROM funnel_gifts WHERE telegram_id=$1 "
        "AND created_at > NOW() - ($2::int * INTERVAL '1 day'))",
        int(telegram_id), COOLDOWN_DAYS,
    )


async def issue(telegram_id: int, step_id: str) -> int | None:
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT 1 FROM users WHERE telegram_id=$1 FOR UPDATE", int(telegram_id))
            recent = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM funnel_gifts WHERE telegram_id=$1 "
                "AND created_at > NOW() - ($2::int * INTERVAL '1 day'))",
                int(telegram_id), COOLDOWN_DAYS,
            )
            if recent:
                return None
            return await conn.fetchval(
                """INSERT INTO funnel_gifts (telegram_id, step_id, days, expires_at)
                   VALUES ($1, $2, $3, NOW() + ($4::int * INTERVAL '1 day')) RETURNING id""",
                int(telegram_id), str(step_id)[:40], GIFT_DAYS, VALID_DAYS,
            )


async def issue_for_broadcast(telegram_id: int, run_id: int | None) -> int:
    """Gift for the admin «+3 дня всем» broadcast: everyone gets one, regardless of the funnel cooldown."""
    return await db._pool_req().fetchval(
        """INSERT INTO funnel_gifts (telegram_id, step_id, days, expires_at)
           VALUES ($1, $2, $3, NOW() + ($4::int * INTERVAL '1 day')) RETURNING id""",
        int(telegram_id), f"broadcast:{run_id or 0}"[:40], GIFT_DAYS, VALID_DAYS,
    )


async def cancel(gift_id: int) -> None:
    """The message did not go out: forget the gift so the cooldown does not start."""
    await db._pool_req().execute("DELETE FROM funnel_gifts WHERE id=$1 AND claimed_at IS NULL", int(gift_id))


async def claim(telegram_id: int, gift_id: int) -> dict:
    price = max(1, int(get_settings().vpn_day_price_rub or 1))
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow(
                "SELECT balance_rub FROM users WHERE telegram_id=$1 FOR UPDATE", int(telegram_id))
            gift = await conn.fetchrow(
                "SELECT *, expires_at <= NOW() AS expired FROM funnel_gifts WHERE id=$1 FOR UPDATE", int(gift_id))
            if not user or not gift or int(gift["telegram_id"]) != int(telegram_id):
                raise ValueError("Подарок не найден")
            if gift["claimed_at"] is not None:
                raise ValueError("Подарок уже получен")
            if gift["expired"]:
                raise ValueError("Срок подарка истёк")
            devices = max(1, int(await conn.fetchval(
                "SELECT COUNT(*) FROM devices WHERE telegram_id=$1 AND COALESCE(kind,'') <> 'router'",
                int(telegram_id)) or 0))
            gift_rub = int(gift["days"]) * price * devices
            # Like the old return promo: clear a negative balance too, so access really starts working.
            debt = max(0, -int(user["balance_rub"] or 0))
            amount = gift_rub + debt
            balance = await conn.fetchval(
                """UPDATE users SET balance_rub=COALESCE(balance_rub,0)+$2,
                   low_balance_notified_at=NULL, trial_end_nudge_at=NULL
                   WHERE telegram_id=$1 RETURNING balance_rub""", int(telegram_id), amount)
            await conn.execute(
                "UPDATE funnel_gifts SET claimed_at=NOW(), gift_rub=$2, debt_repaid_rub=$3 WHERE id=$1",
                int(gift_id), gift_rub, debt)
            await conn.execute(
                """INSERT INTO billing_events (telegram_id,kind,source,amount,balance_after,note)
                   VALUES ($1,'promo','funnel_gift',$2,$3,$4)""",
                int(telegram_id), amount, balance,
                f"Подарок из воронки ({gift['step_id']}): {gift['days']} дн., {gift_rub} ₽, погашение минуса {debt} ₽")
            return {"days": int(gift["days"]), "devices": devices, "gift_rub": gift_rub,
                    "debt_repaid_rub": debt, "balance_rub": int(balance)}


@router.callback_query(F.data.startswith("fgift:"))
async def claim_button(callback: CallbackQuery) -> None:
    from app.keyboards import cabinet_keyboard
    raw = (callback.data or "").split(":", 1)[1]
    if not raw.isdigit():
        await callback.answer("Подарок не найден", show_alert=True)
        return
    try:
        result = await claim(callback.from_user.id, int(raw))
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except Exception:
        logger.exception("Подарок из воронки не начислен %s", callback.from_user.id)
        await callback.answer("Не получилось, попробуйте ещё раз", show_alert=True)
        return
    await callback.answer("Подарок начислен 🎁")
    text = (f"🎁 Начислили <b>{rub_text(result['gift_rub'])}</b> — это {days_text(result['days'])} VPN "
            f"для ваших устройств: {result['devices']}.")
    if result["debt_repaid_rub"]:
        text += f"\nМинус на балансе ({rub_text(result['debt_repaid_rub'])}) тоже погасили."
    text += "\n\nВключите VPN в приложении — доступ уже работает."
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except (TelegramBadRequest, AttributeError):
        pass
    try:
        await callback.message.answer(text, reply_markup=cabinet_keyboard())
    except Exception:
        logger.debug("Не удалось написать о подарке", exc_info=True)
