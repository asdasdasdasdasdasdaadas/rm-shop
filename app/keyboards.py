from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app import runtime


def legal_text() -> str:
    return (
        "Перед использованием примите оферту и политику конфиденциальности. "
        "Документы открываются по ссылкам ниже."
    )


def welcome_text() -> str:
    settings = get_settings()
    return (
        f"Добро пожаловать в <b>{settings.brand_name}</b>.\n\n"
        "Чтобы пользоваться ботом, подпишитесь на канал и нажмите «Проверить подписку»."
    )


def profile_text(first_name: str | None) -> str:
    name = first_name or "друг"
    return f"Привет, {name}.\nВыберите действие."


def channel_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Подписаться на канал", url=settings.required_channel_url))
    builder.row(InlineKeyboardButton(text="Проверить подписку", callback_data="check_sub"))
    return builder.as_markup()


def legal_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оферта", url=settings.legal_offer_url))
    builder.row(InlineKeyboardButton(text="Политика конфиденциальности", url=settings.legal_privacy_url))
    builder.row(InlineKeyboardButton(text="Принимаю", callback_data="accept_legal"))
    return builder.as_markup()


def profile_keyboard(*, trial_available: bool, has_access: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if trial_available:
        builder.row(InlineKeyboardButton(text="Попробовать бесплатно", callback_data="trial"))
    builder.row(InlineKeyboardButton(text="Купить подписку", callback_data="buy"))
    days = get_settings().referral_reward_days
    builder.row(InlineKeyboardButton(text=f"Приведи друга — {days} дн.", callback_data="share"))
    if has_access:
        builder.row(InlineKeyboardButton(text="Моя подписка", callback_data="my_sub"))
        builder.row(InlineKeyboardButton(text="Подключиться", callback_data="connect"))
    builder.row(InlineKeyboardButton(text="VPN не работает", callback_data="vpn_down"))
    return builder.as_markup()


def cabinet_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if runtime.webapp_url:
        builder.row(
            InlineKeyboardButton(
                text="Личный кабинет",
                web_app=WebAppInfo(url=runtime.webapp_url),
            )
        )
    return builder.as_markup()


def back_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def connect_keyboard(sub_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if sub_url.startswith("http://") or sub_url.startswith("https://"):
        builder.row(InlineKeyboardButton(text="Открыть ссылку подписки", url=sub_url))
    builder.row(InlineKeyboardButton(text="Купить подписку", callback_data="buy"))
    builder.row(InlineKeyboardButton(text="VPN не работает", callback_data="vpn_down"))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def buy_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    for code, plan in settings.plans.items():
        if settings.rollypay_configured:
            label = f"{plan['title']} — {plan['rub_str']} RUB"
        elif settings.stars_enabled:
            label = f"{plan['title']} — {plan['stars']} Stars"
        else:
            label = plan["title"]
        builder.row(InlineKeyboardButton(text=label, callback_data=f"buy:{code}"))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def pay_keyboard(pay_url: str, order_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Оплатить", url=pay_url))
    builder.row(InlineKeyboardButton(text="Проверить оплату", callback_data=f"rpc:{order_id}"))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()


def share_keyboard(bot_username: str, telegram_id: int) -> InlineKeyboardMarkup:
    settings = get_settings()
    days = settings.referral_reward_days
    link = f"https://t.me/{bot_username}?start=ref_{telegram_id}"
    share_url = (
        "https://t.me/share/url?url="
        + quote(link)
        + "&text="
        + quote(
            f"Подключайся. Нажми «Попробовать бесплатно» по ссылке — получишь "
            f"+{settings.referral_invitee_days} дн., а я получу {days} дн. VPN."
        )
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отправить другу", url=share_url))
    builder.row(InlineKeyboardButton(text="В профиль", callback_data="profile"))
    return builder.as_markup()
