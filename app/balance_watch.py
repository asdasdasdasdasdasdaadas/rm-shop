"""Turn VPN back on the moment money lands on the balance, whatever brought it.

The users table has a trigger (schema.sql, users_balance_up) that sends NOTIFY balance_up with the telegram id
whenever balance_rub grows: a payment, a referral bonus, a promo code, an admin credit, a refund. This loop
listens on its own connection and, for a user with devices switched off for lack of money, runs the same
sync as after a payment: charge a day and turn the device on. The billing loop is the safety net if a
notification is lost while the connection is down.
"""
from __future__ import annotations

import asyncio
import logging
import time

import asyncpg
from aiogram import Bot

from app import db, runtime
from app.config import get_settings
from app.remnawave import RemnawaveClient

logger = logging.getLogger(__name__)

CHANNEL = "balance_up"
# One user is handled at most this often: a refund after a failed panel call must not loop.
COOLDOWN_SECONDS = 30
RECONNECT_SECONDS = 5


async def reenable_user(rw: RemnawaveClient, bot: Bot | None, telegram_id: int) -> bool:
    """Charge and turn on the user's switched-off devices if the balance now covers a day. True if it ran a sync."""
    from app.balance import sync_user_billing

    price = max(1, get_settings().vpn_day_price_rub)
    paused = await db.flag_on("billing_paused")
    if not await db.devices_to_reenable(price, paused=paused, telegram_id=telegram_id):
        return False
    async with runtime.panel_cron_lock():
        # Re-check under the lock: a payment sync may have done it while we waited.
        if not await db.devices_to_reenable(price, paused=paused, telegram_id=telegram_id):
            return False
        result = await sync_user_billing(rw, telegram_id, bot, source="balance")
    logger.info("Баланс пополнен у %s, устройства включены: %s", telegram_id, result)
    return True


class _Handled:
    def __init__(self) -> None:
        self.at: dict[int, float] = {}

    def due(self, telegram_id: int) -> bool:
        now = time.monotonic()
        if now - self.at.get(telegram_id, -COOLDOWN_SECONDS) < COOLDOWN_SECONDS:
            return False
        self.at[telegram_id] = now
        if len(self.at) > 5000:
            self.at = {k: v for k, v in self.at.items() if now - v < COOLDOWN_SECONDS}
        return True


async def balance_watch_loop(rw: RemnawaveClient, bot: Bot) -> None:
    queue: asyncio.Queue[int] = asyncio.Queue()
    handled = _Handled()

    def on_notify(_conn, _pid, _channel, payload: str) -> None:
        try:
            queue.put_nowait(int(payload))
        except ValueError:
            pass

    later: set[int] = set()

    def retry(uid: int) -> None:
        later.discard(uid)
        queue.put_nowait(uid)

    async def worker() -> None:
        while True:
            uid = await queue.get()
            if not handled.due(uid):
                # Come back once the cooldown is over, so a second top-up right after the first is not lost.
                if uid not in later:
                    later.add(uid)
                    asyncio.get_running_loop().call_later(COOLDOWN_SECONDS, retry, uid)
                continue
            try:
                await reenable_user(rw, bot, uid)
            except Exception:
                logger.exception("Не удалось включить устройства после пополнения %s", uid)

    work = asyncio.create_task(worker(), name="balance-watch-worker")
    try:
        while True:
            conn: asyncpg.Connection | None = None
            try:
                conn = await asyncpg.connect(get_settings().database_url)
                lost = asyncio.Event()
                conn.add_termination_listener(lambda _c: lost.set())
                await conn.add_listener(CHANNEL, on_notify)
                await lost.wait()
                logger.warning("Слежение за балансом: соединение с базой потеряно, переподключаюсь")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Слежение за балансом: не удалось подключиться к базе")
            finally:
                if conn is not None and not conn.is_closed():
                    await conn.close()
            await asyncio.sleep(RECONNECT_SECONDS)
    finally:
        work.cancel()
