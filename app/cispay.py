"""CISPay (https://cispay.app/developers): the shop's payment provider for SBP, cards and crypto.

Orders are kept in `pay_orders` and receipts under `order:<order_id>`. The CISPay transaction id is
stored with the `cis:` prefix; an id without it belongs to the old provider and can no longer be checked.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import aiohttp
from app.config import get_settings

logger = logging.getLogger("rm-shop.cispay")

PREFIX = "cis:"
METHODS = {"sbp": "SBP", "crypto": "CRYPTO", "card": "CARD"}
# CISPay statuses in the lowercase words the checkout, reminders and «Проверить оплату» use.
STATUSES = {"PENDING": "pending", "PAID": "paid", "FAILED": "failed", "EXPIRED": "expired", "REFUNDED": "refunded"}


class CISPayError(Exception):
    """Any CISPay failure: no connection, a refused request or an unusable answer."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


def payment_is_paid(payment: dict | None) -> bool:
    status = str((payment or {}).get("status") or "").lower()
    return status in {"paid", "succeeded"}


def resolve_payment_method(choice: str | None = None) -> str:
    """Our method id from the cabinet or a bot button; an empty choice means SBP."""
    raw = str(choice or "").strip().lower()
    if not raw or raw == "fiat":
        return "sbp"
    if raw in {"sbp", "card", "crypto", "stars"}:
        return raw
    if raw in {"usdt", "btc", "eth", "ton"}:
        raise ValueError("Выберите способ оплаты crypto; валюту и сеть выбирают на странице оплаты")
    raise ValueError("Неизвестный способ оплаты")


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


def bot_link() -> str | None:
    """https://t.me/<bot>: where the payment page sends the buyer back; None until BOT_USERNAME is set."""
    handle = (get_settings().bot_username or "").strip().lstrip("@")
    return f"https://t.me/{handle}" if handle and handle != "your_bot" else None


def normalize(data: dict) -> dict:
    """The transaction with a lowercase status, our prefixed id and the page link as «pay_url»."""
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
        if method and str(payment_method or "sbp").lower() not in get_settings().cispay_method_set:
            method = None
        if not method:
            raise CISPayError("Этот способ оплаты не поддерживается CISPay")
        redirect = bot_link()
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
            # After paying, and after a failed attempt, the buyer goes straight back to the chat with the bot.
            body["redirect_success_url"] = redirect
            body["redirect_fail_url"] = redirect
        logger.info("CISPay create order=%s method=%s amount=%s", order_id, method, body["amount"])
        result = normalize(await self._request("POST", "/payments", json={k: v for k, v in body.items() if v is not None}))
        if not result.get("pay_url"):
            raise CISPayError("CISPay не вернул ссылку на оплату")
        return result

    async def get_payment(self, payment_id: str) -> dict:
        raw = str(payment_id or "")
        if not raw.startswith(PREFIX):
            raise CISPayError("Счёт выставлен прежней кассой, его статус больше не проверить")
        return normalize(await self._request("GET", "/payments/status", params={"id": raw[len(PREFIX):]}))

    async def capabilities(self) -> dict:
        return await self._request("GET", "/store/capabilities")


def verify_webhook(body: bytes, signature: str, api_key: str) -> bool:
    """X-Signature is a hex HMAC-SHA256 of the raw body with the shop's API key."""
    if not body or not signature or not api_key:
        return False
    expected = hmac.new(api_key.strip().encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())

