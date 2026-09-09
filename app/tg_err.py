from __future__ import annotations

from typing import Any


def telegram_fail_reason(exc: BaseException) -> str:
    raw = " ".join(str(exc).strip().split())
    low = raw.lower()
    if "blocked by the user" in low:
        return "пользователь заблокировал бота"
    if "user is deactivated" in low or "user deactivated" in low:
        return "аккаунт Telegram удалён"
    if "chat not found" in low:
        return "чат не найден"
    if "bot was kicked" in low:
        return "бота удалили из чата"
    if "have no rights" in low or "not enough rights" in low:
        return "нет прав писать в этот чат"
    if "too many requests" in low or "retry after" in low:
        return "лимит Telegram, слишком часто"
    if "message is not modified" in low:
        return "сообщение не изменилось"
    if "can't initiate conversation" in low or "bot can't initiate" in low:
        return "пользователь не начинал диалог с ботом"
    if "forbidden" in low:
        return "Telegram запретил отправку: " + (raw[:180] or "Forbidden")
    if not raw:
        return exc.__class__.__name__
    return raw[:240]


def fail_extra(exc: BaseException, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(extra or {})
    out["error"] = telegram_fail_reason(exc)
    out["error_raw"] = str(exc)[:400]
    return out
