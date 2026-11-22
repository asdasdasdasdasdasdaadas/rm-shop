"""Why a device that came online moves no traffic, from what the Remnawave panel already knows — no node setup.

The panel tells us when the subscription was last opened and by which app, when the device was last online,
how much it moved, which node it used and whether that node is up; the sharing poll (app/sharing_alert.py)
adds the IPs the nodes saw. That is enough to tell «нода лежит», «включил и сразу пропал» and «на связи, но
данные не идут» apart. The node logs (app/node_logs.py) say more when they are shipped.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app import db

logger = logging.getLogger("rm-shop.panel-diag")

NOW_MINUTES = 5          # online this recently counts as «на связи сейчас»
SHORT_MINUTES = 3        # online for less than this and gone: «подключился и пропал»
TRICKLE_BYTES = 100 * 1024


def _ago(when: datetime | None, now: datetime) -> str:
    if not when:
        return "никогда"
    minutes = max(0, int((now - when).total_seconds() // 60))
    if minutes < 1:
        return "только что"
    if minutes < 60:
        return f"{minutes} мин назад"
    hours = minutes // 60
    return f"{hours} ч назад" if hours < 48 else f"{hours // 24} дн назад"


def verdict(f: dict, now: datetime | None = None) -> dict:
    """{verdict, details} from the panel facts: panel (bool), node {name, connected}, sub_opened_at, user_agent,
    first_online_at, online_at, traffic, ips (None when the IP poll is off), sessions."""
    now = now or datetime.now(timezone.utc)
    if not f.get("panel"):
        return {"verdict": "", "details": []}
    from app.remnawave import format_bytes
    node, traffic = f.get("node") or {}, int(f.get("traffic") or 0)
    first, online = f.get("first_online_at"), f.get("online_at")
    details = []
    opened = f.get("sub_opened_at")
    agent = str(f.get("user_agent") or "").strip()
    details.append(f"подписку открывали {_ago(opened, now)}" + (f" ({agent[:40]})" if opened and agent else "")
                   if opened else "подписку из приложения не открывали — ключ вставлен вручную")
    if node.get("name"):
        details.append(f"нода {node['name']}" + (" не на связи" if node.get("connected") is False else ""))
    details.append(f"на связи {_ago(online, now)}")
    if f.get("ips") is not None:
        details.append(f"IP на нодах за сутки: {f['ips']}" if f["ips"] else "IP на нодах не видели")
    if f.get("sessions"):
        details.append(f"сессий в приложении: {f['sessions']}")

    if node.get("connected") is False:
        text = f"Нода {node.get('name') or ''} сейчас не на связи — проблема на нашей стороне, не у человека".replace("  ", " ")
    elif online and (now - online).total_seconds() <= NOW_MINUTES * 60:
        text = ("Сейчас на связи, но данные почти не идут — похоже, провайдер режет VPN после подключения. "
                "Стоит попробовать другую ноду или мобильный интернет вместо Wi‑Fi"
                if traffic < TRICKLE_BYTES else
                f"Сейчас на связи, прошло {format_bytes(traffic)} — VPN работает, но им почти не пользуются "
                "или открывается не всё")
    elif first and online and (online - first).total_seconds() < SHORT_MINUTES * 60:
        text = "Подключился на минуту и пропал — соединение рвётся сразу или VPN выключили"
    else:
        text = (f"Был на связи, но прошло всего {format_bytes(traffic)} — соединение держится, а сайты не "
                "открываются: похоже на блокировку провайдером")
    return {"verdict": text, "details": details}


async def diagnose(rw, device_id: int) -> dict:
    """Ask the panel about one device now. {verdict: ""} when there is no panel or it did not answer."""
    if rw is None:
        return {"verdict": "", "details": []}
    from app.remnawave import (fetch_device_network, panel_online_at, panel_sub_opened_at, panel_used_traffic_bytes,
                               panel_user_agent, parse_dt)
    row = await db._pool_req().fetchrow(
        """SELECT remnawave_id, remnawave_uuid, first_online_at,
                  GREATEST(COALESCE(lifetime_traffic_bytes, 0), COALESCE(used_traffic_bytes, 0)) AS traffic
           FROM devices WHERE id = $1""", int(device_id))
    if not row or (row["remnawave_id"] is None and not row["remnawave_uuid"]):
        return {"verdict": "", "details": []}
    try:
        net = await fetch_device_network(rw, remnawave_id=row["remnawave_id"], uuid=row["remnawave_uuid"])
    except Exception:
        logger.warning("Панель не ответила для диагноза устройства %s", device_id, exc_info=True)
        return {"verdict": "", "details": []}
    panel = net.get("panel")
    ips = None
    try:
        from app import sharing_alert
        if not sharing_alert._unsupported:
            ips = len({r["ip"] for r in await db.device_ips_recent(int(device_id))})
    except Exception:
        logger.debug("IP устройства %s не прочитаны", device_id, exc_info=True)
    return verdict({
        "panel": bool(panel),
        "node": net.get("node"),
        "sub_opened_at": panel_sub_opened_at(panel),
        "user_agent": panel_user_agent(panel),
        "first_online_at": parse_dt(row["first_online_at"]),
        "online_at": panel_online_at(panel),
        "traffic": max(int(row["traffic"] or 0), int(panel_used_traffic_bytes(panel) or 0)),
        "ips": ips,
        "sessions": len(net.get("hwid") or []),
    })
