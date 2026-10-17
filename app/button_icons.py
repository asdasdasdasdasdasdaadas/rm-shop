"""Semantic icons for user keyboards, including administrator-authored funnel buttons."""
import asyncio
import logging

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

log = logging.getLogger(__name__)
PACK = 'tgmacicons'  # https://t.me/addemoji/tgmacicons
PINNED_ICONS = {'home': '5257963315258204021'}
# Telegram sticker alt emoji selects a real document ID from the pack; never invent IDs.
ICONS = {
    'home': ('🏠', ('🏠','🏡')),
    'about': ('!', ('❕','❗','ℹ️','ℹ')),
    'cabinet': ('▣', ('👤','🖥','💻')),
    'invite': ('♧', ('👥','👤','🤝')),
    'pay': ('⊕', ('💳','💰','➕')),
    'help': ('◌', ('💬','🗨','🆘')),
    'faq': ('?', ('❓','❔')),
    'channel': ('➤', ('📢','📣','✈️','✈')),
    'back': ('‹', ('⬅️','⬅','🔙')),
    'connect': ('⌁', ('🔗','📱','⚡')),
    'gift': ('◇', ('🎁',)),
    'check': ('✓', ('✅','✔️','✔')),
    'copy': ('▱', ('📋','📄')),
    'history': ('◷', ('🕒','📜')),
}


def kind_for(button):
    callback = button.callback_data or ''
    text = button.text.casefold()
    if callback == 'profile' or 'главное меню' in text or text.strip() == 'главная': return 'home'
    if callback == 'about_service' or 'о сервисе' in text: return 'about'
    if 'кабинет' in text: return 'cabinet'
    if 'частые вопросы' in text: return 'faq'
    if 'поддерж' in text or 'помоги' in text: return 'help'
    if 'копир' in text or button.copy_text: return 'copy'
    if callback == 'share' or 'приглас' in text or 'поделит' in text: return 'invite'
    if 'пополн' in text or 'оплат' in text or button.pay: return 'pay'
    if 'канал' in text: return 'channel'
    if 'назад' in text or 'вернуться' in text: return 'back'
    if 'подар' in text or 'попробовать' in text: return 'gift'
    if 'подключ' in text: return 'connect'
    if 'провер' in text or 'готово' in text: return 'check'
    if 'истори' in text: return 'history'
    if button.web_app: return 'cabinet'
    return None


def decorate(markup, ids):
    rows = []
    for row in markup.inline_keyboard:
        buttons = []
        for button in row:
            kind = kind_for(button)
            if not kind or button.icon_custom_emoji_id:
                buttons.append(button)
                continue
            symbol = ICONS[kind][0]
            if kind in ids:
                button = button.model_copy(update={'icon_custom_emoji_id': ids[kind]})
            elif not button.text.startswith(symbol + ' '):
                button = button.model_copy(update={'text': symbol + ' ' + button.text})
            buttons.append(button)
        rows.append(buttons)
    return markup.model_copy(update={'inline_keyboard': rows})


class ButtonIconsMiddleware(BaseRequestMiddleware):
    def __init__(self, ids):
        self.ids = ids

    async def __call__(self, make_request, bot, method):
        markup = getattr(method, 'reply_markup', None)
        chat_id = getattr(method, 'chat_id', None)
        # Only user private chats; leave staff groups and broadcast channels alone.
        if not isinstance(markup, InlineKeyboardMarkup) or not isinstance(chat_id, int) or chat_id <= 0:
            return await make_request(bot, method)
        decorated = decorate(markup, self.ids)
        request = method.model_copy(update={'reply_markup': decorated})
        try:
            return await make_request(bot, request)
        except TelegramBadRequest as exc:
            reason = str(exc).lower()
            added = any(a.icon_custom_emoji_id != b.icon_custom_emoji_id
                        for ra, rb in zip(markup.inline_keyboard, decorated.inline_keyboard)
                        for a, b in zip(ra, rb))
            if not added or not any(word in reason for word in ('emoji', 'premium')):
                raise
            log.warning('Telegram rejected automatic button emoji; using outline text symbols')
            self.ids = {}
            return await make_request(bot, method.model_copy(update={'reply_markup': decorate(markup, {})}))


async def install_button_icons(bot):
    ids = dict(PINNED_ICONS)
    try:
        pack = await asyncio.wait_for(bot.get_sticker_set(PACK), timeout=10)
        if pack.sticker_type != 'custom_emoji':
            raise ValueError('Expected a custom emoji set')
        available = {s.emoji.replace('\ufe0f',''): s.custom_emoji_id for s in pack.stickers if s.emoji and s.custom_emoji_id}
        for kind, (_, aliases) in ICONS.items():
            if kind in PINNED_ICONS:
                continue
            for alias in aliases:
                found = available.get(alias.replace('\ufe0f',''))
                if found:
                    ids[kind] = found
                    break
        log.info('Button emoji loaded: %s; fallback: %s', ', '.join(ids), ', '.join(k for k in ICONS if k not in ids))
    except Exception as exc:
        # Do not log request URLs or tokens.
        log.warning('Button emoji pack unavailable (%s); keeping pinned icons, using fallback symbols for others', type(exc).__name__)
    bot.session.middleware(ButtonIconsMiddleware(ids))
