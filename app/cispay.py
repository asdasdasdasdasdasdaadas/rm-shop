"""CISPay (https://cispay.app/developers): SBP and crypto invoices on a hosted payment page.

Orders live in `rollypay_orders` next to the RollyPay ones, so every report, funnel and the
`rollypay:<order_id>` receipt key keep working; the CISPay transaction id is stored there as
`cis:<uuid>`, which is how `PaymentRouter` knows where to ask for the status.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import aiohttp
from rollypay.exceptions import RollyPayError

from app.config import get_settings

logger = logging.getLogger("rm-shop.cispay")

PREFIX = "cis:"
METHODS = {"sbp": "SBP", "crypto": "CRYPTO", "card": "CARD"}
# CISPay statuses in the words the rest of the shop already understands (see rollypay.payment_is_paid).
STATUSES = {"PENDING": "pending", "PAID": "paid", "FAILED": "failed", "EXPIRED": "expired", "REFUNDED": "refunded"}


class CISPayError(RollyPayError):
    """Raised for any CISPay failure; a RollyPayError so the existing checkout error handling applies."""


def is_cispay_payment(payment_id: str | None) -> bool:
    return str(payment_id or "").startswith(PREFIX)


def kopecks(amount_rub: Any) -> int:
    try:
        value = Decimal(str(amount_rub).replace(",", ".").replace(" ", ""))
    except InvalidOperation as exc:
        raise ValueError("Некорректная сумма") from exc
    result = int((value * 100).to_integral_value())
    if result <= 0:
        raise ValueError("Некорректная сумма")
    return result


def normalize(data: dict) -> dict:
    """The transaction with a lowercase status and our prefixed id, as the RollyPay payments look."""
    out = dict(data or {})
    out["provider_status"] = out.get("status")
    out["status"] = STATUSES.get(str(out.get("status") or "").upper(), str(out.get("status") or "").lower())
    if out.get("id"):
        out["payment_id"] = PREFIX + str(out["id"])
    if out.get("payment_url"):
        out["pay_url"] = out["payment_url"]
    return out


def _error_text(status: int, data: Any) -> str:
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, list):
        detail = "; ".join(str(item.get("msg") or item) for item in detail if item)
    return f"CISPay {status}: {detail or data or 'нет ответа'}"


class CISPayClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base = (settings.cispay_api_url or "https://api.cispay.app").rstrip("/")
        self._shop = settings.cispay_shop_id.strip()
        self._key = settings.cispay_api_key.strip()
        self._session: aiohttp.ClientSession | None = None
        if self._key and not self._key.startswith("cis_sec_"):
            logger.warning("CISPAY_API_KEY не похож на секретный ключ магазина (ожидается cis_sec_...)")

    async def aclose(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        headers = {"X-Shop-ID": self._shop, "X-Api-Key": self._key, "Accept": "application/json"}
        try:
            async with self._session.request(method, self._base + path, headers=headers, **kwargs) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = {"detail": (await resp.text())[:300]}
                if resp.status >= 400:
                    raise CISPayError(_error_text(resp.status, data))
                return data if isinstance(data, dict) else {}
        except aiohttp.ClientError as exc:
            raise CISPayError(f"CISPay недоступен: {exc}") from exc

    async def create_payment(self, *, amount_rub: str, order_id: str, description: str, customer_id: str,
                             metadata: dict | None = None, payment_method: str | None = None) -> dict:
        method = METHODS.get(str(payment_method or "sbp").lower())
        if not method:
            raise CISPayError("Этот способ оплаты не поддерживается CISPay")
        redirect = (get_settings().webapp_public_url or "").rstrip("/") or None
        try:
            amount = kopecks(amount_rub)
        except ValueError as exc:
            raise CISPayError(str(exc)) from exc
        body: dict[str, Any] = {
            "amount": amount,
            # Crypto in RUB: CISPay converts to USD at the Central Bank rate; card and SBP are RUB only.
            "currency": "RUB",
            "order_id": order_id,
            "payment_method": method,
            "customer_id": str(customer_id)[:40],
            "description": description[:512],
            "payload": str((metadata or {}).get("plan") or "")[:1024] or None,
        }
        if redirect:
            body["redirect_success_url"] = redirect
            body["redirect_fail_url"] = redirect
        logger.info("CISPay create order=%s method=%s amount=%s", order_id, method, body["amount"])
        result = normalize(await self._request("POST", "/payments", json={k: v for k, v in body.items() if v is not None}))
        if not result.get("pay_url"):
            raise CISPayError("CISPay не вернул ссылку на оплату")
        return result

    async def get_payment(self, payment_id: str) -> dict:
        raw = str(payment_id or "")
        raw = raw[len(PREFIX):] if raw.startswith(PREFIX) else raw
        return normalize(await self._request("GET", "/payments/status", params={"id": raw}))

    async def capabilities(self) -> dict:
        return await self._request("GET", "/store/capabilities")


def verify_webhook(body: bytes, signature: str, api_key: str) -> bool:
    """X-Signature is a hex HMAC-SHA256 of the raw body with the shop's API key."""
    if not body or not signature or not api_key:
        return False
    expected = hmac.new(api_key.strip().encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


class PaymentRouter:
    """One object for the checkout code: methods listed in CISPAY_METHODS go to CISPay, the rest to RollyPay.

    Status checks follow the stored payment id, so older RollyPay invoices still resolve after the switch."""

    def __init__(self, rollypay=None, cispay: CISPayClient | None = None) -> None:
        self.rollypay = rollypay
        self.cispay = cispay

    def provider_for(self, method: str | None) -> str | None:
        key = str(method or "sbp").lower()
        if self.cispay is not None and key in get_settings().cispay_method_set:
            return "cispay"
        if self.rollypay is not None:
            return "rollypay"
        return None

    async def create_payment(self, *, payment_method: str | None = None, **kwargs: Any) -> dict:
        provider = self.provider_for(payment_method)
        if provider == "cispay":
            return await self.cispay.create_payment(payment_method=payment_method, **kwargs)
        if provider == "rollypay":
            return await self.rollypay.create_payment(payment_method=payment_method, **kwargs)
        raise CISPayError("Оплата этим способом не настроена")

    async def get_payment(self, payment_id: str) -> dict:
        if is_cispay_payment(payment_id):
            if self.cispay is None:
                raise CISPayError("CISPay не настроен")
            return await self.cispay.get_payment(payment_id)
        if self.rollypay is None:
            raise CISPayError("RollyPay не настроен")
        return await self.rollypay.get_payment(payment_id)

    async def terminal_id(self) -> str:
        if self.rollypay is None:
            raise RuntimeError("RollyPay не настроен")
        return await self.rollypay.terminal_id()

    async def aclose(self) -> None:
        for client in (self.rollypay, self.cispay):
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    logger.debug("Клиент оплаты не закрылся", exc_info=True)
