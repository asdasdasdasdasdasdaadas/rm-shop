from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings
from app.payouts import finish_referral_payout

router = Router()


def _pid(data: str) -> int | None:
    try:
        return int(data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


@router.callback_query(F.data.startswith("po_ok:"))
async def payout_ok(callback: CallbackQuery) -> None:
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    pid = _pid(callback.data or "")
    if not pid:
        await callback.answer("Нет заявки", show_alert=True)
        return
    result = await finish_referral_payout(callback.bot, pid, "paid", callback.from_user.id)
    await callback.answer(result)
    if callback.message:
        try:
            prev = callback.message.html_text or callback.message.text or ""
            await callback.message.edit_text(f"{prev}\n\n{result}.", reply_markup=None)
        except Exception:
            pass


@router.callback_query(F.data.startswith("po_no:"))
async def payout_no(callback: CallbackQuery) -> None:
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    pid = _pid(callback.data or "")
    if not pid:
        await callback.answer("Нет заявки", show_alert=True)
        return
    result = await finish_referral_payout(callback.bot, pid, "rejected", callback.from_user.id)
    await callback.answer(result)
    if callback.message:
        try:
            prev = callback.message.html_text or callback.message.text or ""
            await callback.message.edit_text(f"{prev}\n\n{result}.", reply_markup=None)
        except Exception:
            pass
