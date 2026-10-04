from __future__ import annotations

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
        body += "\nПодключение и состояние доступа — в кабинете."
        can_share = can_share and not local.get("quiet_notifications")
    if can_share and get_settings().referral_program_enabled:
        body += (
            "\n\n🎁 Пригласите друга: "
            "Вам 50 ₽ за первую оплату друга и 5% с каждого его пополнения, пока программа активна."
        )
    from app.funnel_ui import funnel_body
    return funnel_body(body)


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
            await send_funnel_message(bot,
                telegram_id,
                notice_text("referral_invitee_paid", amount=rub_text(amount)),
                reply_markup=with_referral_share(telegram_id, cabinet_keyboard()),
            )
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
    if result and result.get('campaign') and bot:
        gift = result['campaign']
        try:
            await send_funnel_message(bot, gift['referrer_id'],
                "🎁 Трое ваших друзей впервые пополнили баланс — подарок ваш!\n\n"
                f"Начислили {rub_text(gift['amount'])} на VPN: это стоимость 30 дней на 3 устройства "
                "по цене на старте акции. Если устройств больше, подарка хватит на меньший срок.\n\n"
                "Подарок за эту акцию получен. Спасибо, что рекомендуете нас друзьям!",
                reply_markup=with_referral_share(gift['referrer_id'], cabinet_keyboard()))
        except Exception:
            pass
    if result and result['amount'] > 0 and bot:
        try:
            await send_funnel_message(bot, result['referrer_id'],
                f"Друг {name} пополнил баланс. Вам начислено {rub_text(result['amount'])}: "
                + (f"бонус за первую оплату {rub_text(result['bonus'])} и " if result['bonus'] else "")
                + f"5% от пополнения ({rub_text(result['percent'])}).",
                reply_markup=with_referral_share(result["referrer_id"], cabinet_keyboard()))
        except Exception:
            pass
