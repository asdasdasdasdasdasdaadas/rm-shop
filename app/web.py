from __future__ import annotations

import json
import logging
import re
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
from app.config import ROOT, get_settings
from app.keyboards import back_profile_keyboard, connect_keyboard
from app.referrals import maybe_reward_referrer, trial_grant_days, trial_grant_rub
from app.remnawave import (
    RemnawaveClient,
    RemnawaveError,
    days_remaining,
    is_subscription_active,
    parse_expire,
)
from app.rollypay import RollyPayClient, RollyPayError, payment_is_paid, verify_webhook
from app.sync import fetch_panel
from app.texts import days_text, minutes_text, rub_text
from app.trust import MAINTENANCE_TEXT, take_trust, trust_info

logger = logging.getLogger("rm-shop.web")
WEBAPP_DIR = ROOT / "webapp"


def _init_data(request: web.Request) -> str:
    return request.headers.get("X-Init-Data") or request.query.get("initData") or ""


def _user_id(request: web.Request) -> int:
    settings = get_settings()
    raw = _init_data(request)
    data = safe_parse_webapp_init_data(settings.bot_token, raw)
    if not data.user:
        raise web.HTTPUnauthorized(text="no user")
    return int(data.user.id)


def json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"ok": False, "error": message}, status=status)


async def _if_down() -> web.Response | None:
    if await db.flag_on("maintenance"):
        return json_error(MAINTENANCE_TEXT, 503)
    return None


async def index(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "index.html")


async def api_me(request: web.Request) -> web.Response:
    settings = get_settings()
    try:
        parsed = safe_parse_webapp_init_data(settings.bot_token, _init_data(request))
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
    if not parsed.user:
        return json_error("Недействительные данные Telegram", 401)
    telegram_id = int(parsed.user.id)
    if await db.flag_on("maintenance"):
        return web.json_response(
            {
                "ok": True,
                "maintenance": True,
                "brand_name": settings.brand_name,
            }
        )
    bot: Bot = request.app["bot"]
    rw: RemnawaveClient = request.app["rw"]
    await db.upsert_user(telegram_id, parsed.user.username, parsed.user.first_name)
    panel = await fetch_panel(rw, telegram_id)
    local = await db.get_user(telegram_id)

    days = int(local["balance_days"] or 0) if settings.balance_enabled and local else days_remaining(panel)
    balance_rub = int((local or {}).get("balance_rub") or 0) if local else 0
    sub_url = (panel or {}).get("subscriptionUrl") or ""
    devices = []
    if settings.balance_enabled:
        raw_devices = await db.list_devices(telegram_id)
        for item in raw_devices:
            panel_dev = None
            if item.get("remnawave_id"):
                panel_dev = await rw.get_user_by_id(int(item["remnawave_id"]))
            expire = parse_expire((panel_dev or {}).get("expireAt")) if panel_dev else None
            devices.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "username": (panel_dev or {}).get("username") or "",
                    "subscription_url": (panel_dev or {}).get("subscriptionUrl") or "",
                    "days": days_remaining(panel_dev),
                    "active": is_subscription_active(panel_dev),
                    "expire_at": expire.isoformat() if expire else None,
                    "platform": item.get("platform") or "",
                    "client": item.get("client") or "",
                }
            )

    photo = ""
    try:
        photos = await bot.get_user_profile_photos(telegram_id, limit=1)
        if photos.total_count and photos.photos:
            file_id = photos.photos[0][-1].file_id
            photo = f"/api/avatar?uid={telegram_id}&f={file_id}"
    except Exception:
        photo = ""

    tg_user = parsed.user
    name = " ".join(x for x in [tg_user.first_name, tg_user.last_name] if x) if tg_user else ""
    username = f"@{tg_user.username}" if tg_user and tg_user.username else ""
    trust = await trust_info(telegram_id, local, len(devices)) if settings.balance_enabled else None
    if settings.balance_enabled and devices:
        days_left = balance_rub // (max(1, settings.vpn_day_price_rub) * len(devices))
    elif settings.balance_enabled:
        days_left = balance_rub // max(1, settings.vpn_day_price_rub)
    else:
        days_left = days
    days_left = max(0, int(days_left))

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
            "trial_available": bool(settings.trial_enabled and local and not local["trial_used"]),
            "trial_days": trial_grant_days(local) if not settings.balance_enabled else settings.trial_days,
            "trial_rub": trial_grant_rub() if settings.balance_enabled else 0,
            "days": days,
            "days_left": days_left,
            "balance_rub": balance_rub,
            "vpn_day_price_rub": settings.vpn_day_price_rub,
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
            "legal": {
                "offer": settings.legal_offer_url,
                "privacy": settings.legal_privacy_url,
                "support": settings.support_username,
            },
            "plans": [
                {
                    "code": code,
                    "title": p["title"],
                    "days": p["days"],
                    "stars": p["stars"],
                    "rub": p["rub_str"],
                }
                for code, p in settings.shop_plans.items()
            ],
            "devices": devices,
            "trust": trust,
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
    denied = await _if_down()
    if denied:
        return denied
    settings = get_settings()
    try:
        telegram_id = _user_id(request)
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
    local = await db.get_user(telegram_id)
    if not settings.trial_enabled:
        return json_error("Сейчас нельзя попробовать бесплатно")
    if local and local["trial_used"]:
        return json_error("Вы уже пробовали бесплатно")
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
    friend_name = (local or {}).get("first_name")
    await maybe_reward_referrer(bot, rw, telegram_id, friend_name)
    return web.json_response({"ok": True})


async def api_invoice(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    settings = get_settings()
    try:
        telegram_id = _user_id(request)
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
    body = await request.json()
    code = str(body.get("plan") or "")
    plan = settings.shop_plans.get(code)
    if not plan:
        return json_error("Тариф не найден")
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
    try:
        telegram_id = _user_id(request)
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
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
    try:
        telegram_id = _user_id(request)
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
    body = await request.json()
    title = str(body.get("title") or "").strip() or "Устройство"
    platform = str(body.get("platform") or "").strip()[:32] or None
    client = str(body.get("client") or "").strip()[:32] or None
    price = max(1, settings.vpn_day_price_rub)
    if not await db.spend_balance_rub(telegram_id, price):
        return json_error(f"Недостаточно средств. Нужно {rub_text(price)} за сутки.")
    rw: RemnawaveClient = request.app["rw"]
    n = await db.device_count(telegram_id) + 1
    username = f"t{telegram_id}d{n}"[:36]
    try:
        user = await rw.create_user(
            telegram_id=None,
            expire_at=datetime.now(timezone.utc) + timedelta(days=1),
            tag="DEVICE",
            username=username,
            hwid_limit=1,
            description=f"tg:{telegram_id}:device",
        )
    except RemnawaveError as exc:
        await db.add_balance_rub(telegram_id, price)
        return json_error(str(exc), 502)
    rw_id = int(user["id"])
    await db.add_device(telegram_id, title, rw_id, platform, client)
    return web.json_response(
        {
            "ok": True,
            "subscription_url": user.get("subscriptionUrl") or "",
            "title": title,
            "platform": platform or "",
            "client": client or "",
        }
    )


async def api_vpn_report(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    try:
        parsed = safe_parse_webapp_init_data(get_settings().bot_token, _init_data(request))
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
    if not parsed.user:
        return json_error("Недействительные данные Telegram", 401)
    from app.reports import ReportCooldown, submit_vpn_report

    bot: Bot = request.app["bot"]
    rw: RemnawaveClient = request.app["rw"]
    telegram_id = int(parsed.user.id)
    try:
        await submit_vpn_report(bot, rw, telegram_id, parsed.user.username, parsed.user.first_name)
    except ReportCooldown as exc:
        minutes = max(1, exc.wait_sec // 60)
        return json_error(f"Повторно можно через {minutes_text(minutes)}.")
    except Exception:
        logger.exception("VPN report failed")
        return json_error("Не удалось отправить", 502)
    return web.json_response({"ok": True})


async def api_trust(request: web.Request) -> web.Response:
    denied = await _if_down()
    if denied:
        return denied
    try:
        telegram_id = _user_id(request)
    except ValueError:
        return json_error("Недействительные данные Telegram", 401)
    try:
        loan = await take_trust(telegram_id)
    except ValueError as exc:
        return json_error(str(exc))
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
    plan = settings.shop_plans.get(order["plan_code"]) or {"title": "пополнение", "days": 0, "topup_rub": 0}
    try:
        user = await fulfill_rollypay_order(order_id, rw)
    except RemnawaveError as exc:
        logger.exception("RollyPay fulfill failed: %s", exc)
        return web.Response(status=500, text="fulfill failed")
    telegram_id = int(order["telegram_id"])
    try:
        if settings.balance_enabled:
            await bot.send_message(
                telegram_id,
                f"Баланс пополнен на {rub_text(int(plan.get('topup_rub') or 0)) if plan.get('topup_rub') else plan.get('title')}.",
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
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_post("/webhooks/rollypay", rollypay_webhook)
    if settings.webapp_enabled:
        app.router.add_get("/", index)
        app.router.add_get("/app.css", lambda _r: web.FileResponse(WEBAPP_DIR / "app.css"))
        app.router.add_get("/app.js", lambda _r: web.FileResponse(WEBAPP_DIR / "app.js"))
        app.router.add_get("/api/me", api_me)
        app.router.add_get("/api/avatar", api_avatar)
        app.router.add_post("/api/trial", api_trial)
        app.router.add_post("/api/invoice", api_invoice)
        app.router.add_post("/api/promo", api_promo)
        app.router.add_post("/api/devices", api_add_device)
        app.router.add_post("/api/trust", api_trust)
        app.router.add_post("/api/vpn-report", api_vpn_report)
        app.router.add_static("/static", WEBAPP_DIR)
    else:
        app.router.add_get("/", health)
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
