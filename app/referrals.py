from __future__ import annotations

import logging

from app.funnel_ui import send_funnel_message
from html import escape
from math import ceil

from aiogram import Bot

from app import db
from app.notices import notice_text
from app.config import get_settings, referral_is_payout
from app.keyboards import with_referral_share, cabinet_keyboard, share_keyboard
from app.remnawave import RemnawaveClient
from app.texts import friends_acc, rub_text
from app.referral_terms import REFERRAL_BONUS_RUB

logger = logging.getLogger(__name__)


def invitee_extra_days(local: dict | None) -> int:
    extra = get_settings().referral_invitee_days
    if not get_settings().referral_program_enabled or extra < 1 or not local or not local.get("referred_by"):
        return 0
    return extra


def trial_grant_days(local: dict | None) -> int:
    return get_settings().trial_days + invitee_extra_days(local)


def trial_grant_rub() -> int:
    settings = get_settings()
    return max(0, settings.trial_days) * max(1, settings.vpn_day_price_rub)


def trial_is_available(local: dict | None, *, require_bot_start: bool = True) -> bool:
    if not local or local.get("trial_used"):
        return False
    if require_bot_start and not local.get("bot_started_at"):
        return False
    settings = get_settings()
    if int(settings.trial_days or 0) < 1:
        return False
    if settings.trial_enabled:
        return True
    return not bool(local.get("has_paid_topup") or local.get("remnawave_id"))


def referral_payout_public(wallet: dict | None = None) -> dict:
    settings = get_settings()
    data = wallet or {
        "earned": 0,
        "withdrawn": 0,
        "pending": 0,
        "available": 0,
    }
    enabled = bool(referral_is_payout())
    minimum = max(1, int(settings.referral_payout_min or 2000))
    pending = int(data.get("pending") or 0)
    available = int(data.get("available") or 0)
    return {
        "referral_mode": "payout" if referral_is_payout() else "classic",
        "referral_earned": int(data.get("earned") or 0),
        "referral_available": available,
        "referral_pending": pending,
        "referral_payout_enabled": enabled,
        "referral_payout_min": minimum,
        "referral_payout_can": enabled and pending == 0 and available >= minimum,
    }


def referral_month_need() -> int:
    settings = get_settings()
    reward = max(0, int(settings.referral_reward_rub or 0))
    day = max(1, int(settings.vpn_day_price_rub or 1))
    if reward < 1:
        return 0
    return max(1, ceil((day * 30) / reward))


def referrer_next_line(rewarded: int) -> str:
    need = referral_month_need()
    count = max(0, int(rewarded or 0))
    if need < 1:
        return "Отправьте ссылку ещё раз."
    if count > 0 and count % need == 0:
        return f"Месяц за друзей набран. Следующий — ещё {need} {friends_acc(need)} с оплатой."
    left = need if count % need == 0 else need - (count % need)
    return f"Ещё {left} {friends_acc(left)} с оплатой — и месяц VPN."


async def after_topup_keyboard(telegram_id: int):
    from app.funnel_ui import funnel_keyboard
    settings = get_settings()
    local = await db.get_user(telegram_id)
    markup = cabinet_keyboard()
    if settings.referral_program_enabled and local and local.get("first_online_at") and not local.get("quiet_notifications"):
        markup = with_referral_share(telegram_id, markup)
    return funnel_keyboard(markup)


def topup_ok_text(amount: str, *, can_share: bool, local: dict | None = None) -> str:
    body = notice_text("topup_ok", amount=amount)
    if local is not None:
        body += "\nБаланс: " + rub_text(int(local.get("balance_rub") or 0)) + "."
        can_share = can_share and not local.get("quiet_notifications")
    if can_share and get_settings().referral_program_enabled:
        body += (
            "\n\n🎁 Пригласите друга: "
            "другу 50 ₽ сразу, вам 50 ₽, когда он подключит VPN."
        )
    from app.funnel_ui import funnel_body
    return funnel_body(body)


async def _send_reward(bot: Bot, chat: int, text: str, *, amount: int, friend: dict | None = None) -> None:
    """A referral bonus as a card: the friends widget with a «+N ₽» banner for whoever invited (friend = {n, k}),
    the «начисление · по приглашению» receipt for the friend. Old Telegram apps get the same text."""
    from aiogram.exceptions import TelegramForbiddenError
    from app.funnel_ui import funnel_body, funnel_keyboard
    markup = with_referral_share(chat, cabinet_keyboard())
    try:
        if friend is not None:
            from app.widgets import send_referral_widget
            await send_referral_widget(bot, chat, caption=funnel_body(text), reply_markup=funnel_keyboard(markup),
                                       reward={"a": int(amount), **friend})
        else:
            from app.widgets_more import send_admin_credit_widget
            await send_admin_credit_widget(bot, chat, int(amount), funnel_keyboard(markup), source="ref",
                                           caption=funnel_body(text))
        return
    except TelegramForbiddenError:
        raise
    except Exception:
        logger.debug("Карточка реферального бонуса не отправилась %s, шлём текст", chat, exc_info=True)
    await send_funnel_message(bot, chat, text, reply_markup=markup)


async def maybe_reward_menu(bot: Bot | None, telegram_id: int) -> int:
    """50 ₽ to the invited friend once they reach the main menu; whoever invited them hears that the friend
    came and gets their 50 ₽ when the friend connects VPN (reward_connected_friends)."""
    if not get_settings().referral_program_enabled:
        return 0
    try:
        result = await db.reward_referral_menu(telegram_id, REFERRAL_BONUS_RUB)
    except Exception:
        return 0
    if not result:
        return 0
    amount = f"{result['amount']} ₽"
    if bot:
        try:
            await _send_reward(bot, telegram_id, f"🎁 Вы пришли по ссылке друга — начислили <b>{amount}</b> на баланс.",
                               amount=int(result["amount"]))
        except Exception:
            pass
        name = escape(result.get("friend_name") or "Друг")
        try:
            await send_funnel_message(
                bot, result["referrer_id"],
                f"👋 {name} пришёл по вашей ссылке. Как только он подключит VPN, вам начислим <b>{amount}</b>.",
                reply_markup=with_referral_share(result["referrer_id"], cabinet_keyboard()))
        except Exception:
            pass
    return result["amount"]


async def reward_connected_friends(bot: Bot | None) -> int:
    """50 ₽ to whoever invited a friend, once that friend first connects VPN. Runs from the reminder loop."""
    if not get_settings().referral_program_enabled:
        return 0
    rewards = await db.claim_referral_connect_rewards(REFERRAL_BONUS_RUB)
    for item in rewards:
        if not bot:
            break
        raw_name = str(item.get("friend_name") or "Друг")[:32]
        name = escape(item.get("friend_name") or "Друг")
        try:
            await _send_reward(bot, item["referrer_id"],
                               f"🎁 {name} подключил VPN по вашей ссылке. Вам начислено <b>{item['amount']} ₽</b>!",
                               amount=int(item["amount"]), friend={"n": raw_name, "k": "connect"})
        except Exception:
            pass
    return len(rewards)


async def maybe_reward_invitee(bot: Bot | None, telegram_id: int, *, enabled: bool | None = None, amount: int | None = None) -> int:
    settings = get_settings()
    if not (settings.referral_program_enabled if enabled is None else enabled):
        return 0
    amount = int(settings.referral_invitee_reward_rub or 0) if amount is None else amount
    if amount < 1:
        return 0
    after = await db.credit_invitee_bonus_once(telegram_id, amount)
    if after is None:
        return 0
    if bot:
        try:
            await _send_reward(bot, telegram_id, notice_text("referral_invitee_paid", amount=rub_text(amount)),
                               amount=amount)
        except Exception:
            pass
    return amount


async def maybe_reward_referrer(
    bot: Bot | None,
    rw: RemnawaveClient,
    new_user_id: int,
    friend_name: str | None,
    *, payment_key: str | None = None, topup_rub: int = 0, first_payment: bool = False, enabled: bool | None = None, paid_at=None,
) -> None:
    settings = get_settings()
    name = escape(friend_name or "друг")
    result = await db.reward_referral_payment(new_user_id, payment_key or "", topup_rub,
        enabled=settings.referral_program_enabled if enabled is None else enabled, first_payment=first_payment,
        **({"paid_at": paid_at} if paid_at is not None else {}))
    if result and result['amount'] > 0 and bot:
        try:
            await _send_reward(bot, result['referrer_id'],
                f"🎁 Друг {name} впервые пополнил баланс. Вам начислено {rub_text(result['amount'])}!",
                amount=int(result['amount']), friend={"n": str(friend_name or "Друг")[:32], "k": "pay"})
        except Exception:
            pass
