"""Presentation shared by balance reminders and their preview."""
from app.button_icons import PINNED_ICONS

BALANCE_ENDING = (
    f'<tg-emoji emoji-id="{PINNED_ICONS["about"]}">ℹ️</tg-emoji> <b>Баланс на исходе</b>\n\n'
    '<blockquote>Пополните сейчас, чтобы не отвлекаться на оплату во время просмотра или переписки.</blockquote>'
)
BALANCE_EMPTY = (
    f'<tg-emoji emoji-id="{PINNED_ICONS["pay"]}">💰</tg-emoji> <b>Пора пополнить баланс</b>\n\n'
    '<blockquote>Не хватает средств на следующие сутки VPN. Пополните баланс, чтобы продолжить пользоваться сервисом.</blockquote>'
)


def balance_details(balance: int, devices: int, day_price: int) -> str:
    def rub_text(value):
        return f"{value:,} ₽".replace(",", " ")
    return f'\n\nОстаток: <b>{rub_text(balance)}</b>'


def balance_keyboard():
    from aiogram.types import InlineKeyboardButton
    from app.keyboards import payment_nudge_keyboard
    markup = payment_nudge_keyboard(label='Пополнить баланс')
    return markup.model_copy(update={'inline_keyboard': markup.inline_keyboard + [[
        InlineKeyboardButton(text='Главное меню', callback_data='profile')
    ]]})
