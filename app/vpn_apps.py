from __future__ import annotations

import re
from typing import Any

from app.config import shop_overlay

PLATFORMS = ("ios", "macos", "appletv", "android", "androidtv", "windows")
_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,23}$")

DEFAULT_VPN_APPS: list[dict[str, Any]] = [
    {
        "id": "incy",
        "name": "Incy",
        "mark": "IN",
        "deep_link": "incy://import/{url}",
        "platforms": ["ios", "macos", "appletv"],
        "stores": {
            "ios": "https://apps.apple.com/search?term=Incy",
            "macos": "https://apps.apple.com/search?term=Incy",
            "appletv": "https://apps.apple.com/search?term=Incy",
        },
    },
    {
        "id": "happ",
        "name": "Happ",
        "mark": "H",
        "deep_link": "happ://add/{url}",
        "platforms": ["ios", "macos", "appletv", "android", "androidtv", "windows"],
        "stores": {
            "ios": "https://apps.apple.com/app/id6504287215",
            "macos": "https://apps.apple.com/app/id6504287215",
            "appletv": "https://apps.apple.com/app/id6504287215",
            "android": "https://play.google.com/store/apps/details?id=com.happproxy",
            "androidtv": "https://play.google.com/store/apps/details?id=com.happproxy",
            "windows": "https://github.com/Happ-proxy/happ-desktop/releases",
        },
    },
    {
        "id": "v2rayng",
        "name": "v2rayNG",
        "mark": "v2",
        "deep_link": "v2rayng://install-sub?url={enc}",
        "platforms": ["android", "androidtv"],
        "stores": {
            "android": "https://play.google.com/store/apps/details?id=com.v2ray.ang",
            "androidtv": "https://play.google.com/store/apps/details?id=com.v2ray.ang",
        },
    },
    {
        "id": "v2rayn",
        "name": "v2rayN",
        "mark": "v2",
        "deep_link": "",
        "platforms": ["windows"],
        "stores": {
            "windows": "https://github.com/2dust/v2rayN/releases",
        },
    },
]


def _clean_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not (text.startswith("http://") or text.startswith("https://")):
        raise ValueError("Ссылка магазина должна начинаться с http(s)")
    if len(text) > 500:
        raise ValueError("Ссылка магазина слишком длинная")
    return text


def validate_vpn_apps(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return [dict(x) for x in DEFAULT_VPN_APPS]
    if not isinstance(raw, list):
        raise ValueError("Список приложений задан неверно")
    if not raw:
        raise ValueError("Нужно хотя бы одно приложение")
    if len(raw) > 20:
        raise ValueError("Не больше 20 приложений")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Приложение {i}: неверный формат")
        app_id = str(item.get("id") or "").strip().lower()
        if not _ID_RE.match(app_id):
            raise ValueError(f"Приложение {i}: id латиницей, с буквы, до 24 символов")
        if app_id in seen:
            raise ValueError(f"Повторяется id: {app_id}")
        seen.add(app_id)
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 40:
            raise ValueError(f"{app_id}: название от 1 до 40 символов")
        mark = str(item.get("mark") or "").strip() or name[:2].upper()
        if len(mark) > 4:
            raise ValueError(f"{app_id}: значок до 4 символов")
        deep = str(item.get("deep_link") or "").strip()
        if len(deep) > 200:
            raise ValueError(f"{app_id}: шаблон ссылки слишком длинный")
        if deep and "{url}" not in deep and "{enc}" not in deep:
            raise ValueError(f"{app_id}: в шаблоне нужен {{url}} или {{enc}}")
        plats_raw = item.get("platforms") or []
        if not isinstance(plats_raw, list):
            raise ValueError(f"{app_id}: платформы заданы неверно")
        platforms = []
        for p in plats_raw:
            key = str(p or "").strip()
            if key in PLATFORMS and key not in platforms:
                platforms.append(key)
        if not platforms:
            raise ValueError(f"{app_id}: выберите хотя бы одну платформу")
        stores_raw = item.get("stores") or {}
        if not isinstance(stores_raw, dict):
            raise ValueError(f"{app_id}: ссылки магазинов заданы неверно")
        stores = {}
        for p in platforms:
            url = _clean_url(stores_raw.get(p))
            if url:
                stores[p] = url
        out.append(
            {
                "id": app_id,
                "name": name,
                "mark": mark,
                "deep_link": deep,
                "platforms": platforms,
                "stores": stores,
            }
        )
    return out


def public_vpn_apps() -> list[dict[str, Any]]:
    raw = shop_overlay().get("vpn_apps")
    if not raw:
        return [dict(x) for x in DEFAULT_VPN_APPS]
    try:
        return validate_vpn_apps(raw)
    except ValueError:
        return [dict(x) for x in DEFAULT_VPN_APPS]
