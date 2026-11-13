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
    per_day = max(1, int(day_price)) * max(1, int(devices))
    days = max(0, int(balance)) // per_day
    if days >= 1:
        from app.texts import days_text
        left = f"хватит примерно на {days_text(days)}"
    else:
        left = "меньше чем на сутки"
    return f'\n\nОстаток: <b>{rub_text(balance)}</b>, {left}.'


def balance_keyboard(*, promise: bool = False, browser: bool = False):
    """browser: «💻 Пополнить с компьютера» for someone who has never opened the cabinet in a browser."""
    from aiogram.types import InlineKeyboardButton
    from app.keyboards import payment_nudge_keyboard
    markup = with_promise(payment_nudge_keyboard(label='Пополнить баланс'), promise)
    extra = [[InlineKeyboardButton(text='💻 Пополнить с компьютера', callback_data='brw:link')]] if browser else []
    return markup.model_copy(update={'inline_keyboard': markup.inline_keyboard + extra + [[
        InlineKeyboardButton(text='Главное меню', callback_data='profile')
    ]]})


def with_promise(markup, promise: bool):
    """Add «Обещанный платёж» under the top-up button when the person can take one right now."""
    if not promise or markup is None:
        return markup
    from aiogram.types import InlineKeyboardButton
    from app.keyboards import mini_app_screen
    app = mini_app_screen("promise")
    if not app:
        return markup
    button = InlineKeyboardButton(text='🤝 Обещанный платёж', web_app=app)
    rows = list(markup.inline_keyboard)
    return markup.model_copy(update={'inline_keyboard': rows[:1] + [[button]] + rows[1:]})
