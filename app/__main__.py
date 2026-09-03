from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ErrorEvent, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from app import db, runtime
from app.balance import charge_due_devices
from app.config import get_settings
from app.handlers.profile import router as profile_router
from app.handlers.start import router as start_router
from app.handlers.story_mod import router as story_mod_router
from app.remnawave import RemnawaveClient
from app.rollypay import RollyPayClient
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
    if not settings.balance_enabled or interval <= 0:
        return
    while True:
        await asyncio.sleep(interval)
        try:
            await charge_due_devices(rw, bot)
        except Exception:
            logger.exception("Списание за устройства не удалось")


async def panel_sync_loop(rw: RemnawaveClient) -> None:
    interval = get_settings().panel_sync_interval
    if interval <= 0:
        return
    while True:
        await asyncio.sleep(interval)
        try:
            await sync_all(rw)
            logger.info("Сверка с Remnawave завершена")
        except Exception:
            logger.exception("Сверка с Remnawave не удалась")


def _warn_deploy(settings) -> None:
    if not settings.admin_password:
        logger.warning("ADMIN_PASSWORD пуст: вход в /admin не сработает")
    if settings.webapp_enabled and not settings.webapp_public_url.startswith("https://"):
        logger.warning("Для Mini App нужен HTTPS в WEBAPP_PUBLIC_URL (требование Telegram)")
    if settings.rollypay_configured and settings.rollypay_test:
        logger.warning("ROLLYPAY_TEST=true: платежи идут в тестовом режиме")
    if "rmshop:rmshop@" in settings.database_url:
        logger.warning("В DATABASE_URL пароль по умолчанию. Смените POSTGRES_PASSWORD перед продом")


async def main() -> None:
    settings = get_settings()
    _warn_deploy(settings)
    await db.init_db()
    await load_shop_overlay()
    rw = RemnawaveClient()
    rp = RollyPayClient() if settings.rollypay_configured else None
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    runner = await start_http(bot, rw, rp)
    if settings.webapp_enabled and settings.webapp_public_url:
        runtime.webapp_url = settings.webapp_public_url.rstrip("/")
        logger.info("Mini App URL: %s", runtime.webapp_url)
    else:
        runtime.webapp_url = ""
        logger.info("Mini App выключен (WEBAPP_ENABLED=false). Кабинет подключите на деплое.")

    dp = Dispatcher()
    dp["rw"] = rw
    dp["rp"] = rp
    dp.update.outer_middleware(MaintenanceMiddleware())
    dp.update.outer_middleware(BlockedMiddleware())
    dp.include_router(start_router)
    dp.include_router(story_mod_router)
    dp.include_router(profile_router)

    @dp.message_reaction()
    async def on_reaction(_event) -> None:
        return

    @dp.error()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("Unhandled update error: %s", event.exception)

    try:
        me = await bot.get_me()
        await bot.set_my_commands(
            [BotCommand(command="start", description="Открыть профиль")]
        )
        if runtime.webapp_url:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Кабинет",
                    web_app=WebAppInfo(url=runtime.webapp_url),
                )
            )
        else:
            await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Сервис: %s  бот: @%s", settings.brand_name, me.username)
        name = (settings.brand_name or "").strip()[:64]
        if name:
            try:
                await bot.set_my_name(name=name)
            except Exception:
                logger.warning("Не удалось выставить имя бота в Telegram из BRAND_NAME")
        sync_task = asyncio.create_task(panel_sync_loop(rw), name="panel-sync")
        charge_task = asyncio.create_task(balance_charge_loop(rw, bot), name="balance-charge")
        dump_task = asyncio.create_task(backup_loop(bot), name="backup")
        nudge_task = asyncio.create_task(trial_nudge_loop(bot), name="trial-nudge")
        try:
            await dp.start_polling(
                bot,
                drop_pending_updates=True,
                allowed_updates=dp.resolve_used_update_types(),
            )
        finally:
            sync_task.cancel()
            charge_task.cancel()
            dump_task.cancel()
            nudge_task.cancel()
    finally:
        await runner.cleanup()
        if rp is not None:
            await rp.aclose()
        await rw.aclose()
        await db.close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
