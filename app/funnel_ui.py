"""Shared navigation for customer funnel messages (including tracked deep links)."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.keyboards import cabinet_button

CTA = 'Откройте личный кабинет 👇'


def funnel_body(body: str) -> str:
    if CTA in body:
        return body
    marker = 'Продолжая работу с ботом или открывая кабинет, вы принимаете '
    if marker in body:
        before, after = body.split(marker, 1)
        return before.rstrip() + '\n\n' + CTA + '\n\n' + marker + after
    return body.rstrip() + '\n\n' + CTA


def funnel_keyboard(markup=None):
    buttons = [b for row in markup.inline_keyboard for b in row] if markup else []
    # Keep the intended gift/connect/topup destination on the primary button.
    primary = next((b for b in buttons if b.web_app), None) or cabinet_button()
    if primary is None:
        primary = InlineKeyboardButton(text='Личный кабинет', callback_data='help:connect')
    primary = primary.model_copy(update={'text': 'Личный кабинет', 'style': 'success'})
    rows = [[primary], [InlineKeyboardButton(text='В главное меню', callback_data='profile')]]
    seen = set()
    for button in buttons:
        if button.web_app or button.callback_data == 'profile':
            continue
        if button.text in ('Открыть кабинет', 'Личный кабинет'):
            continue
        identity = (button.callback_data, button.url, str(button.copy_text))
        if identity in seen:
            continue
        seen.add(identity)
        rows.append([button.model_copy(update={'style': None})])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_funnel_message(bot, chat_id, text, **kwargs):
    kwargs['reply_markup'] = funnel_keyboard(kwargs.get('reply_markup'))
    return await bot.send_message(chat_id, funnel_body(text), **kwargs)


async def answer_funnel(message, text, **kwargs):
    kwargs['reply_markup'] = funnel_keyboard(kwargs.get('reply_markup'))
    return await message.answer(funnel_body(text), **kwargs)


async def edit_funnel(message, text, **kwargs):
    kwargs['reply_markup'] = funnel_keyboard(kwargs.get('reply_markup'))
    return await message.edit_text(funnel_body(text), **kwargs)
