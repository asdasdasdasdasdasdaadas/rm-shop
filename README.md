# RM Shop

Telegram-бот магазина VPN на [Remnawave](https://docs.rw/). Пользователь проходит канал и оферту, нажимает «Попробовать бесплатно» или покупает подписку через RollyPay. Срок и ссылка подключения создаются в панели Remnawave. Данные пользователей хранятся в PostgreSQL.

Бот ходит в Telegram через long polling. HTTP-сервер на порту 8080 отдаёт health-check, вебхук оплаты, веб-админку и (на деплое) Mini App.

## Содержание

- [Что умеет](#что-умеет)
- [Поднять бота серией команд](#поднять-бота-серией-команд)
- [Сценарий пользователя](#сценарий-пользователя)
- [Рефералка](#рефералка)
- [Оплата](#оплата)
- [Админка](#админка)
- [Mini App](#mini-app)
- [Требования](#требования)
- [Переменные окружения](#переменные-окружения)
- [Локальный запуск без Docker (бот)](#локальный-запуск-без-docker-бот)
- [Деплой: HTTPS, касса, обновление](#деплой-https-касса-обновление)
- [Прокси HTTPS](#прокси-https)
- [RollyPay на проде](#rollypay-на-проде)
- [Структура проекта](#структура-проекта)
- [Эксплуатация](#эксплуатация)
- [Типичные проблемы](#типичные-проблемы)

## Что умеет

1. Обязательная подписка на канал и принятие оферты / политики по ссылкам.
2. Профиль: «Попробовать бесплатно», покупка, реферальная ссылка, «Моя подписка», «Подключиться», «VPN не работает».
3. Создание и продление пользователя в Remnawave (username `tg{telegram_id}`), выдача `subscriptionUrl`.
4. Оплата тарифов 1 / 3 / 6 / 12 месяцев через RollyPay (вебхук + кнопка «Проверить оплату»).
5. Рефералка: пригласивший получает дни после того, как друг нажмёт «Попробовать бесплатно»; другу добавляются дни к бесплатному периоду.
6. Жалоба «VPN не работает» пишется в БД и уходит в Telegram админам из `ADMIN_IDS`.
7. Веб-админка: пользователи, начисление дней, сброс бесплатного периода, сообщения, оплаты, жалобы, рассылка.
8. Опциональный личный кабинет (Telegram Mini App) по HTTPS.

Режим `BALANCE_ENABLED=true` включает баланс в днях и устройства вместо одной общей подписки. По умолчанию выключен.

## Поднять бота серией команд

Поднимается всё нужное: PostgreSQL, HTTP (health, админка, вебхук), сам бот. Docker обязателен.

Перед запуском: токен у [@BotFather](https://t.me/BotFather), бот — админ канала, API Token и UUID сквада в Remnawave, ссылки на оферту и политику.

### 1. Чистый Ubuntu-сервер (Docker + проект)

Сначала Docker. После `usermod` **выйдите из SSH и зайдите снова**, иначе не будет прав на Docker.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
exit
```

Зайдите на сервер ещё раз.

```bash
git clone https://github.com/asdasdasdasdasdasdaadas/rm-shop.git rm-shop
cd rm-shop
cp .env.example .env
nano .env
```

В `.env` обязательно заполните: `BOT_TOKEN`, `BOT_USERNAME`, `REQUIRED_CHANNEL_ID`, `REQUIRED_CHANNEL_URL`, `REMNAWAVE_BASE_URL`, `REMNAWAVE_TOKEN`, `LEGAL_OFFER_URL`, `LEGAL_PRIVACY_URL`. Имеет смысл сразу задать `ADMIN_PASSWORD`, `ADMIN_IDS`, `REMNAWAVE_SQUAD_UUIDS`, `POSTGRES_PASSWORD`.

Дальше одна команда: скрипт соберёт образы, поднимет Postgres и бота, проверит `/health`.

```bash
chmod +x scripts/up.sh
./scripts/up.sh
```

Или те же шаги вручную:

```bash
docker compose up -d --build
curl -s http://127.0.0.1:8080/health
docker compose ps
docker compose logs -f bot
```

Ожидается `{"ok": true}`. Админка: `http://127.0.0.1:8080/admin`.

### 2. Репозиторий уже на машине, Docker стоит

```bash
cd rm-shop
cp -n .env.example .env
nano .env
chmod +x scripts/up.sh
./scripts/up.sh
```

`cp -n` не перезапишет существующий `.env`.

### 3. Полезные команды после запуска

```bash
docker compose logs -f bot
docker compose ps
curl -s http://127.0.0.1:8080/health
docker compose restart bot
docker compose down
```

`docker compose down -v` удалит том Postgres (пользователи и заказы пропадут).

Обновление кода:

```bash
git pull
./scripts/up.sh
```

Порты `8080` и `5432` слушают только `127.0.0.1`. Снаружи нужны 80/443 и прокси, см. [Прокси HTTPS](#прокси-https). Mini App и вебхук RollyPay без HTTPS с интернета не заработают.

## Сценарий пользователя

1. `/start` — проверка подписки на канал (`REQUIRED_CHANNEL_ID`). Бот должен быть администратором канала.
2. Ссылки на оферту и политику, кнопка «Принимаю».
3. Профиль. «Попробовать бесплатно» создаёт или продлевает пользователя в панели на `TRIAL_DAYS` (плюс бонус, если пришёл по рефссылке).
4. «Купить подписку» открывает счёт RollyPay. После оплаты срок продлевается, пользователю уходит сообщение со ссылкой.
5. «Подключиться» / «Моя подписка» показывают актуальный срок из панели (с кэшем `PANEL_SYNC_TTL`). Фон ещё раз сверяет всех по `PANEL_SYNC_INTERVAL`.

Deep-link: `https://t.me/<BOT_USERNAME>?start=ref_<telegram_id>`.

## Рефералка

Срабатывает **не при регистрации**, а когда друг нажимает **«Попробовать бесплатно»**.

| Кто | Что получает | Переменная | По умолчанию |
| --- | --- | --- | --- |
| Пригласивший | дни подписки (или на баланс, если `BALANCE_ENABLED`) | `REFERRAL_REWARD_DAYS` | 7 |
| Друг по ссылке | плюс к бесплатному периоду | `REFERRAL_INVITEE_DAYS` | 5 |

Пример: бесплатно 3 дня, друг по ссылке получает 8 дней, пригласивший — 7. Один друг — одна награда (`referral_rewarded` в БД). Если панель не смогла продлить пригласившему, флаг сбрасывается.

## Оплата

Касса: [RollyPay](https://docs.rollypay.io), платежи через официальный Python SDK ([SDK](https://docs.rollypay.io/sdk/), пакет `rollypay`): `payments.create` и `payments.get`. Вебхук `POST /webhooks/rollypay`.

Подпись вебхука: заголовки `X-Timestamp` и `X-Signature` (HMAC-SHA256 от `timestamp + "." + raw_body` с `ROLLYPAY_SIGNING_SECRET`).

На кассе укажите callback:

`https://<ваш-домен>/webhooks/rollypay`

`ROLLYPAY_TEST=true` — тестовые платежи. Перед продом поставьте `false`.

Telegram Stars (`STARS_ENABLED`) по умолчанию выключены.

## Админка

- URL: `http://127.0.0.1:8080/admin` локально или `https://<домен>/admin` на сервере.
- Пароль: `ADMIN_PASSWORD`. Пустой пароль — вход невозможен.
- В боте команда `/admin` работает только для ID из `ADMIN_IDS` и присылает ссылку.
- Cookie сессии HttpOnly. Флаг Secure включается, если `WEBAPP_PUBLIC_URL` начинается с `https://`.

Возможности: обзор, пользователи (начислить дни, сброс бесплатного периода, личное сообщение), заказы RollyPay, жалобы VPN, рассылка, просмотр настроек без секретов.

## Mini App

Telegram открывает Web App только по **HTTPS**. Локально кабинет обычно выключен (`WEBAPP_ENABLED=false`). На деплое:

```
WEBAPP_ENABLED=true
WEBAPP_PUBLIC_URL=https://lk.example.com
```

После старта у бота появляется кнопка меню «Кабинет». Кабинет ходит в `/api/me`, бесплатный период, оплату, промо, жалобу VPN.

## Требования

- Docker и Docker Compose (рекомендуемый запуск: [серия команд](#поднять-бота-серией-команд)).
- `curl` (его ставит блок установки Docker на Ubuntu).
- Либо Python 3.12, PostgreSQL 16, зависимости из `requirements.txt`.
- Бот от [@BotFather](https://t.me/BotFather).
- Бот — администратор обязательного канала.
- API Token и UUID Internal Squad в Remnawave.
- Публичный HTTPS-домен, если нужны Mini App и вебхук RollyPay.
- Исходящий доступ с сервера до `api.telegram.org` и панели Remnawave.

Схема БД применяется при старте из `app/schema.sql` (`CREATE TABLE IF NOT EXISTS`). Отдельные миграции не нужны.

## Переменные окружения

Скопируйте пример и заполните:

```bash
cp .env.example .env
```

Файл `.env` в git не попадает. В Docker Compose `DATABASE_URL` из `.env` для контейнера бота **перезаписывается** на хост `postgres` внутри сети Compose. Для этого задайте `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. Пароль лучше без символов `@ : / #`.

### Обязательные

| Ключ | Смысл |
| --- | --- |
| `BOT_TOKEN` | Токен от BotFather |
| `BOT_USERNAME` | Username бота без `@` |
| `REQUIRED_CHANNEL_ID` | `@channel` или `-100...` |
| `REQUIRED_CHANNEL_URL` | Ссылка «Подписаться» |
| `REMNAWAVE_BASE_URL` | URL панели без суффикса `/api` |
| `REMNAWAVE_TOKEN` | API Token панели |
| `LEGAL_OFFER_URL` | Ссылка на оферту |
| `LEGAL_PRIVACY_URL` | Ссылка на политику |

### Рекомендуемые на проде

| Ключ | Смысл |
| --- | --- |
| `ADMIN_PASSWORD` | Пароль `/admin` |
| `ADMIN_IDS` | Telegram ID админов через запятую (жалобы VPN, `/admin` в боте) |
| `REMNAWAVE_SQUAD_UUIDS` | UUID Internal Squads через запятую |
| `POSTGRES_PASSWORD` | Пароль БД, не оставляйте `rmshop` |
| `ROLLYPAY_API_KEY` | Ключ кассы |
| `ROLLYPAY_SIGNING_SECRET` | Секрет подписи вебхука |
| `ROLLYPAY_TEST` | `false` на боевых платежах |
| `WEBAPP_ENABLED` | `true` если нужен кабинет |
| `WEBAPP_PUBLIC_URL` | `https://...` без слэша в конце |

### Остальные (есть значения по умолчанию)

| Ключ | По умолчанию | Смысл |
| --- | --- | --- |
| `BRAND_NAME` | `RM Shop` | Название бота и сервиса: приветствие, кабинет, имя в Telegram |
| `SUPPORT_USERNAME` | `@support` | Поддержка в кабинете |
| `TRIAL_ENABLED` | `true` | Кнопка «Попробовать бесплатно» |
| `TRIAL_DAYS` | `3` | Сколько дней даётся бесплатно |
| `REFERRAL_REWARD_DAYS` | `7` | Награда пригласившему |
| `REFERRAL_INVITEE_DAYS` | `5` | Бонус другу к бесплатному периоду |
| `PLAN_*_RUB` | см. `.env.example` | Цены тарифов |
| `STARS_ENABLED` | `false` | Оплата Stars |
| `ROLLYPAY_API_URL` | `https://rollypay.io` | API кассы (не `api.rollypay.io`) |
| `ROLLYPAY_PAYMENT_METHOD` | пусто | `sbp` / `card` или выбор на форме |
| `BALANCE_ENABLED` | `false` | Баланс дней + устройства |
| `PROMO_ENABLED` | `true` | Промокоды |
| `PROMO_CODES` | `TEST:3` | `КОД:дни`, несколько через запятую |
| `REMNAWAVE_HWID_LIMIT` | `1` | Лимит устройств, `0` — без лимита |
| `REMNAWAVE_TRAFFIC_LIMIT_GB` | `0` | `0` — безлимит |
| `REMNAWAVE_TRAFFIC_STRATEGY` | `NO_RESET` | Стратегия трафика в панели |
| `WEBAPP_HOST` | `0.0.0.0` | Адрес HTTP внутри контейнера |
| `WEBAPP_PORT` | `8080` | Порт HTTP |
| `PANEL_SYNC_TTL` | `60` | Кэш карточки панели, сек |
| `PANEL_SYNC_INTERVAL` | `600` | Фоновая сверка, `0` — выкл |
| `VPN_REPORT_COOLDOWN_SEC` | `900` | Кулдаун жалобы VPN |

## Локальный запуск без Docker (бот)

Postgres всё равно в Docker. Бот — на хосте, если так удобнее отлаживать:

```bash
cd rm-shop
cp -n .env.example .env
nano .env
docker compose up -d postgres
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app
```

В `.env` оставьте `DATABASE_URL=postgresql://...@127.0.0.1:5432/...` с тем же паролем, что `POSTGRES_PASSWORD`.

## Деплой: HTTPS, касса, обновление

Сначала поднимите стек [серией команд](#поднять-бота-серией-команд). На боевом сервере в `.env`:

- смените `POSTGRES_PASSWORD` и `ADMIN_PASSWORD`;
- задайте `ADMIN_IDS`;
- ключи RollyPay и `ROLLYPAY_TEST=false`;
- для кабинета: `WEBAPP_ENABLED=true` и `WEBAPP_PUBLIC_URL=https://ваш-домен`.

Потом:

1. HTTPS на `127.0.0.1:8080` ([Прокси HTTPS](#прокси-https)).
2. В кассе RollyPay: `https://ваш-домен/webhooks/rollypay`.
3. В BotFather URL Mini App = `WEBAPP_PUBLIC_URL`.
4. Бот — администратор канала. Проверьте `/start` с другого аккаунта.

Данные Postgres в volume `pgdata`. При старте в лог пишутся предупреждения: пустой `ADMIN_PASSWORD`, Mini App без HTTPS, тестовый RollyPay, пароль БД по умолчанию.

## Прокси HTTPS

Шаблоны: `deploy/Caddyfile` и `deploy/nginx.conf.example`. Подставьте свой домен.

Caddy (сам выпускает сертификат):

```bash
# в deploy/Caddyfile замените lk.example.com
caddy run --config deploy/Caddyfile
```

Nginx: скопируйте пример, положите сертификаты Let's Encrypt, `nginx -t && systemctl reload nginx`.

Проксируйте на `http://127.0.0.1:8080`. Нужны пути:

| Путь | Назначение |
| --- | --- |
| `/health` | проверка живости |
| `/webhooks/rollypay` | оплата |
| `/admin` | админка |
| `/` и `/api/*` | Mini App, если включён |

Firewall: снаружи 80 и 443. Порты 8080 и 5432 с интернета закрыть.

## RollyPay на проде

1. Боевые ключи, `ROLLYPAY_TEST=false`.
2. Callback HTTPS, тот же хост, что у прокси.
3. Проверьте тестовый платёж, затем боевой на малую сумму.
4. Если вебхук не доходит (локалка без HTTPS), в боте остаётся «Проверить оплату» — на проде вебхук должен отрабатывать сам.

## Структура проекта

```
app/            бот, HTTP, БД, Remnawave, RollyPay, рефералка, админка API
app/schema.sql  схема PostgreSQL
webapp/         Mini App (статика)
admin/          веб-админка (статика)
legal/          запасные локальные тексты, если понадобятся файлы
deploy/         примеры Caddy и nginx
docker-compose.yml
scripts/up.sh   проверка .env, сборка, Postgres, бот, /health
Dockerfile
.env.example
```

Точка входа: `python -m app` (`app/__main__.py`).

## Эксплуатация

- Пользователь в панели: `tg{telegram_id}`.
- Фоновая сверка раз в `PANEL_SYNC_INTERVAL` секунд тянет сроки из Remnawave в таблицу `users`.
- Жалоба VPN: не чаще чем раз в `VPN_REPORT_COOLDOWN_SEC`. Нужны непустые `ADMIN_IDS`, иначе в Telegram никто не получит алерт (запись в БД всё равно будет).
- Рассылка и сообщения из админки идут от имени бота.

## Типичные проблемы

**Бот не стартует, ошибка подключения к Postgres.** Поднимите `docker compose up -d postgres`. Для `python -m app` в `DATABASE_URL` должен быть `127.0.0.1`. В контейнере бота хост всегда `postgres`.

**«Сначала подпишитесь на канал», хотя подписка есть.** Бот не админ канала или неверный `REQUIRED_CHANNEL_ID`.

**«Попробовать бесплатно» / оплата: ошибка Remnawave.** Проверьте `REMNAWAVE_BASE_URL` (без `/api`), токен, UUID сквада, доступ с сервера до панели.

**Mini App чёрный экран / не открывается.** Нет HTTPS или `WEBAPP_PUBLIC_URL` не совпадает с доменом в BotFather.

**Вебхук 403.** Неверный `ROLLYPAY_SIGNING_SECRET` или касса стучится не на тот URL.

**Админка не пускает.** Задайте `ADMIN_PASSWORD` и перезапустите контейнер.

**Рефералка не начислила.** Друг должен зайти по `?start=ref_...` (ссылка ставится только при первой записи в БД) и нажать «Попробовать бесплатно». Повтор за того же друга не начисляется.
