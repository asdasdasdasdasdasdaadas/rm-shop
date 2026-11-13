from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from app import db, runtime
from app.balance import charge_due_devices
from app.config import get_settings
from app.handlers.cabinet_login import router as cabinet_login_router
from app.handlers.profile import router as profile_router
from app.handlers.start import router as start_router
from app.handlers.payout_mod import router as payout_mod_router
from app.handlers.tickets import router as tickets_router
from app.live import router as live_router
from app.remnawave import RemnawaveClient
from app.sync import sync_all
from app.maintenance import MaintenanceMiddleware
from app.block import BlockedMiddleware
from app.backup import backup_loop
from app.nudge import trial_nudge_loop
from app.shop_config import load_shop_overlay
from app.web import start_http

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("rm-shop")


async def balance_charge_loop(rw: RemnawaveClient, bot: Bot) -> None:
    settings = get_settings()
    interval = settings.balance_charge_interval
    if interval <= 0:
        return
    await asyncio.sleep(min(20, interval))
    while True:
        async with runtime.panel_cron_lock():
            try:
                await charge_due_devices(rw, bot)
            except Exception:
                logger.exception("Списание за устройства не удалось")
        try:
            n = await db.purge_old_billing_events(settings.billing_events_keep_days)
            if n:
                logger.info("Удалены старые события биллинга: %s", n)
        except Exception:
            logger.exception("Очистка billing_events не удалась")
        await asyncio.sleep(interval)


async def stale_records_loop() -> None:
    """Drop abandoned invoices and old closed tickets once a day. Lists hide them immediately."""
    interval = 24 * 60 * 60
    await asyncio.sleep(interval)
    while True:
        try:
            stale = await db.purge_stale_unpaid_orders()
            if stale:
                logger.info("Удалены неоплаченные счета старше недели: %s", stale)
        except Exception:
            logger.exception("Очистка неоплаченных счетов не удалась")
        try:
            old_tickets = await db.purge_old_closed_tickets()
            if old_tickets:
                logger.info("Удалены закрытые обращения старше месяца: %s", old_tickets)
        except Exception:
            logger.exception("Очистка закрытых обращений не удалась")
        await asyncio.sleep(interval)


async def panel_sync_loop(rw: RemnawaveClient) -> None:
    interval = get_settings().panel_sync_interval
    if interval <= 0:
        return
    await asyncio.sleep(max(60, interval // 2))
    while True:
        async with runtime.panel_cron_lock():
            try:
                await sync_all(rw)
                logger.info("Сверка с Remnawave завершена")
                from app.widgets import note_traffic_baseline
                await note_traffic_baseline()
            except Exception:
                logger.exception("Сверка с Remnawave не удалась")
        await asyncio.sleep(interval)


def _warn_deploy(settings) -> None:
    if not settings.admin_password:
        logger.warning("ADMIN_PASSWORD пуст: вход в /admin не сработает")
    if settings.webapp_enabled and not settings.webapp_public_url.startswith("https://"):
        logger.warning("Для Mini App нужен HTTPS в WEBAPP_PUBLIC_URL (требование Telegram)")
    if settings.cispay_configured and not settings.cispay_method_set:
        logger.warning("CISPAY_METHODS пуст: CISPay настроен, но ни один способ оплаты на него не идёт")
    if settings.cispay_test:
        logger.warning("CISPAY_TEST=true: тестовые платежи CISPay (is_sandbox) зачисляются на баланс")
    if "rmshop:rmshop@" in settings.database_url:
        logger.warning("В DATABASE_URL пароль по умолчанию. Смените POSTGRES_PASSWORD перед продом")


async def main() -> None:
    settings = get_settings()
    _warn_deploy(settings)
    await db.init_db()
    await load_shop_overlay()
    await db.migrate_legacy_promo_codes()
    rw = RemnawaveClient()
    runtime.rw = rw
    from app.cispay import CISPayClient
    rp = CISPayClient() if settings.cispay_configured else None
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    from app.legal_notice import LegalNoticeRequestMiddleware, LegalNoticeInteractionMiddleware
    bot.session.middleware(LegalNoticeRequestMiddleware())
    from app.button_icons import install_button_icons
    await install_button_icons(bot)
    runtime.bot = bot
    if not str(settings.admin_live_chat_id or "").strip():
        logger.warning("ADMIN_LIVE_CHAT_ID пуст: живые события в канал не пойдут")
    runner = await start_http(bot, rw, rp)
    if settings.webapp_enabled and settings.webapp_public_url:
        runtime.webapp_url = settings.webapp_public_url.rstrip("/")
        logger.info("Mini App URL: %s", runtime.webapp_url)
    else:
        runtime.webapp_url = ""
        logger.info("Mini App выключен (WEBAPP_ENABLED=false). Кабинет подключите на деплое.")

    from app.reminder_tracking import ReminderClickMiddleware
    dp = Dispatcher()
    dp.message.outer_middleware(LegalNoticeInteractionMiddleware())
    dp.callback_query.outer_middleware(LegalNoticeInteractionMiddleware())
    dp.callback_query.outer_middleware(ReminderClickMiddleware())
    dp["rw"] = rw
    dp["rp"] = rp
    from app.widgets import UPDATE_TYPES as WIDGET_UPDATES, WidgetQueryMiddleware
    dp.update.outer_middleware(WidgetQueryMiddleware())
    dp.update.outer_middleware(MaintenanceMiddleware())
    dp.update.outer_middleware(BlockedMiddleware())
    dp.include_router(start_router)
    dp.include_router(cabinet_login_router)
    dp.include_router(payout_mod_router)
    dp.include_router(profile_router)
    dp.include_router(tickets_router)
    dp.include_router(live_router)
    from app.funnel_gifts import router as funnel_gifts_router
    dp.include_router(funnel_gifts_router)

    @dp.message_reaction()
    async def on_reaction(_event) -> None:
        return

    @dp.error()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("Unhandled update error: %s", event.exception)

    try:
        me = await bot.get_me()
        from app import ton
        await ton.sync_bot_commands(bot)
        if runtime.webapp_url:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Кабинет",
                    web_app=WebAppInfo(url=runtime.webapp_url),
                )
            )
        else:
            await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        # `settings` was read before the admin overlay loaded, so re-read it: the admin «Название сервиса» wins over BRAND_NAME.
        brand = get_settings().brand_name
        logger.info("Сервис: %s  бот: @%s", brand, me.username)
        name = (brand or "").strip()[:64]
        if name and name != (me.first_name or "").strip():
            try:
                await bot.set_my_name(name=name)
            except Exception:
                logger.warning("Не удалось выставить имя бота в Telegram из названия сервиса")
        from app.billing import cispay_reconcile_loop, payment_effects_loop
        payment_effects_task = asyncio.create_task(payment_effects_loop(rw, bot), name="payment-effects")
        reconcile_task = asyncio.create_task(cispay_reconcile_loop(rp, rw, bot), name="cispay-reconcile")
        sync_task = asyncio.create_task(panel_sync_loop(rw), name="panel-sync")
        charge_task = asyncio.create_task(balance_charge_loop(rw, bot), name="balance-charge")
        stale_task = asyncio.create_task(stale_records_loop(), name="stale-records")
        dump_task = asyncio.create_task(backup_loop(bot), name="backup")
        from app.activity_digest import digest_loop
        digest_task = asyncio.create_task(digest_loop(bot), name="activity-digest")
        nudge_task = asyncio.create_task(trial_nudge_loop(bot, rp), name="trial-nudge")
        from app.ton import ton_watch_loop
        ton_task = asyncio.create_task(ton_watch_loop(rw, bot), name="ton-watch")
        from app.user_gifts import scan_loop as gifts_scan_loop
        gifts_task = asyncio.create_task(gifts_scan_loop(bot), name="gifts-scan")
        from app.balance_watch import balance_watch_loop
        watch_task = asyncio.create_task(balance_watch_loop(rw, bot), name="balance-watch")
        try:
            await dp.start_polling(
                bot,
                drop_pending_updates=True,
                allowed_updates=list(dict.fromkeys([*dp.resolve_used_update_types(), "my_chat_member", *WIDGET_UPDATES])),
            )
        finally:
            digest_task.cancel()
            await asyncio.gather(digest_task, return_exceptions=True)
            payment_effects_task.cancel()
            reconcile_task.cancel()
            await asyncio.gather(payment_effects_task, reconcile_task, return_exceptions=True)
            sync_task.cancel()
            charge_task.cancel()
            stale_task.cancel()
            dump_task.cancel()
            nudge_task.cancel()
            ton_task.cancel()
            gifts_task.cancel()
            watch_task.cancel()
    finally:
        await runner.cleanup()
        if rp is not None:
            await rp.aclose()
        await rw.aclose()
        await db.close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
