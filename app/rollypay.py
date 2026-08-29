from __future__ import annotations

import hmac
import hashlib
import uuid
from typing import Any

import httpx

from app.config import get_settings


class RollyPayError(RuntimeError):
    pass


class RollyPayClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base = settings.rollypay_api_url.rstrip("/")
        key = (settings.rollypay_api_key or "").strip().strip('"').strip("'")
        if key.lower().startswith("x-api-key:"):
            key = key.split(":", 1)[1].strip()
        self.api_key = key
        self._http = httpx.AsyncClient(timeout=20)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        headers = dict(kwargs.pop("headers", {}))
        headers["X-API-Key"] = self.api_key
        headers["X-Nonce"] = str(uuid.uuid4())
        headers.setdefault("Content-Type", "application/json")
        url = f"{self.base}{path}"
        response = await self._http.request(method, url, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise RollyPayError(f"{method} {path} → {response.status_code}: {response.text[:400]}")
        if not response.content:
            return None
        return response.json()

    async def create_payment(
        self,
        *,
        amount_rub: str,
        order_id: str,
        description: str,
        customer_id: str,
        metadata: dict | None = None,
    ) -> dict:
        settings = get_settings()
        payload: dict[str, Any] = {
            "amount": amount_rub,
            "payment_currency": "RUB",
            "order_id": order_id,
            "description": description,
            "customer_id": customer_id,
            "metadata": metadata or {},
        }
        if settings.rollypay_test:
            payload["test"] = True
        if settings.rollypay_payment_method:
            payload["payment_method"] = settings.rollypay_payment_method
        data = await self._request("POST", "/api/v1/payments", json=payload)
        return data if isinstance(data, dict) else {}

    async def get_payment(self, payment_id: str) -> dict:
        data = await self._request("GET", f"/api/v1/payments/{payment_id}")
        return data if isinstance(data, dict) else {}


def verify_webhook(body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    if not timestamp or not signature or not secret:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + body,
        hashlib.sha256,
    ).hexdigest()
    try:
        return hmac.compare_digest(expected, signature.strip().lower())
    except Exception:
        return False
