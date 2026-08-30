from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time

from aiohttp import web
from aiogram import Bot

from app import db
from app.backup import backup_path, create_backup, list_backups, seconds_until_msk_0001
from app.config import ROOT, get_settings
from app.remnawave import RemnawaveClient, RemnawaveError

logger = logging.getLogger("rm-shop.admin")
ADMIN_DIR = ROOT / "admin"
COOKIE = "rm_admin"
COOKIE_TTL = 7 * 24 * 3600


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
    return web.FileResponse(ADMIN_DIR / "index.html")


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
    revenue = 0.0
    for code, count in (raw.get("plans") or {}).items():
        plan = settings.shop_plans.get(code) or settings.plans.get(code)
        if plan:
            revenue += float(plan["rub"]) * int(count)
    return web.json_response({"ok": True, **raw, "revenue_rub": round(revenue, 2)})


async def api_users(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_users(q, limit, (page - 1) * limit)
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


async def api_orders(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_orders(q, limit, (page - 1) * limit)
    return web.json_response({"ok": True, "items": items, "total": total, "page": page, "limit": limit})


async def api_reports(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_reports(limit, (page - 1) * limit)
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
        return web.json_response({"ok": True, "balance_rub": total})
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
    return web.json_response({"ok": True, "balance_rub": total})


async def api_delete_user(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    telegram_id = int(request.match_info["telegram_id"])
    local = await db.get_user(telegram_id)
    if not local:
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    rw: RemnawaveClient = request.app["rw"]
    panel_ids = []
    if local.get("remnawave_id"):
        panel_ids.append(int(local["remnawave_id"]))
    for item in await db.list_devices(telegram_id):
        if item.get("remnawave_id"):
            panel_ids.append(int(item["remnawave_id"]))
    for panel_id in dict.fromkeys(panel_ids):
        try:
            await rw.disable_panel_user(panel_id)
        except RemnawaveError:
            logger.exception("Не удалось отключить панель %s при удалении %s", panel_id, telegram_id)
    if not await db.delete_user(telegram_id):
        return web.json_response({"ok": False, "error": "Пользователь не найден"}, status=404)
    return web.json_response({"ok": True})


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
        return web.json_response({"ok": False, "error": str(exc)}, status=502)
    return web.json_response({"ok": True})


async def _broadcast_all(bot: Bot, text: str) -> tuple[int, int]:
    sent = 0
    failed = 0
    for telegram_id in await db.list_broadcast_ids():
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.035)
    return sent, failed


async def api_broadcast(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    body = await request.json()
    text = str(body.get("text") or "").strip()
    if not text:
        return web.json_response({"ok": False, "error": "Пустой текст"}, status=400)
    if len(text) > 3500:
        return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
    bot: Bot = request.app["bot"]
    sent, failed = await _broadcast_all(bot, text)
    return web.json_response({"ok": True, "sent": sent, "failed": failed})


async def api_settings(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    settings = get_settings()
    flags = await db.get_flags()
    return web.json_response(
        {
            "ok": True,
            "brand_name": settings.brand_name,
            "bot_username": settings.bot_username,
            "trial_enabled": settings.trial_enabled,
            "trial_days": settings.trial_days,
            "balance_enabled": settings.balance_enabled,
            "promo_enabled": settings.promo_enabled,
            "promo_codes": settings.promo_codes,
            "rollypay_configured": settings.rollypay_configured,
            "rollypay_test": settings.rollypay_test,
            "webapp_enabled": settings.webapp_enabled,
            "vpn_day_price_rub": settings.vpn_day_price_rub,
            "referral_reward_rub": settings.referral_reward_rub,
            "maintenance": flags["maintenance"],
            "billing_paused": flags["billing_paused"],
            "maintenance_notice": flags.get("maintenance_notice") or "",
            "plans": [
                {"code": code, "title": p["title"], "days": p["days"], "rub": p["rub_str"]}
                for code, p in settings.shop_plans.items()
            ],
        }
    )


async def api_flags(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    if request.method == "GET":
        flags = await db.get_flags()
        return web.json_response({"ok": True, **flags})
    body = await request.json()
    if "maintenance" in body:
        turning_on = bool(body.get("maintenance"))
        was_on = await db.flag_on("maintenance")
        if turning_on and not was_on:
            text = str(body.get("message") or "").strip()
            if not text:
                return web.json_response(
                    {"ok": False, "error": "Укажите текст оповещения для всех пользователей"},
                    status=400,
                )
            if len(text) > 3500:
                return web.json_response({"ok": False, "error": "Текст слишком длинный"}, status=400)
            await db.set_kv("maintenance_notice", text)
            await db.set_flag("maintenance", True)
            bot: Bot = request.app["bot"]
            sent, failed = await _broadcast_all(bot, text)
            flags = await db.get_flags()
            return web.json_response({"ok": True, **flags, "sent": sent, "failed": failed})
        await db.set_flag("maintenance", turning_on)
    if "billing_paused" in body:
        await db.set_flag("billing_paused", bool(body.get("billing_paused")))
    flags = await db.get_flags()
    return web.json_response({"ok": True, **flags})


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
            "admins": len(get_settings().admin_id_set),
        }
    )


async def api_backup_create(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    try:
        result = await create_backup(reason="админка", bot=request.app["bot"])
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


def mount_admin(app: web.Application) -> None:
    app.router.add_get("/admin", admin_redirect)
    app.router.add_get("/admin/", admin_index)
    app.router.add_get("/admin/app.css", lambda _r: web.FileResponse(ADMIN_DIR / "app.css"))
    app.router.add_get("/admin/app.js", lambda _r: web.FileResponse(ADMIN_DIR / "app.js"))
    app.router.add_post("/admin/api/login", api_login)
    app.router.add_post("/admin/api/logout", api_logout)
    app.router.add_get("/admin/api/session", api_session)
    app.router.add_get("/admin/api/stats", api_stats)
    app.router.add_get("/admin/api/users", api_users)
    app.router.add_get("/admin/api/orders", api_orders)
    app.router.add_get("/admin/api/reports", api_reports)
    app.router.add_get("/admin/api/settings", api_settings)
    app.router.add_post("/admin/api/users/{telegram_id}/grant", api_grant)
    app.router.add_post("/admin/api/users/{telegram_id}/balance", api_balance)
    app.router.add_post("/admin/api/users/{telegram_id}/trial-reset", api_trial_reset)
    app.router.add_post("/admin/api/users/{telegram_id}/message", api_message)
    app.router.add_post("/admin/api/users/{telegram_id}/delete", api_delete_user)
    app.router.add_get("/admin/api/flags", api_flags)
    app.router.add_post("/admin/api/flags", api_flags)
    app.router.add_post("/admin/api/broadcast", api_broadcast)
    app.router.add_get("/admin/api/backups", api_backups)
    app.router.add_post("/admin/api/backups", api_backup_create)
    app.router.add_get("/admin/api/backups/{name}", api_backup_file)
    app.router.add_static("/admin/static", ADMIN_DIR)
