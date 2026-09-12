from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app import db
from app.handlers.start import ack
from app.notices import notice_text

router = Router()

CABINET_SESSION_DAYS = 365


def _challenge_id(data: str | None, prefix: str) -> str:
    raw = data or ""
    if not raw.startswith(prefix):
        return ""
    return raw[len(prefix) :].strip()


@router.callback_query(F.data.startswith("lk:y:"))
async def cabinet_login_yes(callback: CallbackQuery) -> None:
    cid = _challenge_id(callback.data, "lk:y:")
    if not cid or not callback.from_user:
        await ack(callback, notice_text("cabinet_login_gone"))
        return
    token = await db.approve_cabinet_login_challenge(
        cid, int(callback.from_user.id), CABINET_SESSION_DAYS
    )
    if not token:
        await ack(callback, notice_text("cabinet_login_gone"))
        try:
            await callback.message.edit_text(notice_text("cabinet_login_gone"))
        except Exception:
            pass
        return
    text = notice_text("cabinet_login_ok")
    try:
        await callback.message.edit_text(text)
    except Exception:
        pass
    await ack(callback, "Подтверждено")


@router.callback_query(F.data.startswith("lk:n:"))
async def cabinet_login_no(callback: CallbackQuery) -> None:
    cid = _challenge_id(callback.data, "lk:n:")
    if not cid or not callback.from_user:
        await ack(callback, notice_text("cabinet_login_gone"))
        return
    ok = await db.decline_cabinet_login_challenge(cid, int(callback.from_user.id))
    text = notice_text("cabinet_login_no") if ok else notice_text("cabinet_login_gone")
    try:
        await callback.message.edit_text(text)
    except Exception:
        pass
    await ack(callback)
