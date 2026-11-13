from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app import db
from app.cabinet_login import approved_text, request_text
from app.handlers.start import ack
from app.keyboards import cabinet_login_keyboard, cabinet_session_keyboard
from app.notices import notice_text

router = Router()

CABINET_SESSION_DAYS = 365


def _challenge_id(data: str | None, prefix: str) -> str:
    raw = data or ""
    if not raw.startswith(prefix):
        return ""
    return raw[len(prefix) :].strip()


async def open_from_start(message: Message, challenge_id: str) -> None:
    """/start lk_<id> from «Войти через Telegram»: the request becomes this person's and asks «Это вы?»."""
    uid = int(message.from_user.id)
    row = None
    if not await db.user_is_blocked(uid):
        row = await db.bind_cabinet_login_challenge(challenge_id, uid)
    if not row:
        await message.answer(notice_text("cabinet_login_gone"))
        return
    await message.answer(
        request_text(row.get("device"), row.get("created_at")),
        reply_markup=cabinet_login_keyboard(challenge_id),
    )


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
    row = await db.get_cabinet_login_challenge(cid)
    try:
        await callback.message.edit_text(
            approved_text((row or {}).get("device")),
            reply_markup=cabinet_session_keyboard(db.cabinet_token_ref(token)),
        )
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


@router.callback_query(F.data.startswith("lk:x:"))
async def cabinet_session_end(callback: CallbackQuery) -> None:
    """«Это был не я — завершить сеанс» under a confirmed login."""
    ref = _challenge_id(callback.data, "lk:x:")
    if callback.from_user and ref:
        await db.end_cabinet_session(int(callback.from_user.id), ref)
    try:
        await callback.message.edit_text(notice_text("cabinet_login_ended"))
    except Exception:
        pass
    await ack(callback, "Сеанс завершён")
