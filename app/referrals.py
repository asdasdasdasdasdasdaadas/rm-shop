from __future__ import annotations

from html import escape

from aiogram import Bot

from app import db
from app.billing import expire_human
from app.config import get_settings
from app.keyboards import back_profile_keyboard, connect_keyboard
from app.remnawave import RemnawaveClient, RemnawaveError
from app.texts import days_text, rub_text


def invitee_extra_days(local: dict | None) -> int:
    extra = get_settings().referral_invitee_days
    if extra < 1 or not local or not local.get("referred_by"):
        return 0
    return extra


def trial_grant_days(local: dict | None) -> int:
    return get_settings().trial_days + invitee_extra_days(local)


def trial_grant_rub() -> int:
    settings = get_settings()
    return max(0, settings.trial_days) * max(1, settings.vpn_day_price_rub)


async def maybe_reward_referrer(
    bot: Bot,
    rw: RemnawaveClient,
    new_user_id: int,
    friend_name: str | None,
) -> None:
    settings = get_settings()
    name = escape(friend_name or "друг")
    if settings.balance_enabled:
        amount = settings.referral_reward_rub
        if amount < 1:
            return
        referrer_id = await db.claim_referral_reward(new_user_id)
        if not referrer_id:
            return
        await db.add_balance_rub(referrer_id, amount)
        await db.add_balance_rub(new_user_id, amount)
        ref_text = (
            "<b>Поздравляем</b>\n\n"
            f"Друг {name} попробовал VPN бесплатно по вашей ссылке.\n"
            f"Вам начислено <b>{rub_text(amount)}</b> на баланс."
        )
        friend_text = (
            f"За переход по ссылке на баланс начислено <b>{rub_text(amount)}</b>"
        )
        try:
            await bot.send_message(referrer_id, ref_text, reply_markup=back_profile_keyboard())
        except Exception:
            pass
        try:
            await bot.send_message(new_user_id, friend_text, reply_markup=back_profile_keyboard())
        except Exception:
            pass
        return

    days = settings.referral_reward_days
    if days < 1:
        return
    referrer_id = await db.claim_referral_reward(new_user_id)
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
        text = (
            "<b>Поздравляем</b>\n\n"
            f"Друг {name} попробовал VPN бесплатно по вашей ссылке.\n"
            f"Вам начислено <b>{days_text(days)}</b> подписки.\n\n"
            f"Действует до: <b>{expire_human(user)}</b>"
        )
        extra = user.get("subscriptionUrl") or ""
        if extra:
            text += f"\n\nСсылка подписки:\n<code>{extra}</code>"
        sub_url = extra
    except RemnawaveError:
        await db.unclaim_referral_reward(new_user_id)
        return
    try:
        await bot.send_message(
            referrer_id,
            text,
            reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
        )
    except Exception:
        pass
