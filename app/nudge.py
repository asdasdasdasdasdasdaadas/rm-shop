from __future__ import annotations

import asyncio
import logging
import math

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app import db
from app.config import get_settings
from app.keyboards import (
    cabinet_keyboard,
    onboarding_keyboard,
    payment_nudge_keyboard,
    share_keyboard,
)
from app.notices import notice_text
from app.referrals import trial_grant_rub
from app.rollypay import payment_is_paid
from app.texts import days_text, rub_text
from app.tg_err import fail_extra



logger = logging.getLogger("rm-shop.nudge")
NUDGE_INTERVAL = 120
NUDGE_START_DELAY = 15
NUDGE_BATCH = 80


def trial_nudge_text(first_name: str | None, *, already_granted: bool) -> str:
    settings = get_settings()
    name = first_name or "привет"
    days = days_text(settings.trial_days)
    if already_granted:
        extra = (
            "Пробные средства уже на балансе. Добавьте устройство в кабинете — "
            "без него VPN не включится, деньги не спишутся."
        )
    elif settings.balance_enabled:
        extra = (
            f"Заберите подарок в личном кабинете — {rub_text(trial_grant_rub())} на {days}. "
            "Нажмите «Принять подарок», и средства поступят на баланс."
        )
    else:
        extra = f"Бесплатный период — {days}."
    return notice_text("trial_nudge", name=name, extra=extra)


def invite_nudge_text(telegram_id: int, first_name: str | None) -> str:
    settings = get_settings()
    name = first_name or "привет"
    link = f"https://t.me/{settings.bot_username}?start=ref_{telegram_id}"
    if settings.balance_enabled:
        reward = "50 ₽ + 5% с каждого пополнения"
    else:
        reward = days_text(settings.referral_reward_days)
    when = "Когда человек перейдёт по вашей ссылке и первый раз оплатит VPN, бонус придёт вам."
    friend = int(settings.referral_invitee_reward_rub or 0)
    if settings.balance_enabled and friend > 0:
        when += f" Ему после первой оплаты тоже {rub_text(friend)} на баланс."
    return notice_text("invite_nudge", name=name, reward=reward, link=link, when=when)


def info_nudge_text() -> str:
    settings = get_settings()
    if settings.balance_enabled:
        price = rub_text(settings.vpn_day_price_rub)
    else:
        price = days_text(1)
    return notice_text("info_nudge", price=price, story="")


async def _deliver(
    bot: Bot,
    *,
    kind: str,
    telegram_id: int,
    first_name: str | None,
    title: str,
    body: str,
    reply_markup,
    extra: dict | None = None,
) -> bool:
    if not await db.nudge_delivery_allowed(telegram_id, kind):
        return False
    try:
        await bot.send_message(telegram_id, body, reply_markup=reply_markup)
        await db.log_bot_message(
            kind=kind,
            source="auto",
            telegram_id=telegram_id,
            first_name=first_name,
            title=title,
            body=body,
            status="sent",
            extra=extra,
        )
        ok = True
    except Exception as exc:
        logger.debug("Напоминание %s не ушло %s", kind, telegram_id, exc_info=True)
        await db.log_bot_message(
            kind=kind,
            source="auto",
            telegram_id=telegram_id,
            first_name=first_name,
            title=title,
            body=body,
            status="failed",
            extra=fail_extra(exc, {**(extra or {}),
                "retry_after": int(getattr(exc, "retry_after", 120)),
                "permanent": isinstance(exc, (TelegramBadRequest, TelegramForbiddenError)),
            }),
        )
        ok = False
    mark = {
        "nudge_trial": "trial",
        "nudge_invite": "invite",
        "nudge_info": "info",
    }.get(kind)
    if mark and ok:
        await db.mark_nudge_sent(telegram_id, mark)
    await asyncio.sleep(0.035)
    return ok


async def send_due_trial_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    settings = get_settings()
    touched: list[int] = []
    if not settings.trial_enabled:
        return 0, touched
    if not await db.flag_on("trial_nudge"):
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_trial_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        already = bool(row.get("trial_used"))
        body = trial_nudge_text(row.get("first_name"), already_granted=already)
        ok = await _deliver(
            bot,
            kind="nudge_trial",
            telegram_id=telegram_id,
            first_name=row.get("first_name"),
            title="Напоминание: триал",
            body=body,
            reply_markup=onboarding_keyboard(gift=True),
        )
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_due_invite_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if not get_settings().referral_program_enabled or not await db.flag_on("invite_nudge"):
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_invite_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        body = invite_nudge_text(telegram_id, row.get("first_name"))
        ok = await _deliver(
            bot,
            kind="nudge_invite",
            telegram_id=telegram_id,
            first_name=row.get("first_name"),
            title="Напоминание: пригласить друга",
            body=body,
            reply_markup=share_keyboard(get_settings().bot_username, telegram_id),
        )
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_due_info_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if not await db.flag_on("info_nudge"):
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    body = info_nudge_text()
    for row in await db.list_due_info_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        ok = await _deliver(
            bot,
            kind="nudge_info",
            telegram_id=telegram_id,
            first_name=row.get("first_name"),
            title="Напоминание: кабинет",
            body=body,
            reply_markup=cabinet_keyboard(),
        )
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched






async def send_due_device_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_device_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        step = min(3, int(row.get("device_nudge_count") or 0) + 1)
        body = notice_text("device_setup_nudge" if row.get("has_device") else "device_nudge_1")
        ok = await _deliver(
            bot, kind="nudge_device", telegram_id=telegram_id, first_name=row.get("first_name"),
            title="Подарок без первого подключения", body=body, reply_markup=onboarding_keyboard(has_device=bool(row.get("has_device"))), extra={"step": step},
        )
        if ok:
            await db.mark_device_nudge_sent(telegram_id)
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_due_idle_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_idle_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        days = int(row.get("idle_days") or 0)
        if days not in {7, 10, 15, 20}:
            continue
        if row.get("first_online_at") is None:
            segment = "setup"
            markup = onboarding_keyboard(gift=not row.get("trial_used"), has_device=bool(row.get("has_device")))
        elif get_settings().balance_enabled and int(row.get("balance_rub") or 0) <= 0:
            segment = "topup"
            markup = payment_nudge_keyboard(label="Пополнить баланс")
        else:
            segment = "return"
            markup = onboarding_keyboard(has_device=bool(row.get("has_device")))
        body = notice_text(f"idle_{segment}_{days}")
        title = f"Напоминание: не пользуется {days} дн."
        ok = await _deliver(
            bot, kind="nudge_idle", telegram_id=telegram_id, first_name=row.get("first_name"),
            title=title, body=body, reply_markup=markup, extra={"days": days, "segment": segment},
        )
        if ok:
            await db.mark_idle_nudge_sent(telegram_id, days)
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


def _days_left_from_row(row: dict) -> int:
    price = max(1, int(get_settings().vpn_day_price_rub or 1))
    n = max(1, int(row.get("device_count") or 0))
    bal = max(0, int(row.get("balance_rub") or 0))
    return max(0, bal // (price * n))


async def send_due_first_online_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if not get_settings().balance_enabled:
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_first_online_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        if not await db.nudge_delivery_allowed(telegram_id, "nudge_first_online"):
            continue
        if not await db.claim_low_balance_notice(telegram_id):
            continue
        body = notice_text("first_online_nudge", days=days_text(_days_left_from_row(row)))
        ok = await _deliver(
            bot, kind="nudge_first_online", telegram_id=telegram_id, first_name=row.get("first_name"),
            title="Напоминание: после первого онлайна", body=body, reply_markup=payment_nudge_keyboard(label="Пополнить баланс"), extra=None,
        )
        if ok:
            await db.mark_first_online_nudge_sent(telegram_id)
        else:
            await db.release_low_balance_notice(telegram_id)
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_due_trial_end_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    settings = get_settings()
    if not settings.balance_enabled or await db.flag_on("billing_paused"):
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_trial_end_nudges(settings.vpn_day_price_rub, NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        if not await db.nudge_delivery_allowed(telegram_id, "nudge_trial_end"):
            continue
        if not await db.claim_low_balance_notice(telegram_id):
            continue
        devices = max(1, int(row.get("device_count") or 1))
        hours = max(1, math.ceil(24 * int(row["balance_rub"]) / (devices * max(1, settings.vpn_day_price_rub))))
        body = notice_text("trial_end_nudge", hours=hours, devices=devices)
        ok = await _deliver(
            bot, kind="nudge_trial_end", telegram_id=telegram_id, first_name=row.get("first_name"),
            title="Напоминание: сутки до отключения", body=body, reply_markup=payment_nudge_keyboard(label="Пополнить баланс"), extra=None,
        )
        if ok:
            await db.mark_trial_end_nudge_sent(telegram_id)
        else:
            await db.release_low_balance_notice(telegram_id)
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_first_device_thanks(bot: Bot | None, telegram_id: int) -> bool:
    if not bot:
        return False
    if await db.user_is_blocked(telegram_id):
        return False
    if not await db.nudge_delivery_allowed(telegram_id, "first_device_thanks"):
        return False
    user = await db.get_user(telegram_id)
    if user and user.get("first_online_at"):
        return False
    if not await db.take_first_device_thanks(telegram_id):
        return False
    ok = await _deliver(
        bot, kind="first_device_thanks", telegram_id=telegram_id,
        first_name=(user or {}).get("first_name"), title="Устройство добавлено: следующий шаг",
        body=notice_text("device_created_next_step"), reply_markup=onboarding_keyboard(has_device=True),
    )
    if not ok:
        await db.restore_first_device_thanks(telegram_id)
    return ok


async def send_due_payment_nudges(bot: Bot, rp=None, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    if await db.flag_on("maintenance") or not await db.flag_on("payment_nudge", default=True):
        return 0, []
    sent, touched = 0, []
    for row in await db.list_due_payment_nudges(NUDGE_BATCH, skip_ids):
        uid, token = int(row["telegram_id"]), row["checkout_token"]
        try:
            if row.get("checkout_payment_id"):
                if rp is None:
                    continue
                payment = await rp.get_payment(row["checkout_payment_id"])
                status = str(payment.get("status") or "").lower()
                if payment_is_paid(payment) or status == "refunded":
                    await db.cancel_payment_nudge(uid, token)
                    continue
                if status not in {"created", "pending", "processing", "waiting", "expired", "canceled", "cancelled", "failed"}:
                    continue  # Unknown status is not proof of an unpaid invoice.
            if not await db.nudge_delivery_allowed(uid, "nudge_payment"):
                continue
            if not await db.claim_payment_nudge(uid, token):
                continue
            touched.append(uid)
            ok = await _deliver(
                bot, kind="nudge_payment", telegram_id=uid, first_name=row.get("first_name"),
                title="Незавершённая оплата", body=notice_text("payment_nudge"),
                reply_markup=payment_nudge_keyboard(token),
            )
            if not ok:
                await db.release_payment_nudge(uid, token)
            sent += int(ok)
        except Exception:
            logger.exception("Не удалось проверить незавершённую оплату %s", uid)
    return sent, touched


async def trial_nudge_loop(bot: Bot, rp=None) -> None:
    await asyncio.sleep(NUDGE_START_DELAY)
    while True:
        try:
            retry_skip = await db.nudge_retry_suppressed_ids()
            n, skip = await send_due_payment_nudges(bot, rp, retry_skip)
            skip.extend(retry_skip)
            if n:
                logger.info("Напоминание о незавершённой оплате: %s", n)
            skip.extend(await db.nudge_suppressed_ids(hours=6))
            n, ids = await send_due_trial_end_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Предупреждение об окончании подарка: %s", n)
            skip.extend(await db.nudge_suppressed_ids(hours=24))
            n, ids = await send_due_device_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Подарок без подключения: %s", n)
            n, ids = await send_due_first_online_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание после первого онлайна: %s", n)
            n, ids = await send_due_idle_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание: давно не заходил: %s", n)
            n, ids = await send_due_trial_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание о триале: %s", n)
            n, ids = await send_due_invite_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание пригласить друга: %s", n)
            n, ids = await send_due_info_nudges(bot, skip)
            if n:
                logger.info("Справка о кабинете: %s", n)
        except Exception:
            logger.exception("Напоминания не удалось отправить")
        await asyncio.sleep(NUDGE_INTERVAL)
