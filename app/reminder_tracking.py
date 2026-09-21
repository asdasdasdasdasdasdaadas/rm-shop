"""Best-effort reminder analytics; failures must not interrupt delivery or navigation."""
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from aiogram import BaseMiddleware
from app import db

logger = logging.getLogger(__name__)


def tracked_keyboard(markup, token):
    if not markup:
        return markup
    rows=[]
    for row in markup.inline_keyboard:
        buttons=[]
        for button in row:
            if button.web_app:
                parts=urlsplit(button.web_app.url)
                query=dict(parse_qsl(parts.query))
                query['nt']=token
                button=button.model_copy(update={'web_app':button.web_app.model_copy(update={'url':urlunsplit(parts._replace(query=urlencode(query)))})})
            buttons.append(button)
        rows.append(buttons)
    return markup.model_copy(update={'inline_keyboard':rows})


async def send_reminder(bot, telegram_id, body, *, kind, title, reply_markup):
    token=None
    try:
        token=await db.create_reminder_delivery(telegram_id,kind,title,body)
        reply_markup=tracked_keyboard(reply_markup,token)
    except Exception:
        logger.debug('Reminder tracking unavailable',exc_info=True)
    try:
        message=await bot.send_message(telegram_id,body,reply_markup=reply_markup)
    except Exception:
        if token:
            await _finish(token,'failed',None)
        raise
    if token:
        await _finish(token,'sent',getattr(message,'message_id',None))
    return message


async def _finish(token,status,message_id):
    try:
        await db.finish_reminder_delivery(token,status,message_id)
    except Exception:
        logger.debug('Reminder status tracking failed',exc_info=True)


class ReminderClickMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        message=getattr(event,'message',None)
        if message and getattr(event,'from_user',None):
            try:
                await db.record_reminder_click(event.from_user.id,message_id=message.message_id)
            except Exception:
                logger.debug('Reminder callback tracking failed',exc_info=True)
        return await handler(event,data)
