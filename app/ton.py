"""Balance top-ups in TON through the chat widget and Telegram's built-in wallet.

Flow: the widget asks for an order (`t:<rub>`, with the user's wallet), the bot
answers with a TON Connect transaction to the shop wallet whose comment is the
order id, the wallet sends it, the widget reports `p:<order>`, and the bot finds
the transfer on chain through Toncenter and credits the balance. The hash the
widget reports is never trusted: only a transfer seen on chain is credited, and
each order is credited once (payment key `ton:<order>`).

The shop wallet is only an address: no keys are kept on the server.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import math
import re
import secrets
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.ton")

NANO = 10**9
QUOTE_SECONDS = 10 * 60
AMOUNT_RE = re.compile(r"^\s*(\d{1,6}(?:[.,]\d{1,9})?)\s*(?:ton|тон|gram|грам)?\s*$", re.IGNORECASE)
ASK_SECONDS = 15 * 60
MIN_NANO = 1_000_000  # 0.001 TON
ORDER_RE = re.compile(r"^VPN-[A-Z2-9]{6}$")
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TONCENTER = "https://toncenter.com/api/v3"


# ---------- addresses ----------

def _crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def _friendly(workchain: int, account: bytes, *, bounceable: bool = False) -> str:
    body = bytes([0x11 if bounceable else 0x51, workchain & 0xFF]) + account
    return base64.urlsafe_b64encode(body + _crc16(body).to_bytes(2, "big")).decode()


def parse_address(value: str) -> tuple[int, bytes]:
    """(workchain, 32-byte account) from a raw `0:hex` or a user-friendly address; ValueError otherwise."""
    text = str(value or "").strip()
    if ":" in text:
        wc, _, hex_part = text.partition(":")
        try:
            account = bytes.fromhex(hex_part)
            workchain = int(wc)
        except ValueError:
            raise ValueError("Неверный адрес TON") from None
        if len(account) != 32 or workchain not in (0, -1):
            raise ValueError("Неверный адрес TON")
        return workchain, account
    if len(text) != 48:
        raise ValueError("Неверный адрес TON: нужен адрес из 48 символов")
    try:
        raw = base64.urlsafe_b64decode(text.replace("+", "-").replace("/", "_"))
    except (ValueError, TypeError):
        raise ValueError("Неверный адрес TON") from None
    if len(raw) != 36 or _crc16(raw[:34]) != int.from_bytes(raw[34:], "big"):
        raise ValueError("Неверный адрес TON: не сходится контрольная сумма")
    if raw[0] & 0x80:
        raise ValueError("Это адрес тестовой сети TON")
    workchain = raw[1] - 256 if raw[1] > 127 else raw[1]
    return workchain, raw[2:34]


def normalize_wallet(value: str) -> str:
    """The shop wallet as a non-bounceable user-friendly address (UQ…): the form wallets expect for payments."""
    workchain, account = parse_address(value)
    return _friendly(workchain, account, bounceable=False)


def same_address(a: str | None, b: str | None) -> bool:
    try:
        return parse_address(a or "") == parse_address(b or "")
    except ValueError:
        return False


# ---------- transfer comment as a TON Connect payload ----------

def _crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x82F63B78 if crc & 1 else crc >> 1
    return crc ^ 0xFFFFFFFF


def comment_payload(text: str) -> str:
    """Base64 BoC of one cell: 32 zero bits (text comment op) and the UTF-8 text."""
    data = b"\x00\x00\x00\x00" + text.encode()
    if len(data) > 127:
        raise ValueError("comment is too long for one cell")
    cell = bytes([0, 2 * len(data)]) + data
    boc = b"\xb5\xee\x9c\x72" + bytes([0x41, 1, 1, 1, 0, len(cell), 0]) + cell
    return base64.b64encode(boc + _crc32c(boc).to_bytes(4, "little")).decode()


def comment_from_boc(body: str | None) -> str | None:
    """Text comment from a message body BoC when the API didn't decode it: op 0 and UTF-8 in the root cell."""
    try:
        raw = base64.b64decode(body or "")
        if raw[:4] != b"\xb5\xee\x9c\x72":
            return None
        flags, off = raw[4], raw[5]
        size = flags & 7
        pos = 6
        cells = int.from_bytes(raw[pos:pos + size], "big")
        roots = int.from_bytes(raw[pos + size:pos + 2 * size], "big")
        pos += 3 * size + off + roots * size
        if flags & 0x80:
            pos += cells * off
        d1, d2 = raw[pos], raw[pos + 1]
        data = raw[pos + 2:pos + 2 + (d2 + 1) // 2]
        if d2 % 2:
            data = data.rstrip(b"\x00")[:-1] if data.rstrip(b"\x00") else data
        if d1 & 7 or data[:4] != b"\x00\x00\x00\x00":
            return None
        return data[4:].decode("utf-8")
    except (ValueError, IndexError, UnicodeDecodeError):
        return None


# ---------- rate ----------

_rate_cache: tuple[float, Decimal] | None = None


async def _fetch_rate(client: httpx.AsyncClient) -> Decimal:
    try:
        r = await client.get("https://api.coingecko.com/api/v3/simple/price",
                             params={"ids": "the-open-network", "vs_currencies": "rub"})
        r.raise_for_status()
        value = r.json()["the-open-network"]["rub"]
        if value:
            return Decimal(str(value))
    except Exception:
        logger.warning("CoinGecko не отдал курс TON, пробуем tonapi", exc_info=True)
    r = await client.get("https://tonapi.io/v2/rates", params={"tokens": "ton", "currencies": "rub"})
    r.raise_for_status()
    return Decimal(str(r.json()["rates"]["TON"]["prices"]["RUB"]))


async def rub_per_ton() -> Decimal:
    """Market price of 1 TON in rubles, cached for a minute."""
    global _rate_cache
    now = time.monotonic()
    if _rate_cache and now - _rate_cache[0] < 60:
        return _rate_cache[1]
    async with httpx.AsyncClient(timeout=8) as client:
        rate = await _fetch_rate(client)
    if rate <= 0:
        raise ValueError("bad TON rate")
    _rate_cache = (now, rate)
    return rate


def quote_nano(rub: int, rate: Decimal, margin_pct: float) -> int:
    """TON for `rub` at `rate` plus the margin, rounded up to 0.001 TON."""
    ton = Decimal(rub) / rate * (Decimal(1) + Decimal(str(margin_pct)) / 100)
    return math.ceil(ton * 1000) * 10**6


def credited_rub(order: dict, paid_nano: int) -> int:
    """Rubles for what actually arrived, at the order's locked price; never more than paid for."""
    return int(int(order["rub"]) * int(paid_nano) // int(order["nano"]))


# ---------- settings ----------

def configured() -> bool:
    return bool(get_settings().ton_wallet)


def enabled() -> bool:
    """Open to every user: the admin switch is on and a wallet is set."""
    return bool(get_settings().ton_enabled and configured())


def allowed(telegram_id: int) -> bool:
    """Admins can test payments with the switch still off."""
    return enabled() or (configured() and int(telegram_id) in get_settings().admin_id_set)


def parse_amount(text: str | None) -> int | None:
    """Nanotons from what the user typed: «2.5», «2,5», «3 TON». None if it isn't an amount."""
    m = AMOUNT_RE.match(text or "")
    if not m:
        return None
    nano = int(Decimal(m.group(1).replace(",", ".")) * NANO)
    return nano if nano > 0 else None


def rub_for_nano(nano: int, rate: Decimal, margin_pct: float) -> int:
    """Rubles credited for `nano` at `rate` minus the margin, rounded down."""
    rub = Decimal(int(nano)) / NANO * rate / (Decimal(1) + Decimal(str(margin_pct)) / 100)
    return int(rub)


def ton_text(nano: int) -> str:
    """2500000000 → «2,5»."""
    text = f"{Decimal(int(nano)) / NANO:.9f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def limits_nano(rate: Decimal) -> tuple[int, int]:
    """Smallest and largest TON amount for one payment, in nanotons."""
    s = get_settings()
    margin = Decimal(1) + Decimal(str(s.ton_rate_margin_pct)) / 100
    high = int(Decimal(int(s.balance_topup_max or 100000)) * margin / rate * 1000) * 10**6
    return MIN_NANO, max(MIN_NANO, high)


def check_amount(nano: int, rate: Decimal) -> int:
    """Rubles for the amount, or ValueError with a message the user can act on.
    The balance is whole rubles, so a tiny payment (from 0.001 TON) still gives 1 ₽."""
    s = get_settings()
    low, high = limits_nano(rate)
    if nano < low:
        raise ValueError(f"Минимум {ton_text(low)} TON")
    rub = rub_for_nano(nano, rate, s.ton_rate_margin_pct)
    if rub > int(s.balance_topup_max or 100000):
        raise ValueError(f"Максимум {ton_text(high)} TON за раз")
    return max(1, rub)


# ---------- orders ----------

def _new_order_id() -> str:
    return "VPN-" + "".join(secrets.choice(_ALPHABET) for _ in range(6))


async def create_order(telegram_id: int, nano: int, *, chat_id: int | None, message_id: int | None) -> dict:
    """An order for exactly `nano` TON; the ruble amount is locked at the current rate."""
    if not allowed(telegram_id):
        raise ValueError("Оплата в TON выключена")
    rate = await rub_per_ton()
    nano = int(nano)
    rub = check_amount(nano, rate)
    valid_until = int(time.time()) + QUOTE_SECONDS
    for _ in range(5):
        order_id = _new_order_id()
        row = await db._pool_req().fetchrow(
            """INSERT INTO ton_orders (order_id, telegram_id, rub, nano, rate_rub, valid_until, chat_id, message_id)
               VALUES ($1,$2,$3,$4,$5,to_timestamp($6),$7,$8) ON CONFLICT (order_id) DO NOTHING RETURNING *""",
            order_id, int(telegram_id), int(rub), nano, rate, valid_until, chat_id, message_id,
        )
        if row:
            return dict(row)
    raise RuntimeError("could not allocate a TON order id")


def transaction(order: dict) -> dict:
    """TON Connect sendTransaction request for the order."""
    return {
        "valid_until": int(order["valid_until"].timestamp()) if isinstance(order["valid_until"], datetime)
        else int(order["valid_until"]),
        "messages": [{
            "address": get_settings().ton_wallet,
            "amount": str(int(order["nano"])),
            "payload": comment_payload(order["order_id"]),
        }],
    }


async def get_order(order_id: str) -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM ton_orders WHERE order_id=$1", order_id)
    return dict(row) if row else None


async def mark_sent(order_id: str, telegram_id: int, *, sender: str | None, msg_hash: str | None) -> dict | None:
    row = await db._pool_req().fetchrow(
        """UPDATE ton_orders SET status = CASE WHEN status='paid' THEN status ELSE 'sent' END,
               sent_at=COALESCE(sent_at, NOW()), sender=COALESCE($3, sender), msg_hash=COALESCE($4, msg_hash)
           WHERE order_id=$1 AND telegram_id=$2 RETURNING *""",
        order_id, int(telegram_id), sender, msg_hash,
    )
    return dict(row) if row else None


async def expire_stale() -> int:
    """Orders nobody paid: unsent ones an hour after the quote ran out, sent ones after a day."""
    result = await db._pool_req().execute(
        """UPDATE ton_orders SET status='expired'
           WHERE (status='pending' AND valid_until < NOW() - INTERVAL '1 hour')
              OR (status='sent' AND sent_at < NOW() - INTERVAL '1 day')"""
    )
    try:
        return int(str(result).split()[-1])
    except (ValueError, IndexError):
        return 0


async def has_open_orders() -> bool:
    return bool(await db._pool_req().fetchval(
        "SELECT EXISTS (SELECT 1 FROM ton_orders WHERE status IN ('pending','sent') AND created_at > NOW() - INTERVAL '1 day')"))


# ---------- chain ----------

def parse_incoming(tx: dict) -> dict | None:
    """An incoming transfer from a Toncenter v3 transaction, or None for anything else."""
    msg = tx.get("in_msg") or {}
    source = msg.get("source")
    try:
        value = int(msg.get("value") or 0)
    except (TypeError, ValueError):
        value = 0
    description = tx.get("description") or {}
    if not source or value <= 0 or msg.get("bounced") or description.get("aborted"):
        return None
    content = msg.get("message_content") or {}
    decoded = content.get("decoded") or {}
    comment = decoded.get("comment") if decoded.get("type") == "text_comment" else None
    if comment is None and content.get("body"):
        comment = comment_from_boc(content.get("body"))
    return {
        "tx_hash": str(tx.get("hash") or ""),
        "sender": str(source),
        "nano": value,
        "comment": (str(comment).strip() if comment else None),
        "utime": int(tx.get("now") or 0),
    }


async def fetch_transactions(limit: int = 50) -> list[dict]:
    s = get_settings()
    headers = {"X-API-Key": s.toncenter_api_key} if s.toncenter_api_key else {}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        r = await client.get(f"{TONCENTER}/transactions",
                             params={"account": s.ton_wallet, "limit": limit, "offset": 0, "sort": "desc"})
        r.raise_for_status()
        return list(r.json().get("transactions") or [])


_scan_lock = asyncio.Lock()
_last_scan = 0.0


async def scan(*, rw=None, bot=None, min_interval: float = 3.0) -> int:
    """Look at recent transfers to the shop wallet and credit matching orders. Returns how many were credited."""
    global _last_scan
    if not configured():
        return 0
    async with _scan_lock:
        if time.monotonic() - _last_scan < min_interval:
            return 0
        _last_scan = time.monotonic()
        credited = 0
        for tx in await fetch_transactions():
            incoming = parse_incoming(tx)
            if not incoming or not incoming["tx_hash"]:
                continue
            if await _handle_incoming(incoming, rw=rw, bot=bot):
                credited += 1
        return credited


MIN_UNMATCHED_NANO = 10_000_000  # 0.01 TON: smaller transfers without an order are spam


async def _handle_incoming(incoming: dict, *, rw=None, bot=None) -> bool:
    pool = db._pool_req()
    comment = (incoming["comment"] or "").upper()
    order = await get_order(comment) if ORDER_RE.match(comment) else None
    if not order:
        # The wallet may be used for other things too: only list transfers that could be a missed payment.
        if incoming["nano"] < MIN_UNMATCHED_NANO:
            return False
        first = await pool.fetchval("SELECT EXTRACT(EPOCH FROM MIN(created_at))::bigint FROM ton_orders")
        if not first or incoming["utime"] < int(first):
            return False
    await pool.execute(
        """INSERT INTO ton_incoming (tx_hash, sender, nano, comment, order_id, utime)
           VALUES ($1,$2,$3,$4,$5,to_timestamp($6)) ON CONFLICT (tx_hash) DO NOTHING""",
        incoming["tx_hash"], incoming["sender"], incoming["nano"], incoming["comment"],
        order["order_id"] if order else None, incoming["utime"],
    )
    if not order or order["status"] == "paid":
        return False
    return await credit(order, incoming, rw=rw, bot=bot)


async def credit(order: dict, incoming: dict, *, rw=None, bot=None) -> bool:
    amount = credited_rub(order, incoming["nano"])
    if amount < 1:
        logger.warning("TON %s: пришло слишком мало (%s нано)", order["order_id"], incoming["nano"])
        return False
    # Claim the transfer for this order first: a second scan or a reused hash can't credit twice.
    claimed = await db._pool_req().fetchval(
        """UPDATE ton_orders SET tx_hash=$2, paid_nano=$3, sender=COALESCE(sender, $4)
           WHERE order_id=$1 AND status <> 'paid' AND (tx_hash IS NULL OR tx_hash=$2) RETURNING order_id""",
        order["order_id"], incoming["tx_hash"], incoming["nano"], incoming["sender"],
    )
    if not claimed:
        return False
    receipt = await db.credit_payment_once(int(order["telegram_id"]), "ton", f"ton:{order['order_id']}", amount)
    if receipt is None:
        return False
    from app.billing import after_credit
    await after_credit(receipt, rw or _rw, bot or _bot, amount=amount, title=f"{amount} ₽ в TON")
    await notify_widget_paid(order, amount)
    logger.info("TON %s: зачислено %s ₽", order["order_id"], amount)
    return True


# ---------- widget ----------

_rw = None
_bot = None


def _state(nano: int, rub: int, *, waiting: str | None = None, paid: dict | None = None) -> dict[str, Any]:
    """Widget data: n — TON to send (nano), c — rubles it gives, w — order waiting for the chain, ok — credited."""
    state: dict[str, Any] = {"n": int(nano), "c": int(rub)}
    if waiting:
        state["w"] = waiting
    if paid:
        state["ok"] = paid
    return state


async def notify_widget_paid(order: dict, amount: int) -> None:
    bot = _bot
    if not bot or not order.get("chat_id") or not order.get("message_id"):
        return
    from app.widgets import EditMessageWidgetData, _json
    user = await db.get_user(int(order["telegram_id"]))
    paid = {"o": order["order_id"], "c": amount, "b": int((user or {}).get("balance_rub") or 0)}
    try:
        await bot(EditMessageWidgetData(chat_id=int(order["chat_id"]), message_id=int(order["message_id"]),
                                        chat_data=_json(_state(order["nano"], order["rub"], paid=paid))))
    except Exception:
        logger.debug("Виджет оплаты TON не обновлён", exc_info=True)


async def handle_query(bot, query: dict[str, Any], user_id: int, data: str) -> dict[str, Any]:
    """Requests from the payment widget: t:<nano> make an order, p:<order> wallet sent it, q:<order> status."""
    kind, _, arg = data.partition(":")
    qtype = query.get("type") or {}
    chat_id = (query.get("chat") or {}).get("id")
    message_id = query.get("message_id")
    if kind == "t":
        if not arg.isdigit() or not 0 < int(arg) < 10**16:
            return {"e": "Неверная сумма"}
        try:
            order = await create_order(user_id, int(arg), chat_id=chat_id, message_id=message_id)
        except ValueError as exc:
            return {"e": str(exc)}
        except Exception:
            logger.exception("Счёт TON не создан")
            return {"e": "Курс TON недоступен, попробуйте позже"}
        return {"o": order["order_id"], "n": int(order["nano"]), "c": int(order["rub"]), "tx": transaction(order)}
    order = await get_order(arg.upper()) if ORDER_RE.match(arg.upper()) else None
    if not order or int(order["telegram_id"]) != user_id:
        return {"e": "Счёт не найден"}
    if kind == "p":
        wallet = qtype.get("wallet") or {}
        order = await mark_sent(order["order_id"], user_id, sender=wallet.get("address"),
                                msg_hash=qtype.get("msg_hash")) or order
        if chat_id and message_id:
            from app.widgets import EditMessageWidgetData, _json
            try:
                await bot(EditMessageWidgetData(chat_id=int(chat_id), message_id=int(message_id),
                                                chat_data=_json(_state(order["nano"], order["rub"],
                                                                       waiting=order["order_id"]))))
            except Exception:
                logger.debug("Состояние ожидания TON не записано", exc_info=True)
        watch(order["order_id"])
        return {"w": order["order_id"]}
    if kind == "q":
        if order["status"] in ("pending", "sent"):
            try:
                await asyncio.wait_for(scan(), timeout=10)
            except Exception:
                logger.debug("Проверка TON по запросу не удалась", exc_info=True)
            order = await get_order(order["order_id"]) or order
        if order["status"] == "paid":
            user = await db.get_user(user_id)
            return {"ok": {"o": order["order_id"], "c": int(order["credited_rub"] or 0),
                           "b": int((user or {}).get("balance_rub") or 0)}}
        return {"st": order["status"]}
    return {"e": "Неизвестный запрос"}


_watchers: dict[str, asyncio.Task] = {}


def watch(order_id: str, *, seconds: int = 180) -> None:
    """Poll the chain for a few minutes after the wallet reports a sent transfer."""
    if order_id in _watchers and not _watchers[order_id].done():
        return

    async def run() -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            await asyncio.sleep(4)
            try:
                await scan()
            except Exception:
                logger.debug("Проверка TON не удалась", exc_info=True)
            order = await get_order(order_id)
            if not order or order["status"] == "paid":
                return
    _watchers[order_id] = asyncio.create_task(run(), name=f"ton-watch-{order_id}")


async def ton_watch_loop(rw, bot) -> None:
    """Credit transfers that arrived while nobody was watching: closed chat, lost connection, restart."""
    global _rw, _bot
    _rw, _bot = rw, bot
    while True:
        await asyncio.sleep(60)
        if not configured():
            continue
        try:
            await expire_stale()
            if await has_open_orders():
                await scan(min_interval=30)
        except Exception:
            logger.exception("Фоновая проверка TON не удалась")


# Who was asked «Сколько TON отправить?» and when: their next number is the amount.
_asked: dict[int, float] = {}


def awaiting_amount(telegram_id: int) -> bool:
    asked = _asked.get(int(telegram_id))
    return bool(asked and time.monotonic() - asked < ASK_SECONDS)


async def ask_amount(bot, telegram_id: int, *, rub: int | None = None):
    """Ask how much TON to send; the reply goes to `amount_reply`."""
    from aiogram.types import ForceReply
    if not allowed(telegram_id):
        raise ValueError("Оплата в TON выключена")
    lines = ["<b>Сколько TON отправить?</b>", "Напишите число, например <code>2,5</code>."]
    try:
        rate = await rub_per_ton()
        margin = Decimal(1) + Decimal(str(get_settings().ton_rate_margin_pct)) / 100
        low, _ = limits_nano(rate)
        lines.append(f"Курс: 1 TON ≈ {int(rate / margin)} ₽ на баланс. Минимум {ton_text(low)} TON.")
        if rub:
            lines.append(f"Для {rub} ₽ — примерно {ton_text(quote_nano(rub, rate, get_settings().ton_rate_margin_pct))} TON.")
    except Exception:
        logger.debug("Курс TON для подсказки не получен", exc_info=True)
    _asked[int(telegram_id)] = time.monotonic()
    return await bot.send_message(telegram_id, "\n".join(lines), parse_mode="HTML",
                                  reply_markup=ForceReply(input_field_placeholder="Например, 2,5"))


async def amount_reply(bot, telegram_id: int, text: str) -> str | None:
    """Send the payment card for the typed amount. Returns an error to show, or None when the card is out."""
    nano = parse_amount(text)
    if nano is None:
        return "Не понял сумму. Напишите число, например 2,5"
    try:
        rate = await rub_per_ton()
    except Exception:
        logger.warning("Курс TON недоступен", exc_info=True)
        return "Курс TON сейчас недоступен, попробуйте через минуту"
    try:
        rub = check_amount(nano, rate)
    except ValueError as exc:
        return str(exc)
    _asked.pop(int(telegram_id), None)
    await send_pay_widget(bot, telegram_id, nano=nano, rub=rub)
    return None


async def send_pay_widget(bot, telegram_id: int, *, nano: int, rub: int):
    from app.widgets import SendWidget, _json, ton_pay_html
    if not allowed(telegram_id):
        raise ValueError("Оплата в TON выключена")
    return await bot(SendWidget(
        chat_id=telegram_id, html=ton_pay_html(), chat_data=_json(_state(nano, rub)),
        caption=f"Перевод {ton_text(nano)} TON → ≈ {rub} ₽ на баланс. Курс фиксируется в момент оплаты.",
        allow_queries=True,
    ))


async def admin_list(limit: int = 100) -> dict:
    pool = db._pool_req()
    orders = await pool.fetch(
        """SELECT o.*, u.username, u.first_name FROM ton_orders o LEFT JOIN users u ON u.telegram_id=o.telegram_id
           WHERE o.status IN ('paid','sent') OR o.created_at > NOW() - INTERVAL '1 day'
           ORDER BY o.created_at DESC LIMIT $1""", int(limit))
    unmatched = await pool.fetch(
        "SELECT * FROM ton_incoming WHERE order_id IS NULL ORDER BY seen_at DESC LIMIT $1", int(limit))
    paid = await pool.fetchrow(
        """SELECT COUNT(*)::int AS n, COALESCE(SUM(credited_rub),0)::int AS rub, COALESCE(SUM(paid_nano),0)::bigint AS nano
           FROM ton_orders WHERE status='paid'""")

    def clean(row) -> dict:
        out = {}
        for key, value in dict(row).items():
            if isinstance(value, datetime):
                value = value.astimezone(timezone.utc).isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            out[key] = value
        return out

    return {
        "enabled": enabled(),
        "wallet": get_settings().ton_wallet,
        "paid": clean(paid) if paid else {"n": 0, "rub": 0, "nano": 0},
        "orders": [clean(r) for r in orders],
        "unmatched": [clean(r) for r in unmatched],
    }
