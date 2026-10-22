"""Semantic icons for user keyboards, including administrator-authored funnel buttons."""
import asyncio
import logging
import re

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

log = logging.getLogger(__name__)
PACK = 'tgmacicons'  # https://t.me/addemoji/tgmacicons
PINNED_ICONS = {
    'home': '5257963315258204021',
    'channel': '5258165702707125574',
    'invite': '5258513401784573443',
    'message': '5287595522993991899',
    # Verified against tgmacicons with getStickerSet; also used if Telegram is unavailable.
    'about': '5258503720928288433',
    'cabinet': '5258362837411045098',
    'pay': '5258204546391351475',
    'help': '5258215846450305872',
    'faq': '5258328383183396223',
    'back': '5258132936401624790',
    'connect': '5323404142809467476',
    'gift': '5258134813302332906',
    'check': '5357069174512303778',
    'copy': '5258477770735885832',
    'history': '5258419835922030550',
    'cancel': '5267123797600783095',
    'document': '5258477770735885832',
    'rating': '5258185631355378853',
    'retry': '5260687119092817530',
    'action': '5204189706237004154',
}
# Telegram sticker alt emoji selects a real document ID from the pack; never invent IDs.
ICONS = {
    'home': ('🏠', ('🏠','🏡','🏘')),
    'about': ('!', ('❕','❗','ℹ️','ℹ')),
    'cabinet': ('▣', ('👤','🖥','💻')),
    'invite': ('♧', ('👥','👤','🤝')),
    'message': ('✉', ('✉️', '💬')),
    'pay': ('⊕', ('💳','💰','➕')),
    'help': ('◌', ('💬','🗨','🆘')),
    'faq': ('?', ('❓','❔','📖')),
    'channel': ('➤', ('📢','📣','✈️','✈')),
    'back': ('‹', ('⬅️','⬅','🔙')),
    'connect': ('⌁', ('🔗','📱','⚡')),
    'gift': ('◇', ('🎁','📦')),
    'check': ('✓', ('✅','✔️','✔')),
    'copy': ('▱', ('📋','📄')),
    'history': ('◷', ('🕒','📜','🕔','🕘')),
    'cancel': ('×', ('❌', '✖️', '🚫')),
    'document': ('▤', ('📄', '📃', '📜')),
    'rating': ('★', ('⭐', '🌟', '⭐️')),
    'retry': ('↻', ('🔄', '🔁')),
    'action': ('›', ('➡️', '▶️', '🔘')),
}


def kind_for(button):
    callback = button.callback_data or ''
    text = button.text.casefold()
    if callback.startswith(('lk:n:', 'ticket_cancel', 'help_ticket_cancel', 'po_no:')) or any(word in text for word in ('отмен', 'отклон')): return 'cancel'
    if callback.startswith(('lk:y:', 'ticket_finish:', 'ticket_close:', 'rpc:', 'po_ok:')) or callback in ('accept_legal', 'check_sub', 'vpn_feedback:ok', 'welcome:continue'): return 'check'
    if callback.startswith('ticket_rate:'): return 'rating'
    if callback == 'try_again': return 'retry'
    if callback.startswith(('buy:', 'resume_pay:')) or callback == 'buy': return 'pay'
    if callback.startswith(('paywhy:', 'payreason:', 'vpn_feedback:')): return 'message'
    if any(word in text for word in ('оферта', 'конфиденциальност', 'условия')): return 'document'
    if 'помощ' in text or 'проблем' in text: return 'help'
    if callback == 'profile' or 'главное меню' in text or text.strip() == 'главная': return 'home'
    if callback == 'about_service' or 'о сервисе' in text: return 'about'
    if 'кабинет' in text: return 'cabinet'
    if 'частые вопросы' in text: return 'faq'
    if 'отправить сообщение' in text or 'написать сообщение' in text: return 'message'
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
    return 'action'


# Strip decorative Unicode prefixes when replacing them with a pack icon.
# Keep text-only symbols and numbers (e.g. support ratings) intact.
_LEADING_EMOJI = re.compile(r'^(?:[\U0001f000-\U0001faff\u2600-\u27bf\ufe0f\u200d]+\s*)+')


def _button_label(text):
    cleaned = _LEADING_EMOJI.sub('', text).strip()
    for symbol, _ in ICONS.values():
        if cleaned.startswith(symbol + ' '):
            cleaned = cleaned[len(symbol) + 1:]
            break
    return cleaned or text


def decorate(markup, ids, allowed_ids=None):
    allowed = set(ids.values()) if allowed_ids is None else set(allowed_ids)
    rows = []
    for row in markup.inline_keyboard:
        buttons = []
        for button in row:
            kind = kind_for(button)
            icon = button.icon_custom_emoji_id
            if icon not in allowed:
                icon = ids.get(kind) or ids.get('action') or next(iter(ids.values()), None)
            text = _button_label(button.text)
            if not icon:
                symbol = ICONS[kind][0]
                text = symbol + ' ' + text
            buttons.append(button.model_copy(update={'icon_custom_emoji_id': icon, 'text': text}))
        rows.append(buttons)
    return markup.model_copy(update={'inline_keyboard': rows})


class ButtonIconsMiddleware(BaseRequestMiddleware):
    def __init__(self, ids, allowed_ids=None):
        self.ids = ids
        self.allowed_ids = set(ids.values()) if allowed_ids is None else set(allowed_ids)

    async def __call__(self, make_request, bot, method):
        markup = getattr(method, 'reply_markup', None)
        if not isinstance(markup, InlineKeyboardMarkup):
            return await make_request(bot, method)
        decorated = decorate(markup, self.ids, self.allowed_ids)
        request = method.model_copy(update={'reply_markup': decorated})
        try:
            return await make_request(bot, request)
        except TelegramBadRequest as exc:
            reason = str(exc).lower()
            added = any(b.icon_custom_emoji_id for row in decorated.inline_keyboard for b in row)
            if not added or not any(word in reason for word in ('emoji', 'premium')):
                raise
            log.warning('Telegram rejected automatic button emoji; using outline text symbols')
            self.ids = {}
            self.allowed_ids = set()
            return await make_request(bot, method.model_copy(update={'reply_markup': decorate(markup, {})}))


async def install_button_icons(bot):
    ids = dict(PINNED_ICONS)
    allowed = set(ids.values())
    try:
        pack = await asyncio.wait_for(bot.get_sticker_set(PACK), timeout=10)
        if pack.sticker_type != 'custom_emoji':
            raise ValueError('Expected a custom emoji set')
        allowed = {s.custom_emoji_id for s in pack.stickers if s.custom_emoji_id}
        if not allowed:
            raise ValueError('Empty custom emoji set')
        available = {s.emoji.replace('\ufe0f',''): s.custom_emoji_id for s in pack.stickers if s.emoji and s.custom_emoji_id}
        # Verify pinned and manually chosen IDs against the actual set as well.
        ids = {kind: icon for kind, icon in PINNED_ICONS.items() if icon in allowed}
        for kind, (_, aliases) in ICONS.items():
            if kind in ids:
                continue
            for alias in aliases:
                found = available.get(alias.replace('\ufe0f',''))
                if found:
                    ids[kind] = found
                    break
        default = ids.get('action') or ids.get('message') or next(s.custom_emoji_id for s in pack.stickers if s.custom_emoji_id)
        ids = {kind: ids.get(kind, default) for kind in ICONS}
        log.info('Button icons loaded from %s: %s', PACK, ', '.join(ids))
    except Exception as exc:
        # Do not log request URLs or tokens.
        log.warning('Button emoji pack unavailable (%s); using pinned icons', type(exc).__name__)
    bot.session.middleware(ButtonIconsMiddleware(ids, allowed))
