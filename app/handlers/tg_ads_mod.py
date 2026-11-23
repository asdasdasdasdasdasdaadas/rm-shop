"""Buttons under the Telegram Ads alerts: «На паузу», «Вернуть остаток» and the weekly hours offer (admins only)."""
from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings

router = Router()
logger = logging.getLogger("rm-shop.tg-ads-mod")


def _ad(data: str) -> int | None:
    try:
        return int(data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


async def _done(callback: CallbackQuery, line: str) -> None:
    """Drop the buttons and say under the alert what was done and by whom."""
    msg = callback.message
    if msg is None:
        return
    who = escape(callback.from_user.first_name or str(callback.from_user.id))
    try:
        await msg.edit_text(f"{msg.html_text}\n\n{line} — {who}", parse_mode="HTML", reply_markup=None)
    except Exception:
        logger.debug("Тревога Telegram Ads не обновилась", exc_info=True)


@router.callback_query(F.data.startswith("tga_pause:") | F.data.startswith("tga_refund:"))
async def tg_ads_action(callback: CallbackQuery) -> None:
    from app import tg_ads, tg_cabinet
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    ad_id = _ad(callback.data or "")
    if not ad_id:
        await callback.answer("Нет объявления", show_alert=True)
        return
    refund = (callback.data or "").startswith("tga_refund:")
    try:
        if refund:
            await tg_cabinet.refund(ad_id)
        else:
            await tg_cabinet.set_paused(ad_id, True)
    except (ValueError, tg_ads.TgAdsError) as exc:
        await callback.answer(str(exc)[:190], show_alert=True)
        return
    if refund:
        await callback.answer("На паузе, остаток вернётся на баланс через 10 минут")
        await _done(callback, "↩️ На паузе, остаток вернётся на баланс кабинета через 10 минут")
    else:
        await callback.answer("На паузе")
        await _done(callback, "⏸ Поставлено на паузу")


@router.callback_query(F.data.startswith("tga_sched:"))
async def tg_ads_schedule(callback: CallbackQuery) -> None:
    from app import tg_schedule
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    apply = callback.data == "tga_sched:apply"
    text = await (tg_schedule.apply_offer() if apply else tg_schedule.skip_offer())
    await callback.answer(text[:190])
    await _done(callback, ("🕒 " if apply else "") + text)
