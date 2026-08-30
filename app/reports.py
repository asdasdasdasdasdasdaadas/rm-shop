from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any

from aiogram import Bot

from app import db
from app.billing import expire_human
from app.config import get_settings
from app.remnawave import (
    RemnawaveClient,
    days_remaining,
    fetch_user_diagnostics,
    format_bytes,
    is_subscription_active,
    panel_user_key,
    parse_expire,
)
from app.sync import fetch_panel

TG_LIMIT = 3500


class ReportCooldown(Exception):
    def __init__(self, wait_sec: int) -> None:
        self.wait_sec = wait_sec
        super().__init__("cooldown")


def _dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _clip_context(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return {}
    text = json.dumps(raw, ensure_ascii=False, default=str)
    if len(text) > 20000:
        return {"_truncated": True, "preview": text[:8000]}
    return raw


def _items(data: Any) -> list:
    if data is None or (isinstance(data, dict) and data.get("_error")):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("devices", "users", "items", "history", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        if any(k in data for k in ("hwid", "uuid", "id", "name")):
            return [data]
    return []


def _human_dt(value) -> str:
    dt = _dt(value)
    if not dt:
        return "нет"
    return dt.astimezone().strftime("%d.%m.%Y %H:%M:%S")


def _ago(value) -> str:
    dt = _dt(value)
    if not dt:
        return "никогда"
    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    sec = int(delta.total_seconds())
    if sec < 0:
        return "только что"
    if sec < 60:
        return f"{sec} с назад"
    if sec < 3600:
        return f"{sec // 60} мин назад"
    if sec < 86400:
        return f"{sec // 3600} ч назад"
    return f"{sec // 86400} дн назад"


def _line(label: str, value: Any) -> str:
    text = "нет" if value is None or value == "" else str(value)
    return f"{label}: <code>{escape(text)}</code>"


def _squads(user: dict) -> str:
    raw = user.get("activeInternalSquads")
    names: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                names.append(str(item.get("name") or item.get("uuid") or ""))
            elif item:
                names.append(str(item))
    return ", ".join(x for x in names if x) or "нет"


def _compact(data: Any, limit: int = 900) -> str:
    if data is None:
        return "нет"
    if isinstance(data, dict) and data.get("_error"):
        return f"ошибка панели: {data.get('_error')}"
    try:
        text = json.dumps(data, ensure_ascii=False, default=str)
    except TypeError:
        text = str(data)
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def _guess(local: dict | None, devices: list[dict], panels: list[dict], flags: dict) -> list[str]:
    reasons: list[str] = []
    if flags.get("blocked"):
        reasons.append("Пользователь заблокирован в магазине")
    if flags.get("maintenance"):
        reasons.append("Сейчас включены техработы")
    if flags.get("billing_paused"):
        reasons.append("Тарификация на паузе")
    if not devices and get_settings().balance_enabled:
        reasons.append("В кабинете нет устройств")
    if local and get_settings().balance_enabled and int(local.get("balance_rub") or 0) <= 0 and devices:
        reasons.append("Баланс 0, устройства могут быть отключены")
    if not panels:
        reasons.append("В Remnawave нет учётки")
        return reasons
    for panel in panels:
        status = str(panel.get("status") or "").upper()
        title = panel.get("username") or panel.get("id") or "учётка"
        if status == "DISABLED":
            reasons.append(f"{title}: статус DISABLED")
        elif status == "EXPIRED":
            reasons.append(f"{title}: статус EXPIRED")
        elif status == "LIMITED":
            reasons.append(f"{title}: лимит трафика")
        elif not is_subscription_active(panel):
            reasons.append(f"{title}: подписка неактивна")
        expire = parse_expire(panel.get("expireAt"))
        if expire and expire <= datetime.now(timezone.utc):
            reasons.append(f"{title}: срок вышел {expire_human(panel)}")
        traffic = panel.get("userTraffic") if isinstance(panel.get("userTraffic"), dict) else {}
        online = traffic.get("onlineAt") or panel.get("onlineAt")
        first = traffic.get("firstConnectedAt") or panel.get("firstConnectedAt")
        if not first and not online:
            reasons.append(f"{title}: ни разу не подключался к ноде")
        elif online:
            dt = _dt(online)
            if dt and (datetime.now(timezone.utc) - dt).total_seconds() > 3600:
                reasons.append(f"{title}: последний онлайн {_ago(online)}")
        if not traffic.get("lastConnectedNodeUuid") and not panel.get("lastConnectedNodeUuid"):
            reasons.append(f"{title}: нет lastConnectedNodeUuid")
    if not reasons:
        reasons.append("Панель видит активную подписку — смотреть клиент, ноду и HWID")
    return reasons


def _panel_block(diag: dict, shop_title: str) -> str:
    user = diag.get("user") or {}
    traffic = user.get("userTraffic") if isinstance(user.get("userTraffic"), dict) else {}
    used = traffic.get("usedTrafficBytes") or user.get("usedTrafficBytes")
    life = traffic.get("lifetimeUsedTrafficBytes") or user.get("lifetimeUsedTrafficBytes")
    limit = user.get("trafficLimitBytes")
    online = traffic.get("onlineAt") or user.get("onlineAt")
    first = traffic.get("firstConnectedAt") or user.get("firstConnectedAt")
    node_uuid = traffic.get("lastConnectedNodeUuid") or user.get("lastConnectedNodeUuid") or ""
    lines = [
        f"<b>Панель: {escape(str(shop_title or user.get('username') or user.get('id') or 'учётка'))}</b>",
        _line("id", user.get("id")),
        _line("username", user.get("username")),
        _line("uuid", user.get("uuid")),
        _line("shortUuid", user.get("shortUuid")),
        _line("status", user.get("status")),
        _line("активна", "да" if is_subscription_active(user) else "нет"),
        _line("до", expire_human(user)),
        _line("дней", days_remaining(user)),
        _line("создана", _human_dt(user.get("createdAt"))),
        _line("обновлена", _human_dt(user.get("updatedAt"))),
        _line("tag", user.get("tag")),
        _line("description", user.get("description")),
        _line("сквады", _squads(user)),
        _line("HWID limit", user.get("hwidDeviceLimit")),
        _line("traffic strategy", user.get("trafficLimitStrategy")),
        _line("лимит", format_bytes(int(limit or 0))),
        _line("трафик сейчас", format_bytes(int(used or 0))),
        _line("трафик всего", format_bytes(int(life or 0))),
        _line("первый коннект", f"{_human_dt(first)} ({_ago(first)})"),
        _line("онлайн", f"{_human_dt(online)} ({_ago(online)})"),
        _line("last node uuid", node_uuid or "нет"),
        _line("subLastUserAgent", user.get("subLastUserAgent") or user.get("lastUserAgent")),
        _line("subLastOpenedAt", _human_dt(user.get("subLastOpenedAt") or user.get("subLastOpened"))),
        _line("ссылка", user.get("subscriptionUrl") or "нет"),
    ]
    node = diag.get("node")
    if isinstance(node, dict) and not node.get("_error"):
        lines.append(
            _line(
                "нода",
                f"{node.get('name') or node.get('uuid')} · {node.get('address') or ''} "
                f"status={node.get('isConnected') if 'isConnected' in node else node.get('status')}",
            )
        )
    elif node_uuid:
        lines.append(_line("нода raw", _compact(node, 400)))
    hwid_items = _items(diag.get("hwid"))
    lines.append(_line("HWID устройств", len(hwid_items)))
    for item in hwid_items[:8]:
        lines.append(
            "  "
            + escape(
                " · ".join(
                    str(x)
                    for x in [
                        item.get("hwid") or item.get("fingerprint"),
                        item.get("platform") or item.get("os"),
                        item.get("deviceModel") or item.get("deviceOs"),
                        item.get("userAgent"),
                        _human_dt(item.get("createdAt") or item.get("updatedAt")),
                    ]
                    if x
                )
            )
        )
    if isinstance(diag.get("hwid"), dict) and diag["hwid"].get("_error") and not hwid_items:
        lines.append(_line("HWID", diag["hwid"].get("_error")))
    if diag.get("bandwidth") and not (isinstance(diag["bandwidth"], dict) and diag["bandwidth"].get("_error")):
        lines.append(_line("bandwidth", _compact(diag.get("bandwidth"), 500)))
    if diag.get("subscription") and not (
        isinstance(diag["subscription"], dict) and diag["subscription"].get("_error")
    ):
        lines.append(_line("subscription api", _compact(diag.get("subscription"), 500)))
    return "\n".join(lines)


def _client_block(ctx: dict) -> str:
    if not ctx:
        return "Клиент: данных нет"
    tg = ctx.get("telegram") if isinstance(ctx.get("telegram"), dict) else {}
    br = ctx.get("browser") if isinstance(ctx.get("browser"), dict) else {}
    me = ctx.get("me") if isinstance(ctx.get("me"), dict) else {}
    device = ctx.get("device") if isinstance(ctx.get("device"), dict) else {}
    conn = br.get("connection") if isinstance(br.get("connection"), dict) else {}
    screen = br.get("screen") if isinstance(br.get("screen"), dict) else {}
    lines = [
        "<b>Клиент</b>",
        _line("источник", ctx.get("source")),
        _line("экран", ctx.get("view") or ctx.get("screen")),
        _line("мастер шаг", ctx.get("wizard_step")),
        _line("открытое устройство", device.get("title") or "нет"),
        _line("клиент приложения", device.get("client") or ctx.get("client")),
        _line("платформа устройства", device.get("platform") or ctx.get("platform")),
        _line("TG platform", tg.get("platform")),
        _line("TG version", tg.get("version")),
        _line("язык TG", tg.get("language")),
        _line("premium", tg.get("isPremium")),
        _line("viewport", f"{tg.get('viewportHeight')} / stable {tg.get('viewportStableHeight')}"),
        _line("UA", br.get("userAgent")),
        _line("язык браузера", br.get("language")),
        _line("таймзона", f"{br.get('timezone')} (UTC{br.get('timezoneOffset')})"),
        _line("online", br.get("online")),
        _line("сеть", f"{conn.get('type')} rtt={conn.get('rtt')} down={conn.get('downlink')}"),
        _line("экран", f"{screen.get('w')}x{screen.get('h')} dpr={screen.get('dpr')}"),
        _line("кабинет days", me.get("days")),
        _line("кабинет days_left", me.get("days_left")),
        _line("баланс", me.get("balance_rub")),
        _line("устройств в ЛК", me.get("device_count")),
        _line("has_access", me.get("has_access")),
    ]
    return "\n".join(lines)


def _chunks(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for line in text.split("\n"):
        add = len(line) + 1
        if size + add > TG_LIMIT and buf:
            parts.append("\n".join(buf))
            buf = [line]
            size = add
        else:
            buf.append(line)
            size += add
    if buf:
        parts.append("\n".join(buf))
    return parts or [text[:TG_LIMIT]]


def _shop_block(local: dict | None, devices: list[dict], flags: dict) -> str:
    lines = [
        "<b>Магазин</b>",
        _line("создан", _human_dt((local or {}).get("created_at"))),
        _line("оферта", _human_dt((local or {}).get("accepted_legal_at"))),
        _line("триал", (local or {}).get("trial_used")),
        _line("баланс руб", (local or {}).get("balance_rub")),
        _line("заблокирован", _human_dt((local or {}).get("blocked_at")) if (local or {}).get("blocked_at") else "нет"),
        _line("причина блока", (local or {}).get("blocked_reason")),
        _line("last_synced", _human_dt((local or {}).get("last_synced_at"))),
        _line("техработы", flags.get("maintenance")),
        _line("тарификация на паузе", flags.get("billing_paused")),
        _line("устройств", len(devices)),
    ]
    for item in devices:
        lines.append(
            escape(
                f"  {item.get('title')} · {item.get('platform')}/{item.get('client')} · "
                f"rw={item.get('remnawave_id')} · {item.get('subscription_url') or 'без ссылки'}"
            )
        )
    return "\n".join(lines)


async def _load_panels(rw: RemnawaveClient, telegram_id: int) -> list[dict]:
    seen: set[str] = set()
    panels: list[dict] = []
    for panel_id in await db.list_panel_ids_for_user(telegram_id):
        try:
            user = await rw.get_user_by_id(panel_id)
        except Exception:
            user = None
        if not user:
            continue
        key = panel_user_key(user) or str(user.get("id"))
        if key in seen:
            continue
        seen.add(key)
        panels.append(user)
    if not panels:
        try:
            user = await fetch_panel(rw, telegram_id, force=True)
        except Exception:
            user = None
        if user:
            panels.append(user)
    return panels


async def submit_vpn_report(
    bot: Bot,
    rw: RemnawaveClient,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    client_context: dict | None = None,
) -> dict:
    settings = get_settings()
    last = await db.last_vpn_report_at(telegram_id)
    last_dt = _dt(last)
    if last_dt:
        wait = timedelta(seconds=settings.vpn_report_cooldown_sec) - (datetime.now(timezone.utc) - last_dt)
        if wait.total_seconds() > 0:
            raise ReportCooldown(int(wait.total_seconds()))

    await db.upsert_user(telegram_id, username, first_name)
    local = await db.get_user(telegram_id)
    devices = await db.list_devices(telegram_id)
    flags = {
        "maintenance": await db.flag_on("maintenance"),
        "billing_paused": await db.flag_on("billing_paused"),
        "blocked": bool((local or {}).get("blocked_at")),
    }
    ctx = _clip_context(client_context)
    panels = await _load_panels(rw, telegram_id)
    diags: list[dict] = []
    for panel in panels:
        try:
            diags.append(await fetch_user_diagnostics(rw, panel))
        except Exception as exc:
            diags.append({"user": panel, "error": str(exc)})

    reasons = _guess(local, devices, panels, flags)
    now = datetime.now().astimezone().strftime("%d.%m.%Y %H:%M:%S")
    uname = f"@{username}" if username else "без username"
    name = first_name or "—"
    expire = _dt((panels[0] or {}).get("expireAt")) if panels else _dt((local or {}).get("expire_at"))
    status = str((panels[0] or {}).get("status") or (local or {}).get("panel_status") or "")
    sub_url = (panels[0] or {}).get("subscriptionUrl") or (local or {}).get("subscription_url") or ""
    uuid = str((panels[0] or {}).get("uuid") or (local or {}).get("remnawave_uuid") or "") or None

    payload = {
        "when": now,
        "who": {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
        },
        "why": reasons,
        "shop": {
            "local": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in (local or {}).items()},
            "devices": [
                {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in item.items()}
                for item in devices
            ],
            "flags": flags,
        },
        "client": ctx,
        "remnawave": diags,
    }

    saved = await db.save_vpn_report(
        telegram_id,
        username,
        first_name,
        expire,
        status or None,
        sub_url or None,
        uuid,
        payload,
    )

    head = [
        "<b>VPN не работает</b>",
        "",
        _line("когда", now),
        f"кто: {escape(name)} ({escape(uname)})",
        _line("Telegram ID", telegram_id),
        _line("язык бота", (ctx.get("telegram") or {}).get("language") if isinstance(ctx.get("telegram"), dict) else None),
        "",
        "<b>Почему (гипотезы)</b>",
    ]
    for item in reasons:
        head.append(f"— {escape(item)}")
    head.extend(["", _shop_block(local, devices, flags), "", _client_block(ctx)])
    for diag in diags:
        title = ""
        user = diag.get("user") or {}
        for item in devices:
            if item.get("remnawave_id") is not None and user.get("id") is not None:
                if int(item["remnawave_id"]) == int(user["id"]):
                    title = str(item.get("title") or "")
                    break
        head.extend(["", _panel_block(diag, title)])

    log = "\n".join(head)
    chunks = _chunks(log)
    total = len(chunks)
    for admin_id in settings.admin_id_set:
        for i, chunk in enumerate(chunks, 1):
            prefix = f"<i>часть {i}/{total}</i>\n" if total > 1 else ""
            try:
                await bot.send_message(admin_id, prefix + chunk)
            except Exception:
                continue
    return saved
