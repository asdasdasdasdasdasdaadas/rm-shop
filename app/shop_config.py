from __future__ import annotations

import json
from typing import Any

from app import db
from app.config import SHOP_KEYS, get_settings, set_shop_overlay
from app.notices import NOTICE_FIELDS, public_notices, validate_notices
from app.vpn_apps import public_vpn_apps, validate_vpn_apps

KV_KEY = "shop_settings"


def _as_int(value: Any, lo: int, hi: int, name: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: укажите целое число")
    if n < lo or n > hi:
        raise ValueError(f"{name}: от {lo} до {hi}")
    return n


def _as_float(value: Any, lo: float, hi: float, name: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: укажите число")
    if n < lo or n > hi:
        raise ValueError(f"{name}: от {lo} до {hi}")
    return n


def _as_str(value: Any, lo: int, hi: int, name: str) -> str:
    text = str(value or "").strip()
    if len(text) < lo or len(text) > hi:
        raise ValueError(f"{name}: длина от {lo} до {hi}")
    return text


def _as_url(value: Any, name: str) -> str:
    text = _as_str(value, 8, 500, name)
    if not (text.startswith("http://") or text.startswith("https://")):
        raise ValueError(f"{name}: нужна ссылка http(s)")
    return text


def validate_shop(body: dict) -> dict:
    out: dict[str, Any] = {}
    out["brand_name"] = _as_str(body.get("brand_name"), 1, 64, "Название")
    out["support_username"] = _as_str(body.get("support_username"), 1, 80, "Поддержка")
    out["legal_offer_url"] = _as_url(body.get("legal_offer_url"), "Оферта")
    out["legal_privacy_url"] = _as_url(body.get("legal_privacy_url"), "Политика")
    out["vpn_day_price_rub"] = _as_int(body.get("vpn_day_price_rub"), 1, 10000, "Цена суток")
    out["max_devices"] = _as_int(body.get("max_devices"), 0, 50, "Максимум устройств")
    out["remnawave_hwid_limit"] = _as_int(body.get("remnawave_hwid_limit"), 0, 20, "Лимит HWID")
    out["trial_enabled"] = bool(body.get("trial_enabled"))
    out["trial_days"] = _as_int(body.get("trial_days"), 1, 90, "Дни триала")
    out["referral_reward_rub"] = _as_int(body.get("referral_reward_rub"), 0, 100000, "Реф. в рублях")
    out["referral_reward_days"] = _as_int(body.get("referral_reward_days"), 0, 365, "Реф. дни пригласившему")
    out["referral_invitee_days"] = _as_int(body.get("referral_invitee_days"), 0, 365, "Реф. дни другу")
    out["balance_topup_min"] = _as_int(body.get("balance_topup_min"), 1, 100000, "Мин. пополнение")
    out["balance_topup_max"] = _as_int(body.get("balance_topup_max"), 1, 100000, "Макс. пополнение")
    out["balance_topup_step"] = _as_int(body.get("balance_topup_step"), 1, 100000, "Шаг пополнения")
    if out["balance_topup_max"] < out["balance_topup_min"]:
        raise ValueError("Максимум пополнения не меньше минимума")
    out["promo_enabled"] = bool(body.get("promo_enabled"))
    codes = str(body.get("promo_codes") or "").strip()
    if len(codes) > 2000:
        raise ValueError("Промокоды слишком длинные")
    out["promo_codes"] = codes
    out["plan_1m_rub"] = _as_float(body.get("plan_1m_rub"), 1, 100000, "Тариф 1 месяц")
    out["plan_3m_rub"] = _as_float(body.get("plan_3m_rub"), 1, 100000, "Тариф 3 месяца")
    out["plan_6m_rub"] = _as_float(body.get("plan_6m_rub"), 1, 100000, "Тариф 6 месяцев")
    out["plan_12m_rub"] = _as_float(body.get("plan_12m_rub"), 1, 100000, "Тариф 12 месяцев")
    out["vpn_report_cooldown_sec"] = _as_int(body.get("vpn_report_cooldown_sec"), 0, 86400, "Пауза жалобы VPN")
    out["vpn_apps"] = validate_vpn_apps(body.get("vpn_apps"))
    out["notices"] = validate_notices(body.get("notices"))
    return {k: out[k] for k in SHOP_KEYS}


def snapshot() -> dict:
    s = get_settings()
    hwid = s.remnawave_hwid_limit
    return {
        "ok": True,
        "balance_enabled": s.balance_enabled,
        "notice_fields": NOTICE_FIELDS,
        "values": {
            "brand_name": s.brand_name,
            "support_username": s.support_username,
            "legal_offer_url": s.legal_offer_url,
            "legal_privacy_url": s.legal_privacy_url,
            "vpn_day_price_rub": s.vpn_day_price_rub,
            "max_devices": s.max_devices,
            "remnawave_hwid_limit": 0 if hwid is None else int(hwid),
            "trial_enabled": s.trial_enabled,
            "trial_days": s.trial_days,
            "referral_reward_rub": s.referral_reward_rub,
            "referral_reward_days": s.referral_reward_days,
            "referral_invitee_days": s.referral_invitee_days,
            "balance_topup_min": s.balance_topup_min,
            "balance_topup_max": s.balance_topup_max,
            "balance_topup_step": s.balance_topup_step,
            "promo_enabled": s.promo_enabled,
            "promo_codes": s.promo_codes,
            "plan_1m_rub": s.plan_1m_rub,
            "plan_3m_rub": s.plan_3m_rub,
            "plan_6m_rub": s.plan_6m_rub,
            "plan_12m_rub": s.plan_12m_rub,
            "vpn_report_cooldown_sec": s.vpn_report_cooldown_sec,
            "vpn_apps": public_vpn_apps(),
            "notices": public_notices(),
        },
    }


async def load_shop_overlay() -> None:
    raw = (await db.get_kv(KV_KEY)).strip()
    if not raw:
        set_shop_overlay({})
        return
    try:
        data = json.loads(raw)
    except ValueError:
        set_shop_overlay({})
        return
    if not isinstance(data, dict):
        set_shop_overlay({})
        return
    set_shop_overlay(data)


async def save_shop_overlay(body: dict) -> dict:
    cleaned = validate_shop(body)
    await db.set_kv(KV_KEY, json.dumps(cleaned, ensure_ascii=False))
    set_shop_overlay(cleaned)
    return snapshot()
