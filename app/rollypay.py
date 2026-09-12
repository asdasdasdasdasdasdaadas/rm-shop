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

PAY_HOST = "https://pay.rollypay.io/pay"


def payment_is_paid(payment: dict | None) -> bool:
    status = str((payment or {}).get("status") or "").lower()
    return status in {"paid", "succeeded"}


_CRYPTO_METHODS = frozenset({"usdt", "btc", "eth", "ton", "crypto"})
_FIAT_METHODS = frozenset({"sbp", "card", "fiat"})


def resolve_payment_method(choice: str | None = None) -> str | None:
    raw = str(choice or "").strip().lower()
    if raw in _CRYPTO_METHODS:
        raise ValueError("Оплата криптой недоступна")
    if raw and raw not in _FIAT_METHODS:
        raise ValueError("Неизвестный способ оплаты")
    return "sbp"


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


def _pay_url(data: dict) -> str:
    url = str(data.get("pay_url") or "").strip()
    if url:
        return url
    token = str(data.get("token") or "").strip()
    if token:
        return f"{PAY_HOST}/{token}"
    return ""


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
        settings = get_settings()
        method = "sbp"
        redirect = (settings.webapp_public_url or "").rstrip("/") or None
        sandbox = bool(settings.rollypay_test) and not self._live_key
        if settings.rollypay_test and self._live_key:
            logger.warning(
                "ROLLYPAY_TEST=true пропущен: ключ rpk_live_. Иначе страница оплаты "
                "открывается, а активация QR СБП отвечает 400"
            )
        logger.info(
            "RollyPay create order=%s method=%s amount=%s test=%s",
            order_id,
            method,
            amount_rub,
            sandbox,
        )

        def _create() -> dict:
            if sandbox:
                body: dict[str, Any] = {
                    "amount": amount_rub,
                    "order_id": order_id,
                    "payment_currency": "RUB",
                    "payment_method": method,
                    "description": description,
                    "customer_id": customer_id,
                    "test": True,
                }
                if redirect:
                    body["redirect_url"] = redirect
                    body["success_redirect_url"] = redirect
                if metadata:
                    body["metadata"] = metadata
                data = self._sdk.request("POST", "payments", json=body)
            else:
                data = self._sdk.payments.create(
                    amount=amount_rub,
                    order_id=order_id,
                    payment_currency="RUB",
                    payment_method=method,
                    description=description,
                    customer_id=customer_id,
                    redirect_url=redirect,
                    success_redirect_url=redirect,
                    metadata=metadata or None,
                )
            result = data if isinstance(data, dict) else {}
            url = _pay_url(result)
            if url:
                result["pay_url"] = url
            return result

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
