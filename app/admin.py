from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time

from html import escape

from aiohttp import web
from aiogram import Bot
from aiogram.types import FSInputFile

from app import db, runtime
from app.announcements import (
    DEFAULT_CLOSING,
    DEFAULT_KICKER,
    DEFAULT_LEAD,
    DEFAULT_TITLE,
    announcement_photo_path,
    content_type_for,
    fill_placeholders,
    format_announcement_body,
    save_announcement_photo,
    validate_announcement_photo,
)
from app.balance import sync_user_billing
from app.block import blocked_notice
from app.backup import (
    MAX_UPLOAD,
    backup_path,
    create_backup,
    list_backups,
    restore_backup,
    seconds_until_msk_0001,
)
from app.config import ROOT, get_settings
from app.shop_config import save_shop_overlay, snapshot as shop_snapshot
from app.keyboards import (
    blocked_keyboard,
    cabinet_keyboard,
    help_connect_keyboard,
    share_keyboard,
    story_nudge_keyboard,
    trial_nudge_keyboard,
)
from app.maintenance import clear_photo, has_photo, photo_path, save_photo
from app.notices import notice_text
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
    fetch_device_network,
    panel_display_traffic_bytes,
    panel_first_connected_at,
    panel_lifetime_traffic_bytes,
    panel_online_at,
    panel_sub_opened_at,
    panel_used_traffic_bytes,
    panel_user_agent,
)
from app.texts import days_text, rub_text, subscription_reissued_text
from app.tg_err import fail_extra, telegram_fail_reason

logger = logging.getLogger("rm-shop.admin")
ADMIN_DIR = ROOT / "admin"
COOKIE = "rm_admin"
COOKIE_TTL = 7 * 24 * 3600
_NO_STORE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


def _secret() -> bytes:
    settings = get_settings()
    return hashlib.sha256((settings.admin_password + settings.bot_token).encode("utf-8")).digest()


def _make_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_secret(), ts.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def _token_ok(value: str | None) -> bool:
    settings = get_settings()
    if not settings.admin_password or not value or "." not in value:
        return False
    ts, sig = value.split(".", 1)
    expected = hmac.new(_secret(), ts.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    try:
        age = time.time() - int(ts)
    except ValueError:
        return False
    return 0 <= age <= COOKIE_TTL


def _authed(request: web.Request) -> bool:
    return _token_ok(request.cookies.get(COOKIE))


def _need_auth(request: web.Request) -> web.Response | None:
    if _authed(request):
        return None
    return web.json_response({"ok": False, "error": "Нужна авторизация"}, status=401)


async def admin_redirect(_request: web.Request) -> web.Response:
    raise web.HTTPFound("/admin/")


async def admin_index(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(ADMIN_DIR / "index.html", headers=_NO_STORE)


async def api_admin_build(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "build": "43"})


async def api_login(request: web.Request) -> web.Response:
    settings = get_settings()
    if not settings.admin_password:
        return web.json_response({"ok": False, "error": "Задайте ADMIN_PASSWORD в .env"}, status=503)
    body = await request.json()
    password = str(body.get("password") or "")
    given = password.encode("utf-8")
    expected = settings.admin_password.encode("utf-8")
    if len(given) != len(expected) or not hmac.compare_digest(given, expected):
        return web.json_response({"ok": False, "error": "Неверный пароль"}, status=403)
    resp = web.json_response({"ok": True, "brand": settings.brand_name})
    resp.set_cookie(
        COOKIE,
        _make_token(),
        max_age=COOKIE_TTL,
        httponly=True,
        samesite="Lax",
        path="/",
        secure=settings.webapp_public_url.startswith("https://"),
    )
    return resp


async def api_logout(_request: web.Request) -> web.Response:
    resp = web.json_response({"ok": True})
    resp.del_cookie(COOKIE, path="/")
    return resp


async def api_session(request: web.Request) -> web.Response:
    if not _authed(request):
        return web.json_response({"ok": False, "auth": False}, status=401)
    settings = get_settings()
    return web.json_response({"ok": True, "auth": True, "brand": settings.brand_name})


async def api_stats(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    settings = get_settings()
    raw = await db.admin_stats()
    topups = await db.admin_topup_summary()
    revenue = float(topups.get("amount_rub") or 0)
    if not revenue:
        for code, count in (raw.get("plans") or {}).items():
            plan = settings.plan_by_code(code) or settings.plans.get(code)
            if plan:
                revenue += float(plan["rub"]) * int(count)
    return web.json_response(
        {
            "ok": True,
            **raw,
            "topups": topups,
            "revenue_rub": round(revenue, 2),
            "jobs": {
                "billing": await db.get_job_report("billing"),
                "panel_sync": await db.get_job_report("panel_sync"),
            },
        }
    )


def _query_extra(request: web.Request, *keys: str) -> dict:
    out: dict[str, str] = {}
    for key in keys:
        val = str(request.query.get(key) or "").strip()
        if val:
            out[key] = val
    return out


async def api_users(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    extra = _query_extra(
        request,
        "status",
        "trial",
        "devices",
        "online",
        "bal_sign",
        "bal_min",
        "bal_max",
        "from",
        "to",
        "paid",
    )
    items, total = await db.admin_list_users(q, limit, (page - 1) * limit, extra)
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


def _iso_value(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _device_base(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "title": item.get("title") or "Устройство",
        "platform": item.get("platform") or "",
        "client": item.get("client") or "",
        "status": str(item.get("panel_status") or item.get("status") or ""),
        "last_online_at": _iso_value(item.get("last_online_at")),
        "first_connected_at": None,
        "used_traffic_bytes": item.get("used_traffic_bytes"),
        "lifetime_traffic_bytes": item.get("lifetime_traffic_bytes"),
        "user_agent": "",
        "sub_last_opened_at": None,
        "node": None,
        "sessions": [],
    }


async def _enrich_device_network(rw: RemnawaveClient, item: dict) -> dict:
    out = _device_base(item)
    remnawave_id = item.get("remnawave_id")
    try:
        panel_id = int(remnawave_id) if remnawave_id is not None else None
    except (TypeError, ValueError):
        panel_id = None
    uuid = str(item.get("remnawave_uuid") or "").strip() or None
    try:
        extra = await fetch_device_network(rw, remnawave_id=panel_id, uuid=uuid)
    except Exception:
        logger.exception("device network telegram=%s device=%s", item.get("telegram_id"), item.get("id"))
        return out
    panel = extra.get("panel") if isinstance(extra.get("panel"), dict) else None
    if panel:
        online = panel_online_at(panel)
        first = panel_first_connected_at(panel)
        used = panel_used_traffic_bytes(panel)
        life = panel_lifetime_traffic_bytes(panel)
        shown = panel_display_traffic_bytes(panel)
        status = str(panel.get("status") or "").strip()
        if online:
            out["last_online_at"] = online.isoformat()
        if first:
            out["first_connected_at"] = first.isoformat()
        if shown is not None:
            out["used_traffic_bytes"] = shown
        elif used is not None:
            out["used_traffic_bytes"] = used
        if life is not None:
            out["lifetime_traffic_bytes"] = life
        elif shown is not None:
            out["lifetime_traffic_bytes"] = shown
        if status:
            out["status"] = status
        out["user_agent"] = panel_user_agent(panel)
        opened = panel_sub_opened_at(panel)
        if opened:
            out["sub_last_opened_at"] = opened.isoformat()
    node = extra.get("node")
    if isinstance(node, dict):
        out["node"] = node
    sessions = extra.get("hwid")
    if isinstance(sessions, list):
        out["sessions"] = sessions
    return out


async def api_user_devices(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    try:
        telegram_id = int(request.match_info["telegram_id"])
    except (KeyError, TypeError, ValueError):
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    local = await db.get_user(telegram_id)
    if not local:
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    rows = await db.list_devices(telegram_id)
    if not rows and local.get("remnawave_id"):
        rows = [
            {
                "id": None,
                "title": "Подписка",
                "platform": "",
                "client": "",
                "panel_status": str(local.get("panel_status") or ""),
                "last_online_at": None,
                "used_traffic_bytes": local.get("used_traffic_bytes"),
                "lifetime_traffic_bytes": local.get("lifetime_traffic_bytes"),
                "remnawave_id": local.get("remnawave_id"),
                "remnawave_uuid": local.get("remnawave_uuid"),
                "telegram_id": telegram_id,
            }
        ]
    rw: RemnawaveClient = request.app["rw"]
    sem = asyncio.Semaphore(4)

    async def one(row: dict) -> dict:
        async with sem:
            return await _enrich_device_network(rw, row)

    items = await asyncio.gather(*(one(row) for row in rows)) if rows else []
    return web.json_response({"ok": True, "items": list(items)})


async def api_referrals(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_referrals(
        q, limit, (page - 1) * limit, _query_extra(request, "reward", "from", "to")
    )
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


def _ad_public(row: dict) -> dict:
    settings = get_settings()
    slug = str(row.get("slug") or "")
    return {
        "id": int(row["id"]),
        "slug": slug,
        "title": row.get("title") or "",
        "url": f"https://t.me/{settings.bot_username}?start=ad_{slug}",
        "clicks": int(row.get("clicks") or 0),
        "users": int(row.get("users") or 0),
        "trial": int(row.get("trial") or 0),
        "paid": int(row.get("paid") or 0),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "archived": bool(row.get("archived_at")),
    }


async def api_ad_links(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    if request.method == "GET":
        archived = str(request.query.get("archived") or "") in {"1", "true", "yes"}
        items = [_ad_public(r) for r in await db.list_ad_links(include_archived=archived)]
        return web.json_response({"ok": True, "items": items})
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        row = await db.create_ad_link(str(body.get("title") or ""), str(body.get("slug") or ""))
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    item = _ad_public({**row, "users": 0, "trial": 0, "paid": 0, "clicks": int(row.get("clicks") or 0)})
    return web.json_response({"ok": True, "item": item})


async def api_ad_link_archive(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    try:
        link_id = int(request.match_info["link_id"])
    except (KeyError, TypeError, ValueError):
        return web.json_response({"ok": False, "error": "Ссылка не найдена"}, status=404)
    if not await db.archive_ad_link(link_id):
        return web.json_response({"ok": False, "error": "Ссылка уже скрыта или не найдена"}, status=404)
    return web.json_response({"ok": True})


async def api_payouts(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_payouts(
        q, limit, (page - 1) * limit, _query_extra(request, "status")
    )
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


async def api_payout_resolve(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    payout_id = int(request.match_info["payout_id"])
    body = await request.json()
    action = str(body.get("action") or "").strip()
    if action not in {"paid", "rejected"}:
        return web.json_response({"ok": False, "error": "Нужно paid или rejected"}, status=400)
    from app.payouts import finish_referral_payout

    bot: Bot = request.app["bot"]
    result = await finish_referral_payout(bot, payout_id, action, None)
    if result not in {"Выплачено", "Отказано"}:
        return web.json_response({"ok": False, "error": result}, status=400)
    return web.json_response({"ok": True, "result": result})


async def api_orders(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_orders(
        q, limit, (page - 1) * limit, _query_extra(request, "status", "from", "to")
    )
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


async def api_messages(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 40)))
    items, total = await db.admin_list_messages(
        q,
        limit,
        (page - 1) * limit,
        _query_extra(request, "channel", "source", "kind", "from", "to"),
    )
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


MSG_RETRY_MAX = 80
_MSG_RETRY_SKIP = {"maintenance_hit"}


async def _retry_markup(kind: str, telegram_id: int, extra: dict | None):
    extra = extra if isinstance(extra, dict) else {}
    settings = get_settings()
    if kind == "broadcast":
        tpl = str(extra.get("template") or "")
        if tpl == "invite":
            return share_keyboard(settings.bot_username, telegram_id)
        if tpl == "unused":
            return cabinet_keyboard()
        if tpl == "update":
            return cabinet_keyboard()
        return None
    if kind == "nudge_invite":
        return share_keyboard(settings.bot_username, telegram_id)
    if kind == "nudge_trial":
        user = await db.get_user(telegram_id)
        already = bool(user and (user.get("trial_used") or int(user.get("balance_rub") or 0) > 0))
        return trial_nudge_keyboard(trial_available=not already)
    if kind == "nudge_story":
        return story_nudge_keyboard()
    if kind == "first_device_thanks":
        return cabinet_keyboard()
    if kind == "nudge_device":
        return help_connect_keyboard()
    if kind in {"nudge_info", "nudge_idle", "low_balance", "nudge_first_online", "nudge_trial_end", "welcome_intro"}:
        return cabinet_keyboard()
    return None


async def retry_logged_message(bot: Bot, row: dict) -> tuple[bool, str]:
    kind = str(row.get("kind") or "")
    telegram_id = row.get("telegram_id")
    if kind in _MSG_RETRY_SKIP:
        return False, "Это входящее обращение, его нельзя отправить"
    if not telegram_id:
        return False, "Нет получателя"
    telegram_id = int(telegram_id)
    if await db.user_is_blocked(telegram_id):
        return False, "Пользователь заблокирован в магазине"
    extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
    origin = "manual"
    if kind == "cabinet_link":
        from app.balance import send_cabinet_link_to

        try:
            ok = await send_cabinet_link_to(bot, telegram_id, force=True, source="manual")
        except ValueError as exc:
            return False, str(exc)
        return (True, "") if ok else (False, "Не удалось отправить ссылку")
    body = str(row.get("body") or "").strip()
    if not body:
        return False, "Пустой текст"
    markup = await _retry_markup(kind, telegram_id, extra)
    title = str(row.get("title") or "")[:160]
    log_extra = {"retry_of": int(row["id"])}
    if extra.get("template"):
        log_extra["template"] = extra.get("template")
    if extra.get("image_name"):
        log_extra["image_name"] = extra.get("image_name")
    if extra.get("step") is not None:
        log_extra["step"] = extra.get("step")
    try:
        photo = None
        if extra.get("template") == "update" and extra.get("image_name"):
            photo = announcement_photo_path(str(extra.get("image_name") or ""))
        await _deliver_broadcast(bot, telegram_id, body, markup, photo)
    except Exception as exc:
        await db.log_bot_message(
            kind=kind,
            source=origin,
            telegram_id=telegram_id,
            username=row.get("username"),
            first_name=row.get("first_name"),
            title=title,
            body=body,
            status="failed",
            extra=fail_extra(exc, log_extra),
        )
        return False, telegram_fail_reason(exc)
    await db.log_bot_message(
        kind=kind,
        source=origin,
        telegram_id=telegram_id,
        username=row.get("username"),
        first_name=row.get("first_name"),
        title=title,
        body=body,
        status="sent",
        extra=log_extra,
    )
    return True, ""


async def api_message_retry(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    try:
        row = await db.get_message_log(int(request.match_info["msg_id"]))
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "Запись не найдена"}, status=404)
    if not row:
        return web.json_response({"ok": False, "error": "Запись не найдена"}, status=404)
    if str(row.get("status") or "") != "failed":
        return web.json_response({"ok": False, "error": "Повторить можно только ошибку"}, status=400)
    ok, err = await retry_logged_message(request.app["bot"], row)
    if not ok:
        return web.json_response({"ok": False, "error": err or "Не удалось отправить"}, status=502)
    return web.json_response({"ok": True})


async def api_messages_retry_failed(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    extra = _query_extra(request, "channel", "source", "kind", "from", "to")
    items, total = await db.admin_list_failed_messages(q, MSG_RETRY_MAX, extra)
    if not items:
        return web.json_response({"ok": False, "error": "Ошибок по фильтру нет"}, status=400)
    sent = 0
    failed = 0
    last_error = ""
    bot: Bot = request.app["bot"]
    for row in items:
        ok, err = await retry_logged_message(bot, row)
        if ok:
            sent += 1
        else:
            failed += 1
            last_error = err or last_error
        await asyncio.sleep(0.035)
    return web.json_response(
        {
            "ok": True,
            "sent": sent,
            "failed": failed,
            "tried": len(items),
            "total": total,
            "capped": total > len(items),
            "error": last_error or None,
        }
    )


async def api_tickets(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 40)))
    items, total = await db.admin_list_tickets(
        q,
        limit,
        (page - 1) * limit,
        _query_extra(request, "status", "from", "to"),
    )
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


async def api_ticket_one(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    ticket_id = int(request.match_info["ticket_id"])
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        return web.json_response({"ok": False, "error": "Тикет не найден"}, status=404)
    from app.tickets import serialize_messages

    messages = serialize_messages(await db.list_ticket_messages(ticket_id), for_admin=True)
    return web.json_response({"ok": True, "ticket": ticket, "messages": messages})


async def api_ticket_act(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    ticket_id = int(request.match_info["ticket_id"])
    from app.tickets import close_ticket, parse_ticket_request, receive_admin_reply, serialize_messages

    text, action, files = await parse_ticket_request(request)
    bot: Bot = request.app["bot"]
    try:
        if action == "close":
            ticket = await close_ticket(bot, ticket_id)
        else:
            ticket = await receive_admin_reply(bot, ticket_id, text, attachments=files)
    except KeyError:
        return web.json_response({"ok": False, "error": "Тикет не найден"}, status=404)
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    messages = serialize_messages(await db.list_ticket_messages(ticket_id), for_admin=True)
    return web.json_response({"ok": True, "ticket": ticket, "messages": messages})


async def api_ticket_file(request: web.Request) -> web.StreamResponse:
    denied = _need_auth(request)
    if denied:
        return denied
    from app.tickets import http_file_response

    try:
        att_id = int(request.match_info["att_id"])
    except (KeyError, ValueError, TypeError):
        return web.json_response({"ok": False, "error": "Файл не найден"}, status=404)
    row = await db.get_ticket_attachment(att_id)
    if not row:
        return web.json_response({"ok": False, "error": "Файл не найден"}, status=404)
    return http_file_response(row)


async def api_billing(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    telegram_id = None
    raw_tid = str(request.query.get("telegram_id") or "").strip()
    if raw_tid.isdigit():
        telegram_id = int(raw_tid)
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 40)))
    items, total = await db.admin_list_billing(
        q,
        limit,
        (page - 1) * limit,
        telegram_id,
        _query_extra(request, "kind", "source", "from", "to"),
    )
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


async def api_grant(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    body = await request.json()
    days = int(body.get("days") or 0)
    if days < 1 or days > 3650:
        return web.json_response({"ok": False, "error": "Укажите число от 1 до 3650"}, status=400)
    if not await db.get_user(telegram_id):
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    settings = get_settings()
    if settings.balance_enabled:
        total = await db.add_balance_rub(telegram_id, days)
        await db.log_billing_event(
            telegram_id,
            "admin_grant",
            source="admin",
            amount=days,
            balance_after=total,
            note="Начисление из админки",
        )
        billing = await sync_user_billing(request.app["rw"], telegram_id, request.app.get("bot"))
        return web.json_response({"ok": True, "balance_rub": total, "billing": billing})
    rw: RemnawaveClient = request.app["rw"]
    local = await db.get_user(telegram_id)
    panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
    try:
        user = await rw.extend_subscription(telegram_id, days, tag="ADMIN", panel_user_id=panel_id)
    except RemnawaveError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=502)
    await db.save_panel_snapshot(telegram_id, user)
    return web.json_response({"ok": True, "expire_at": user.get("expireAt")})


async def api_balance(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    body = await request.json()
    try:
        amount = int(body.get("amount"))
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "Укажите сумму в рублях"}, status=400)
    if amount == 0 or abs(amount) > 1_000_000:
        return web.json_response({"ok": False, "error": "Сумма от -1000000 до 1000000, не ноль"}, status=400)
    if not await db.get_user(telegram_id):
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    total = await db.add_balance_rub(telegram_id, amount)
    await db.log_billing_event(
        telegram_id,
        "admin_balance",
        source="admin",
        amount=amount,
        balance_after=total,
        note="Правка баланса в админке",
    )
    billing = await sync_user_billing(request.app["rw"], telegram_id, request.app.get("bot"))
    return web.json_response({"ok": True, "balance_rub": total, "billing": billing})


async def _purge_user(rw: RemnawaveClient, telegram_id: int) -> str:
    if telegram_id in get_settings().admin_id_set:
        return "skipped"
    local = await db.get_user(telegram_id)
    if not local:
        return "missing"
    for panel_id in await db.list_panel_ids_for_user(telegram_id):
        try:
            await rw.disable_panel_user(panel_id)
        except RemnawaveError:
            logger.exception("Не удалось отключить панель %s при удалении %s", panel_id, telegram_id)
    if not await db.delete_user(telegram_id):
        return "missing"
    return "ok"


async def _apply_block(
    rw: RemnawaveClient,
    telegram_id: int,
    blocked: bool,
    reason: str | None = None,
) -> str:
    if telegram_id in get_settings().admin_id_set:
        return "skipped"
    if not await db.get_user(telegram_id):
        return "missing"
    if blocked:
        for panel_id in await db.list_panel_ids_for_user(telegram_id):
            try:
                await rw.disable_panel_user(panel_id)
            except RemnawaveError:
                logger.exception("Не удалось отключить панель %s при блоке %s", panel_id, telegram_id)
        await db.set_user_blocked(telegram_id, True, reason)
    else:
        await db.set_user_blocked(telegram_id, False)
        await db.clear_device_billing(telegram_id)
    return "ok"


async def api_delete_user(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    result = await _purge_user(request.app["rw"], telegram_id)
    if result == "missing":
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    if result == "skipped":
        return web.json_response({"ok": False, "error": "Админа удалить нельзя"}, status=400)
    return web.json_response({"ok": True})


async def api_purge_bot_blockers(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    ids, total = await db.list_idle_bot_blockers(200)
    bot: Bot = request.app["bot"]
    rw: RemnawaveClient = request.app["rw"]
    deleted = 0
    clawed = 0
    skipped = 0
    for telegram_id in ids:
        if telegram_id in get_settings().admin_id_set:
            skipped += 1
            continue
        result = await db.clawback_idle_referral(telegram_id)
        if result:
            clawed += 1
            name = escape(str(result.get("invitee_name") or "друг"))
            text = notice_text(
                "referral_clawback",
                name=name,
                amount=rub_text(int(result["amount"])),
            )
            try:
                await bot.send_message(int(result["referrer_id"]), text)
            except Exception:
                logger.debug(
                    "Не удалось написать о возврате рефералки %s",
                    result["referrer_id"],
                    exc_info=True,
                )
        status = await _purge_user(rw, telegram_id)
        if status == "ok":
            deleted += 1
        else:
            skipped += 1
        await asyncio.sleep(0.02)
    remaining = max(0, int(total) - deleted)
    return web.json_response(
        {
            "ok": True,
            "deleted": deleted,
            "clawed": clawed,
            "skipped": skipped,
            "total": total,
            "remaining": remaining,
        }
    )


async def api_block_user(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    body = await request.json()
    blocked = bool(body.get("blocked"))
    reason = str(body.get("reason") or "").strip() or None
    result = await _apply_block(request.app["rw"], telegram_id, blocked, reason)
    if result == "missing":
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    if result == "skipped":
        return web.json_response({"ok": False, "error": "Админа заблокировать нельзя"}, status=400)
    if blocked:
        bot: Bot = request.app["bot"]
        try:
            await bot.send_message(telegram_id, blocked_notice(), reply_markup=blocked_keyboard())
        except Exception:
            logger.debug("Не удалось написать заблокированному %s", telegram_id, exc_info=True)
    return web.json_response({"ok": True, "blocked": blocked})


BULK_MAX = 500


async def api_users_bulk(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    body = await request.json()
    action = str(body.get("action") or "").strip()
    if action not in {"delete", "trial_reset", "message", "block", "unblock", "reissue", "cabinet_link"}:
        return web.json_response({"ok": False, "error": "Неизвестное действие"}, status=400)
    ids: list[int] = []
    if body.get("all_matching"):
        extra = {}
        for key in ("status", "trial", "devices", "online", "bal_sign", "bal_min", "bal_max", "from", "to"):
            val = str(body.get(key) or "").strip()
            if val:
                extra[key] = val
        q = str(body.get("q") or "")
        ids, total = await db.admin_user_ids(q, BULK_MAX + 1, extra)
        if total > BULK_MAX:
            return web.json_response(
                {
                    "ok": False,
                    "error": f"Слишком много совпадений ({total}). Уточните поиск, максимум {BULK_MAX}.",
                },
                status=400,
            )
    else:
        raw = body.get("ids") or []
        if not isinstance(raw, list) or not raw:
            return web.json_response({"ok": False, "error": "Никого не выбрано"}, status=400)
        for item in raw[: BULK_MAX + 1]:
            try:
                ids.append(int(item))
            except (TypeError, ValueError):
                continue
        ids = list(dict.fromkeys(ids))
        if len(ids) > BULK_MAX:
            return web.json_response(
                {"ok": False, "error": f"За раз не больше {BULK_MAX} пользователей"},
                status=400,
            )
    if not ids:
        return web.json_response({"ok": False, "error": "Никого не выбрано"}, status=400)
    if action == "cabinet_link":
        from app.balance import _cabinet_public_base

        if not _cabinet_public_base().startswith("https://"):
            return web.json_response(
                {"ok": False, "error": "Нужен HTTPS в WEBAPP_PUBLIC_URL"},
                status=400,
            )
    ok_n = 0
    skipped = 0
    failed = 0
    rw: RemnawaveClient = request.app["rw"]
    bot: Bot = request.app["bot"]
    text = str(body.get("text") or "").strip()
    if action == "message":
        if not text:
            return web.json_response({"ok": False, "error": "Пустой текст"}, status=400)
        if len(text) > 3500:
            return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
        job = _bc_job(request.app)
        if job.get("running"):
            return web.json_response({"ok": False, "error": "Рассылка уже идёт", **job}, status=409)
        started = _start_broadcast_job(request.app, text, ids)
        return web.json_response({"ok": True, "queued": True, **started})
    for telegram_id in ids:
        try:
            if action == "delete":
                result = await _purge_user(rw, telegram_id)
                if result == "ok":
                    ok_n += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1
            elif action == "block":
                result = await _apply_block(rw, telegram_id, True)
                if result == "ok":
                    ok_n += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1
            elif action == "unblock":
                result = await _apply_block(rw, telegram_id, False)
                if result == "ok":
                    ok_n += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1
            elif action == "trial_reset":
                if await db.reset_trial(telegram_id):
                    ok_n += 1
                else:
                    failed += 1
            elif action == "reissue":
                links = await _reissue_user_subscriptions(rw, telegram_id)
                await _notify_reissued(bot, {telegram_id: links})
                ok_n += 1
            elif action == "cabinet_link":
                from app.balance import send_cabinet_link_to

                if await send_cabinet_link_to(bot, telegram_id, force=True, source="manual"):
                    ok_n += 1
                else:
                    failed += 1
            else:
                continue
        except Exception:
            logger.exception("Массовое действие %s не удалось для %s", action, telegram_id)
            failed += 1
    return web.json_response(
        {"ok": True, "action": action, "done": ok_n, "skipped": skipped, "failed": failed, "total": len(ids)}
    )


async def api_trial_reset(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    if not await db.reset_trial(telegram_id):
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    return web.json_response({"ok": True})


async def api_message(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    body = await request.json()
    text = str(body.get("text") or "").strip()
    if not text:
        return web.json_response({"ok": False, "error": "Пустой текст"}, status=400)
    bot: Bot = request.app["bot"]
    try:
        await bot.send_message(telegram_id, text)
    except Exception as exc:
        await db.log_bot_message(
            kind="admin_dm",
            source="manual",
            telegram_id=telegram_id,
            title="Сообщение из админки",
            body=text,
            status="failed",
            extra=fail_extra(exc),
        )
        return web.json_response({"ok": False, "error": str(exc)}, status=502)
    await db.log_bot_message(
        kind="admin_dm",
        source="manual",
        telegram_id=telegram_id,
        title="Сообщение из админки",
        body=text,
        status="sent",
    )
    return web.json_response({"ok": True})


async def api_cabinet_link(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    from app.balance import send_cabinet_link_to

    try:
        ok = await send_cabinet_link_to(
            request.app["bot"],
            telegram_id,
            force=True,
            source="manual",
        )
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    if not ok:
        return web.json_response({"ok": False, "error": "Не удалось отправить ссылку"}, status=502)
    return web.json_response({"ok": True})


async def _broadcast_all(
    bot: Bot,
    text: str,
    job: dict,
    ids: list[int] | None = None,
    template: str | None = None,
) -> None:
    tpl = str(template or "").strip()
    if tpl in {"invite", "unused"}:
        audience = "using" if tpl == "invite" else "unused"
        targets = await db.list_broadcast_targets(audience)
    elif ids is not None:
        targets = [{"telegram_id": int(item), "first_name": None} for item in ids]
    else:
        targets = await db.list_broadcast_targets("all")
    job["total"] = len(targets)
    settings = get_settings()
    for row in targets:
        if not job.get("running"):
            break
        telegram_id = int(row["telegram_id"])
        body, markup = _broadcast_payload(tpl, text, telegram_id, row.get("first_name"), settings)
        extra = {"template": tpl or "custom"}
        image_name = str(job.get("image_name") or "").strip()
        if image_name:
            extra["image_name"] = image_name
        photo = announcement_photo_path(image_name) if tpl == "update" else None
        try:
            await _deliver_broadcast(bot, telegram_id, body, markup, photo)
            job["sent"] = int(job.get("sent") or 0) + 1
            await db.log_bot_message(
                kind="broadcast",
                source="manual",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title=_broadcast_title(tpl),
                body=body,
                status="sent",
                extra=extra,
            )
        except Exception as exc:
            job["failed"] = int(job.get("failed") or 0) + 1
            await db.log_bot_message(
                kind="broadcast",
                source="manual",
                telegram_id=telegram_id,
                first_name=row.get("first_name"),
                title=_broadcast_title(tpl),
                body=body,
                status="failed",
                extra=fail_extra(exc, extra),
            )
        await asyncio.sleep(0.035)


async def _deliver_broadcast(bot: Bot, telegram_id: int, body: str, markup, photo) -> None:
    if photo is None:
        await bot.send_message(telegram_id, body, reply_markup=markup)
        return
    if len(body) <= 1024:
        await bot.send_photo(
            telegram_id,
            FSInputFile(photo),
            caption=body,
            parse_mode=None,
            reply_markup=markup,
        )
        return
    await bot.send_photo(
        telegram_id,
        FSInputFile(photo),
        parse_mode=None,
    )
    await bot.send_message(telegram_id, body, reply_markup=markup)


def _broadcast_title(template: str) -> str:
    if template == "invite":
        return "Рассылка: пользуются VPN"
    if template == "unused":
        return "Рассылка: не подключались"
    if template == "update":
        return "Анонс обновления"
    return "Рассылка"


def _referral_reward_label() -> str:
    settings = get_settings()
    if settings.balance_enabled:
        return rub_text(settings.referral_reward_rub)
    return days_text(settings.referral_reward_days)


def _broadcast_payload(
    template: str,
    text: str,
    telegram_id: int,
    first_name: str | None,
    settings,
) -> tuple[str, object]:
    if template == "invite":
        link = f"https://t.me/{settings.bot_username}?start=ref_{telegram_id}"
        body = notice_text(
            "broadcast_invite",
            reward=_referral_reward_label(),
            link=link,
            name=escape(str(first_name or "друг")),
        )
        return body, share_keyboard(settings.bot_username, telegram_id)
    if template == "unused":
        body = notice_text(
            "broadcast_unused",
            name=escape(str(first_name or "друг")),
        )
        return body, cabinet_keyboard()
    if template == "update":
        return fill_placeholders(text, first_name), cabinet_keyboard()
    return text, None


async def _run_broadcast_job(
    app: web.Application,
    text: str,
    ids: list[int] | None = None,
    template: str | None = None,
) -> None:
    job = _bc_job(app)
    bot: Bot = app["bot"]
    try:
        await _broadcast_all(bot, text, job, ids, template)
        prefix = "Выбранным. " if job.get("scope") == "selected" else ""
        job["message"] = f"{prefix}Отправлено: {job.get('sent') or 0}, ошибок: {job.get('failed') or 0}"
    except Exception as exc:
        logger.exception("Рассылка не удалась")
        job["error"] = str(exc)
        job["message"] = f"Сбой: {exc}"
    finally:
        job["running"] = False


def _new_bc_job() -> dict:
    return {
        "running": False,
        "scope": "all",
        "template": "",
        "image_name": "",
        "total": 0,
        "sent": 0,
        "failed": 0,
        "error": None,
        "message": "",
    }


def _bc_job(app: web.Application) -> dict:
    job = app.get("broadcast_job")
    if not isinstance(job, dict):
        job = _new_bc_job()
        app["broadcast_job"] = job
    return job


def _start_broadcast_job(
    app: web.Application,
    text: str,
    ids: list[int] | None = None,
    template: str | None = None,
    *,
    image_name: str | None = None,
) -> dict:
    job = _bc_job(app)
    job.update(_new_bc_job())
    job["running"] = True
    job["scope"] = "selected" if ids is not None else "all"
    job["template"] = str(template or "")
    job["image_name"] = str(image_name or "")
    if ids is not None:
        job["total"] = len(ids)
    job["message"] = "Запущено"
    asyncio.create_task(_run_broadcast_job(app, text, ids, template))
    return job


def _broadcast_template_preview(template: str) -> str:
    settings = get_settings()
    if template == "invite":
        link = f"https://t.me/{settings.bot_username}?start=ref_…"
        return notice_text(
            "broadcast_invite",
            reward=_referral_reward_label(),
            link=link,
            name="друг",
        )
    if template == "unused":
        return notice_text("broadcast_unused", name="друг")
    return ""


async def api_broadcast(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    job = _bc_job(request.app)
    audiences = {}
    if request.method == "GET" or not job.get("running"):
        audiences = await db.broadcast_audience_counts()
    if request.method == "GET":
        extra = {"audiences": audiences} if audiences else {}
        if not job.get("running"):
            extra["previews"] = {
                "invite": _broadcast_template_preview("invite"),
                "unused": _broadcast_template_preview("unused"),
            }
        return web.json_response({"ok": True, **job, **extra})
    if job.get("running"):
        return web.json_response({"ok": False, "error": "Рассылка уже идёт", **job}, status=409)
    body = await request.json()
    template = str(body.get("template") or "").strip()
    if template not in {"", "invite", "unused"}:
        return web.json_response({"ok": False, "error": "Неизвестный шаблон"}, status=400)
    text = str(body.get("text") or "").strip()
    if template in {"invite", "unused"}:
        text = _broadcast_template_preview(template)
        audience = "using" if template == "invite" else "unused"
        ids = await db.list_broadcast_ids(audience)
        if not ids:
            return web.json_response({"ok": False, "error": "Нет получателей для этого шаблона"}, status=400)
        started = _start_broadcast_job(request.app, text, ids, template)
        return web.json_response({"ok": True, **started, "audiences": audiences})
    if not text:
        return web.json_response({"ok": False, "error": "Пустой текст"}, status=400)
    if len(text) > 3500:
        return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
    audience = str(body.get("audience") or "all").strip() or "all"
    if audience not in {"all", "using", "unused"}:
        return web.json_response({"ok": False, "error": "Неизвестная аудитория"}, status=400)
    ids = None if audience == "all" else await db.list_broadcast_ids(audience)
    if ids is not None and not ids:
        return web.json_response({"ok": False, "error": "Нет получателей"}, status=400)
    started = _start_broadcast_job(request.app, text, ids, None)
    return web.json_response({"ok": True, **started, "audiences": audiences})


def _clip_field(value: object, *, max_len: int, label: str) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        raise ValueError(f"{label}: до {max_len} символов")
    return text


def _clean_announcement(body: dict) -> dict:
    kicker = _clip_field((body or {}).get("kicker"), max_len=80, label="Надзаголовок")
    title = _clip_field((body or {}).get("title"), max_len=80, label="Заголовок")
    if len(title) < 2:
        raise ValueError("Заголовок: от 2 до 80 символов")
    lead = _clip_field((body or {}).get("lead"), max_len=800, label="Вступление")
    closing = _clip_field((body or {}).get("closing"), max_len=400, label="Завершение")
    raw = (body or {}).get("items")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = []
    if not isinstance(raw, list):
        raw = []
    items: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if not text:
            continue
        if len(text) > 160:
            raise ValueError("Пункт слишком длинный: до 160 символов")
        items.append(text)
        if len(items) >= 12:
            break
    if not items and not lead:
        raise ValueError("Добавьте вступление или хотя бы один пункт")
    return {
        "kicker": kicker,
        "title": title,
        "lead": lead,
        "closing": closing,
        "items": items,
    }


async def _read_announcement_payload(request: web.Request) -> tuple[dict, bytes, str]:
    ctype = request.content_type or ""
    photo = b""
    filename = "photo.jpg"
    if ctype.startswith("multipart/"):
        payload: dict = {}
        reader = await request.multipart()
        while True:
            field = await reader.next()
            if field is None:
                break
            name = field.name or ""
            if name == "file":
                filename = field.filename or "photo.jpg"
                photo = await field.read()
            elif name:
                payload[name] = await field.text()
        return payload, photo, filename
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}, b"", filename


async def api_announcements(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    if request.method == "GET":
        items = await db.list_update_announcements(30)
        counts = await db.broadcast_audience_counts()
        job = _bc_job(request.app)
        return web.json_response(
            {
                "ok": True,
                "items": items,
                "recipients": int(counts.get("all") or 0),
                "defaults": {
                    "kicker": DEFAULT_KICKER,
                    "title": DEFAULT_TITLE,
                    "lead": DEFAULT_LEAD,
                    "closing": DEFAULT_CLOSING,
                },
                "broadcast": {
                    "running": bool(job.get("running")),
                    "sent": int(job.get("sent") or 0),
                    "failed": int(job.get("failed") or 0),
                    "total": int(job.get("total") or 0),
                    "message": str(job.get("message") or ""),
                    "template": str(job.get("template") or ""),
                },
            }
        )
    job = _bc_job(request.app)
    if job.get("running"):
        return web.json_response({"ok": False, "error": "Рассылка уже идёт", **job}, status=409)
    payload, photo, filename = await _read_announcement_payload(request)
    try:
        cleaned = _clean_announcement(payload)
        if photo:
            validate_announcement_photo(photo, filename)
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    text = format_announcement_body(
        kicker=cleaned["kicker"],
        title=cleaned["title"],
        lead=cleaned["lead"],
        items=cleaned["items"],
        closing=cleaned["closing"],
    )
    if len(text) > 3500:
        return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
    ids = await db.list_broadcast_ids("all")
    if not ids:
        return web.json_response({"ok": False, "error": "Нет получателей"}, status=400)
    saved = await db.create_update_announcement(
        cleaned["title"],
        cleaned["items"],
        text,
        kicker=cleaned["kicker"],
        lead=cleaned["lead"],
        closing=cleaned["closing"],
    )
    image_name = ""
    if photo and saved.get("id"):
        try:
            image_name = save_announcement_photo(int(saved["id"]), photo, filename)
            saved = await db.set_announcement_image(int(saved["id"]), image_name) or saved
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
    started = _start_broadcast_job(
        request.app,
        text,
        None,
        "update",
        image_name=image_name or None,
    )
    return web.json_response({"ok": True, "announcement": saved, **started})


async def api_announcement_image(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    try:
        ann = await db.get_update_announcement(int(request.match_info["ann_id"]))
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "Анонс не найден"}, status=404)
    path = announcement_photo_path((ann or {}).get("image_name"))
    if not path:
        return web.json_response({"ok": False, "error": "Картинка не загружена"}, status=404)
    return web.FileResponse(
        path,
        headers={"Content-Type": content_type_for(path), "Cache-Control": "no-store"},
    )


async def api_settings(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    if request.method == "GET":
        from app.live import get_live_chat_hint

        data = shop_snapshot()
        data["live_chat_hint"] = await get_live_chat_hint()
        return web.json_response(data)
    try:
        body = await request.json()
        data = await save_shop_overlay(body)
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    except Exception:
        logger.exception("Не удалось сохранить настройки")
        return web.json_response({"ok": False, "error": "Не удалось сохранить"}, status=500)
    from app.live import get_live_chat_hint

    data["live_chat_hint"] = await get_live_chat_hint()
    return web.json_response(data)


async def api_flags(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    if request.method == "GET":
        flags = await db.get_flags()
        return web.json_response({"ok": True, **flags, "maintenance_has_photo": has_photo()})
    body = await request.json()
    if "maintenance" in body:
        turning_on = bool(body.get("maintenance"))
        was_on = await db.flag_on("maintenance")
        if turning_on and not was_on:
            text = str(body.get("message") or "").strip()
            if not text:
                text = (await db.get_kv("maintenance_notice")).strip()
            if not text:
                return web.json_response(
                    {"ok": False, "error": "Сохраните текст оповещения"},
                    status=400,
                )
            if len(text) > 3500:
                return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
            await db.set_kv("maintenance_notice", text)
            await db.set_flag("maintenance", True)
            flags = await db.get_flags()
            return web.json_response({"ok": True, **flags, "maintenance_has_photo": has_photo()})
        await db.set_flag("maintenance", turning_on)
    if "billing_paused" in body:
        await db.set_flag("billing_paused", bool(body.get("billing_paused")))
    if "trial_nudge" in body:
        await db.set_flag("trial_nudge", bool(body.get("trial_nudge")))
    if "invite_nudge" in body:
        await db.set_flag("invite_nudge", bool(body.get("invite_nudge")))
    if "info_nudge" in body:
        await db.set_flag("info_nudge", bool(body.get("info_nudge")))
    if "story_nudge" in body:
        await db.set_flag("story_nudge", bool(body.get("story_nudge")))
    flags = await db.get_flags()
    return web.json_response({"ok": True, **flags, "maintenance_has_photo": has_photo()})


async def api_backups(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    wait = seconds_until_msk_0001()
    return web.json_response(
        {
            "ok": True,
            "items": list_backups(),
            "next_in_sec": int(wait),
            "keep_days": get_settings().backup_keep_days,
        }
    )


async def api_backup_create(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    try:
        result = await create_backup(reason="админка")
    except Exception as exc:
        logger.exception("Ручной бэкап не удался")
        return web.json_response({"ok": False, "error": str(exc)[:300]}, status=500)
    return web.json_response(result)


async def api_backup_file(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    path = backup_path(str(request.match_info["name"]))
    if not path:
        return web.json_response({"ok": False, "error": "Файл не найден"}, status=404)
    return web.FileResponse(
        path,
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


async def api_backup_restore(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    filename = "dump.sql"
    data = b""
    ctype = request.content_type or ""
    try:
        if ctype.startswith("multipart/"):
            reader = await request.multipart()
            while True:
                field = await reader.next()
                if field is None:
                    break
                if field.name != "file":
                    continue
                filename = field.filename or "dump.sql"
                data = await field.read()
                break
        else:
            body = await request.json()
            source = backup_path(str(body.get("name") or ""))
            if not source:
                return web.json_response({"ok": False, "error": "Файл бэкапа не найден"}, status=404)
            filename = source.name
            data = source.read_bytes()
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    if not data:
        return web.json_response({"ok": False, "error": "Прикрепите файл .sql или .sql.gz"}, status=400)
    if len(data) > MAX_UPLOAD:
        return web.json_response({"ok": False, "error": "Файл больше 80 МБ"}, status=400)
    try:
        result = await restore_backup(data, filename)
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    except Exception as exc:
        logger.exception("Импорт бэкапа не удался")
        return web.json_response({"ok": False, "error": str(exc)[:800]}, status=500)
    return web.json_response(result)


async def api_maintenance_save(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    ctype = request.content_type or ""
    text = ""
    photo = b""
    filename = "photo.jpg"
    if ctype.startswith("multipart/"):
        reader = await request.multipart()
        while True:
            field = await reader.next()
            if field is None:
                break
            if field.name == "message":
                text = (await field.text()).strip()
            elif field.name == "file":
                filename = field.filename or "photo.jpg"
                photo = await field.read()
    else:
        body = await request.json()
        text = str(body.get("message") or "").strip()
    if not text:
        return web.json_response({"ok": False, "error": "Введите текст оповещения"}, status=400)
    if len(text) > 3500:
        return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
    await db.set_kv("maintenance_notice", text)
    if photo:
        try:
            await save_photo(photo, filename)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
    flags = await db.get_flags()
    return web.json_response({"ok": True, **flags, "maintenance_has_photo": has_photo()})


async def api_maintenance_photo(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    if request.method == "DELETE":
        await clear_photo()
        return web.json_response({"ok": True, "maintenance_has_photo": False})
    path = photo_path()
    if not path:
        return web.json_response({"ok": False, "error": "Картинка не загружена"}, status=404)
    ctype = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "application/octet-stream")
    return web.FileResponse(path, headers={"Content-Type": ctype, "Cache-Control": "no-store"})


SUB_CHUNK = 100


def _new_sub_job() -> dict:
    return {
        "running": False,
        "apply_squads": False,
        "revoke": False,
        "total": 0,
        "done": 0,
        "failed": 0,
        "error": None,
        "notified": 0,
        "message": "",
    }


def _sub_job(app: web.Application) -> dict:
    job = app.get("sub_replace_job")
    if not isinstance(job, dict):
        job = _new_sub_job()
        app["sub_replace_job"] = job
    return job


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def _panel_user_for_account(rw: RemnawaveClient, account: dict) -> dict | None:
    user = None
    if account.get("remnawave_id") is not None:
        user = await rw.get_user_by_id(int(account["remnawave_id"]))
    if not user and account.get("remnawave_uuid"):
        user = await rw.get_user_by_id(str(account["remnawave_uuid"]))
    return user


async def _persist_subscription(telegram_id: int, panel: dict, account: dict) -> tuple[str, str]:
    url = str(panel.get("subscriptionUrl") or "")
    title = str(account.get("title") or "")
    panel_id = panel.get("id")
    local = await db.get_user(telegram_id)
    if local and panel_id is not None and local.get("remnawave_id") is not None:
        if int(local["remnawave_id"]) == int(panel_id):
            await db.save_panel_snapshot(telegram_id, panel)
    elif local and not get_settings().balance_enabled:
        await db.save_panel_snapshot(telegram_id, panel)
    if panel_id is not None:
        device_title = await db.save_device_subscription(int(panel_id), panel)
        if device_title:
            title = device_title
    return title, url


async def _replace_one(
    rw: RemnawaveClient,
    account: dict,
    apply_squads: bool,
    revoke: bool,
    squads: list[str],
) -> tuple[str, str]:
    user = await _panel_user_for_account(rw, account)
    if not user:
        raise RemnawaveError("Учётка в панели не найдена")
    if apply_squads and squads:
        await rw.update_user(user, {"activeInternalSquads": squads})
    if revoke:
        user = await rw.revoke_subscription(user)
    return await _persist_subscription(int(account["telegram_id"]), user, account)


async def _notify_reissued(bot: Bot, by_user: dict[int, list[tuple[str, str]]]) -> int:
    sent = 0
    for telegram_id, links in by_user.items():
        if await db.user_is_blocked(telegram_id):
            continue
        seen: set[str] = set()
        unique: list[tuple[str, str]] = []
        for title, url in links:
            key = url or title
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append((title, url))
        try:
            await bot.send_message(
                telegram_id,
                subscription_reissued_text(unique),
                reply_markup=cabinet_keyboard(),
            )
            sent += 1
        except Exception:
            logger.debug("Не удалось написать о перевыпуске %s", telegram_id, exc_info=True)
        await asyncio.sleep(0.035)
    return sent


async def _sync_links_from_panel(
    rw: RemnawaveClient, accounts: list[dict]
) -> dict[int, list[tuple[str, str]]]:
    by_user: dict[int, list[tuple[str, str]]] = {}
    for account in accounts:
        telegram_id = int(account["telegram_id"])
        try:
            user = await _panel_user_for_account(rw, account)
            if not user:
                continue
            title, url = await _persist_subscription(telegram_id, user, account)
            by_user.setdefault(telegram_id, []).append((title, url))
        except Exception:
            logger.exception("Не удалось обновить ссылку в ЛК для %s", account)
    return by_user


async def _reissue_user_subscriptions(rw: RemnawaveClient, telegram_id: int) -> list[tuple[str, str]]:
    ids = await db.list_panel_ids_for_user(telegram_id)
    if not ids:
        raise RemnawaveError("Нет подписки в панели")
    links: list[tuple[str, str]] = []
    for panel_id in ids:
        panel = await rw.get_user_by_id(panel_id)
        if not panel:
            continue
        panel = await rw.revoke_subscription(panel)
        title, url = await _persist_subscription(
            telegram_id, panel, {"title": "", "remnawave_id": panel_id}
        )
        links.append((title, url))
    if not links:
        raise RemnawaveError("Учётка в панели не найдена")
    return links


async def _try_bulk_ids(
    rw: RemnawaveClient,
    ids: list[int],
    apply_squads: bool,
    revoke: bool,
    squads: list[str],
) -> bool:
    if not ids:
        return True
    try:
        if apply_squads:
            for chunk in _chunks(ids, SUB_CHUNK):
                await rw.bulk_update_squads(chunk, squads)
        if revoke:
            for chunk in _chunks(ids, SUB_CHUNK):
                await rw.bulk_revoke_subscription(chunk)
        return True
    except RemnawaveError:
        logger.exception("Массовая замена подписок через bulk API не удалась, иду по одной")
        return False


async def _run_replace_job(app: web.Application, apply_squads: bool, revoke: bool) -> None:
    job = _sub_job(app)
    rw: RemnawaveClient = app["rw"]
    squads = get_settings().squad_uuids
    try:
        job["message"] = "Жду очередь панели"
        async with runtime.panel_cron_lock():
            job["message"] = "Идёт замена"
            accounts = await db.list_panel_accounts()
            job["total"] = len(accounts)
            if not accounts:
                job["message"] = "Нет учёток в панели"
                return
            ids = [int(a["remnawave_id"]) for a in accounts if a.get("remnawave_id") is not None]
            uuid_only = [a for a in accounts if a.get("remnawave_id") is None]
            bulk_ok = await _try_bulk_ids(rw, ids, apply_squads, revoke, squads)
            if bulk_ok:
                job["done"] = len(ids)
                rest = uuid_only
            else:
                rest = accounts
                job["done"] = 0
            by_user: dict[int, list[tuple[str, str]]] = {}
            for account in rest:
                try:
                    title, url = await _replace_one(rw, account, apply_squads, revoke, squads)
                    job["done"] += 1
                    if revoke:
                        by_user.setdefault(int(account["telegram_id"]), []).append((title, url))
                except Exception:
                    job["failed"] += 1
                    logger.exception("Не удалось заменить подписку для %s", account)
            if revoke:
                if bulk_ok:
                    synced = await _sync_links_from_panel(rw, [a for a in accounts if a.get("remnawave_id") is not None])
                    for telegram_id, links in synced.items():
                        by_user.setdefault(telegram_id, []).extend(links)
                bot: Bot = app["bot"]
                job["notified"] = await _notify_reissued(bot, by_user)
            parts = [f"Готово: {job['done']} из {job['total']}"]
            if job["failed"]:
                parts.append(f"ошибок {job['failed']}")
            if revoke:
                parts.append(f"уведомлений {job['notified']}")
            job["message"] = ", ".join(parts)
    except Exception as exc:
        logger.exception("Сбой массовой замены подписок")
        job["error"] = str(exc)
        job["message"] = f"Сбой: {exc}"
    finally:
        job["running"] = False


async def api_replace_subscriptions(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    job = _sub_job(request.app)
    if request.method == "GET":
        return web.json_response({"ok": True, **job})
    if job.get("running"):
        return web.json_response({"ok": False, "error": "Уже выполняется", **job}, status=409)
    body = await request.json()
    apply_squads = bool(body.get("apply_squads"))
    revoke = bool(body.get("revoke"))
    if not apply_squads and not revoke:
        return web.json_response(
            {"ok": False, "error": "Включите сквады и/или перевыпуск ссылок"},
            status=400,
        )
    if apply_squads and not get_settings().squad_uuids:
        return web.json_response(
            {"ok": False, "error": "В .env пустой REMNAWAVE_SQUAD_UUIDS"},
            status=400,
        )
    job.update(_new_sub_job())
    job["running"] = True
    job["apply_squads"] = apply_squads
    job["revoke"] = revoke
    job["message"] = "Запущено"
    asyncio.create_task(_run_replace_job(request.app, apply_squads, revoke))
    return web.json_response({"ok": True, **job})


def mount_admin(app: web.Application) -> None:
    app.router.add_get("/admin", admin_redirect)
    app.router.add_get("/admin/", admin_index)
    app.router.add_get("/admin/stats", admin_index)
    app.router.add_get("/admin/promo", admin_index)
    app.router.add_get("/admin/app.css", lambda _r: web.FileResponse(ADMIN_DIR / "app.css", headers=_NO_STORE))
    app.router.add_get("/admin/app.js", lambda _r: web.FileResponse(ADMIN_DIR / "app.js", headers=_NO_STORE))
    app.router.add_get("/admin/api/build", api_admin_build)
    app.router.add_post("/admin/api/login", api_login)
    app.router.add_post("/admin/api/logout", api_logout)
    app.router.add_get("/admin/api/session", api_session)
    app.router.add_get("/admin/api/stats", api_stats)
    app.router.add_get("/admin/api/users", api_users)
    app.router.add_get("/admin/api/users/{telegram_id}/devices", api_user_devices)
    app.router.add_post("/admin/api/users/bulk", api_users_bulk)
    app.router.add_get("/admin/api/referrals", api_referrals)
    app.router.add_get("/admin/api/ads", api_ad_links)
    app.router.add_post("/admin/api/ads", api_ad_links)
    app.router.add_post("/admin/api/ads/{link_id}/archive", api_ad_link_archive)
    app.router.add_get("/admin/api/payouts", api_payouts)
    app.router.add_post("/admin/api/payouts/{payout_id}", api_payout_resolve)
    app.router.add_get("/admin/api/orders", api_orders)
    app.router.add_get("/admin/api/messages", api_messages)
    app.router.add_post("/admin/api/messages/retry-failed", api_messages_retry_failed)
    app.router.add_post("/admin/api/messages/{msg_id}/retry", api_message_retry)
    app.router.add_get("/admin/api/tickets", api_tickets)
    app.router.add_get("/admin/api/tickets/files/{att_id}", api_ticket_file)
    app.router.add_get("/admin/api/tickets/{ticket_id}", api_ticket_one)
    app.router.add_post("/admin/api/tickets/{ticket_id}", api_ticket_act)
    app.router.add_get("/admin/api/billing", api_billing)
    app.router.add_get("/admin/api/settings", api_settings)
    app.router.add_post("/admin/api/settings", api_settings)
    app.router.add_post("/admin/api/users/purge-bot-blockers", api_purge_bot_blockers)
    app.router.add_post("/admin/api/users/{telegram_id}/grant", api_grant)
    app.router.add_post("/admin/api/users/{telegram_id}/balance", api_balance)
    app.router.add_post("/admin/api/users/{telegram_id}/trial-reset", api_trial_reset)
    app.router.add_post("/admin/api/users/{telegram_id}/message", api_message)
    app.router.add_post("/admin/api/users/{telegram_id}/cabinet-link", api_cabinet_link)
    app.router.add_post("/admin/api/users/{telegram_id}/delete", api_delete_user)
    app.router.add_post("/admin/api/users/{telegram_id}/block", api_block_user)
    app.router.add_get("/admin/api/flags", api_flags)
    app.router.add_post("/admin/api/flags", api_flags)
    app.router.add_get("/admin/api/subscriptions/replace", api_replace_subscriptions)
    app.router.add_post("/admin/api/subscriptions/replace", api_replace_subscriptions)
    app.router.add_post("/admin/api/maintenance", api_maintenance_save)
    app.router.add_get("/admin/api/maintenance/photo", api_maintenance_photo)
    app.router.add_delete("/admin/api/maintenance/photo", api_maintenance_photo)
    app.router.add_get("/admin/api/broadcast", api_broadcast)
    app.router.add_post("/admin/api/broadcast", api_broadcast)
    app.router.add_get("/admin/api/announcements", api_announcements)
    app.router.add_post("/admin/api/announcements", api_announcements)
    app.router.add_get("/admin/api/announcements/{ann_id}/image", api_announcement_image)
    app.router.add_get("/admin/api/backups", api_backups)
    app.router.add_post("/admin/api/backups", api_backup_create)
    app.router.add_post("/admin/api/backups/restore", api_backup_restore)
    app.router.add_get("/admin/api/backups/{name}", api_backup_file)
    app.router.add_static("/admin/static", ADMIN_DIR)
