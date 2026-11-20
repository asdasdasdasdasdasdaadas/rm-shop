"""«Шеринг подписки»: one device used from many IP addresses at once, or from too many in a day.

Every 10 minutes the bot asks Remnawave which IPs each node sees (POST /connections/by-node/{uuid},
then GET /connections/by-node/{jobId}: users[].ips[].{ip, lastSeen}). Each device is its own panel user,
so the IPs land per device in device_ips (kept 30 days). The admin gets a message when a device has
sharing_alert_simultaneous IPs seen in the last 10 minutes, or sharing_alert_daily IPs within 24 hours.
One message per device per 3 days, sooner when the number of IPs grew by half since the last one.
It goes to the live channel when one is set, otherwise to each admin in private, like «Застрял на подключении».
Panels without the connections API (older than mid-2026) just switch the check off until the next restart.

With sharing_block_enabled, a device over sharing_block_simultaneous / sharing_block_daily is punished (see punish):
the device deleted, other keys off, balance to −100 000 ₽, mark «Шеринг», blocked in the bot; the admins get the card
with what was done and «Разблокировать и вернуть баланс».
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app import db
from app.config import get_settings
from app.remnawave import RemnawaveError, _unwrap, format_bytes, parse_dt

logger = logging.getLogger("rm-shop.sharing")
router = Router()

POLL_SECONDS = 600
NOW_MINUTES = 10
KEEP_DAYS = 30
REPEAT_DAYS = 3
SHOW_IPS = 10
JOB_WAIT_SECONDS = 40

_unsupported = False


def _nodes(payload) -> list[str]:
    data = _unwrap(payload)
    if isinstance(data, dict):
        data = data.get("nodes") or data.get("items") or []
    out = []
    for n in data if isinstance(data, list) else []:
        if isinstance(n, dict) and n.get("uuid") and not n.get("isDisabled") and n.get("isConnected", True):
            out.append(str(n["uuid"]))
    return out


def parse_node_result(payload) -> dict[int, list[tuple[str, datetime]]] | None:
    """{panel user id: [(ip, last seen)]} once the job is done, None while it still runs."""
    data = _unwrap(payload)
    if not isinstance(data, dict) or not data.get("isCompleted"):
        return None
    out: dict[int, list[tuple[str, datetime]]] = {}
    result = data.get("result") or {}
    for user in result.get("users") or []:
        try:
            uid = int(user.get("userId"))
        except (TypeError, ValueError):
            continue
        for item in user.get("ips") or []:
            ip, seen = str(item.get("ip") or "").strip(), parse_dt(item.get("lastSeen"))
            if ip and seen:
                out.setdefault(uid, []).append((ip, seen))
    return out


async def _node_ips(rw, node_uuid: str) -> dict[int, list[tuple[str, datetime]]]:
    job = _unwrap(await rw._request("POST", f"/connections/by-node/{node_uuid}", json={}))
    job_id = (job or {}).get("jobId") if isinstance(job, dict) else None
    if not job_id:
        return {}
    for _ in range(JOB_WAIT_SECONDS // 2):
        await asyncio.sleep(2)
        raw = await rw._request("GET", f"/connections/by-node/{job_id}")
        data = _unwrap(raw)
        if isinstance(data, dict) and data.get("isFailed"):
            return {}
        got = parse_node_result(raw)
        if got is not None:
            return got
    logger.info("IP с ноды %s не пришли за %s с", node_uuid, JOB_WAIT_SECONDS)
    return {}


async def collect(rw) -> int:
    """Ask every node, store the IPs per device. Returns how many (device, ip) rows were written."""
    global _unsupported
    try:
        nodes = _nodes(await rw._request("GET", "/nodes"))
    except RemnawaveError:
        logger.warning("Список нод не получен", exc_info=True)
        return 0
    seen: dict[int, dict[str, datetime]] = {}
    for node in nodes:
        try:
            got = await _node_ips(rw, node)
        except RemnawaveError as exc:
            if "→ 404" in str(exc):
                _unsupported = True
                logger.warning("Панель не отдаёт IP подключений (нет /connections) — проверка шеринга выключена")
                return 0
            logger.warning("IP с ноды %s не получены", node, exc_info=True)
            continue
        for uid, ips in got.items():
            bucket = seen.setdefault(uid, {})
            for ip, when in ips:
                if ip not in bucket or when > bucket[ip]:
                    bucket[ip] = when
    return await db.store_device_ips(seen)


def _ago(when: datetime | None, now: datetime) -> str:
    if not when:
        return ""
    minutes = max(0, int((now - when).total_seconds() // 60))
    if minutes < NOW_MINUTES:
        return "сейчас"
    if minutes < 60:
        return f"{minutes} мин назад"
    hours = minutes // 60
    return f"{hours} ч назад" if hours < 24 else f"{hours // 24} дн назад"


def _admin_link() -> str:
    base = (get_settings().webapp_public_url or "").rstrip("/")
    return f"{base}/admin" if base.startswith("https://") else ""


def format_alert(row: dict, ips: list[dict], now: datetime | None = None, *,
                 blocked: bool = False, actions: list[str] = ()) -> tuple[str, InlineKeyboardMarkup]:
    from app.live import _heading, _who
    now = now or datetime.now(timezone.utc)
    lines = [_heading("action", "🔁", "Шеринг подписки — заблокирован" if blocked else "Шеринг подписки"), "", _who(row), ""]
    if blocked:
        lines[-1:-1] = list(actions) or ["Все ключи выключены, в боте заблокирован. Пополнение их не включит."]
    app_bits = " · ".join(escape(str(x)) for x in (row.get("platform"), row.get("client")) if x)
    lines.append(f"Устройство: <b>{escape(str(row.get('title') or 'без названия'))}</b>" + (f" · {app_bits}" if app_bits else ""))
    lines.append(f"Одновременно: <b>{int(row['now_ips'])} IP</b> · за сутки: <b>{int(row['day_ips'])} IP</b>")
    lines.append("")
    for item in ips[:SHOW_IPS]:
        lines.append(f"<code>{escape(str(item['ip']))}</code> — {_ago(parse_dt(item['last_seen']), now)}")
    if len(ips) > SHOW_IPS:
        lines.append(f"… и ещё {len(ips) - SHOW_IPS}")
    total = int(row.get("lifetime_traffic_bytes") or row.get("used_traffic_bytes") or 0)
    created = parse_dt(row.get("created_at")) or now
    days = max(1, (now - created).days or 1)
    lines.append("")
    lines.append(f"Трафик: всего <b>{format_bytes(total)}</b> · в среднем {format_bytes(total // days)} в день")
    tid = int(row["telegram_id"])
    buttons = [[InlineKeyboardButton(text="Разблокировать и вернуть баланс", callback_data=f"shr:unblock:{tid}") if blocked else
                InlineKeyboardButton(text="Сбросить подключения", callback_data=f"shr:drop:{int(row['device_id'])}")]]
    second = []
    link = _admin_link()
    if link:
        second.append(InlineKeyboardButton(text="Открыть клиента", url=f"{link}#users?q={tid}"))
    handle = str(row.get("username") or "").lstrip("@").strip()
    if handle:
        second.append(InlineKeyboardButton(text="Написать", url=f"https://t.me/{handle}"))
    if second:
        buttons.insert(0, second)
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_due(bot) -> int:
    s = get_settings()
    if not s.sharing_alert_enabled:
        return 0
    from app.stuck_alert import _targets
    targets = await _targets()
    if not targets:
        return 0
    rows = await db.claim_sharing_alerts(int(s.sharing_alert_simultaneous), int(s.sharing_alert_daily),
                                         NOW_MINUTES, REPEAT_DAYS)
    for row in rows:
        ips = await db.device_ips_recent(int(row["device_id"]))
        text, markup = format_alert(row, ips)
        await _send_admins(bot, text, markup)
    return len(rows)


async def _send_admins(bot, text: str, markup) -> None:
    from app.stuck_alert import _targets
    for chat in await _targets():
        try:
            await bot.send_message(chat, text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            logger.warning("Уведомление о шеринге не ушло в %s", chat, exc_info=True)


def _rub(n: int) -> str:
    return f"{n:,}".replace(",", " ").replace("-", "−") + " ₽"


async def punish(rw, bot, row: dict) -> list[str]:
    """Everything that happens to a person caught sharing; returns what was done, for the admin card.

    Always: every key switched off, connections dropped, the mark «Шеринг», blocked in the bot (so neither a top-up
    nor the daily billing switches anything back on). By the settings: the sharing device deleted (panel and here),
    the balance brought down to sharing_penalty_balance_rub (the difference is remembered for «Разблокировать»)."""
    s = get_settings()
    tid, device_id = int(row["telegram_id"]), int(row["device_id"])
    done: list[str] = []
    device = await db.get_device(tid, device_id) if s.sharing_delete_device else None
    if device:
        try:
            if device.get("remnawave_id"):
                await rw.delete_panel_user(int(device["remnawave_id"]))
            await db.delete_device(tid, device_id)
            await db.log_billing_event(tid, "device_delete", source="sharing", device_id=device_id,
                                       device_title=str(device.get("title") or ""), note="Удалено за шеринг")
            done.append(f"🗑 Устройство «{escape(str(device.get('title') or 'без названия'))}» удалено")
        except RemnawaveError:
            logger.warning("Устройство %s не удалилось в панели (tg %s)", device_id, tid, exc_info=True)
            done.append("⚠️ Панель не удалила устройство — оно выключено вместе с остальными")
    panel_ids = await db.list_panel_ids_for_user(tid)   # a device the panel refused to delete is still here
    off = 0
    for panel_id in panel_ids:
        try:
            await rw.disable_panel_user(panel_id)
            off += 1
        except RemnawaveError:
            logger.warning("Ключ %s не выключился при блоке за шеринг (tg %s)", panel_id, tid, exc_info=True)
    if panel_ids:
        try:
            await rw._request("POST", "/connections/drop", json={
                "dropBy": {"by": "userIds", "userIds": panel_ids}, "targetNodes": {"target": "allNodes"}})
        except RemnawaveError:
            logger.warning("Подключения tg %s не сбросились", tid, exc_info=True)
    if off:
        done.append(f"⏸ {'Остальные ключи' if done else 'Ключи'} выключены: {off}")
    await db.mark_sharing(tid)
    if s.sharing_penalty_enabled:
        target = int(s.sharing_penalty_balance_rub)
        taken, after = await db.apply_sharing_penalty(tid, target)
        if taken:
            await db.log_billing_event(tid, "sharing", source="sharing", amount=-taken, balance_after=after,
                                       note=f"Шеринг: баланс до {_rub(target)}")
        done.append(f"💸 Баланс: {_rub(after)}" + (f" (списано {_rub(taken)})" if taken else ""))
    reason = (f"Шеринг: {int(row['now_ips'])} IP одновременно, {int(row['day_ips'])} за сутки "
              f"({row.get('title') or 'устройство'})")
    await db.set_user_blocked(tid, True, reason)
    done.append("⛔️ Пометка «Шеринг», в боте заблокирован")
    logger.info("Шеринг: tg %s — %s", tid, "; ".join(done))
    return done


async def block_due(rw, bot) -> list[dict]:
    """Punish everyone over the block thresholds. Returns who was caught and what was done."""
    s = get_settings()
    if not s.sharing_block_enabled:
        return []
    from app.block import notify_blocked
    caught = []
    for row in await db.sharing_offenders(int(s.sharing_block_simultaneous), int(s.sharing_block_daily), NOW_MINUTES):
        tid = int(row["telegram_id"])
        if tid in s.admin_id_set:
            continue
        ips = await db.device_ips_recent(int(row["device_id"]))   # before the device (and its IPs) is deleted
        actions = await punish(rw, bot, row)
        caught.append({"telegram_id": tid, "username": row.get("username"), "first_name": row.get("first_name"),
                       "title": row.get("title"), "now_ips": int(row["now_ips"]), "day_ips": int(row["day_ips"]),
                       "actions": [re.sub(r"<[^>]+>", "", a) for a in actions]})
        if s.sharing_notify_user:
            await notify_blocked(bot, tid)
        text, markup = format_alert(row, ips, blocked=True, actions=actions)
        await _send_admins(bot, text, markup)
    return caught


_lock = asyncio.Lock()


async def run_check(rw, bot) -> dict:
    """One full pass: IPs from the panel, punish, warn, prune. The loop and «Проверить сейчас» share the lock,
    so one person is never punished twice by two passes at once."""
    async with _lock:
        if _unsupported:
            return {"ok": False, "error": "Панель не отдаёт IP подключений (нужна Remnawave с /connections)"}
        rows = await collect(rw)
        caught = await block_due(rw, bot)   # first: a blocked person gets the block card, not a second warning
        warned = await send_due(bot)
        await db.prune_device_ips(KEEP_DAYS)
        return {"ok": not _unsupported, "ips": rows, "caught": caught, "warned": warned,
                **({"error": "Панель не отдаёт IP подключений (нужна Remnawave с /connections)"} if _unsupported else {})}


async def sharing_loop(rw, bot) -> None:
    await asyncio.sleep(60)
    while not _unsupported:
        try:
            s = get_settings()
            if s.sharing_alert_enabled or s.sharing_block_enabled:
                await run_check(rw, bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Проверка шеринга")
        await asyncio.sleep(POLL_SECONDS)


@router.callback_query(F.data.startswith("shr:drop:"))
async def drop_connections(callback: CallbackQuery, rw) -> None:
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        device_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Нет устройства", show_alert=True)
        return
    panel_id = await db._pool_req().fetchval("SELECT remnawave_id FROM devices WHERE id=$1", device_id)
    if not panel_id:
        await callback.answer("Устройство уже удалено", show_alert=True)
        return
    try:
        await rw._request("POST", "/connections/drop", json={
            "dropBy": {"by": "userIds", "userIds": [int(panel_id)]},
            "targetNodes": {"target": "allNodes"}})
    except RemnawaveError as exc:
        logger.warning("Сброс подключений устройства %s", device_id, exc_info=True)
        await callback.answer(f"Панель не сбросила: {str(exc)[:150]}", show_alert=True)
        return
    await callback.answer("Подключения сброшены. Устройство переподключится само, если им пользуется один человек.",
                          show_alert=True)


@router.callback_query(F.data.startswith("shr:unblock:"))
async def unblock(callback: CallbackQuery, rw) -> None:
    if callback.from_user.id not in get_settings().admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        tid = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Нет пользователя", show_alert=True)
        return
    from app.admin import _apply_block
    if await _apply_block(rw, tid, False) == "missing":
        await callback.answer("Пользователь уже удалён", show_alert=True)
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer("Разблокирован, списанный баланс возвращён. Пометка «Шеринг» осталась. "
                          "Ключи включатся сами, если на балансе есть деньги.", show_alert=True)
