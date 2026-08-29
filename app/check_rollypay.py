"""Проверка ключа кассы: python -m app.check_rollypay"""

from __future__ import annotations

from rollypay.exceptions import AuthenticationError, RollyPayError

from app.config import get_settings
from app.rollypay import RollyPayClient


def main() -> None:
    settings = get_settings()
    if not settings.rollypay_configured:
        print("ROLLYPAY_API_KEY пуст")
        raise SystemExit(1)
    client = RollyPayClient()
    try:
        data = client._sdk.terminals.list()
    except AuthenticationError as exc:
        print("401 invalid api key. Касса ключ не приняла.")
        print(exc)
        print("Нужен api_key вида rpk_live_... из настроек кассы, не signing_secret.")
        print("В .env без кавычек. Если в ключе есть $, в Docker Compose пишите $$ вместо $.")
        print("После правки: docker compose up -d --force-recreate bot")
        raise SystemExit(1) from exc
    except RollyPayError as exc:
        print("Ошибка API:", exc)
        raise SystemExit(1) from exc
    n = len(data) if isinstance(data, list) else 1
    print("Ключ принят. Касс:", n)


if __name__ == "__main__":
    main()
