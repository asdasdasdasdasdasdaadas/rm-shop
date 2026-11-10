"""Best-effort reminder analytics; failures must not interrupt delivery or navigation."""
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramForbiddenError
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


BALANCE_WIDGET_KINDS = {'nudge_trial_end', 'low_balance'}
# Setup reminders go out as a live checklist; «balance is ending» as a ticking countdown.
SETUP_WIDGET_KINDS = {'first_device_thanks', 'nudge_device', 'nudge_nodevice'}


async def _care_widget(bot, kind, telegram_id, body, reply_markup):
    if len(body) > 1024:
        return None
    from app import widgets_care
    if kind == 'nudge_trial_end':
        return await widgets_care.send_countdown_widget(bot, telegram_id, caption=body, reply_markup=reply_markup)
    if kind in SETUP_WIDGET_KINDS:
        return await widgets_care.send_setup_widget(bot, telegram_id, caption=body, reply_markup=reply_markup)
    return None


def with_ton_button(markup):
    """Put «Gram (TON)» next to the first (top-up) button of a balance reminder, when that payment is on."""
    from app.keyboards import ton_button
    button = ton_button()
    if not button or not markup or not markup.inline_keyboard:
        return markup
    rows = [list(row) for row in markup.inline_keyboard]
    if any(b.callback_data == 'ton_pay' for row in rows for b in row):
        return markup
    if len(rows[0]) == 1:
        rows[0].append(button)
    else:
        rows.insert(1, [button])
    return markup.model_copy(update={'inline_keyboard': rows})


async def send_reminder(bot, telegram_id, body, *, kind, title, reply_markup, preserve=False, step_id=None):
    from app.funnel_ui import funnel_body, funnel_keyboard
    if not preserve:
        body = funnel_body(body)
        reply_markup = funnel_keyboard(reply_markup)
    token=None
    try:
        token=await db.create_reminder_delivery(telegram_id,kind,title,body,step_id=step_id)
        reply_markup=tracked_keyboard(reply_markup,token)
    except Exception:
        logger.debug('Reminder tracking unavailable',exc_info=True)
    if kind in BALANCE_WIDGET_KINDS:
        try:
            reply_markup = with_ton_button(reply_markup)
        except Exception:
            logger.debug('Кнопка Gram (TON) не добавлена', exc_info=True)
    try:
        from pathlib import Path
        from aiogram.types import FSInputFile
        banner = Path(__file__).parent / 'assets' / 'balance-reminder.png'
        message = None
        if kind == 'nudge_trial_end' or kind in SETUP_WIDGET_KINDS:
            try:
                message = await _care_widget(bot, kind, telegram_id, body, reply_markup)
            except TelegramForbiddenError:
                raise
            except Exception:
                logger.warning('Виджет %s не отправился', kind, exc_info=True)
        if message is None and kind in BALANCE_WIDGET_KINDS and len(body) <= 1024:
            # A live balance widget with a countdown; old Telegram apps show the caption, errors fall back to the banner.
            from app.widgets import send_balance_widget
            try:
                message = await send_balance_widget(bot, telegram_id, caption=body, reply_markup=reply_markup)
            except TelegramForbiddenError:
                raise
            except Exception:
                logger.warning('Виджет баланса не отправился, шлём баннер', exc_info=True)
        if message is None and kind in BALANCE_WIDGET_KINDS and banner.is_file() and len(body) <= 1024:
            message = await bot.send_photo(telegram_id, FSInputFile(banner), caption=body,
                                           parse_mode='HTML', reply_markup=reply_markup)
        elif message is None:
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
        if getattr(event, "data", None) == "funnel_test:click":
            return await handler(event, data)
        message=getattr(event,'message',None)
        if message and getattr(event,'from_user',None):
            try:
                await db.record_reminder_click(event.from_user.id,message_id=message.message_id)
            except Exception:
                logger.debug('Reminder callback tracking failed',exc_info=True)
        return await handler(event,data)
