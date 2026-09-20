from __future__ import annotations

from html import escape
from math import ceil

from aiogram import Bot

from app import db
from app.billing import expire_human
from app.notices import notice_text, sub_block
from app.config import get_settings, referral_is_payout
from app.keyboards import back_profile_keyboard, cabinet_keyboard, connect_keyboard, share_keyboard
from app.remnawave import RemnawaveClient, RemnawaveError
from app.texts import days_text, friends_acc, rub_text


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
    enabled = bool(settings.balance_enabled and referral_is_payout())
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
    settings = get_settings()
    local = await db.get_user(telegram_id)
    if settings.referral_program_enabled and local and local.get("first_online_at"):
        return share_keyboard(settings.bot_username, telegram_id)
    return cabinet_keyboard()


def topup_ok_text(amount: str, *, can_share: bool) -> str:
    body = notice_text("topup_ok", amount=amount)
    if can_share and get_settings().referral_program_enabled:
        body += (
            "\n\nЕсли VPN уже нужен — отправьте ссылку другу. "
            "Вам 50 ₽ за первую оплату друга и 5% с каждого его пополнения, пока программа активна."
        )
    return body


async def maybe_reward_invitee(bot: Bot | None, telegram_id: int) -> int:
    settings = get_settings()
    if not settings.balance_enabled or not settings.referral_program_enabled:
        return 0
    amount = int(settings.referral_invitee_reward_rub or 0)
    if amount < 1:
        return 0
    claimed = await db.claim_invitee_payment_bonus(telegram_id)
    if not claimed:
        return 0
    after = await db.add_balance_rub(telegram_id, amount)
    await db.log_billing_event(
        telegram_id,
        "referral",
        source="invitee",
        amount=amount,
        balance_after=after,
        note="Бонус другу за первую оплату по ссылке",
    )
    if bot:
        try:
            await bot.send_message(
                telegram_id,
                notice_text("referral_invitee_paid", amount=rub_text(amount)),
            )
        except Exception:
            pass
    return amount


async def maybe_reward_referrer(
    bot: Bot | None,
    rw: RemnawaveClient,
    new_user_id: int,
    friend_name: str | None,
    *, payment_key: str | None = None, topup_rub: int = 0, first_payment: bool = False,
) -> None:
    settings = get_settings()
    payout = referral_is_payout()
    name = escape(friend_name or "друг")
    if settings.balance_enabled:
        result = await db.reward_referral_payment(new_user_id, payment_key or "", topup_rub,
            enabled=settings.referral_program_enabled, first_payment=first_payment)
        if result and result['amount'] > 0 and bot:
            try:
                await bot.send_message(result['referrer_id'],
                    f"Друг {name} пополнил баланс. Вам начислено {rub_text(result['amount'])}: "
                    f"бонус за первую оплату {rub_text(result['bonus'])} и 5% от пополнения "
                    f"({rub_text(result['percent'])}).", reply_markup=cabinet_keyboard())
            except Exception:
                pass
        return
    if not settings.referral_program_enabled:
        return
    days = settings.referral_reward_days
    if days < 1:
        return
    referrer_id = await db.claim_referral_reward(new_user_id, require_paid=True)
    if not referrer_id:
        return
    try:
        local = await db.get_user(referrer_id)
        panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
        user = await rw.extend_subscription(
            referrer_id,
            days,
            tag="REF",
            panel_user_id=panel_id,
        )
        await db.save_panel_snapshot(referrer_id, user)
        extra = user.get("subscriptionUrl") or ""
        key = "referral_referrer_paid_days" if payout else "referral_referrer_days"
        text = notice_text(
            key,
            name=name,
            days=days_text(days),
            expire=expire_human(user),
            sub_block=sub_block(extra),
        )
        sub_url = extra
    except RemnawaveError:
        await db.unclaim_referral_reward(new_user_id)
        return
    if not bot:
        return
    try:
        await bot.send_message(
            referrer_id,
            text,
            reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
        )
    except Exception:
        pass
