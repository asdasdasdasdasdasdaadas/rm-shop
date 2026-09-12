from __future__ import annotations

from urllib.parse import quote

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app.notices import notice_text
from app.texts import days_text, rub_text
from app import runtime

def support_url() -> str:
    raw = (get_settings().support_username or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.replace("://tg.me/", "://t.me/", 1)
    handle = raw.lstrip("@")
    if not handle or handle == "support":
        handle = "way_proxy_support"
    return f"https://t.me/{handle}"


def legal_text() -> str:
    return notice_text("legal")


def welcome_text() -> str:
    return notice_text("welcome", brand=get_settings().brand_name)


def profile_text(first_name: str | None, *, balance_rub: int | None = None) -> str:
    name = first_name or "друг"
    settings = get_settings()
    if settings.balance_enabled:
        rub = 0 if balance_rub is None else balance_rub
        return notice_text(
            "profile_balance",
            name=name,
            balance=rub_text(rub),
            price=rub_text(settings.vpn_day_price_rub),
        )
    return notice_text("profile_days", name=name)


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


def cabinet_login_keyboard(challenge_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=f"lk:y:{challenge_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"lk:n:{challenge_id}"),
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
            style="success",
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
            style="success",
        )
    )
    return builder.as_markup()


def story_webapp_button(*, story_offer: bool) -> InlineKeyboardButton | None:
    settings = get_settings()
    url = mini_app_url()
    if (
        not story_offer
        or not settings.balance_enabled
        or not settings.story_reward_enabled
        or settings.story_reward_rub <= 0
        or not url
    ):
        return None
    return InlineKeyboardButton(
        text=f"История — {rub_text(settings.story_reward_rub)}",
        web_app=WebAppInfo(url=url),
    )


def profile_keyboard(*, trial_available: bool, has_access: bool, story_offer: bool = True) -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    if trial_available:
        builder.row(
            InlineKeyboardButton(text="Попробовать бесплатно", callback_data="trial")
        )
    if settings.balance_enabled:
        builder.row(
            InlineKeyboardButton(
                text="Пополнить баланс",
                callback_data="buy",
                style="success",
            ),
            InlineKeyboardButton(
                text="Приведи друга",
                callback_data="share",
            ),
        )
    else:
        builder.row(InlineKeyboardButton(text="Купить подписку", callback_data="buy"))
        days = settings.referral_reward_days
        builder.row(
            InlineKeyboardButton(
                text=f"Приведи друга — {days_text(days)}",
                callback_data="share",
            )
        )
        if has_access:
            builder.row(InlineKeyboardButton(text="Моя подписка", callback_data="my_sub"))
            builder.row(InlineKeyboardButton(text="Подключиться", callback_data="connect"))
    story_btn = story_webapp_button(story_offer=story_offer)
    if story_btn:
        builder.row(story_btn)
    builder.row(
        InlineKeyboardButton(text="Частые вопросы", callback_data="faq"),
        InlineKeyboardButton(text="Поддержка", callback_data="support_ticket"),
    )
    add_cabinet_row(builder)
    return builder.as_markup()


def faq_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_cabinet_row(builder)
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def help_connect_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Не получается подключиться",
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
                style="success",
            )
        )
    add_cabinet_row(builder)
    return builder.as_markup()


def back_profile_keyboard(*, cabinet: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    if cabinet:
        add_cabinet_row(builder)
    return builder.as_markup()


def connect_keyboard(sub_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if sub_url.startswith("http://") or sub_url.startswith("https://"):
        builder.row(InlineKeyboardButton(text="Открыть ссылку подписки", url=sub_url))
    buy_title = "Пополнить баланс" if get_settings().balance_enabled else "Купить подписку"
    builder.row(InlineKeyboardButton(text="Перевыпустить ссылку", callback_data="reissue_sub"))
    builder.row(InlineKeyboardButton(text=buy_title, callback_data="buy"))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def buy_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    if settings.balance_enabled and runtime.webapp_url:
        builder.row(
            InlineKeyboardButton(
                text="Пополнить",
                web_app=WebAppInfo(url=runtime.webapp_url),
                style="success",
            )
        )
        builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
        return builder.as_markup()
    for code, plan in settings.shop_plans.items():
        if settings.rollypay_configured:
            label = f"{plan['title']} — {plan['rub_str']} рублей"
        elif settings.stars_enabled:
            label = f"{plan['title']} — {plan['stars']} звёзд"
        else:
            label = plan["title"]
        builder.row(InlineKeyboardButton(text=label, callback_data=f"buy:{code}"))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def pay_keyboard(pay_url: str, order_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оплатить", url=pay_url, style="success"))
    builder.row(InlineKeyboardButton(text="Проверить оплату", callback_data=f"rpc:{order_id}"))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def invite_url(telegram_id: int, bot_username: str | None = None) -> str:
    handle = (bot_username or get_settings().bot_username or "").lstrip("@")
    return f"https://t.me/{handle}?start=ref_{int(telegram_id)}"


def invite_share_text() -> str:
    settings = get_settings()
    if settings.balance_enabled:
        text = (
            "VPN: сутки только за свои устройства. Подключайтесь по ссылке."
        )
        bonus = int(settings.referral_invitee_reward_rub or 0)
        if bonus > 0:
            text += f" При первой оплате на баланс ещё {bonus} ₽."
        return text
    extra = settings.referral_invitee_days
    text = (
        "VPN: ссылку подписки всегда можно взять у нас. Подключайтесь по ссылке."
    )
    if extra > 0:
        text += f" При бесплатном периоде +{days_text(extra)}."
    return text


def invite_copy_text(telegram_id: int, bot_username: str | None = None) -> str:
    block = f"{invite_share_text()}\n\n{invite_url(telegram_id, bot_username)}"
    return block[:256]


def share_keyboard(bot_username: str, telegram_id: int, *, story_offer: bool = False) -> InlineKeyboardMarkup:
    share_text = invite_share_text()
    link = invite_url(telegram_id, bot_username)
    share_url = (
        "https://t.me/share/url?url="
        + quote(link)
        + "&text="
        + quote(share_text)
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отправить другу", url=share_url, style="success")
    )
    builder.row(
        InlineKeyboardButton(
            text="Скопировать текст",
            copy_text=CopyTextButton(text=invite_copy_text(telegram_id, bot_username)),
        )
    )
    add_cabinet_row(builder)
    story_btn = story_webapp_button(story_offer=story_offer)
    if story_btn:
        builder.row(story_btn)
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def _telegram_profile_url(telegram_id: int, username: str | None) -> str:
    handle = (username or "").lstrip("@").strip()
    if handle:
        return f"https://t.me/{handle}"
    return f"tg://user?id={int(telegram_id)}"


def story_mod_keyboard(telegram_id: int, username: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Открыть профиль",
            url=_telegram_profile_url(telegram_id, username),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Подтвердить",
            callback_data=f"st_ok:{telegram_id}",
            style="success",
        ),
        InlineKeyboardButton(
            text="Отказать",
            callback_data=f"st_no:{telegram_id}",
            style="danger",
        ),
    )
    return builder.as_markup()


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
            style="success",
        ),
        InlineKeyboardButton(
            text="Отказать",
            callback_data=f"po_no:{payout_id}",
            style="danger",
        ),
    )
    return builder.as_markup()
