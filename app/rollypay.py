from __future__ import annotations

import asyncio
import hashlib
import hmac
import uuid
from typing import Any

from rollypay import RollyPayClient as SdkClient
from rollypay.exceptions import RollyPayError

from app.config import get_settings

__all__ = ["RollyPayClient", "RollyPayError", "payment_is_paid", "verify_webhook"]


def payment_is_paid(payment: dict | None) -> bool:
    status = str((payment or {}).get("status") or "").lower()
    return status in {"paid", "succeeded"}


def _clean_key(raw: str) -> str:
    key = (raw or "").strip().strip('"').strip("'")
    if key.lower().startswith("x-api-key:"):
        key = key.split(":", 1)[1].strip()
    return key


def _sdk_base_url(raw: str) -> str:
    base = (raw or "").strip().rstrip("/")
    if "api.rollypay.io" in base:
        return "https://rollypay.io/api/v1"
    if base.endswith("/api/v1"):
        return base
    return f"{base}/api/v1"


class RollyPayClient:
    """Официальный SDK https://docs.rollypay.io/sdk/ в async-обёртке."""

    def __init__(self) -> None:
        settings = get_settings()
        sdk = SdkClient(
            api_key=_clean_key(settings.rollypay_api_key),
            base_url=_sdk_base_url(settings.rollypay_api_url),
            timeout=30,
        )
        orig = sdk.request

        def request_with_nonce(method: str, path: str, **kwargs: Any) -> Any:
            headers = dict(kwargs.pop("headers", {}) or {})
            headers["X-Nonce"] = str(uuid.uuid4())
            return orig(method, path, headers=headers, **kwargs)

        sdk.request = request_with_nonce  # type: ignore[method-assign]
        self._sdk = sdk

    async def aclose(self) -> None:
        await asyncio.to_thread(self._sdk._session.close)

    def _payload(
        self,
        *,
        amount_rub: str,
        order_id: str,
        description: str,
        customer_id: str,
        metadata: dict | None,
    ) -> dict[str, Any]:
        settings = get_settings()
        payload: dict[str, Any] = {
            "amount": amount_rub,
            "order_id": order_id,
            "payment_currency": "RUB",
            "description": description,
            "customer_id": customer_id,
            "metadata": metadata or {},
        }
        method = (settings.rollypay_payment_method or "").strip()
        if method:
            payload["payment_method"] = method
        redirect = (settings.webapp_public_url or "").rstrip("/")
        if redirect:
            payload["redirect_url"] = redirect
            payload["success_redirect_url"] = redirect
        if settings.rollypay_test:
            payload["test"] = True
        return payload

    async def create_payment(
        self,
        *,
        amount_rub: str,
        order_id: str,
        description: str,
        customer_id: str,
        metadata: dict | None = None,
    ) -> dict:
        payload = self._payload(
            amount_rub=amount_rub,
            order_id=order_id,
            description=description,
            customer_id=customer_id,
            metadata=metadata,
        )

        def _create() -> dict:
            if payload.get("test"):
                data = self._sdk.request("POST", "payments", json=payload)
            else:
                data = self._sdk.payments.create(
                    amount=payload["amount"],
                    order_id=payload["order_id"],
                    payment_currency=payload["payment_currency"],
                    payment_method=payload.get("payment_method"),
                    description=payload.get("description"),
                    customer_id=payload.get("customer_id"),
                    redirect_url=payload.get("redirect_url"),
                    success_redirect_url=payload.get("success_redirect_url"),
                    metadata=payload.get("metadata"),
                )
            return data if isinstance(data, dict) else {}

        return await asyncio.to_thread(_create)

    async def get_payment(self, payment_id: str) -> dict:
        def _get() -> dict:
            data = self._sdk.payments.get(payment_id)
            return data if isinstance(data, dict) else {}

        return await asyncio.to_thread(_get)


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
