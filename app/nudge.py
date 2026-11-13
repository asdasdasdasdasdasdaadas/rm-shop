from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app import db
from app.config import get_settings
from app.keyboards import onboarding_keyboard, payment_nudge_keyboard
from app.notices import notice_text
from app.referrals import trial_grant_rub
from app.referral_terms import referral_terms
from app.reminder_tracking import send_reminder
from app.cispay import payment_is_paid
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
            "Подарок уже на балансе. Добавьте устройство в кабинете — "
            "там найдёте инструкцию для подключения."
        )
    else:
        extra = (
            f"Заберите подарок в личном кабинете — {rub_text(trial_grant_rub())} на {days}. "
            "Нажмите «Принять подарок», и средства поступят на баланс."
        )
    return notice_text("trial_nudge", name=name, extra=extra)


def invite_nudge_text(telegram_id: int, first_name: str | None) -> str:
    settings = get_settings()
    name = first_name or "привет"
    link = f"https://t.me/{settings.bot_username}?start=ref_{telegram_id}"
    reward = "50 ₽"
    terms = referral_terms(settings)
    when = terms["when"] + (" " + terms["friend"] if terms["friend"] else "")
    if not settings.referral_program_enabled:
        return terms["note"] + "\n\n" + terms["when"]
    body = notice_text("invite_nudge", name=name, reward=reward, link=link, when=when)
    if when not in body:
        body += "\n\nАктуальные условия: " + when
    return body


def info_nudge_text() -> str:
    settings = get_settings()
    price = rub_text(settings.vpn_day_price_rub)
    return notice_text("info_nudge", price=price, story="")


async def _deliver(bot: Bot, **kwargs) -> bool:
    kind = kwargs['kind']
    if not db.is_marketing_message(kind):
        return await _deliver_unbudgeted(bot, **kwargs)
    slot = await db.reserve_optional_message(kwargs['telegram_id'], kind)
    if slot is None:
        return False
    sent = False
    try:
        sent = await _deliver_unbudgeted(bot, **kwargs)
        return sent
    finally:
        await db.finish_optional_message(slot, sent)


async def _deliver_unbudgeted(
    bot: Bot,
    *,
    kind: str,
    telegram_id: int,
    first_name: str | None,
    title: str,
    body: str,
    reply_markup,
    extra: dict | None = None,
    preserve: bool = False,
) -> bool:
    if not preserve:
        from app.funnel_ui import funnel_body, funnel_keyboard
        body = funnel_body(body)
        reply_markup = funnel_keyboard(reply_markup)
    if not await db.nudge_delivery_allowed(telegram_id, kind):
        return False
    try:
        await send_reminder(bot, telegram_id, body, kind=kind, title=title, reply_markup=reply_markup, preserve=preserve,
                            step_id=(extra or {}).get("step_id"))
        ok = True
    except Exception as exc:
        logger.debug("Напоминание %s не ушло %s", kind, telegram_id, exc_info=True)
        extra = fail_extra(exc, {**(extra or {}),
            "retry_after": int(getattr(exc, "retry_after", 120)),
            "permanent": isinstance(exc, (TelegramBadRequest, TelegramForbiddenError)),
        })
        ok = False
    try:
        await db.log_bot_message(kind=kind, source="auto", telegram_id=telegram_id,
            first_name=first_name, title=title, body=body, status="sent" if ok else "failed", extra=extra)
    except Exception:
        logger.exception("Could not log reminder delivery %s", kind)
    mark = {
        "nudge_trial": "trial",
        "nudge_invite": "invite",
        "nudge_info": "info",
    }.get(kind)
    if mark and ok:
        await db.mark_nudge_sent(telegram_id, mark)
    await asyncio.sleep(0.035)
    return ok


def gift_ending_text() -> str:
    settings = get_settings()
    minimum = max(1, int(settings.balance_topup_min or 50))
    price = max(1, int(settings.vpn_day_price_rub or 1))
    return notice_text("gift_ending_nudge", min=minimum, days=days_text(max(1, minimum // price)))


async def send_due_trial_end_nudges(
    bot: Bot, skip_ids: list[int] | None = None, *,
    body: str | None = None, button_ids: list[str] | None = None,
) -> tuple[int, list[int]]:
    touched: list[int] = []
    settings = get_settings()
    if await db.flag_on("billing_paused"):
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    await db.rearm_balance_warnings(settings.vpn_day_price_rub)
    for row in await db.list_due_trial_end_nudges(settings.vpn_day_price_rub, NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        stage = 3 if int(row.get("stage") or 1) == 3 else 1
        if not await db.nudge_delivery_allowed(telegram_id, "nudge_trial_end"):
            continue
        if not await db.claim_balance_ending_notice(telegram_id, settings.vpn_day_price_rub, stage=stage):
            continue
        count = max(1, int(row.get("device_count") or 1))
        from app.balance_notifications import balance_details, balance_keyboard
        suffix = balance_details(int(row.get('balance_rub') or 0), count, settings.vpn_day_price_rub)
        gift = stage == 1 and not row.get("paid")
        if gift:
            # Never paid: the balance is the gift, so the last day sells the first top-up.
            text = gift_ending_text()
        else:
            text = ((body or "").strip() or notice_text("balance_ending_nudge")) + suffix
        promise = False
        if not gift and stage == 1:
            from app.trust import promise_available
            promise = await promise_available(telegram_id)
        if button_ids is None:
            reply, keep = balance_keyboard(promise=promise), True
        else:
            from app.balance_notifications import with_promise
            from app.funnel_board import markup as board_markup
            reply, keep = board_markup(button_ids, telegram_id, promise=promise), True
            if promise and not any(
                    (b if isinstance(b, str) else b.get("action")) == "promise" for b in button_ids):
                reply = with_promise(reply, True)
        ok = await _deliver(
            bot, kind="nudge_trial_end", telegram_id=telegram_id, first_name=row.get("first_name"),
            title="Подарок заканчивается" if gift else "Баланс заканчивается", body=text, reply_markup=reply, extra=None, preserve=keep,
        )
        if not ok:
            await db.release_balance_ending_notice(telegram_id, stage=stage)
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


async def send_due_payment_nudges(
    bot: Bot, rp=None, skip_ids: list[int] | None = None, *,
    body: str | None = None, button_ids: list[str] | None = None, honor_flag: bool = True,
) -> tuple[int, list[int]]:
    if await db.flag_on("maintenance") or (honor_flag and not await db.flag_on("payment_nudge", default=True)):
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
            text = (body or "").strip() or notice_text("payment_nudge")
            if button_ids is None:
                reply, keep = payment_nudge_keyboard(token), False
            else:
                from app.funnel_board import markup as board_markup
                reply, keep = board_markup(button_ids, uid, token=token), True
            from app.checkout_feedback import add_question_button
            reply = add_question_button(reply, token)
            ok = await _deliver(
                bot, kind="nudge_payment", telegram_id=uid, first_name=row.get("first_name"),
                title="Незавершённая оплата", body=text, reply_markup=reply, preserve=keep,
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
            await db.resolve_exit_feedback()
            await db.resolve_recovered_vpn_feedback()
            retry_skip = await db.nudge_retry_suppressed_ids()
            muted = await db.exit_feedback_suppressed_ids()
            muted.extend(await db.quiet_notification_ids())
            try:
                from app.referrals import reward_connected_friends
                await reward_connected_friends(bot)
            except Exception:
                logger.exception("Бонус за подключившегося друга не начислен")
            from app.funnel_board import send_due as send_board
            n, _ids = await send_board(bot, rp, retry_skip, muted)
            if n:
                logger.info("Воронка: %s", n)
        except Exception:
            logger.exception("Напоминания не удалось отправить")
        await asyncio.sleep(NUDGE_INTERVAL)
