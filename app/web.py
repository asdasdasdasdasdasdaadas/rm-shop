from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

from aiohttp import web
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import LabeledPrice
from aiogram.utils.web_app import safe_parse_webapp_init_data

from app import db, runtime
from app.admin import mount_admin
from app.billing import fulfill_rollypay_order, subscription_issued_text
from app.config import ROOT, get_settings, referral_is_payout
from app.keyboards import back_profile_keyboard, connect_keyboard, support_url
from app.referrals import maybe_reward_referrer, referral_payout_public, trial_grant_days, trial_grant_rub, trial_is_available
from app.remnawave import (
    PANEL_LEASE_DAYS,
    RemnawaveClient,
    RemnawaveError,
    days_remaining,
    is_subscription_active,
    parse_dt,
    parse_expire,
    panel_lease_until,
    username_taken,
)
from app.rollypay import RollyPayClient, RollyPayError, payment_is_paid, verify_webhook
from app.sync import fetch_panel
from app.notices import notice_text
from app.texts import days_text, minutes_text, rub_text
from app.balance import sync_user_billing
from app.block import blocked_notice
from app.maintenance import current_text
from app.vpn_apps import public_vpn_apps
from app.story import notify_admins_story
from app.trust import take_trust, trust_info

logger = logging.getLogger("rm-shop.web")
WEBAPP_DIR = ROOT / "webapp"
_PHOTO_TTL = 600.0
_photo_cache: dict[int, tuple[float, str]] = {}


def _device_as_panel(item: dict) -> dict:
    expire = parse_dt(item.get("expire_at"))
    if expire is None:
        billed = parse_dt(item.get("last_billed_at"))
        if billed:
            expire = billed + timedelta(days=PANEL_LEASE_DAYS)
    return {
        "username": "",
        "subscriptionUrl": item.get("subscription_url") or "",
        "status": str(item.get("panel_status") or "") or "ACTIVE",
        "expireAt": expire.isoformat() if expire else None,
    }


async def _avatar_url(bot: Bot, telegram_id: int) -> str:
    now = time.monotonic()
    hit = _photo_cache.get(telegram_id)
    if hit and now - hit[0] < _PHOTO_TTL:
        return hit[1]
    photo = ""
    try:
        photos = await bot.get_user_profile_photos(telegram_id, limit=1)
        if photos.total_count and photos.photos:
            file_id = photos.photos[0][-1].file_id
            photo = f"/api/avatar?uid={telegram_id}&f={file_id}"
    except Exception:
        photo = ""
    _photo_cache[telegram_id] = (now, photo)
    return photo


def _story_check_state(local, settings) -> dict:
    minutes = int(settings.story_check_minutes or 0)
    pending_at = parse_dt((local or {}).get("story_pending_at"))
    rewarded = bool(local and local.get("story_rewarded_at"))
    until = None
    remain = 0
    if pending_at and not rewarded and minutes > 0:
        until = pending_at + timedelta(minutes=minutes)
        remain = max(0, int((until - datetime.now(timezone.utc)).total_seconds()))
    return {
        "story_rewarded": rewarded,
        "story_pending": bool(pending_at and not rewarded),
        "story_check_until": until.isoformat() if until else None,
        "story_check_seconds": remain,
        "story_check_minutes": minutes,
    }


def _init_data(request: web.Request) -> str:
    return request.headers.get("X-Init-Data") or request.query.get("initData") or ""


def _lk_token(request: web.Request) -> str:
    header = (request.headers.get("X-Lk-Token") or "").strip()
    if header:
        return header
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (request.query.get("t") or "").strip()


async def _resolve_telegram_id(request: web.Request):
    settings = get_settings()
    raw = _init_data(request)
    if raw:
        try:
            parsed = safe_parse_webapp_init_data(settings.bot_token, raw)
            if parsed.user:
                return int(parsed.user.id), parsed
        except ValueError:
            pass
    token = _lk_token(request)
    if token:
        uid = await db.get_cabinet_token_user(token)
        if uid:
            return uid, None
    return None, None


def json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"ok": False, "error": message}, status=status)


async def _if_down() -> web.Response | None:
    if await db.flag_on("maintenance"):
        return json_error(await current_text(), 503)
    return None


async def _if_blocked(telegram_id: int) -> web.Response | None:
    if await db.user_is_blocked(telegram_id):
        return json_error(blocked_notice(), 403)
    return None


async def _require_tg(request: web.Request) -> tuple[int | None, web.Response | None]:
    denied = await _if_down()
    if denied:
        return None, denied
    telegram_id, _parsed = await _resolve_telegram_id(request)
    if not telegram_id:
        return None, json_error("Ссылка недействительна или истекла", 401)
    denied = await _if_blocked(telegram_id)
    if denied:
        return None, denied
    return telegram_id, None


async def _require_miniapp(request: web.Request) -> tuple[int | None, web.Response | None]:
    denied = await _if_down()
    if denied:
        return None, denied
    settings = get_settings()
    raw = _init_data(request)
    if not raw:
        return None, json_error("Откройте кабинет из Telegram, чтобы выложить историю", 401)
    try:
        parsed = safe_parse_webapp_init_data(settings.bot_token, raw)
    except ValueError:
        return None, json_error("Ссылка недействительна или истекла", 401)
    if not parsed.user:
        return None, json_error("Ссылка недействительна или истекла", 401)
    telegram_id = int(parsed.user.id)
    denied = await _if_blocked(telegram_id)
    if denied:
        return None, denied
    return telegram_id, None


def _public_origin(request: web.Request) -> str:
    settings = get_settings()
    base = (settings.webapp_public_url or "").rstrip("/")
    if base:
        return base
    return str(request.url.origin).rstrip("/")


_NO_STORE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


async def index(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "index.html", headers=_NO_STORE)


async def webapp_css(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "app.css", headers=_NO_STORE)


async def webapp_js(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "app.js", headers=_NO_STORE)


async def webapp_qrcode(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "qrcode.min.js", headers=_NO_STORE)


async def webapp_open(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "open.html", headers=_NO_STORE)


def _story_image_path():
    for name in ("stories_img.jpg", "stories_img.jpeg", "stories_img.png", "story.png"):
        path = WEBAPP_DIR / name
        if path.is_file():
            return path
    return WEBAPP_DIR / "story.png"


def _story_media_type(path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


async def webapp_story(_request: web.Request) -> web.FileResponse:
    path = _story_image_path()
    return web.FileResponse(
        path,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Type": _story_media_type(path),
        },
    )


async def api_me(request: web.Request) -> web.Response:
    settings = get_settings()
    telegram_id, parsed = await _resolve_telegram_id(request)
    if not telegram_id:
        return json_error("Ссылка недействительна или истекла", 401)
    if await db.flag_on("maintenance"):
        return web.json_response(
            {
                "ok": True,
                "maintenance": True,
                "notice": await current_text(),
                "brand_name": settings.brand_name,
            }
        )
    if await db.user_is_blocked(telegram_id):
        return web.json_response(
            {
                "ok": True,
                "blocked": True,
                "notice": blocked_notice(),
                "brand_name": settings.brand_name,
            }
        )
    bot: Bot = request.app["bot"]
    rw: RemnawaveClient = request.app["rw"]
    tg_user = parsed.user if parsed else None
    if tg_user:
        await db.upsert_user(telegram_id, tg_user.username, tg_user.first_name)
    local = await db.get_user(telegram_id)
    panel = await fetch_panel(rw, telegram_id, local=local)

    days = int(local["balance_days"] or 0) if settings.balance_enabled and local else days_remaining(panel)
    balance_rub = int((local or {}).get("balance_rub") or 0) if local else 0
    sub_url = (panel or {}).get("subscriptionUrl") or ""
    devices = []
    if settings.balance_enabled:
        raw_devices = await db.list_devices(telegram_id)
        for item in raw_devices:
            panel_dev = _device_as_panel(item)
            expire = parse_expire(panel_dev.get("expireAt"))
            devices.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "username": panel_dev.get("username") or "",
                    "subscription_url": panel_dev.get("subscriptionUrl") or "",
                    "days": days_remaining(panel_dev),
                    "active": is_subscription_active(panel_dev),
                    "expire_at": expire.isoformat() if expire else None,
                    "platform": item.get("platform") or "",
                    "client": item.get("client") or "",
                }
            )

    photo = await _avatar_url(bot, telegram_id)

    name = " ".join(x for x in [tg_user.first_name, tg_user.last_name] if x) if tg_user else ""
    username = f"@{tg_user.username}" if tg_user and tg_user.username else ""
    if not username and local and local.get("username"):
        nick = str(local["username"])
        username = nick if nick.startswith("@") else f"@{nick}"
    trust = await trust_info(telegram_id, local, len(devices)) if settings.balance_enabled else None
    if settings.balance_enabled and devices:
        days_left = balance_rub // (max(1, settings.vpn_day_price_rub) * len(devices))
    elif settings.balance_enabled:
        days_left = balance_rub // max(1, settings.vpn_day_price_rub)
    else:
        days_left = days
    days_left = max(0, int(days_left))
    wallet = await db.referral_wallet(telegram_id) if settings.balance_enabled else None

    return web.json_response(
        {
            "ok": True,
            "maintenance": False,
            "user": {
                "name": name or (local or {}).get("first_name") or "Пользователь",
                "username": username,
                "photo": photo,
            },
            "brand_name": settings.brand_name,
            "balance_enabled": settings.balance_enabled,
            "promo_enabled": settings.promo_enabled,
            "trial_available": trial_is_available(local),
            "trial_days": trial_grant_days(local) if not settings.balance_enabled else settings.trial_days,
            "trial_rub": trial_grant_rub() if settings.balance_enabled else 0,
            "days": days,
            "days_left": days_left,
            "billing_active": bool(settings.balance_enabled and devices),
            "balance_rub": balance_rub,
            "vpn_day_price_rub": settings.vpn_day_price_rub,
            "max_devices": settings.max_devices,
            "has_access": bool(
                (settings.balance_enabled and (balance_rub > 0 or devices))
                or days > 0
                or is_subscription_active(panel)
                or devices
            ),
            "subscription_url": sub_url if not settings.balance_enabled else "",
            "invite_url": f"https://t.me/{settings.bot_username}?start=ref_{telegram_id}",
            "referral_reward_days": settings.referral_reward_days,
            "referral_invitee_days": settings.referral_invitee_days,
            "referral_reward_rub": settings.referral_reward_rub,
            **referral_payout_public(wallet),
            "story_reward_enabled": bool(
                settings.balance_enabled
                and settings.story_reward_enabled
                and settings.story_reward_rub > 0
            ),
            "story_reward_rub": settings.story_reward_rub if settings.balance_enabled else 0,
            **_story_check_state(local, settings),
            "story_media_url": (
                f"{_public_origin(request)}"
                f"{'/story.jpg' if _story_media_type(_story_image_path()) == 'image/jpeg' else '/story.png'}"
                f"?v=stories4"
            ),
            "story_share_text": (
                settings.story_share_text.strip()
                or "VPN без границ. Подключайся в боте."
            ),
            "story_bot_url": f"https://t.me/{settings.bot_username}",
            "legal": {
                "offer": settings.legal_offer_url,
                "privacy": settings.legal_privacy_url,
                "support": support_url(),
            },
            "plans": [
                {
                    "code": code,
                    "title": p["title"],
                    "days": p["days"],
                    "stars": p["stars"],
                    "rub": p["rub_str"],
                    "topup_rub": int(p.get("topup_rub") or 0),
                }
                for code, p in settings.shop_plans.items()
            ],
            "topup_min": settings.balance_topup_min if settings.balance_enabled else 0,
            "topup_max": settings.balance_topup_max if settings.balance_enabled else 0,
            "topup_step": settings.balance_topup_step if settings.balance_enabled else 0,
            "devices": devices,
            "trust": trust,
            "vpn_apps": public_vpn_apps(),
        }
    )


async def api_avatar(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    file_id = request.query.get("f")
    if not file_id:
        raise web.HTTPNotFound()
    try:
        tg_file = await bot.get_file(file_id)
        buf = BytesIO()
        await bot.download(tg_file, destination=buf)
        data = buf.getvalue()
    except Exception:
        raise web.HTTPNotFound()
    return web.Response(body=data, content_type="image/jpeg")


async def api_trial(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    settings = get_settings()
    local = await db.get_user(telegram_id)
    if local and local["trial_used"]:
        return json_error("Вы уже пробовали бесплатно")
    if not trial_is_available(local):
        return json_error("Сейчас нельзя попробовать бесплатно")
    rw: RemnawaveClient = request.app["rw"]
    try:
        if settings.balance_enabled:
            await db.add_balance_rub(telegram_id, trial_grant_rub())
            await db.mark_trial_used(telegram_id)
        else:
            panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
            user = await rw.extend_subscription(
                telegram_id,
                trial_grant_days(local),
                tag="TRIAL",
                panel_user_id=panel_id,
            )
            rw_id = user.get("id")
            panel_pk = int(rw_id) if rw_id is not None and str(rw_id).isdigit() else None
            await db.mark_trial_used(telegram_id, panel_pk)
            await db.save_panel_snapshot(telegram_id, user)
    except RemnawaveError as exc:
        return json_error(str(exc), 502)
    bot: Bot = request.app["bot"]
    if not referral_is_payout():
        friend_name = (local or {}).get("first_name")
        await maybe_reward_referrer(bot, rw, telegram_id, friend_name)
    return web.json_response({"ok": True})


async def api_story_share(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_miniapp(request)
    if denied:
        return denied
    settings = get_settings()
    amount = int(settings.story_reward_rub or 0)
    minutes = int(settings.story_check_minutes or 0)
    if not (settings.balance_enabled and settings.story_reward_enabled and amount > 0):
        return json_error("Награда за историю сейчас недоступна")
    local = await db.get_user(telegram_id)
    if not local:
        return json_error("Пользователь не найден")
    if local.get("story_rewarded_at"):
        return web.json_response({"ok": True, "already": True, "balance_rub": int(local.get("balance_rub") or 0)})
    pending_at = parse_dt(local.get("story_pending_at"))
    if not pending_at:
        started = await db.start_story_check(telegram_id)
        if not started:
            local = await db.get_user(telegram_id)
            pending_at = parse_dt((local or {}).get("story_pending_at"))
            if (local or {}).get("story_rewarded_at"):
                return web.json_response(
                    {"ok": True, "already": True, "balance_rub": int((local or {}).get("balance_rub") or 0)}
                )
        else:
            local = await db.get_user(telegram_id) or local
            pending_at = parse_dt(local.get("story_pending_at")) or datetime.now(timezone.utc)
            bot = request.app.get("bot")
            if bot:
                asyncio.create_task(notify_admins_story(bot, local, amount))
    until = pending_at + timedelta(minutes=minutes) if pending_at else None
    remain = max(0, int((until - datetime.now(timezone.utc)).total_seconds())) if until else 0
    return web.json_response(
        {
            "ok": True,
            "pending": True,
            "story_check_until": until.isoformat() if until else None,
            "story_check_seconds": remain,
            "balance_rub": int((local or {}).get("balance_rub") or 0),
        }
    )


async def api_referral_payout(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    try:
        body = await request.json()
    except Exception:
        body = {}
    details = str((body or {}).get("details") or "")
    bot: Bot = request.app["bot"]
    from app.payouts import request_referral_payout

    ok, message = await request_referral_payout(bot, telegram_id, details)
    if not ok:
        return json_error(message)
    wallet = await db.referral_wallet(telegram_id)
    return web.json_response({"ok": True, "message": message, **referral_payout_public(wallet)})


async def api_invoice(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    settings = get_settings()
    body = await request.json()
    code = str(body.get("plan") or "")
    plan = settings.plan_by_code(code)
    if not plan:
        return json_error("Тариф не найден")
    if not settings.rollypay_configured and int(plan.get("stars") or 0) < 1:
        return json_error("Эта сумма доступна при оплате в рублях")
    if settings.rollypay_configured:
        rp: RollyPayClient | None = request.app.get("rp")
        if rp is None:
            return json_error("Оплата не настроена")
        order_id = uuid.uuid4().hex
        try:
            data = await rp.create_payment(
                amount_rub=plan["rub_str"],
                order_id=order_id,
                description=f"{settings.brand_name}: {plan['title']}",
                customer_id=str(telegram_id),
                metadata={"telegram_id": str(telegram_id), "plan": code},
            )
        except RollyPayError as exc:
            return json_error("Не удалось создать платёж", 502)
        pay_url = str(data.get("pay_url") or "")
        payment_id = str(data.get("payment_id") or "")
        if not pay_url or not payment_id:
            return json_error("Не удалось получить ссылку на оплату", 502)
        await db.save_rollypay_order(order_id, telegram_id, code, payment_id, pay_url)
        return web.json_response({"ok": True, "pay_url": pay_url, "order_id": order_id})
    if not settings.stars_enabled:
        return json_error("Оплата не настроена")
    bot: Bot = request.app["bot"]
    title = "Пополнение" if settings.balance_enabled else "Подписка"
    link = await bot.create_invoice_link(
        title=f"{title}: {plan['title']}",
        description=f"{days_text(plan['days'])}, трафик безлимитный.",
        payload=f"plan:{code}",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
        provider_token="",
    )
    return web.json_response({"ok": True, "invoice_url": link})


async def api_promo(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    settings = get_settings()
    if not settings.promo_enabled:
        return json_error("Промокоды выключены")
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    body = await request.json()
    code = str(body.get("code") or "").strip().upper()
    days = settings.promo_map.get(code)
    if not days:
        return json_error("Промокод не найден")
    if not await db.use_promo(telegram_id, code):
        return json_error("Промокод уже использован")
    rw: RemnawaveClient = request.app["rw"]
    if settings.balance_enabled:
        await db.add_balance_rub(telegram_id, days * max(1, settings.vpn_day_price_rub))
    else:
        local = await db.get_user(telegram_id)
        panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
        try:
            user = await rw.extend_subscription(telegram_id, days, tag="PROMO", panel_user_id=panel_id)
            await db.save_panel_snapshot(telegram_id, user)
        except RemnawaveError as exc:
            return json_error(str(exc), 502)
    return web.json_response({"ok": True, "days": days})


async def api_add_device(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    settings = get_settings()
    if not settings.balance_enabled:
        return json_error("Баланс выключен")
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    body = await request.json()
    title = str(body.get("title") or "").strip() or "Устройство"
    platform = str(body.get("platform") or "").strip()[:32] or None
    client = str(body.get("client") or "").strip()[:32] or None
    cap = int(settings.max_devices or 0)
    if cap > 0 and await db.device_count(telegram_id) >= cap:
        return json_error(f"Можно подключить не больше {cap} устройств")
    price = max(1, settings.vpn_day_price_rub)
    if not await db.spend_balance_rub(telegram_id, price):
        return json_error(f"Недостаточно средств. Нужно {rub_text(price)} за сутки.")
    rw: RemnawaveClient = request.app["rw"]
    user = None
    last_error: RemnawaveError | None = None
    for _ in range(6):
        username = f"t{telegram_id}x{secrets.token_hex(4)}"[:36]
        try:
            user = await rw.create_user(
                telegram_id=None,
                expire_at=panel_lease_until(),
                tag="DEVICE",
                username=username,
                hwid_limit=settings.remnawave_hwid_limit,
                description=f"tg:{telegram_id}:device",
            )
            break
        except RemnawaveError as exc:
            last_error = exc
            if not username_taken(exc):
                break
    if user is None:
        await db.add_balance_rub(telegram_id, price)
        return json_error(str(last_error or "Не удалось создать устройство"), 502)
    rw_id = int(user["id"])
    await db.add_device(telegram_id, title, rw_id, platform, client)
    await db.save_device_subscription(rw_id, user)
    return web.json_response(
        {
            "ok": True,
            "subscription_url": user.get("subscriptionUrl") or "",
            "title": title,
            "platform": platform or "",
            "client": client or "",
        }
    )


async def api_reissue_device(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    settings = get_settings()
    if not settings.balance_enabled:
        return json_error("Баланс выключен")
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    try:
        device_id = int(request.match_info["device_id"])
    except (KeyError, TypeError, ValueError):
        return json_error("Устройство не найдено", 404)
    item = await db.get_device(telegram_id, device_id)
    if not item or not item.get("remnawave_id"):
        return json_error("Устройство не найдено", 404)
    rw: RemnawaveClient = request.app["rw"]
    panel = await rw.get_user_by_id(int(item["remnawave_id"]))
    if not panel:
        return json_error("Устройство в панели не найдено", 404)
    try:
        user = await rw.revoke_subscription(panel)
    except RemnawaveError as exc:
        return json_error(str(exc), 502)
    await db.save_device_subscription(int(item["remnawave_id"]), user)
    return web.json_response({"ok": True, "subscription_url": user.get("subscriptionUrl") or ""})


async def api_delete_device(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    settings = get_settings()
    if not settings.balance_enabled:
        return json_error("Баланс выключен")
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    try:
        device_id = int(request.match_info["device_id"])
    except (KeyError, TypeError, ValueError):
        return json_error("Устройство не найдено", 404)
    item = await db.get_device(telegram_id, device_id)
    if not item:
        return json_error("Устройство не найдено", 404)
    rw: RemnawaveClient = request.app["rw"]
    if item.get("remnawave_id"):
        try:
            await rw.delete_panel_user(int(item["remnawave_id"]))
        except RemnawaveError as exc:
            return json_error(str(exc), 502)
    removed = await db.delete_device(telegram_id, device_id)
    if not removed:
        return json_error("Устройство не найдено", 404)
    await db.log_billing_event(
        telegram_id,
        "device_delete",
        source="user",
        device_id=device_id,
        device_title=str(item.get("title") or ""),
        note="Устройство удалено из кабинета",
    )
    return web.json_response({"ok": True})


async def api_reissue_subscription(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    rw: RemnawaveClient = request.app["rw"]
    panel = await fetch_panel(rw, telegram_id, force=True)
    if not panel:
        return json_error("Подписка ещё не создана")
    try:
        user = await rw.revoke_subscription(panel)
    except RemnawaveError as exc:
        return json_error(str(exc), 502)
    await db.save_panel_snapshot(telegram_id, user)
    return web.json_response({"ok": True, "subscription_url": user.get("subscriptionUrl") or ""})


async def api_vpn_report(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    local = await db.get_user(telegram_id)
    from app.reports import ReportCooldown, submit_vpn_report

    bot: Bot = request.app["bot"]
    rw: RemnawaveClient = request.app["rw"]
    username = (local or {}).get("username")
    first_name = (local or {}).get("first_name")
    try:
        body = await request.json()
    except Exception:
        body = {}
    context = body.get("context") if isinstance(body, dict) else None
    try:
        await submit_vpn_report(bot, rw, telegram_id, username, first_name, client_context=context)
    except ReportCooldown as exc:
        minutes = max(1, exc.wait_sec // 60)
        return json_error(f"Повторно можно через {minutes_text(minutes)}.")
    except Exception:
        logger.exception("VPN report failed")
        return json_error("Не удалось отправить", 502)
    return web.json_response({"ok": True})


async def api_trust(request: web.Request) -> web.Response:
    telegram_id, denied = await _require_tg(request)
    if denied:
        return denied
    try:
        loan = await take_trust(telegram_id)
    except ValueError as exc:
        return json_error(str(exc))
    await sync_user_billing(request.app["rw"], telegram_id, request.app.get("bot"))
    return web.json_response({"ok": True, "loan": loan})


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def rollypay_webhook(request: web.Request) -> web.Response:
    settings = get_settings()
    body = await request.read()
    signature = request.headers.get("X-Signature") or ""
    timestamp = request.headers.get("X-Timestamp") or ""
    if not settings.rollypay_signing_secret:
        return web.Response(status=503, text="signing secret is not set")
    if not verify_webhook(body, timestamp, signature, settings.rollypay_signing_secret):
        return web.Response(status=403, text="invalid signature")
    try:
        event = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return web.Response(status=400, text="invalid json")
    order_id = str(event.get("order_id") or "")
    payment_id = str(event.get("payment_id") or "")
    if not payment_is_paid(event):
        return web.Response(text="OK")
    order = await db.get_rollypay_order(order_id) if order_id else None
    if not order and payment_id:
        order = await db.get_rollypay_order_by_payment(payment_id)
    if not order:
        logger.warning("RollyPay webhook: unknown order %s / %s", order_id, payment_id)
        return web.Response(text="OK")
    order_id = order["order_id"]
    if order["status"] == "granted":
        return web.Response(text="OK")
    rw: RemnawaveClient = request.app["rw"]
    bot: Bot = request.app["bot"]
    plan = settings.plan_by_code(order["plan_code"]) or {"title": "пополнение", "days": 0, "topup_rub": 0}
    try:
        user = await fulfill_rollypay_order(order_id, rw, bot=bot)
    except RemnawaveError as exc:
        logger.exception("RollyPay fulfill failed: %s", exc)
        return web.Response(status=500, text="fulfill failed")
    telegram_id = int(order["telegram_id"])
    try:
        if settings.balance_enabled:
            await bot.send_message(
                telegram_id,
                notice_text(
                    "topup_ok",
                    amount=rub_text(int(plan.get("topup_rub") or 0)) if plan.get("topup_rub") else plan.get("title"),
                ),
            )
        elif user:
            sub_url = user.get("subscriptionUrl") or ""
            await bot.send_message(
                telegram_id,
                subscription_issued_text(user, f"Подписка оформлена: {plan.get('title')}"),
                parse_mode=ParseMode.HTML,
                reply_markup=connect_keyboard(sub_url) if sub_url else back_profile_keyboard(),
            )
    except Exception:
        logger.exception("Не удалось уведомить пользователя %s об оплате", telegram_id)
    return web.Response(text="OK")


def build_web_app() -> web.Application:
    settings = get_settings()
    app = web.Application(client_max_size=80 * 1024 * 1024)
    app.router.add_get("/health", health)
    app.router.add_post("/webhooks/rollypay", rollypay_webhook)
    if settings.webapp_enabled:
        app.router.add_get("/", index)
        app.router.add_get("/app.css", webapp_css)
        app.router.add_get("/app.js", webapp_js)
        app.router.add_get("/qrcode.min.js", webapp_qrcode)
        app.router.add_get("/open.html", webapp_open)
        app.router.add_get("/story.png", webapp_story)
        app.router.add_get("/story.jpg", webapp_story)
        app.router.add_get("/stories_img.png", webapp_story)
        app.router.add_get("/stories_img.jpg", webapp_story)
        app.router.add_get("/api/me", api_me)
        app.router.add_get("/api/avatar", api_avatar)
        app.router.add_post("/api/trial", api_trial)
        app.router.add_post("/api/invoice", api_invoice)
        app.router.add_post("/api/promo", api_promo)
        app.router.add_post("/api/devices", api_add_device)
        app.router.add_post("/api/devices/{device_id}/reissue", api_reissue_device)
        app.router.add_delete("/api/devices/{device_id}", api_delete_device)
        app.router.add_post("/api/subscription/reissue", api_reissue_subscription)
        app.router.add_post("/api/trust", api_trust)
        app.router.add_post("/api/vpn-report", api_vpn_report)
        app.router.add_post("/api/story-share", api_story_share)
        app.router.add_post("/api/referral-payout", api_referral_payout)
        app.router.add_static("/static", WEBAPP_DIR)
    else:
        app.router.add_get("/", health)
    app.router.add_static("/icons", WEBAPP_DIR / "icons")
    mount_admin(app)
    return app


async def start_http(bot: Bot, rw: RemnawaveClient, rp: RollyPayClient | None) -> web.AppRunner:
    settings = get_settings()
    app = build_web_app()
    app["bot"] = bot
    app["rw"] = rw
    app["rp"] = rp
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, settings.webapp_port)
    await site.start()
    logger.info("HTTP %s:%s (webapp=%s)", settings.webapp_host, settings.webapp_port, settings.webapp_enabled)
    return runner


async def start_tunnel(port: int) -> str:
    import asyncio

    from app import runtime

    proc = await asyncio.create_subprocess_exec(
        "cloudflared",
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
        "--protocol",
        "http2",
        "--no-autoupdate",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    runtime.tunnel_proc = proc
    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    assert proc.stdout
    url = ""

    async def drain() -> None:
        while True:
            line = await proc.stdout.readline()
            if not line:
                logger.warning("cloudflared закрыл поток логов")
                break
            logger.info("cloudflared: %s", line.decode("utf-8", "replace").strip())

    while True:
        line = await proc.stdout.readline()
        if not line:
            raise RuntimeError("cloudflared завершился без URL")
        text = line.decode("utf-8", "replace")
        logger.info("cloudflared: %s", text.strip())
        match = pattern.search(text)
        if match:
            url = match.group(0)
            break
    asyncio.create_task(drain(), name="cloudflared-drain")
    return url
