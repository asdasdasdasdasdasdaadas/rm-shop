"""Connection evidence and support context. Never treats subscription opens as VPN use."""
from datetime import datetime, timezone
from app import db
from app.remnawave import panel_online_at, panel_display_traffic_bytes


def connection_result(panel, now=None):
    now = now or datetime.now(timezone.utc)
    online = panel_online_at(panel)
    recent = (online is not None and 0 <= (now - online).total_seconds() <= 300
              and str(panel.get("status") or "").upper() not in {"DISABLED", "EXPIRED", "LIMITED"})
    traffic = panel_display_traffic_bytes(panel) or 0
    return {"status": "connected" if recent else "not_confirmed",
            "previously_connected": bool(online or traffic > 0),
            "last_online_at": online.isoformat() if online else None}


async def support_context(telegram_id, raw):
    if not isinstance(raw, dict):
        return ""
    try:
        device_id = int(raw.get("device_id"))
    except (TypeError, ValueError):
        return ""
    device = await db.get_device(telegram_id, device_id)
    if not device:
        return ""
    stages = {"subscription": "Добавление подписки / включение VPN", "check": "Проверка подключения"}
    results = {"connected": "Недавнее подключение подтверждено", "not_confirmed": "Недавнее подключение не подтверждено", "unavailable": "Панель не ответила"}
    # Only bounded labels; URLs, tokens and arbitrary client diagnostics are not accepted.
    client = str(raw.get("client") or device.get("client") or "не указано")[:40]
    client = " ".join(client.split())
    stage = str(raw.get('stage') or '')
    result = str(raw.get('result') or '')
    return ("\n\nДиагностика подключения:\n"
            f"Устройство: {device.get('title') or 'Без названия'} (#{device_id})\n"
            f"Платформа: {device.get('platform') or 'не указана'}\n"
            f"Приложение (выбрано пользователем): {client}\n"
            f"Этап: {stages.get(stage, stages['subscription'])}\n"
            f"Результат на экране: {results.get(result, 'Проверка ещё не запускалась')}\n"
            f"Последний онлайн по синхронизации: {device.get('last_online_at') or 'не подтверждён'}\n"
            f"Статус доступа: {device.get('panel_status') or 'неизвестен'}")
