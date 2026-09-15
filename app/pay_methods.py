from __future__ import annotations

from typing import Any

from app.config import get_settings, shop_overlay

KNOWN_PAY_METHODS: dict[str, dict[str, str]] = {
    "sbp": {
        "title": "СБП",
        "note": "Для оплаты через СБП требуется, чтобы у вас было установлено приложение банка.",
    },
    "card": {
        "title": "Оплата картой",
        "note": "Оплата картой откроется на защищённой странице банка.",
    },
    "stars": {
        "title": "Telegram Stars",
        "note": "Оплата звёздами прямо в Telegram, без перехода в банк.",
    },
}

DEFAULT_PAY_METHODS: list[dict[str, Any]] = [
    {"id": "sbp", "enabled": True},
    {"id": "card", "enabled": True},
    {"id": "stars", "enabled": False},
]


def _normalize_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    method_id = str(raw.get("id") or "").strip().lower()
    if method_id not in KNOWN_PAY_METHODS:
        return None
    base = KNOWN_PAY_METHODS[method_id]
    title = str(raw.get("title") or base["title"]).strip() or base["title"]
    note = str(raw.get("note") or base["note"]).strip() or base["note"]
    if len(title) > 64:
        raise ValueError(f"{method_id}: название слишком длинное")
    if len(note) > 300:
        raise ValueError(f"{method_id}: подсказка слишком длинная")
    return {
        "id": method_id,
        "title": title,
        "note": note,
        "enabled": raw.get("enabled") is True,
    }


def validate_pay_methods(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return [dict(item) for item in DEFAULT_PAY_METHODS]
    if not isinstance(raw, list):
        raise ValueError("Способы оплаты: нужен список")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in raw:
        cleaned = _normalize_item(item)
        if not cleaned:
            continue
        if cleaned["id"] in seen:
            continue
        seen.add(cleaned["id"])
        out.append(cleaned)
    for item in DEFAULT_PAY_METHODS:
        if item["id"] not in seen:
            out.append(dict(item))
    return out


def configured_pay_methods() -> list[dict[str, Any]]:
    raw = shop_overlay().get("pay_methods")
    try:
        return validate_pay_methods(raw)
    except ValueError:
        return [dict(item) for item in DEFAULT_PAY_METHODS]


def method_available(method_id: str, settings=None) -> bool:
    s = settings or get_settings()
    key = str(method_id or "").strip().lower()
    if key in {"sbp", "card"}:
        return bool(s.rollypay_configured)
    if key == "stars":
        return True
    return False


def public_pay_methods() -> list[dict[str, Any]]:
    settings = get_settings()
    out: list[dict[str, Any]] = []
    for item in configured_pay_methods():
        if not item.get("enabled"):
            continue
        method_id = item["id"]
        if not method_available(method_id, settings):
            continue
        base = KNOWN_PAY_METHODS[method_id]
        out.append(
            {
                "id": method_id,
                "title": item.get("title") or base["title"],
                "note": item.get("note") or base["note"],
            }
        )
    return out


def admin_pay_methods() -> list[dict[str, Any]]:
    settings = get_settings()
    out: list[dict[str, Any]] = []
    for item in configured_pay_methods():
        method_id = item["id"]
        base = KNOWN_PAY_METHODS[method_id]
        available = method_available(method_id, settings)
        hint = ""
        if method_id in {"sbp", "card"} and not available:
            hint = "Нужны ключи RollyPay в окружении"
        out.append(
            {
                "id": method_id,
                "title": item.get("title") or base["title"],
                "note": item.get("note") or base["note"],
                "enabled": bool(item.get("enabled")),
                "available": available,
                "hint": hint,
            }
        )
    return out
