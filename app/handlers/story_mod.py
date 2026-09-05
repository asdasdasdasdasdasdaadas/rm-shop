from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings
from app.remnawave import RemnawaveClient
from app.story import approve_story, close_story_admin_messages, reject_story

router = Router()


def _uid(data: str) -> int | None:
    try:
        return int(data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


@router.callback_query(F.data.startswith("st_ok:"))
async def story_ok(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    uid = _uid(callback.data or "")
    if not uid:
        await callback.answer("Нет пользователя", show_alert=True)
        return
    result = await approve_story(rw, callback.bot, uid)
    await close_story_admin_messages(callback.bot, uid, result)
    await callback.answer(result)


@router.callback_query(F.data.startswith("st_no:"))
async def story_no(callback: CallbackQuery) -> None:
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    uid = _uid(callback.data or "")
    if not uid:
        await callback.answer("Нет пользователя", show_alert=True)
        return
    result = await reject_story(callback.bot, uid)
    await close_story_admin_messages(callback.bot, uid, result)
    await callback.answer(result)
