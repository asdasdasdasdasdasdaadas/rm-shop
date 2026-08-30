from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time

from aiohttp import web
from aiogram import Bot

from app import db
from app.block import BLOCKED_NOTICE
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
from app.keyboards import blocked_keyboard, cabinet_keyboard
from app.maintenance import clear_photo, has_photo, photo_path, save_photo
from app.remnawave import RemnawaveClient, RemnawaveError
from app.texts import subscription_reissued_text

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


async def api_referrals(request: web.Request) -> web.Response:
    denied = _need_auth(request)
    if denied:
        return denied
    q = str(request.query.get("q") or "")
    page = max(1, int(request.query.get("page") or 1))
    limit = min(100, max(1, int(request.query.get("limit") or 30)))
    items, total = await db.admin_list_referrals(q, limit, (page - 1) * limit)
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
            await bot.send_message(telegram_id, BLOCKED_NOTICE, reply_markup=blocked_keyboard())
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
    if action not in {"delete", "trial_reset", "message", "block", "unblock", "reissue"}:
        return web.json_response({"ok": False, "error": "Неизвестное действие"}, status=400)
    ids: list[int] = []
    if body.get("all_matching"):
        q = str(body.get("q") or "")
        ids, total = await db.admin_user_ids(q, BULK_MAX + 1)
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
            else:
                await bot.send_message(telegram_id, text)
                ok_n += 1
                await asyncio.sleep(0.035)
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
    if request.method == "GET":
        return web.json_response(shop_snapshot())
    try:
        body = await request.json()
        data = await save_shop_overlay(body)
    except ValueError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)
    except Exception:
        logger.exception("Не удалось сохранить настройки")
        return web.json_response({"ok": False, "error": "Не удалось сохранить"}, status=500)
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
    app.router.add_get("/admin/app.css", lambda _r: web.FileResponse(ADMIN_DIR / "app.css"))
    app.router.add_get("/admin/app.js", lambda _r: web.FileResponse(ADMIN_DIR / "app.js"))
    app.router.add_post("/admin/api/login", api_login)
    app.router.add_post("/admin/api/logout", api_logout)
    app.router.add_get("/admin/api/session", api_session)
    app.router.add_get("/admin/api/stats", api_stats)
    app.router.add_get("/admin/api/users", api_users)
    app.router.add_post("/admin/api/users/bulk", api_users_bulk)
    app.router.add_get("/admin/api/referrals", api_referrals)
    app.router.add_get("/admin/api/orders", api_orders)
    app.router.add_get("/admin/api/reports", api_reports)
    app.router.add_get("/admin/api/settings", api_settings)
    app.router.add_post("/admin/api/settings", api_settings)
    app.router.add_post("/admin/api/users/{telegram_id}/grant", api_grant)
    app.router.add_post("/admin/api/users/{telegram_id}/balance", api_balance)
    app.router.add_post("/admin/api/users/{telegram_id}/trial-reset", api_trial_reset)
    app.router.add_post("/admin/api/users/{telegram_id}/message", api_message)
    app.router.add_post("/admin/api/users/{telegram_id}/delete", api_delete_user)
    app.router.add_post("/admin/api/users/{telegram_id}/block", api_block_user)
    app.router.add_get("/admin/api/flags", api_flags)
    app.router.add_post("/admin/api/flags", api_flags)
    app.router.add_get("/admin/api/subscriptions/replace", api_replace_subscriptions)
    app.router.add_post("/admin/api/subscriptions/replace", api_replace_subscriptions)
    app.router.add_post("/admin/api/maintenance", api_maintenance_save)
    app.router.add_get("/admin/api/maintenance/photo", api_maintenance_photo)
    app.router.add_delete("/admin/api/maintenance/photo", api_maintenance_photo)
    app.router.add_post("/admin/api/broadcast", api_broadcast)
    app.router.add_get("/admin/api/backups", api_backups)
    app.router.add_post("/admin/api/backups", api_backup_create)
    app.router.add_post("/admin/api/backups/restore", api_backup_restore)
    app.router.add_get("/admin/api/backups/{name}", api_backup_file)
    app.router.add_static("/admin/static", ADMIN_DIR)
