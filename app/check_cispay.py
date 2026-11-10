"""Проверка ключей CISPay: python -m app.check_cispay"""

from __future__ import annotations

import asyncio

from app.cispay import CISPayClient, CISPayError
from app.config import get_settings


async def _run() -> int:
    settings = get_settings()
    if not settings.cispay_configured:
        print("CISPAY_SHOP_ID или CISPAY_API_KEY пуст")
        return 1
    client = CISPayClient()
    try:
        data = await client.capabilities()
    except CISPayError as exc:
        print("Ключи не приняты:", exc)
        print("Нужны ID магазина (UUID) и секретный ключ cis_sec_... из «Настроек магазина».")
        return 1
    finally:
        await client.aclose()
    print("Магазин:", data.get("store_name"), "· активен" if data.get("is_active") else "· ВЫКЛЮЧЕН")
    for item in data.get("payment_methods") or []:
        fee = int(item.get("system_fee_percent") or 0) / 100
        print(f"  {item.get('payment_method')}: {'включён' if item.get('is_active') else 'выключен'}, комиссия {fee:g}%")
    print("Через CISPay идут:", ", ".join(sorted(settings.cispay_method_set)) or "ничего (CISPAY_METHODS)")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
