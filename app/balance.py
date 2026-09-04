from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app import db, runtime
from app.config import get_settings
from app.remnawave import PANEL_LEASE_DAYS, RemnawaveClient, RemnawaveError, is_subscription_active, panel_lease_until
from app.trust import collect_due_trusts
from app.notices import notice_text
from app.texts import rub_text

logger = logging.getLogger("rm-shop.balance")
CABINET_LINK_DAYS = 10


BILL_PERIOD = timedelta(hours=24)


def _lease_until() -> datetime:
    return panel_lease_until()


def _billed_recently(last_billed_at, last_billed_on=None) -> bool:
    if last_billed_at is None and last_billed_on is None:
        return False
    dt = last_billed_at
    if dt is None:
        if isinstance(last_billed_on, datetime):
            dt = last_billed_on
        else:
            dt = datetime.combine(last_billed_on, datetime.min.time(), tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc) < dt + BILL_PERIOD


async def _notify_empty(bot: Bot | None, tg_id: int, price: int, warned: set[int]) -> None:
    if not bot or tg_id in warned:
        return
    warned.add(tg_id)
    if not await db.claim_low_balance_notice(tg_id):
        return
    try:
        await bot.send_message(
            tg_id,
            notice_text("low_balance", price=rub_text(price)),
        )
    except Exception:
        pass


async def _bill_due_device(
    rw: RemnawaveClient,
    bot: Bot | None,
    item: dict,
    price: int,
    paused: bool,
    warned: set[int],
    source: str = "cron",
) -> str:
    tg_id = int(item["telegram_id"])
    panel_id = int(item["remnawave_id"])
    device_id = int(item["id"])
    title = str(item.get("title") or "")
    if paused:
        try:
            await rw.extend_panel_user(panel_id, PANEL_LEASE_DAYS)
            await db.mark_devices_billed([device_id], status="ACTIVE", expire_at=_lease_until())
            await db.log_billing_event(
                tg_id,
                "pause",
                source=source,
                device_id=device_id,
                device_title=title,
                note="Пауза тарификации, сутки без списания",
            )
            return "extended"
        except RemnawaveError:
            logger.exception("Не удалось продлить устройство %s при паузе тарификации", item["id"])
            await db.log_billing_event(
                tg_id,
                "error",
                source=source,
                device_id=device_id,
                device_title=title,
                note="Панель не продлила устройство при паузе",
            )
            return "error"
    if await db.spend_balance_rub(tg_id, price):
        try:
            await rw.extend_panel_user(panel_id, PANEL_LEASE_DAYS)
            await db.mark_devices_billed([device_id], status="ACTIVE", expire_at=_lease_until())
            await db.log_billing_event(
                tg_id,
                "charge",
                source=source,
                amount=-price,
                device_id=device_id,
                device_title=title,
                note="Списание за сутки VPN",
            )
            return "extended"
        except RemnawaveError:
            await db.add_balance_rub(tg_id, price)
            logger.exception("Не удалось продлить устройство %s", item["id"])
            await db.log_billing_event(
                tg_id,
                "error",
                source=source,
                device_id=device_id,
                device_title=title,
                note="Панель не продлила, деньги вернули",
            )
            return "error"
    try:
        await rw.disable_panel_user(panel_id)
    except RemnawaveError:
        logger.exception("Не удалось отключить устройство %s", item["id"])
        await db.log_billing_event(
            tg_id,
            "error",
            source=source,
            device_id=device_id,
            device_title=title,
            note="Панель не отключила устройство",
        )
        return "error"
    await db.mark_devices_billed([device_id], status="DISABLED")
    await db.log_billing_event(
        tg_id,
        "disable",
        source=source,
        device_id=device_id,
        device_title=title,
        note="Не хватило баланса на сутки",
    )
    await _notify_empty(bot, tg_id, price, warned)
    return "disabled"


def _chunks(items: list, size: int):
    n = max(1, int(size))
    for i in range(0, len(items), n):
        yield items[i : i + n]


def _panel_mode(used_bulk: bool, used_one: bool) -> str:
    if used_bulk and used_one:
        return "смешано"
    if used_bulk:
        return "пакет"
    if used_one:
        return "по одному"
    return "нет"


async def _decide_user_devices(devices: list[dict], price: int, paused: bool) -> tuple[list[dict], list[dict]]:
    if not devices:
        return [], []
    if paused:
        return list(devices), []
    paid = await db.take_device_charges(int(devices[0]["telegram_id"]), price, len(devices))
    return devices[:paid], devices[paid:]


async def _extend_already_charged(
    rw: RemnawaveClient,
    item: dict,
    price: int,
    paused: bool,
    source: str,
) -> bool:
    tg_id = int(item["telegram_id"])
    panel_id = int(item["remnawave_id"])
    device_id = int(item["id"])
    title = str(item.get("title") or "")
    try:
        await rw.extend_panel_user(panel_id, PANEL_LEASE_DAYS)
        await db.mark_devices_billed([device_id], status="ACTIVE", expire_at=_lease_until())
        await db.log_billing_event(
            tg_id,
            "pause" if paused else "charge",
            source=source,
            amount=0 if paused else -price,
            device_id=device_id,
            device_title=title,
            note="Пауза тарификации, сутки без списания" if paused else "Списание за сутки VPN",
        )
    except RemnawaveError:
        if not paused:
            await db.add_balance_rub(tg_id, price)
        logger.exception("Не удалось продлить устройство %s", device_id)
        await db.log_billing_event(
            tg_id,
            "error",
            source=source,
            device_id=device_id,
            device_title=title,
            note="Панель не продлила устройство при паузе" if paused else "Панель не продлила, деньги вернули",
        )
        return False
    return True


async def _commit_extends(
    rw: RemnawaveClient,
    items: list[dict],
    *,
    price: int,
    paused: bool,
    source: str,
    chunk: int,
) -> tuple[int, str]:
    if not items:
        return 0, "нет"
    ok = 0
    used_bulk = False
    used_one = False
    kind = "pause" if paused else "charge"
    note = "Пауза тарификации, сутки без списания" if paused else "Списание за сутки VPN"
    amount = 0 if paused else -price
    for part in _chunks(items, chunk):
        pids = [int(x["remnawave_id"]) for x in part]
        try:
            await rw.bulk_refresh_lease(pids, PANEL_LEASE_DAYS)
            used_bulk = True
        except RemnawaveError:
            logger.warning("Пакетное продление недоступно, иду по одному (%s шт.)", len(part))
            used_one = True
            for item in part:
                if await _extend_already_charged(rw, item, price, paused, source):
                    ok += 1
            continue
        await db.mark_devices_billed(
            [int(x["id"]) for x in part],
            status="ACTIVE",
            expire_at=_lease_until(),
        )
        await db.log_billing_events(
            [
                {
                    "telegram_id": int(item["telegram_id"]),
                    "kind": kind,
                    "source": source,
                    "amount": amount,
                    "device_id": int(item["id"]),
                    "device_title": str(item.get("title") or ""),
                    "note": note,
                }
                for item in part
            ]
        )
        ok += len(part)
    return ok, _panel_mode(used_bulk, used_one)


async def _commit_revives(
    rw: RemnawaveClient,
    items: list[dict],
    *,
    chunk: int,
) -> tuple[int, str]:
    if not items:
        return 0, "нет"
    ok = 0
    used_bulk = False
    used_one = False
    until = _lease_until()
    for part in _chunks(items, chunk):
        pids = [int(x["remnawave_id"]) for x in part]
        try:
            await rw.bulk_refresh_lease(pids, PANEL_LEASE_DAYS)
            used_bulk = True
        except RemnawaveError:
            logger.warning("Пакетное включение недоступно, иду по одному (%s шт.)", len(part))
            used_one = True
            for item in part:
                try:
                    await rw.enable_panel_user(int(item["remnawave_id"]))
                except RemnawaveError:
                    logger.exception("Не удалось включить устройство %s", item["id"])
                    await db.log_billing_event(
                        int(item["telegram_id"]),
                        "error",
                        source="cron",
                        device_id=int(item["id"]),
                        device_title=str(item.get("title") or ""),
                        note="Панель не включила уже оплаченное устройство",
                    )
                    continue
                await db.mark_devices_billed(
                    [int(item["id"])],
                    status="ACTIVE",
                    expire_at=until,
                    touch_billed=False,
                )
                await db.log_billing_event(
                    int(item["telegram_id"]),
                    "revive",
                    source="cron",
                    device_id=int(item["id"]),
                    device_title=str(item.get("title") or ""),
                    note="Снова включили устройство: срок в панели кончился раньше оплаты",
                )
                ok += 1
            continue
        await db.mark_devices_billed(
            [int(x["id"]) for x in part],
            status="ACTIVE",
            expire_at=until,
            touch_billed=False,
        )
        await db.log_billing_events(
            [
                {
                    "telegram_id": int(item["telegram_id"]),
                    "kind": "revive",
                    "source": "cron",
                    "amount": 0,
                    "device_id": int(item["id"]),
                    "device_title": str(item.get("title") or ""),
                    "note": "Снова включили устройство: срок в панели кончился раньше оплаты",
                }
                for item in part
            ]
        )
        ok += len(part)
    return ok, _panel_mode(used_bulk, used_one)


async def _disable_one(
    rw: RemnawaveClient,
    bot: Bot | None,
    item: dict,
    price: int,
    warned: set[int],
    source: str,
) -> bool:
    tg_id = int(item["telegram_id"])
    panel_id = int(item["remnawave_id"])
    device_id = int(item["id"])
    title = str(item.get("title") or "")
    try:
        await rw.disable_panel_user(panel_id)
    except RemnawaveError:
        logger.exception("Не удалось отключить устройство %s", device_id)
        await db.log_billing_event(
            tg_id,
            "error",
            source=source,
            device_id=device_id,
            device_title=title,
            note="Панель не отключила устройство",
        )
        return False
    await db.mark_devices_billed([device_id], status="DISABLED")
    await db.log_billing_event(
        tg_id,
        "disable",
        source=source,
        device_id=device_id,
        device_title=title,
        note="Не хватило баланса на сутки",
    )
    await _notify_empty(bot, tg_id, price, warned)
    return True


async def _commit_disables(
    rw: RemnawaveClient,
    items: list[dict],
    *,
    bot: Bot | None,
    price: int,
    source: str,
    chunk: int,
) -> tuple[int, str]:
    if not items:
        return 0, "нет"
    warned: set[int] = set()
    ok = 0
    used_bulk = False
    used_one = False
    for part in _chunks(items, chunk):
        pids = [int(x["remnawave_id"]) for x in part]
        try:
            await rw.bulk_update_users(pids, {"status": "DISABLED"})
            used_bulk = True
        except RemnawaveError:
            logger.warning("Пакетное отключение недоступно, иду по одному (%s шт.)", len(part))
            used_one = True
            for item in part:
                if await _disable_one(rw, bot, item, price, warned, source):
                    ok += 1
            continue
        await db.mark_devices_billed(
            [int(x["id"]) for x in part],
            status="DISABLED",
        )
        await db.log_billing_events(
            [
                {
                    "telegram_id": int(item["telegram_id"]),
                    "kind": "disable",
                    "source": source,
                    "amount": 0,
                    "device_id": int(item["id"]),
                    "device_title": str(item.get("title") or ""),
                    "note": "Не хватило баланса на сутки",
                }
                for item in part
            ]
        )
        for item in part:
            await _notify_empty(bot, int(item["telegram_id"]), price, warned)
            ok += 1
    return ok, _panel_mode(used_bulk, used_one)


async def charge_due_devices(rw: RemnawaveClient, bot: Bot | None = None) -> None:
    settings = get_settings()
    if not settings.balance_enabled:
        return
    await collect_due_trusts(bot)
    flags = await db.get_flags()
    if flags.get("maintenance"):
        return
    price = max(1, settings.vpn_day_price_rub)
    paused = bool(flags.get("billing_paused"))
    started = time.monotonic()
    seen: set[int] = set()
    pending: list[dict] = []
    for item in await db.devices_due_for_billing():
        seen.add(int(item["id"]))
        pending.append(item)
    for item in await db.devices_to_retry_disable():
        if int(item["id"]) in seen:
            continue
        pending.append(item)
    chunk = max(20, min(200, settings.billing_bulk_chunk))
    extended = 0
    disabled = 0
    extend_mode = "нет"
    disable_mode = "нет"
    if pending:
        groups: dict[int, list[dict]] = defaultdict(list)
        for item in pending:
            groups[int(item["telegram_id"])].append(item)
        for rows in groups.values():
            rows.sort(key=lambda x: int(x["id"]))
        sem = asyncio.Semaphore(max(1, settings.billing_concurrency))

        async def decide(tg_id: int, devices: list[dict]) -> tuple[list[dict], list[dict]]:
            async with sem:
                return await _decide_user_devices(devices, price, paused)

        keys = list(groups.items())
        decided: list[tuple[list[dict], list[dict]]] = []
        for part in _chunks(keys, 400):
            decided.extend(
                await asyncio.gather(*[decide(tg, rows) for tg, rows in part])
            )
        extend: list[dict] = []
        disable: list[dict] = []
        for ext, dis in decided:
            extend.extend(ext)
            disable.extend(dis)
        extended, extend_mode = await _commit_extends(
            rw, extend, price=price, paused=paused, source="cron", chunk=chunk
        )
        disabled, disable_mode = await _commit_disables(
            rw, disable, bot=bot, price=price, source="cron", chunk=chunk
        )
        for item in extend:
            seen.add(int(item["id"]))
        for item in disable:
            seen.add(int(item["id"]))
    revive = [
        item
        for item in await db.devices_needing_revive()
        if int(item["id"]) not in seen
    ]
    revived, revive_mode = await _commit_revives(rw, revive, chunk=chunk)
    logger.info(
        "Списание: к оплате %s, продлили %s, отключили %s, включили снова %s",
        len(pending),
        extended,
        disabled,
        revived,
    )
    await db.set_job_report(
        "billing",
        {
            "pending": len(pending),
            "extended": extended,
            "disabled": disabled,
            "revived": revived,
            "extend_mode": extend_mode,
            "disable_mode": disable_mode,
            "revive_mode": revive_mode,
            "paused": paused,
            "seconds": round(time.monotonic() - started, 1),
        },
    )
    await send_low_balance_cabinet_links(bot)


async def sync_user_billing(
    rw: RemnawaveClient,
    telegram_id: int,
    bot: Bot | None = None,
) -> dict:
    settings = get_settings()
    result = {"extended": 0, "disabled": 0, "revived": 0}
    if not settings.balance_enabled:
        return result
    if await db.user_is_blocked(telegram_id):
        return result
    price = max(1, settings.vpn_day_price_rub)
    paused = await db.flag_on("billing_paused")
    warned: set[int] = set()
    for item in await db.list_devices(telegram_id):
        if not item.get("remnawave_id"):
            continue
        row = {
            "id": item["id"],
            "telegram_id": telegram_id,
            "remnawave_id": item["remnawave_id"],
            "title": item.get("title") or "",
        }
        if paused or not _billed_recently(item.get("last_billed_at"), item.get("last_billed_on")):
            status = await _bill_due_device(rw, bot, row, price, paused, warned, source="admin")
            if status == "extended":
                result["extended"] += 1
            elif status == "disabled":
                result["disabled"] += 1
            continue
        local_status = str(item.get("panel_status") or "").upper()
        if local_status not in {"DISABLED", "EXPIRED", ""}:
            expire = item.get("expire_at")
            if expire is not None:
                if getattr(expire, "tzinfo", None) is None:
                    expire = expire.replace(tzinfo=timezone.utc)
                if expire > datetime.now(timezone.utc) + timedelta(hours=12):
                    continue
        try:
            panel = await rw.get_user_by_id(int(item["remnawave_id"]))
        except RemnawaveError:
            logger.exception("Не удалось проверить устройство %s после смены баланса", item["id"])
            continue
        if is_subscription_active(panel):
            continue
        try:
            await rw.enable_panel_user(int(item["remnawave_id"]))
            result["revived"] += 1
            await db.mark_devices_billed(
                [int(item["id"])],
                status="ACTIVE",
                expire_at=_lease_until(),
                touch_billed=False,
            )
            await db.log_billing_event(
                telegram_id,
                "revive",
                source="admin",
                device_id=int(item["id"]),
                device_title=str(item.get("title") or ""),
                note="Включили устройство: оплаченные сутки ещё не кончились",
            )
        except RemnawaveError:
            logger.exception("Не удалось включить устройство %s после правки баланса", item["id"])
            result["disabled"] += 1
    if bot:
        await db.purge_expired_cabinet_tokens()
        await send_cabinet_link_to(bot, telegram_id)
    return result


async def send_cabinet_link_to(bot: Bot, telegram_id: int) -> bool:
    settings = get_settings()
    if not settings.balance_enabled or not settings.webapp_enabled:
        return False
    price = max(1, settings.vpn_day_price_rub)
    if telegram_id not in await db.users_needing_cabinet_link(price):
        return False
    sent = await _issue_and_send_cabinet_link(bot, telegram_id)
    return sent > 0


async def send_low_balance_cabinet_links(bot: Bot | None) -> int:
    settings = get_settings()
    if not bot or not settings.balance_enabled or not settings.webapp_enabled:
        return 0
    await db.purge_expired_cabinet_tokens()
    price = max(1, settings.vpn_day_price_rub)
    ids = await db.users_needing_cabinet_link(price)
    if not ids:
        return 0
    sem = asyncio.Semaphore(4)

    async def one(telegram_id: int) -> int:
        async with sem:
            return await _issue_and_send_cabinet_link(bot, telegram_id)

    sent = sum(await asyncio.gather(*[one(tid) for tid in ids]))
    if sent:
        logger.info("Ссылки на кабинет из браузера: %s", sent)
    return sent


async def _issue_and_send_cabinet_link(bot: Bot, telegram_id: int) -> int:
    settings = get_settings()
    base = (settings.webapp_public_url or runtime.webapp_url or "").rstrip("/")
    if not base.startswith("http"):
        return 0
    token = await db.issue_cabinet_token(telegram_id, CABINET_LINK_DAYS)
    url = f"{base}/?t={token}"
    text = notice_text("cabinet_link", url=url)
    try:
        await bot.send_message(telegram_id, text)
        return 1
    except Exception:
        await db.delete_cabinet_token(token)
        logger.debug("Ссылка на кабинет не ушла %s", telegram_id, exc_info=True)
        return 0
