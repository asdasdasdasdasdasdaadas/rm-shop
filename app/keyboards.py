from __future__ import annotations

from html import escape
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app.notices import notice_text
from app.texts import rub_text
from app import runtime
from app.button_icons import PINNED_ICONS

def support_url() -> str:
    raw = (get_settings().support_username or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.replace("://tg.me/", "://t.me/", 1)
    handle = raw.lstrip("@")
    if not handle or handle == "support":
        handle = "way_proxy_support"
    return f"https://t.me/{handle}"


def legal_text() -> str:
    settings = get_settings()
    offer = escape(settings.legal_offer_url, quote=True)
    privacy = escape(settings.legal_privacy_url, quote=True)
    return (
        f'Продолжая работу с ботом или открывая кабинет, вы принимаете '
        f'<a href="{offer}">оферту</a> и подтверждаете ознакомление с '
        f'<a href="{privacy}">политикой конфиденциальности</a>.'
    )


def welcome_text() -> str:
    return notice_text("welcome", brand=get_settings().brand_name) + "\n\n" + legal_text()


def tariff_block() -> str:
    """Short price and terms block for the first /start message. Switched off in the admin panel settings."""
    settings = get_settings()
    price = max(1, int(getattr(settings, 'vpn_day_price_rub', 6) or 6))
    minimum = max(1, int(getattr(settings, 'balance_topup_min', 50) or 50))
    lines = [f'💸 <b>{price} ₽ в день</b> за устройство · без подписки · пополнение от {minimum} ₽']
    if getattr(settings, 'referral_program_enabled', False):
        from app.referral_terms import REFERRAL_BONUS_RUB as bonus
        lines.append(f'🎁 Позовите друга: ему {bonus} ₽ сразу, вам {bonus} ₽, когда он подключит VPN')
    return '\n'.join(lines)


def main_menu_text(first_name: str | None, balance_rub: int | None = None) -> str:
    """Main menu body. Fixed in code: the admin panel no longer overrides it."""
    name = escape(str(first_name or "").strip())
    greeting = f"👋 {name}, привет!" if name else "👋 Привет!"
    price = rub_text(get_settings().vpn_day_price_rub)
    return (
        f"{greeting}\n\n"
        f"Баланс: <b>{rub_text(int(balance_rub or 0))}</b> · {price} в день за устройство\n\n"
        "В «Личном кабинете» можно добавить устройство, подключить VPN и пополнить баланс."
    )


def profile_text(first_name: str | None, *, balance_rub: int | None = None) -> str:
    return main_menu_text(first_name, balance_rub) + "\n\n" + legal_text()


def mini_app_url() -> str:
    return (runtime.webapp_url or (get_settings().webapp_public_url or "").rstrip("/")).rstrip("/")


def cabinet_button() -> InlineKeyboardButton | None:
    url = mini_app_url()
    if not url:
        return None
    return InlineKeyboardButton(
        text="Открыть кабинет",
        web_app=WebAppInfo(url=url),
        style="success",
    )


def mini_app_screen(screen: str):
    """The cabinet opened straight on one screen (topup, promise, …); None without a mini app URL."""
    url = mini_app_url()
    if not url:
        return None
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["screen"] = screen
    return WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query))))


def payment_nudge_keyboard(token: str | None = None, *, label: str = "Продолжить оплату") -> InlineKeyboardMarkup:
    if token:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=label, callback_data=f"resume_pay:{token}")
        ]])
    url = mini_app_url()
    if not url:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=label, callback_data="buy")
        ]])
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["screen"] = "topup"
    url = urlunsplit(parts._replace(query=urlencode(query)))
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))
    ]])


def cabinet_login_keyboard(challenge_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтвердить",
                    callback_data=f"lk:y:{challenge_id}",
                ),
                InlineKeyboardButton(
                    text="Отклонить",
                    callback_data=f"lk:n:{challenge_id}",
                    style="danger",
                ),
            ]
        ]
    )


def add_cabinet_row(builder: InlineKeyboardBuilder) -> None:
    btn = cabinet_button()
    if btn:
        builder.row(btn)


def channel_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Подписаться на канал",
            url=settings.required_channel_url,
            style="primary",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Проверить подписку",
            callback_data="check_sub",
        )
    )
    return builder.as_markup()


def legal_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оферта", url=settings.legal_offer_url))
    builder.row(
        InlineKeyboardButton(
            text="Политика конфиденциальности",
            url=settings.legal_privacy_url,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Принимаю",
            callback_data="accept_legal",
        )
    )
    return builder.as_markup()


def story_webapp_button(*, story_offer: bool) -> InlineKeyboardButton | None:
    return None


def profile_keyboard(*, trial_available: bool, has_access: bool, story_offer: bool = True) -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    cabinet = cabinet_button()
    builder.row(
        cabinet.model_copy(update={"text": "Личный кабинет"}) if cabinet else
        InlineKeyboardButton(text="Личный кабинет", callback_data="help:connect", style="success")
    )
    channel_url = (settings.required_channel_url or "").strip()
    if channel_url:
        builder.row(InlineKeyboardButton(text="Новостной канал", url=channel_url))
    builder.row(
        InlineKeyboardButton(text="Пригласить", callback_data="share"),
        InlineKeyboardButton(text="О сервисе", callback_data="about_service"),
    )
    return builder.as_markup()


def faq_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_cabinet_row(builder)
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="profile"))
    return builder.as_markup()


def onboarding_keyboard(*, gift: bool = False, has_device: bool = False) -> InlineKeyboardMarkup:
    label = "Забрать подарок" if gift else "Продолжить подключение" if has_device else "Подключить VPN"
    url = mini_app_url()
    if url:
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        query["screen"] = "gift" if gift else "connect"
        button = InlineKeyboardButton(text=label, web_app=WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query)))))
    else:
        button = InlineKeyboardButton(text=label, callback_data="trial" if gift else "help:connect")
    return InlineKeyboardMarkup(inline_keyboard=[
        [button], [InlineKeyboardButton(text="Нужна помощь", callback_data="help:connect")]
    ])


def help_connect_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button = cabinet_button()
    if button:
        builder.row(button.model_copy(update={"text": "Подключить VPN"}))
    builder.row(
        InlineKeyboardButton(
            text="Нужна помощь",
            callback_data="help:connect",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Другая проблема",
            callback_data="help:other",
        )
    )
    return builder.as_markup()


def help_ticket_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Отменить", callback_data="help_ticket_cancel"),
        ]]
    )


def help_connect_reply_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_cabinet_row(builder)
    builder.row(
        InlineKeyboardButton(
            text="Другая проблема",
            callback_data="help:other",
        )
    )
    return builder.as_markup()


def cabinet_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_cabinet_row(builder)
    return builder.as_markup()


def story_nudge_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    story_btn = story_webapp_button(story_offer=True)
    if story_btn:
        builder.row(story_btn)
    add_cabinet_row(builder)
    return builder.as_markup()


def blocked_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Поддержка", callback_data="support_ticket"))
    return builder.as_markup()


def try_again_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Попробовать ещё раз", callback_data="try_again"))
    return builder.as_markup()


def trial_nudge_keyboard(*, trial_available: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if trial_available:
        builder.row(
            InlineKeyboardButton(
                text="Попробовать бесплатно",
                callback_data="trial",
            )
        )
    add_cabinet_row(builder)
    return builder.as_markup()


def back_profile_keyboard(*, cabinet: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="profile"))
    if cabinet:
        add_cabinet_row(builder)
    return builder.as_markup()


def ton_button(text: str = "Gram (TON)", *, telegram_id: int | None = None) -> InlineKeyboardButton | None:
    """Pay in Gram (TON) from the chat; None while it is switched off. Admins see it before the switch is on."""
    from app import ton
    shown = ton.enabled() or (telegram_id is not None and ton.allowed(telegram_id))
    return InlineKeyboardButton(text=text, callback_data="ton_pay") if shown else None


def _cabinet_pay_label(settings) -> str:
    if settings.rub_pay_configured:
        return "Картой / СБП"
    if settings.stars_enabled:
        return "Звёздами"
    return "Пополнить"


def buy_keyboard(telegram_id: int | None = None) -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    ton_btn = ton_button(telegram_id=telegram_id)
    if runtime.webapp_url:
        # Two equal ways to pay side by side: the cabinet (card, SBP, Stars) and Gram (TON) in the chat.
        cabinet = InlineKeyboardButton(text=_cabinet_pay_label(settings) if ton_btn else "Пополнить",
                                       web_app=WebAppInfo(url=runtime.webapp_url))
        builder.row(cabinet, *([ton_btn] if ton_btn else []))
        builder.row(InlineKeyboardButton(text="Главное меню", callback_data="profile"))
        return builder.as_markup()
    for code, plan in settings.shop_plans.items():
        if settings.rub_pay_configured:
            label = f"{plan['title']} — {plan['rub_str']} рублей"
        elif settings.stars_enabled:
            label = f"{plan['title']} — {plan['stars']} звёзд"
        else:
            label = plan["title"]
        builder.row(InlineKeyboardButton(text=label, callback_data=f"buy:{code}"))
    if ton_btn:
        builder.row(ton_button("Оплатить в Gram (TON)", telegram_id=telegram_id))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="profile"))
    return builder.as_markup()


def pay_keyboard(pay_url: str, order_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оплатить", url=pay_url))
    builder.row(InlineKeyboardButton(text="Проверить оплату", callback_data=f"rpc:{order_id}"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="profile"))
    return builder.as_markup()


def invite_url(telegram_id: int, bot_username: str | None = None) -> str:
    handle = (bot_username or get_settings().bot_username or "").lstrip("@")
    return f"https://t.me/{handle}?start=ref_{int(telegram_id)}"


def invite_message(telegram_id: int, settings=None) -> str:
    settings = settings or get_settings()
    from app.referral_terms import referral_terms
    terms = referral_terms(settings)
    icon = f'<tg-emoji emoji-id="{PINNED_ICONS["invite"]}">👥</tg-emoji>'
    body = icon + ' <b>Поделитесь ссылкой с другом</b>\n'
    if settings.referral_program_enabled:
        body += 'Другу <b>50 ₽</b> сразу, вам <b>50 ₽</b>, когда друг подключит VPN.'
    else:
        body += escape(terms['note']) + '\n\n' + escape(terms['when'])
    link = escape(invite_url(telegram_id, settings.bot_username))
    body += ('\n\n<tg-emoji emoji-id="5258093637450866522">🤖</tg-emoji> '
             '<b>Реферальная ссылка</b>\n<blockquote><code>' + link + '</code></blockquote>')
    return body


def invite_share_text() -> str:
    settings = get_settings()
    brand = (settings.brand_name or "VPN").strip() or "VPN"
    if settings.referral_program_enabled:
        return f"Попробуй {brand} бесплатно — 50 ₽ уже на балансе."
    return f"Попробуй {brand} — VPN для телефона и компьютера."


def invite_copy_text(telegram_id: int, bot_username: str | None = None) -> str:
    link = invite_url(telegram_id, bot_username)
    text = invite_share_text()
    if len(text) + len(link) + 2 > 256:
        text = "Попробуй VPN по моей ссылке."
    return f"{text}\n\n{link}"


def referral_share_button(telegram_id: int, bot_username: str | None = None) -> InlineKeyboardButton:
    url = "https://t.me/share/url?" + urlencode({
        "url": invite_url(telegram_id, bot_username),
        "text": invite_share_text(),
    })
    return InlineKeyboardButton(
        text="Поделиться ссылкой", url=url,
        icon_custom_emoji_id=PINNED_ICONS["invite"],
    )


def with_referral_share(telegram_id: int, markup: InlineKeyboardMarkup | None = None) -> InlineKeyboardMarkup:
    rows = [list(row) for row in markup.inline_keyboard] if markup else []
    button = referral_share_button(telegram_id)
    if not any(item.url == button.url for row in rows for item in row):
        rows.insert(0, [button])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def share_keyboard(bot_username: str, telegram_id: int, *, story_offer: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(referral_share_button(telegram_id, bot_username))
    builder.row(
        InlineKeyboardButton(
            text="Скопировать ссылку",
            copy_text=CopyTextButton(text=invite_url(telegram_id, bot_username)),
        )
    )
    story_btn = story_webapp_button(story_offer=story_offer)
    if story_btn:
        builder.row(story_btn)
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="profile"))
    return builder.as_markup()


def _telegram_profile_url(telegram_id: int, username: str | None) -> str:
    handle = (username or "").lstrip("@").strip()
    if handle:
        return f"https://t.me/{handle}"
    return f"tg://user?id={int(telegram_id)}"




def payout_mod_keyboard(
    payout_id: int, username: str | None, telegram_id: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Открыть профиль",
            url=_telegram_profile_url(telegram_id, username),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Выплачено",
            callback_data=f"po_ok:{payout_id}",
        ),
        InlineKeyboardButton(
            text="Отказать",
            callback_data=f"po_no:{payout_id}",
            style="danger",
        ),
    )
    return builder.as_markup()


def support_welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Я помогу", callback_data="welcome:continue")
    ]])


def vpn_feedback_keyboard(*, returning: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Всё работает" if not returning else "Вернуться к VPN", callback_data="vpn_feedback:ok" if not returning else "help:connect")],
            [InlineKeyboardButton(text="Нужна помощь", callback_data="vpn_feedback:help")]]
    if not returning:
        rows.append([InlineKeyboardButton(text="Не подошли условия", callback_data="vpn_feedback:terms")])
    if returning:
        rows.append([InlineKeyboardButton(text="Пока не нужен", callback_data="vpn_feedback:later")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_webapp_button() -> InlineKeyboardButton | None:
    """«Поддержка» opening the support chat screen of the mini app; None when the mini app has no URL."""
    url = mini_app_url()
    if not url:
        return None
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["screen"] = "support"
    return InlineKeyboardButton(text="Поддержка", web_app=WebAppInfo(url=urlunsplit(parts._replace(query=urlencode(query)))))


def _pack_emoji(kind: str, fallback: str) -> str:
    # Animated icon from the tgmacicons pack, same as on the buttons; plain emoji where custom emoji are unsupported.
    return f'<tg-emoji emoji-id="{PINNED_ICONS[kind]}">{fallback}</tg-emoji>'


def about_service_content():
    settings = get_settings()
    price = int(getattr(settings, 'vpn_day_price_rub', 6) or 6)
    minimum = int(getattr(settings, 'balance_topup_min', 50) or 50)
    body = (
        f'<b>{escape(settings.brand_name)}</b> — VPN прямо в Telegram. '
        'Без подписки: пополняете баланс, и он тратится по дням.\n\n'
        f'{_pack_emoji("pay", "💰")} <b>Сколько стоит</b>\n'
        f'{price} ₽ в день за одно устройство. Платите только за те, что добавили: '
        'удалили устройство — списания за него прекратились.\n'
        f'Пополнить можно от {minimum} ₽.'
    )
    if getattr(settings, 'referral_program_enabled', True):
        body += '\n\n' + _pack_emoji('gift', '📦') + ' <b>Позовите друга</b>\nДругу 50 ₽ сразу, вам 50 ₽, когда он подключит VPN.'
    body += '\n\n' + _pack_emoji('cabinet', '👤') + ' <b>Где кабинет</b>\nЗдесь, в боте: <b>Главное меню</b> → <b>Личный кабинет</b>.'
    rows = [[InlineKeyboardButton(text='Главное меню', callback_data='profile', style='success')]]
    rows.append([
        InlineKeyboardButton(text='Условия сервиса', url=settings.legal_offer_url,
                             icon_custom_emoji_id=PINNED_ICONS['document']),
        support_webapp_button() or InlineKeyboardButton(text='Поддержка', url=support_url()),
    ])
    return body, InlineKeyboardMarkup(inline_keyboard=rows)
