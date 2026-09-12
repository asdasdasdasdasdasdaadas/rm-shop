from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import uuid
from typing import Any

from rollypay import RollyPayClient as SdkClient
from rollypay.exceptions import RollyPayError

from app.config import get_settings

logger = logging.getLogger("rm-shop.rollypay")

__all__ = [
    "RollyPayClient",
    "RollyPayError",
    "payment_is_paid",
    "resolve_payment_method",
    "verify_webhook",
]


def payment_is_paid(payment: dict | None) -> bool:
    status = str((payment or {}).get("status") or "").lower()
    return status in {"paid", "succeeded"}


_CRYPTO_METHODS = frozenset({"usdt", "btc", "eth", "ton", "crypto"})
_FIAT_METHODS = frozenset({"sbp", "card", "fiat"})


def _fiat_method(raw: str) -> str | None:
    method = str(raw or "").strip().lower()
    if not method or method == "fiat":
        return None
    if method in _CRYPTO_METHODS:
        return None
    if method in {"sbp", "card"}:
        return method
    return None


def resolve_payment_method(choice: str | None = None) -> str | None:
    raw = str(choice or "").strip().lower()
    if raw in _CRYPTO_METHODS:
        raise ValueError("Оплата криптой недоступна")
    picked = _fiat_method(raw)
    if picked:
        return picked
    if raw and raw not in _FIAT_METHODS:
        raise ValueError("Неизвестный способ оплаты")
    configured = _fiat_method(get_settings().rollypay_payment_method)
    if str(get_settings().rollypay_payment_method or "").strip().lower() in _CRYPTO_METHODS:
        logger.warning("ROLLYPAY_PAYMENT_METHOD указывает на крипту — касса откроет карту или СБП")
    return configured


def _clean_key(raw: str) -> str:
    key = (raw or "").replace("\ufeff", "").replace("\r", "").strip()
    key = key.strip('"').strip("'")
    if " #" in key:
        key = key.split(" #", 1)[0].strip()
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
        key = _clean_key(settings.rollypay_api_key)
        base = _sdk_base_url(settings.rollypay_api_url)
        prefix = key[:8] if len(key) >= 8 else key
        logger.info("RollyPay SDK %s ключ длина=%s начало=%s", base, len(key), prefix)
        if key and not key.startswith(("rpk_live_", "rpk_test_")):
            logger.warning(
                "ROLLYPAY_API_KEY не похож на ключ кассы (ожидается rpk_live_... или rpk_test_...). "
                "Не подставляйте signing_secret. В Docker символ $ в ключе пишите как $$"
            )
        sdk = SdkClient(api_key=key, base_url=base, timeout=30)
        orig = sdk.request

        def request_with_nonce(method: str, path: str, **kwargs: Any) -> Any:
            headers = dict(kwargs.pop("headers", {}) or {})
            headers["X-Nonce"] = str(uuid.uuid4())
            return orig(method, path, headers=headers, **kwargs)

        sdk.request = request_with_nonce  # type: ignore[method-assign]
        self._sdk = sdk
        self._live_key = key.startswith("rpk_live_")

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
        payment_method: str | None,
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
        method = _fiat_method(payment_method)
        if method:
            payload["payment_method"] = method
        redirect = (settings.webapp_public_url or "").rstrip("/")
        if redirect:
            payload["redirect_url"] = redirect
            payload["success_redirect_url"] = redirect
        if settings.rollypay_test and self._live_key:
            logger.warning(
                "ROLLYPAY_TEST=true пропущен: ключ rpk_live_. Иначе страница оплаты "
                "открывается, а активация карты и СБП отвечает 400"
            )
        elif settings.rollypay_test:
            payload["test"] = True
        if not payload.get("metadata"):
            payload.pop("metadata", None)
        return payload

    async def create_payment(
        self,
        *,
        amount_rub: str,
        order_id: str,
        description: str,
        customer_id: str,
        metadata: dict | None = None,
        payment_method: str | None = None,
    ) -> dict:
        payload = self._payload(
            amount_rub=amount_rub,
            order_id=order_id,
            description=description,
            customer_id=customer_id,
            metadata=metadata,
            payment_method=payment_method,
        )
        logger.info(
            "RollyPay create order=%s method=%s amount=%s test=%s",
            order_id,
            payload.get("payment_method") or "default",
            amount_rub,
            bool(payload.get("test")),
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
