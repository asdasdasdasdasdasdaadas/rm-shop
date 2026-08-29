#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Нужна команда: $1"
    exit 1
  }
}

env_val() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env 2>/dev/null | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return
  fi
  local raw="${line#*=}"
  raw="${raw%%#*}"
  raw="$(printf '%s' "$raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  printf '%s' "$raw"
}

need docker
need curl
docker compose version >/dev/null 2>&1 || {
  echo "Нужен Docker Compose (плагин: docker compose)"
  exit 1
}

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Создан файл .env из .env.example."
  echo "Заполните обязательные поля и запустите снова: $0"
  exit 1
fi

missing=0
for key in BOT_TOKEN BOT_USERNAME REQUIRED_CHANNEL_ID REQUIRED_CHANNEL_URL \
  REMNAWAVE_BASE_URL REMNAWAVE_TOKEN LEGAL_OFFER_URL LEGAL_PRIVACY_URL; do
  val="$(env_val "$key")"
  if [[ -z "$val" ]]; then
    echo "В .env не заполнено: $key"
    missing=1
    continue
  fi
  case "$key:$val" in
    BOT_USERNAME:your_bot|\
    REQUIRED_CHANNEL_ID:@your_channel|\
    REQUIRED_CHANNEL_URL:https://t.me/your_channel|\
    REMNAWAVE_BASE_URL:https://panel.example.com|\
    LEGAL_OFFER_URL:https://example.com/offer|\
    LEGAL_PRIVACY_URL:https://example.com/privacy)
      echo "В .env всё ещё пример: $key=$val"
      missing=1
      ;;
  esac
done
if [[ "$missing" -ne 0 ]]; then
  echo "Исправьте .env и запустите снова."
  exit 1
fi

docker compose up -d --build

echo "Жду HTTP..."
ok=0
for _ in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8080/health >/dev/null; then
    ok=1
    break
  fi
  sleep 1
done

if [[ "$ok" -ne 1 ]]; then
  echo "Бот не ответил на http://127.0.0.1:8080/health"
  docker compose logs --tail 80 bot
  exit 1
fi

echo "Готово. Сервис: $(env_val BRAND_NAME)  @$(env_val BOT_USERNAME)"
echo "Health: http://127.0.0.1:8080/health"
echo "Админка: http://127.0.0.1:8080/admin"
echo "Логи: docker compose logs -f bot"
