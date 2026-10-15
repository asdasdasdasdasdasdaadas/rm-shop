"""Personal five-day recovery offers, with durable retries and shared contact limits."""
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from app import db
from app.config import get_settings
from app.keyboards import mini_app_url
from app.notices import notice_text
from app.texts import rub_text

logger = logging.getLogger(__name__)


def keyboard():
    url = mini_app_url()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Личный кабинет',web_app=WebAppInfo(url=url),style='success')]
        if url else [InlineKeyboardButton(text='Личный кабинет',callback_data='help:connect',style='success')],
        [InlineKeyboardButton(text='Главное меню',callback_data='profile')],
    ])


def _terms(code: str, count: int, amount: int) -> str:
    return (f'\n\n<code>{code}</code>\n\n'
            f'Начислим {rub_text(amount)} — на 5 дней для ваших устройств: {count}. '
            'Минус погасим отдельно.\n\n'
            'Введите код в разделе «Промокод» в кабинете. '
            'Он действует 7 дней, только для вас и один раз. '
            'Если добавите устройства, подарка хватит на меньший срок.')


def message(code: str, count: int, amount: int, custom: str | None = None) -> str:
    terms = _terms(code, count, amount)
    raw = (custom or '').strip()
    if not raw:
        return notice_text('winback_promo', code=code, devices=str(count), amount=rub_text(amount)) + terms
    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return '{' + key + '}'
    try:
        body = raw.format_map(_Safe({'code': code, 'devices': str(count), 'amount': rub_text(amount)}))
    except Exception:
        body = raw
    if 'Введите код' not in body:
        body += terms
    return body


async def send_due(bot, skip_ids=None, *, custom=None, force=False, button_ids=None):
    """Compatibility entry point: promotional recovery offers are retired."""
    return 0, []
