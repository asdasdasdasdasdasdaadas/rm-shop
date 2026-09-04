from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "response" in payload:
        return payload["response"]
    return payload


def _as_users(data: Any) -> list[dict]:
    data = _unwrap(data)
    if not data:
        return []
    if isinstance(data, list):
        return [u for u in data if isinstance(u, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("users"), list):
            return [u for u in data["users"] if isinstance(u, dict)]
        nested = data.get("user")
        if isinstance(nested, dict):
            merged = dict(nested)
            traffic = data.get("userTraffic")
            if isinstance(traffic, dict) and not isinstance(merged.get("userTraffic"), dict):
                merged["userTraffic"] = traffic
            for key in (
                "onlineAt",
                "lastConnectedAt",
                "firstConnectedAt",
                "subLastOpenedAt",
                "subLastOpened",
                "usedTrafficBytes",
            ):
                if key in data and merged.get(key) in (None, ""):
                    merged[key] = data[key]
            return [merged]
        if "username" in data or "id" in data or "uuid" in data or "shortUuid" in data:
            return [data]
    return []


def panel_user_key(user: dict | None) -> str:
    if not user:
        return ""
    uid = str(user.get("uuid") or "").strip()
    if uid:
        return uid
    raw_id = user.get("id")
    if raw_id is not None and str(raw_id).strip() != "":
        return str(raw_id).strip()
    return ""


def _by_telegram(data: Any, telegram_id: int) -> dict | None:
    for user in _as_users(data):
        raw = user.get("telegramId")
        if raw is None:
            continue
        try:
            if int(raw) == int(telegram_id):
                return user
        except (TypeError, ValueError):
            continue
    return None


def parse_expire(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_dt(value: Any) -> datetime | None:
    if value is None or value is False:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        n = float(value)
        if n > 1e12:
            n /= 1000.0
        if n > 1e9:
            try:
                return datetime.fromtimestamp(n, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        return None
    if isinstance(value, dict):
        for key in ("onlineAt", "date", "$date", "timestamp"):
            if key in value:
                dt = parse_dt(value[key])
                if dt:
                    return dt
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return parse_expire(text)


def panel_online_at(user: dict | None) -> datetime | None:
    if not user:
        return None
    traffic = user.get("userTraffic") if isinstance(user.get("userTraffic"), dict) else {}
    nested = user.get("traffic") if isinstance(user.get("traffic"), dict) else {}
    for raw in (
        traffic.get("onlineAt"),
        nested.get("onlineAt"),
        user.get("onlineAt"),
        traffic.get("lastConnectedAt"),
        nested.get("lastConnectedAt"),
        user.get("lastConnectedAt"),
        user.get("lastOnlineAt"),
        user.get("lastOnline"),
        user.get("subLastOpenedAt"),
        user.get("subLastOpened"),
    ):
        dt = parse_dt(raw)
        if dt:
            return dt
    return None


def iso_expire(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# Запас в панели: Remnawave часто хранит только дату UTC и гасит учётку в полночь.
# Сутки в приложении не должны упираться в эту обрезку и в задержку крона.
PANEL_LEASE_DAYS = 3


def panel_lease_until(*, min_days: int | None = None) -> datetime:
    now = datetime.now(timezone.utc)
    days = max(2, int(min_days if min_days is not None else PANEL_LEASE_DAYS))
    floor = now + timedelta(days=days)
    at_noon = floor.replace(hour=12, minute=0, second=0, microsecond=0)
    if at_noon <= floor:
        at_noon += timedelta(days=1)
    return at_noon


def gb_to_bytes(gb: int) -> int:
    return 0 if gb <= 0 else gb * 1024 * 1024 * 1024


def format_bytes(n: int | None) -> str:
    if not n:
        return "0 Б"
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} Б"


class RemnawaveError(RuntimeError):
    pass


def username_taken(exc: RemnawaveError) -> bool:
    text = str(exc).lower()
    return "a019" in text or "username already exists" in text


class RemnawaveClient:
    def __init__(self) -> None:
        settings = get_settings()
        base = settings.remnawave_base_url.rstrip("/")
        self.base = base if base.endswith("/api") else f"{base}/api"
        self.token = settings.remnawave_token
        self._lookup = "stream"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=4.0),
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _page_inner(self, payload: Any) -> dict:
        if isinstance(payload, dict) and isinstance(payload.get("response"), dict):
            return payload["response"]
        if isinstance(payload, dict):
            return payload
        return {}

    async def _users_stream_page(
        self, cursor: Any, size: int
    ) -> tuple[list[dict], Any, bool]:
        params: dict[str, Any] = {"size": size}
        if cursor is not None and cursor != "":
            params["cursor"] = cursor
        data = await self._request(
            "GET",
            "/users/stream",
            params=params,
            timeout=httpx.Timeout(30.0, connect=8.0),
        )
        if not isinstance(data, dict):
            raise RemnawaveError("GET /users/stream: нужен JSON")
        inner = self._page_inner(data)
        users = _as_users(inner if inner else data)
        next_cursor = inner.get("nextCursor")
        has_more = bool(inner.get("hasMore"))
        if next_cursor in ("", None):
            next_cursor = None
        return users, next_cursor, has_more

    async def _users_list_page(self, start: int, size: int) -> tuple[list[dict], bool]:
        last: RemnawaveError | None = None
        data = None
        for params in (
            {"start": start, "size": size},
            {"skip": start, "take": size},
        ):
            try:
                data = await self._request(
                    "GET",
                    "/users",
                    params=params,
                    timeout=httpx.Timeout(30.0, connect=8.0),
                )
                last = None
                break
            except RemnawaveError as exc:
                last = exc
        if last:
            raise last
        if not isinstance(data, dict):
            raise RemnawaveError("GET /users: нужен JSON")
        inner = self._page_inner(data)
        users = _as_users(inner if inner else data)
        if isinstance(inner.get("data"), list) and not users:
            users = [u for u in inner["data"] if isinstance(u, dict)]
        total = inner.get("total")
        if isinstance(total, int):
            return users, start + len(users) < total
        return users, len(users) >= size

    async def iter_user_pages(self, size: int = 250):
        cursor = None
        seen_cursors: set[str] = set()
        stream_ok = False
        try:
            while True:
                users, next_cursor, has_more = await self._users_stream_page(cursor, size)
                stream_ok = True
                yield users
                if next_cursor is None and not has_more:
                    return
                if not has_more:
                    return
                marker = str(next_cursor)
                if next_cursor is None or marker in seen_cursors:
                    return
                seen_cursors.add(marker)
                cursor = next_cursor
            return
        except RemnawaveError:
            if stream_ok:
                return
        start = 0
        while True:
            users, has_more = await self._users_list_page(start, size)
            yield users
            if not has_more or not users:
                return
            start += len(users)

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base}{path}"
        timeout = kwargs.pop("timeout", None)
        try:
            response = await self._client.request(method, url, timeout=timeout, **kwargs)
        except httpx.HTTPError as exc:
            raise RemnawaveError(f"{method} {path}: {exc}") from exc
        if response.status_code >= 400:
            raise RemnawaveError(f"{method} {path} → {response.status_code}: {response.text[:500]}")
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    async def safe_get(self, *paths: str, params: dict | None = None) -> Any:
        last = ""
        for path in paths:
            if not path:
                continue
            try:
                kwargs: dict[str, Any] = {}
                if params:
                    kwargs["params"] = params
                return _unwrap(await self._request("GET", path, **kwargs))
            except RemnawaveError as exc:
                last = str(exc)[:400]
                continue
        return {"_error": last} if last else None

    async def get_user_by_id(self, user_id: int | str) -> dict | None:
        ident = str(user_id).strip()
        if not ident:
            return None
        paths = [f"/users/{ident}"]
        if ident.isdigit():
            paths.append(f"/users/by-id/{ident}")
        for path in paths:
            try:
                data = await self._request("GET", path)
            except RemnawaveError:
                continue
            users = _as_users(data)
            if users:
                return users[0]
        return None

    async def get_user_by_telegram(self, telegram_id: int) -> dict | None:
        if self._lookup == "stream":
            try:
                data = await self._request(
                    "GET",
                    "/users/stream",
                    params={"telegramId": telegram_id, "size": 5},
                )
                return _by_telegram(data, telegram_id)
            except RemnawaveError:
                self._lookup = "by-telegram"

        try:
            data = await self._request("GET", f"/users/by-telegram-id/{telegram_id}")
            return _by_telegram(data, telegram_id)
        except RemnawaveError:
            return None

    async def create_user(
        self,
        telegram_id: int | None,
        expire_at: datetime,
        traffic_limit_gb: int = 0,
        tag: str | None = None,
        username: str | None = None,
        hwid_limit: int | None = None,
        description: str | None = None,
    ) -> dict:
        settings = get_settings()
        uname = (username or (f"tg{telegram_id}" if telegram_id else "user"))[:36]
        payload: dict[str, Any] = {
            "username": uname,
            "status": "ACTIVE",
            "expireAt": iso_expire(expire_at),
            "trafficLimitBytes": 0,
            "trafficLimitStrategy": settings.remnawave_traffic_strategy,
            "description": description or (f"tg:{telegram_id}" if telegram_id else uname),
        }
        if telegram_id is not None:
            payload["telegramId"] = telegram_id
        if settings.squad_uuids:
            payload["activeInternalSquads"] = settings.squad_uuids
        limit = settings.remnawave_hwid_limit if hwid_limit is None else hwid_limit
        if limit is not None:
            payload["hwidDeviceLimit"] = limit
        if tag:
            payload["tag"] = tag
        data = await self._request("POST", "/users", json=payload)
        users = _as_users(data)
        if not users:
            raise RemnawaveError("Панель не вернула пользователя после создания")
        return users[0]

    async def revoke_subscription(self, user: dict) -> dict:
        uid = panel_user_key(user)
        if not uid and user.get("id") is not None:
            fresh = await self.get_user_by_id(user["id"])
            if fresh:
                user = fresh
                uid = panel_user_key(user)
        if not uid:
            raise RemnawaveError("Не удалось определить пользователя в панели")
        data = await self._request("POST", f"/users/{uid}/actions/revoke", json={})
        users = _as_users(data)
        if not users:
            raise RemnawaveError("Панель не вернула пользователя после перевыпуска ссылки")
        return users[0]

    async def bulk_revoke_subscription(self, user_ids: list[int]) -> None:
        if not user_ids:
            return
        timeout = httpx.Timeout(60.0, connect=8.0)
        try:
            await self._request(
                "POST",
                "/users/bulk/revoke-subscription",
                json={"userIds": user_ids},
                timeout=timeout,
            )
            return
        except RemnawaveError:
            pass
        await self._request(
            "POST",
            "/users/bulk/revoke-subscription",
            json={"uuids": [str(uid) for uid in user_ids]},
            timeout=timeout,
        )

    async def bulk_update_squads(self, user_ids: list[int], squad_uuids: list[str]) -> None:
        if not user_ids or not squad_uuids:
            return
        timeout = httpx.Timeout(60.0, connect=8.0)
        body = {"userIds": user_ids, "activeInternalSquads": squad_uuids}
        try:
            await self._request("POST", "/users/bulk/update-squads", json=body, timeout=timeout)
            return
        except RemnawaveError:
            pass
        await self._request(
            "POST",
            "/users/bulk/update-squads",
            json={"uuids": [str(uid) for uid in user_ids], "activeInternalSquads": squad_uuids},
            timeout=timeout,
        )

    async def _bulk_post(self, path: str, user_ids: list[int], extra: dict[str, Any]) -> None:
        if not user_ids:
            return
        timeout = httpx.Timeout(60.0, connect=8.0)
        try:
            await self._request("POST", path, json={"userIds": user_ids, **extra}, timeout=timeout)
            return
        except RemnawaveError:
            pass
        await self._request(
            "POST",
            path,
            json={"uuids": [str(uid) for uid in user_ids], **extra},
            timeout=timeout,
        )

    async def bulk_extend_expiration(self, user_ids: list[int], days: int) -> None:
        if days < 1:
            return
        await self._bulk_post("/users/bulk/extend-expiration-date", user_ids, {"extendDays": int(days)})

    async def bulk_refresh_lease(self, user_ids: list[int], days: int = PANEL_LEASE_DAYS) -> None:
        expire = iso_expire(panel_lease_until(min_days=days))
        try:
            await self.bulk_update_users(user_ids, {"status": "ACTIVE", "expireAt": expire})
            return
        except RemnawaveError:
            pass
        await self.bulk_extend_expiration(user_ids, max(1, int(days)))
        try:
            await self.bulk_update_users(user_ids, {"status": "ACTIVE", "expireAt": expire})
        except RemnawaveError:
            try:
                await self.bulk_update_users(user_ids, {"status": "ACTIVE"})
            except RemnawaveError:
                pass

    async def bulk_update_users(self, user_ids: list[int], fields: dict[str, Any]) -> None:
        if not fields:
            return
        await self._bulk_post("/users/bulk/update", user_ids, {"fields": fields})

    async def update_user(self, user: dict, patch: dict[str, Any]) -> dict:
        body = dict(patch)
        if user.get("id") is not None:
            body["id"] = user["id"]
        if user.get("uuid"):
            body["uuid"] = user["uuid"]
        data = await self._request("PATCH", "/users", json=body)
        users = _as_users(data)
        return users[0] if users else body

    async def _user_action(self, user: dict, action: str) -> dict:
        uid = panel_user_key(user)
        numeric = user.get("id")
        idents: list[str] = []
        if uid:
            idents.append(str(uid))
        if numeric is not None and str(numeric).strip() not in idents:
            idents.append(str(numeric).strip())
        last: RemnawaveError | None = None
        for ident in idents:
            for path in (f"/users/{ident}/actions/{action}", f"/users/{ident}/{action}"):
                try:
                    data = await self._request("POST", path, json={})
                    users = _as_users(data)
                    return users[0] if users else user
                except RemnawaveError as exc:
                    last = exc
        if last:
            raise last
        raise RemnawaveError(f"Не удалось выполнить {action}")

    async def extend_panel_user(self, panel_user_id: int, days: int) -> dict:
        patch = {
            "expireAt": iso_expire(panel_lease_until(min_days=days)),
            "status": "ACTIVE",
        }
        try:
            return await self.update_user({"id": panel_user_id}, patch)
        except RemnawaveError:
            user = await self.get_user_by_id(panel_user_id)
            if not user:
                raise RemnawaveError("Устройство в панели не найдено")
            return await self.update_user(user, patch)

    async def enable_panel_user(self, panel_user_id: int) -> dict:
        user = await self.get_user_by_id(panel_user_id)
        if not user:
            raise RemnawaveError("Устройство в панели не найдено")
        try:
            user = await self._user_action(user, "enable")
        except RemnawaveError:
            user = await self.update_user(user, {"status": "ACTIVE"})
        return await self.update_user(
            user,
            {
                "status": "ACTIVE",
                "expireAt": iso_expire(panel_lease_until()),
            },
        )

    async def disable_panel_user(self, panel_user_id: int) -> None:
        user = {"id": panel_user_id}
        try:
            await self.update_user(user, {"status": "DISABLED"})
            return
        except RemnawaveError:
            pass
        try:
            await self._user_action(user, "disable")
        except RemnawaveError:
            pass

    async def delete_panel_user(self, panel_user_id: int) -> None:
        user = await self.get_user_by_id(panel_user_id)
        if not user:
            return
        uid = panel_user_key(user)
        if uid:
            try:
                await self._request("DELETE", f"/users/{uid}")
                return
            except RemnawaveError:
                pass
        await self.disable_panel_user(panel_user_id)

    async def extend_subscription(
        self,
        telegram_id: int,
        days: int,
        traffic_limit_gb: int | None = None,
        tag: str | None = None,
        create_if_missing: bool = True,
        panel_user_id: int | None = None,
    ) -> dict:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        user = None
        if panel_user_id is not None:
            user = await self.get_user_by_id(panel_user_id)
        if not user:
            user = await self.get_user_by_telegram(telegram_id)
        extra_days = timedelta(days=days)
        if user:
            current = parse_expire(user.get("expireAt"))
            base = current if current and current > now else now
            patch: dict[str, Any] = {
                "expireAt": iso_expire(base + extra_days),
                "status": "ACTIVE",
                "telegramId": telegram_id,
                "trafficLimitBytes": 0,
            }
            if settings.squad_uuids:
                patch["activeInternalSquads"] = settings.squad_uuids
            if tag:
                patch["tag"] = tag
            return await self.update_user(user, patch)
        if not create_if_missing:
            raise RemnawaveError("Пользователь в панели не найден")
        return await self.create_user(telegram_id, now + extra_days, 0, tag=tag)


def is_subscription_active(user: dict | None) -> bool:
    if not user:
        return False
    status = str(user.get("status") or "").upper()
    if status in {"DISABLED", "EXPIRED"}:
        return False
    expire = parse_expire(user.get("expireAt"))
    if expire and expire <= datetime.now(timezone.utc):
        return False
    return True


def days_remaining(user: dict | None) -> int:
    if not user:
        return 0
    expire = parse_expire(user.get("expireAt"))
    if not expire:
        return 0
    delta = expire - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds() // 86400))


async def fetch_user_diagnostics(rw: RemnawaveClient, user: dict) -> dict:
    uid = panel_user_key(user) or user.get("id")
    numeric = user.get("id")
    short = str(user.get("shortUuid") or "").strip()
    traffic = user.get("userTraffic") if isinstance(user.get("userTraffic"), dict) else {}
    node_uuid = str(
        traffic.get("lastConnectedNodeUuid")
        or user.get("lastConnectedNodeUuid")
        or ""
    ).strip()
    hwid = None
    bandwidth = None
    node = None
    sub = None
    if uid:
        hwid = await rw.safe_get(f"/hwid/devices/{uid}")
        if isinstance(hwid, dict) and hwid.get("_error") and numeric is not None:
            hwid = await rw.safe_get(f"/hwid/devices/{numeric}")
    if numeric is not None:
        bandwidth = await rw.safe_get(f"/bandwidth-stats/users/{numeric}")
        if isinstance(bandwidth, dict) and bandwidth.get("_error") and uid:
            bandwidth = await rw.safe_get(f"/bandwidth-stats/users/{uid}")
        sub = await rw.safe_get(f"/subscriptions/by-id/{numeric}")
    if isinstance(sub, dict) and sub.get("_error") and user.get("uuid"):
        sub = await rw.safe_get(f"/subscriptions/by-uuid/{user.get('uuid')}")
    if isinstance(sub, dict) and sub.get("_error") and short:
        sub = await rw.safe_get(f"/subscriptions/by-short-uuid/{short}")
    if node_uuid:
        node = await rw.safe_get(f"/nodes/{node_uuid}")
    return {
        "user": user,
        "hwid": hwid,
        "bandwidth": bandwidth,
        "node": node,
        "subscription": sub,
    }
