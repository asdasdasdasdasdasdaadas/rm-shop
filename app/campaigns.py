"""Durable announcement queue for manually launched referral campaigns."""
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from html import escape
from urllib.parse import urlencode

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter, TelegramNetworkError, TelegramServerError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from app import db
from app.keyboards import invite_url
from app.tg_err import fail_extra

logger = logging.getLogger(__name__)


def parse_campaign_moscow_time(value: str) -> datetime:
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M').replace(
            tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise ValueError('Укажите дату и время запуска по МСК') from None


def campaign_announcement(telegram_id: int, reward: int):
    link = invite_url(telegram_id)
    text = (
        "🎁 Месяц VPN на 3 устройства — за трёх друзей!\n\n"
        "Поделитесь своей ссылкой. Когда трое разных друзей впервые пополнят баланс во время акции, "
        f"вы получите {reward} ₽ на VPN — стоимость 30 дней на трёх устройствах по тарифу на старте акции.\n\n"
        "Учитываются и ранее приглашённые друзья, если они ещё не платили. "
        "Оплата роутера не участвует. Один подарок за эту акцию. "
        "При другом количестве устройств срок расходования баланса изменится.\n\n"
        f"Ваша ссылка: {escape(link)}"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="Поделиться ссылкой", url="https://t.me/share/url?" + urlencode({
            "url": link, "text": "Пользуюсь этим VPN. Подключайся по моей ссылке!"}))]])
    return text, markup


async def deliver_campaign_message(bot, row: dict) -> float:
    text, markup = campaign_announcement(row['telegram_id'], row['reward_rub'])
    error = None
    retryable = False
    retry = None
    pause = 0.05
    try:
        await bot.send_message(row['telegram_id'], text, reply_markup=markup,
                               link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as exc:
        error = str(exc)[:400]
        retryable = isinstance(exc, (TelegramRetryAfter, TelegramNetworkError, TelegramServerError, OSError, TimeoutError))
        if isinstance(exc, TelegramRetryAfter):
            retry = max(1, int(exc.retry_after))
            pause = retry
        elif retryable and row['attempts'] < 3:
            retry = 60
        extra = fail_extra(exc, {'campaign_id': row['campaign_id']})
    else:
        extra = {'campaign_id': row['campaign_id']}
    # Persist delivery before optional audit logging: logging failure must not resend.
    await db.finish_campaign_message(row['campaign_id'], row['telegram_id'],
                                    error=error, retry_seconds=retry, retryable=retryable)
    try:
        await db.log_bot_message(kind='broadcast', source='campaign', telegram_id=row['telegram_id'],
            title='Акция: три друга — месяц VPN', body=text,
            status='failed' if error else 'sent', extra=extra)
    except Exception:
        logger.exception('Could not log campaign announcement')
    return pause


async def campaign_announcement_loop(bot) -> None:
    next_schedule_check = 0
    while True:
        try:
            if time.monotonic() >= next_schedule_check:
                await db.change_referral_campaign('scheduled_start')
                next_schedule_check = time.monotonic() + 2
            row = await db.claim_campaign_message()
            pause = await deliver_campaign_message(bot, row) if row else 2
        except Exception:
            logger.exception('Campaign announcement worker failed')
            pause = 10
        await asyncio.sleep(pause)
