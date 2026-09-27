"""Show the legal footer until the user's next interaction, preserving the menu."""
import logging

from aiogram import BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import SendMessage, EditMessageText
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions

from app import db

logger = logging.getLogger(__name__)
MARKER = "Продолжая работу с ботом или открывая кабинет, вы принимаете "


def without_notice(text: str) -> str:
    return text.split(MARKER, 1)[0].rstrip()


class LegalNoticeRequestMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        if not isinstance(method, (SendMessage, EditMessageText)) or MARKER not in method.text:
            return await make_request(bot, method)
        try:
            telegram_id = int(method.chat_id)
        except (TypeError, ValueError):
            return await make_request(bot, method)
        if telegram_id <= 0:
            return await make_request(bot, method)
        local = await db.get_user(telegram_id)
        clean = without_notice(method.text)
        if local and local.get("accepted_legal_at") and clean:
            method = method.model_copy(update={"text": clean})
        result = await make_request(bot, method)
        if MARKER in method.text and isinstance(result, Message) and clean:
            markup = method.reply_markup.model_dump_json() if method.reply_markup else None
            await db.remember_legal_message(telegram_id, result.message_id, clean, markup)
            await db.mark_legal_notice(telegram_id)
        return result


class LegalNoticeInteractionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, CallbackQuery) and event.data == "funnel_test:click":
            return await handler(event, data)
        if not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return await handler(event, data)
        message = event.message if isinstance(event, CallbackQuery) else event
        if not isinstance(message, Message) or message.chat.type != "private":
            return await handler(event, data)
        telegram_id = event.from_user.id
        bot = data["bot"]
        await db.accept_legal_after_notice(telegram_id)
        pending = await db.pending_legal_messages(telegram_id)
        # Old menus sent before this feature can be cleaned when clicked too.
        if isinstance(event, CallbackQuery) and MARKER in (message.text or ""):
            if not any(row["message_id"] == message.message_id for row in pending):
                pending.append({"message_id": message.message_id,
                                "body": without_notice(message.html_text),
                                "markup": message.reply_markup.model_dump_json() if message.reply_markup else None})
        await hide_legal_messages(bot, telegram_id, pending)
        return await handler(event, data)


async def hide_legal_messages(bot, telegram_id: int, pending=None):
    if pending is None:
        pending = await db.pending_legal_messages(telegram_id)
    from aiogram.types import InlineKeyboardMarkup
    for row in pending:
        try:
            markup = InlineKeyboardMarkup.model_validate_json(row["markup"]) if row.get("markup") else None
            await bot.edit_message_text(row["body"], chat_id=telegram_id,
                                       message_id=row["message_id"], parse_mode="HTML",
                                       reply_markup=markup,
                                       link_preview_options=LinkPreviewOptions(is_disabled=True))
            await db.forget_legal_message(telegram_id, row["message_id"])
        except Exception:
            logger.warning("Cannot hide legal footer telegram=%s message=%s", telegram_id, row["message_id"], exc_info=True)
