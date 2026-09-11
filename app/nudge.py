from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app import db
from app.config import get_settings
from app.keyboards import cabinet_keyboard, share_keyboard, story_nudge_keyboard, trial_nudge_keyboard
from app.notices import notice_text
from app.referrals import trial_grant_rub
from app.texts import days_text, rub_text
from app.tg_err import fail_extra


def _story_reward_on() -> bool:
    settings = get_settings()
    return bool(settings.balance_enabled and settings.story_reward_enabled and settings.story_reward_rub > 0)

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
        extra = f"На баланс сразу ляжет {rub_text(trial_grant_rub())} на {days}."
    else:
        extra = f"Бесплатный период — {days}."
    return notice_text("trial_nudge", name=name, extra=extra)


def invite_nudge_text(telegram_id: int, first_name: str | None) -> str:
    settings = get_settings()
    name = first_name or "привет"
    link = f"https://t.me/{settings.bot_username}?start=ref_{telegram_id}"
    if settings.balance_enabled:
        reward = rub_text(settings.referral_reward_rub)
    else:
        reward = days_text(settings.referral_reward_days)
    when = "Когда человек перейдёт по вашей ссылке и первый раз оплатит VPN, бонус придёт вам."
    friend = int(settings.referral_invitee_reward_rub or 0)
    if settings.balance_enabled and friend > 0:
        when += f" Ему после первой оплаты тоже {rub_text(friend)} на баланс."
    return notice_text("invite_nudge", name=name, reward=reward, link=link, when=when)


def info_nudge_text() -> str:
    settings = get_settings()
    story = ""
    if settings.balance_enabled and settings.story_reward_enabled and settings.story_reward_rub > 0:
        story = (
            f"\n\nЗа историю в Telegram можно получить {rub_text(settings.story_reward_rub)} на баланс."
        )
    if settings.balance_enabled:
        price = rub_text(settings.vpn_day_price_rub)
    else:
        price = days_text(1)
    return notice_text("info_nudge", price=price, story=story)


async def _deliver(
    bot: Bot,
    *,
    kind: str,
    telegram_id: int,
    first_name: str | None,
    title: str,
    body: str,
    reply_markup,
) -> bool:
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
            extra=fail_extra(exc),
        )
        ok = False
    mark = {
        "nudge_trial": "trial",
        "nudge_invite": "invite",
        "nudge_info": "info",
        "nudge_story": "story",
    }.get(kind)
    if mark:
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
        already = bool(row.get("trial_used")) or int(row.get("balance_rub") or 0) > 0
        body = trial_nudge_text(row.get("first_name"), already_granted=already)
        ok = await _deliver(
            bot,
            kind="nudge_trial",
            telegram_id=telegram_id,
            first_name=row.get("first_name"),
            title="Напоминание: триал",
            body=body,
            reply_markup=trial_nudge_keyboard(trial_available=not already),
        )
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_due_invite_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if not await db.flag_on("invite_nudge"):
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


async def send_story_offer_now(bot: Bot | None, telegram_id: int) -> bool:
    if not bot:
        return False
    if not _story_reward_on():
        return False
    if not await db.flag_on("story_nudge", default=True):
        return False
    if await db.flag_on("maintenance"):
        return False
    if await db.user_is_blocked(telegram_id):
        return False
    claimed = await db.take_story_nudge(telegram_id)
    if not claimed:
        return False
    settings = get_settings()
    body = notice_text("story_nudge", amount=rub_text(settings.story_reward_rub))
    try:
        await bot.send_message(telegram_id, body, reply_markup=story_nudge_keyboard())
        await db.log_bot_message(
            kind="nudge_story",
            source="auto",
            telegram_id=telegram_id,
            first_name=claimed.get("first_name"),
            title="Напоминание: история",
            body=body,
            status="sent",
        )
        logger.info("Предложение выложить историю отправлено %s", telegram_id)
        return True
    except Exception as exc:
        logger.warning("Не удалось отправить предложение истории %s", telegram_id, exc_info=True)
        await db.restore_story_nudge(telegram_id)
        await db.log_bot_message(
            kind="nudge_story",
            source="auto",
            telegram_id=telegram_id,
            first_name=claimed.get("first_name"),
            title="Напоминание: история",
            body=body,
            status="failed",
            extra=fail_extra(exc),
        )
        return False


async def send_due_story_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    if not _story_reward_on():
        return 0, touched
    if not await db.flag_on("story_nudge", default=True):
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_story_nudges(NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        ok = await send_story_offer_now(bot, telegram_id)
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
        body = notice_text(f"device_nudge_{step}")
        try:
            await bot.send_message(telegram_id, body, reply_markup=cabinet_keyboard())
            await db.log_bot_message(
                kind="nudge_device",
                source="auto",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title=f"Напоминание: устройство {step}/3",
                body=body,
                status="sent",
                extra={"step": step},
            )
            ok = True
        except Exception as exc:
            logger.debug("Напоминание про устройство не ушло %s", telegram_id, exc_info=True)
            await db.log_bot_message(
                kind="nudge_device",
                source="auto",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title=f"Напоминание: устройство {step}/3",
                body=body,
                status="failed",
                extra=fail_extra(exc, {"step": step}),
            )
            ok = False
        await db.mark_device_nudge_sent(telegram_id)
        await asyncio.sleep(0.035)
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
        body = notice_text("first_online_nudge", days=days_text(_days_left_from_row(row)))
        try:
            await bot.send_message(telegram_id, body, reply_markup=share_keyboard(get_settings().bot_username, telegram_id))
            await db.log_bot_message(
                kind="nudge_first_online",
                source="auto",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title="Напоминание: после первого онлайна",
                body=body,
                status="sent",
            )
            ok = True
        except Exception as exc:
            logger.debug("Напоминание после онлайна не ушло %s", telegram_id, exc_info=True)
            await db.log_bot_message(
                kind="nudge_first_online",
                source="auto",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title="Напоминание: после первого онлайна",
                body=body,
                status="failed",
                extra=fail_extra(exc),
            )
            ok = False
        await db.mark_first_online_nudge_sent(telegram_id)
        await asyncio.sleep(0.035)
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_due_trial_end_nudges(bot: Bot, skip_ids: list[int] | None = None) -> tuple[int, list[int]]:
    touched: list[int] = []
    settings = get_settings()
    if not settings.balance_enabled:
        return 0, touched
    if await db.flag_on("maintenance"):
        return 0, touched
    sent = 0
    for row in await db.list_due_trial_end_nudges(settings.vpn_day_price_rub, NUDGE_BATCH, skip_ids):
        telegram_id = int(row["telegram_id"])
        body = notice_text("trial_end_nudge")
        try:
            await bot.send_message(telegram_id, body, reply_markup=share_keyboard(get_settings().bot_username, telegram_id))
            await db.log_bot_message(
                kind="nudge_trial_end",
                source="auto",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title="Напоминание: сутки до отключения",
                body=body,
                status="sent",
            )
            ok = True
        except Exception as exc:
            logger.debug("Напоминание за сутки до нуля не ушло %s", telegram_id, exc_info=True)
            await db.log_bot_message(
                kind="nudge_trial_end",
                source="auto",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title="Напоминание: сутки до отключения",
                body=body,
                status="failed",
                extra=fail_extra(exc),
            )
            ok = False
        await db.mark_trial_end_nudge_sent(telegram_id)
        await asyncio.sleep(0.035)
        touched.append(telegram_id)
        if ok:
            sent += 1
    return sent, touched


async def send_first_device_thanks(bot: Bot | None, telegram_id: int) -> bool:
    if not bot:
        return False
    if await db.user_is_blocked(telegram_id):
        return False
    if not await db.take_first_device_thanks(telegram_id):
        return False
    body = notice_text("first_device_thanks")
    kb = cabinet_keyboard()
    try:
        await bot.send_message(telegram_id, body, reply_markup=kb)
        await db.log_bot_message(
            kind="first_device_thanks",
            source="auto",
            telegram_id=telegram_id,
            title="После первого устройства",
            body=body,
            status="sent",
        )
        return True
    except Exception as exc:
        logger.debug("Не удалось отправить благодарность %s", telegram_id, exc_info=True)
        await db.restore_first_device_thanks(telegram_id)
        await db.log_bot_message(
            kind="first_device_thanks",
            source="auto",
            telegram_id=telegram_id,
            title="После первого устройства",
            body=body,
            status="failed",
            extra=fail_extra(exc),
        )
        return False


async def trial_nudge_loop(bot: Bot) -> None:
    await asyncio.sleep(NUDGE_START_DELAY)
    while True:
        try:
            skip: list[int] = []
            n, ids = await send_due_device_nudges(bot)
            skip.extend(ids)
            if n:
                logger.info("Напоминание добавить устройство: %s", n)
            n, ids = await send_due_first_online_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание после первого онлайна: %s", n)
            n, ids = await send_due_trial_end_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание за сутки до отключения: %s", n)
            n, ids = await send_due_story_nudges(bot, skip)
            skip.extend(ids)
            if n:
                logger.info("Напоминание про историю: %s", n)
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
