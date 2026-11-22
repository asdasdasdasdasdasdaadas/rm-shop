"""Xray logs from the VPN nodes, for the devices we watch: why someone connects but gets no traffic.

Each node runs deploy/node-logs/ship.py. Once a minute it asks the bot which xray users to watch
(GET /webhooks/node-logs/watch): new devices and those flagged «подключился, но трафика нет». It tails
xray's access and error logs and sends here only the lines of those users (POST /webhooks/node-logs), plus
error lines from their IP addresses. The bot keeps KEEP_HOURS of them and reads them as a diagnosis:
the device never reached the node, its key is refused, connections open and break at once, or traffic flows.
Both requests carry «Authorization: Bearer <NODE_LOGS_TOKEN>».
"""
from __future__ import annotations

import hmac
import logging
import re
from datetime import datetime, timedelta, timezone

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.node-logs")

KEEP_HOURS = 72
WATCH_HOURS = 72          # a new device is watched this long, and a «no traffic» one since its alert
MAX_LINES = 500           # one POST
_cleaned_at: datetime | None = None
NAME_LOOKUPS = 30         # panel lookups per watch request, for devices whose xray name is not known yet

# 2026/11/22 17:30:01.123456 from 1.2.3.4:51234 accepted tcp:www.google.com:443 [IN >> DIRECT] email: tg1_iphone
_TS = r"(?P<ts>\d{4}/\d\d/\d\d \d\d:\d\d:\d\d(?:\.\d+)?)"
ACCESS = re.compile(_TS + r" from (?:tcp:|udp:)?\[?(?P<ip>[0-9a-fA-F.:]+?)\]?:\d+ (?P<verdict>accepted|rejected)\s+"
                    r"(?P<dest>\S+)?(?:.*?email: (?P<email>\S+))?")
IP_IN_TEXT = re.compile(r"(?:from |remote )(?:tcp:|udp:)?\[?(\d{1,3}(?:\.\d{1,3}){3}|[0-9a-fA-F:]{4,})\]?:\d+")
ERROR_KINDS = (
    ("reality", re.compile(r"REALITY: processed invalid connection|reality.*(?:invalid|failed)", re.I)),
    ("handshake", re.compile(r"handshake|tls: |first record does not look like", re.I)),
    ("refused", re.compile(r"invalid request user id|not found user|user .*expired|invalid user", re.I)),
    ("ends", re.compile(r"connection ends|connection reset|broken pipe|closed pipe|EOF|i/o timeout|context canceled", re.I)),
)
KIND_LABELS = {"accepted": "соединение принято", "rejected": "отклонено нодой", "reality": "Reality не прошёл",
               "handshake": "рукопожатие не прошло", "refused": "ключ не принят", "ends": "соединение оборвалось",
               "other": "ошибка"}


def token_ok(header: str | None) -> bool:
    want = str(get_settings().node_logs_token or "").strip()
    got = str(header or "").removeprefix("Bearer ").strip()
    return bool(want) and hmac.compare_digest(want.encode(), got.encode())


def _when(ts: str | None, fallback: datetime) -> datetime:
    """xray writes the node's local time without a zone; nodes run in UTC (the docker default)."""
    if not ts:
        return fallback
    try:
        return datetime.strptime(ts[:19], "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return fallback


def parse(line: str, source: str, now: datetime) -> dict | None:
    """One xray line → {at, ip, email, kind, dest}; None for lines that say nothing about a client."""
    line = str(line or "").strip()
    if not line:
        return None
    m = ACCESS.search(line) if source == "a" else None
    if m:
        kind = "accepted" if m["verdict"] == "accepted" else "rejected"
        if kind == "rejected":
            for key, rx in ERROR_KINDS:
                if key == "refused" and rx.search(line):
                    kind = "refused"
        return {"at": _when(m["ts"], now), "ip": m["ip"], "email": m["email"] or "", "kind": kind,
                "dest": (m["dest"] or "")[:200], "raw": line[:600]}
    ts = re.match(_TS, line)
    ip = IP_IN_TEXT.search(line)
    kind = next((key for key, rx in ERROR_KINDS if rx.search(line)), "other")
    if not ip and kind == "other":
        return None
    return {"at": _when(ts["ts"] if ts else None, now), "ip": ip.group(1) if ip else "", "email": "",
            "kind": kind, "dest": "", "raw": line[:600]}


async def watch_list(rw=None) -> list[str]:
    """The xray user names the nodes should send: numeric panel ids and, once known, panel usernames."""
    pool = db._pool_req()
    rows = await pool.fetch(
        f"""SELECT d.remnawave_id, n.username FROM devices d
            LEFT JOIN node_log_names n ON n.remnawave_id = d.remnawave_id
            WHERE d.remnawave_id IS NOT NULL AND COALESCE(d.kind, '') <> 'router'
              AND (d.created_at > NOW() - INTERVAL '{WATCH_HOURS} hours'
                   OR d.no_traffic_alert_at > NOW() - INTERVAL '{WATCH_HOURS} hours'
                   OR d.id IN (SELECT device_id FROM node_log_watch WHERE until_at > NOW()))""")
    names: list[str] = []
    missing = []
    for r in rows:
        names.append(str(r["remnawave_id"]))
        if r["username"]:
            names.append(str(r["username"]))
        else:
            missing.append(int(r["remnawave_id"]))
    if rw is not None:
        for panel_id in missing[:NAME_LOOKUPS]:
            try:
                panel = await rw.get_user_by_id(panel_id)
            except Exception:
                logger.debug("Имя в панели не получено для %s", panel_id, exc_info=True)
                continue
            uname = str((panel or {}).get("username") or "").strip()
            if uname:
                await pool.execute("""INSERT INTO node_log_names (remnawave_id, username) VALUES ($1, $2)
                                      ON CONFLICT (remnawave_id) DO UPDATE SET username = EXCLUDED.username""",
                                   panel_id, uname)
                names.append(uname)
    return sorted(set(names))


async def _devices_by_email(emails: set[str]) -> dict[str, tuple[int, int]]:
    """xray user name → (device id, telegram id)."""
    if not emails:
        return {}
    ids = [int(e) for e in emails if e.isdigit()]
    rows = await db._pool_req().fetch(
        """SELECT d.id, d.telegram_id, d.remnawave_id::text AS pid, n.username FROM devices d
           LEFT JOIN node_log_names n ON n.remnawave_id = d.remnawave_id
           WHERE d.remnawave_id = ANY($1::bigint[]) OR n.username = ANY($2::text[])""",
        ids, sorted(emails))
    out: dict[str, tuple[int, int]] = {}
    for r in rows:
        for key in (r["pid"], r["username"]):
            if key:
                out[str(key)] = (int(r["id"]), int(r["telegram_id"]))
    return out


async def ingest(node: str, lines: list, now: datetime | None = None) -> int:
    """Store the lines a node sent. Error lines without a user get one by IP from that node's recent lines."""
    now = now or datetime.now(timezone.utc)
    node = str(node or "").strip()[:60] or "node"
    parsed = []
    for item in list(lines or [])[:MAX_LINES]:
        if isinstance(item, dict):
            got = parse(str(item.get("line") or ""), str(item.get("f") or "a"), now)
        else:
            got = parse(str(item), "a", now)
        if got:
            parsed.append(got)
    if not parsed:
        return 0
    by_email = await _devices_by_email({p["email"] for p in parsed if p["email"]})
    pool = db._pool_req()
    ips = sorted({p["ip"] for p in parsed if p["ip"] and not p["email"]})
    by_ip: dict[str, tuple[int, int]] = {}
    for p in parsed:   # this batch first, then what the node sent before
        if p["email"] in by_email and p["ip"]:
            by_ip[p["ip"]] = by_email[p["email"]]
    if ips:
        for r in await pool.fetch(
                """SELECT DISTINCT ON (ip) ip, device_id, telegram_id FROM node_log_lines
                   WHERE node = $1 AND ip = ANY($2::text[]) AND device_id IS NOT NULL
                     AND at > NOW() - INTERVAL '6 hours' ORDER BY ip, at DESC""", node, ips):
            by_ip.setdefault(r["ip"], (int(r["device_id"]), int(r["telegram_id"])))
    rows = []
    for p in parsed:
        dev = by_email.get(p["email"]) if p["email"] else by_ip.get(p["ip"])
        rows.append((node, p["at"], p["ip"], p["email"], dev[0] if dev else None, dev[1] if dev else None,
                     p["kind"], p["dest"], p["raw"]))
    cols = list(zip(*rows))
    await pool.execute(
        """INSERT INTO node_log_lines (node, at, ip, email, device_id, telegram_id, kind, dest, raw)
           SELECT $1, * FROM unnest($2::timestamptz[], $3::text[], $4::text[], $5::bigint[], $6::bigint[],
                                    $7::text[], $8::text[], $9::text[])""",
        node, *[list(c) for c in cols[1:]])
    global _cleaned_at
    if _cleaned_at is None or now - _cleaned_at > timedelta(minutes=10):
        _cleaned_at = now
        await pool.execute(f"DELETE FROM node_log_lines WHERE at < NOW() - INTERVAL '{KEEP_HOURS} hours'")
    return len(rows)


async def watch_device(device_id: int, hours: int = 24) -> None:
    await db._pool_req().execute(
        """INSERT INTO node_log_watch (device_id, until_at) VALUES ($1, NOW() + make_interval(hours => $2))
           ON CONFLICT (device_id) DO UPDATE SET until_at = EXCLUDED.until_at""", int(device_id), int(hours))


SUMMARY_SQL = """
SELECT node, kind, COUNT(*)::int AS n, COUNT(DISTINCT NULLIF(dest, ''))::int AS dests,
       COUNT(DISTINCT NULLIF(ip, ''))::int AS ips, MIN(at) AS first_at, MAX(at) AS last_at
FROM node_log_lines WHERE device_id = $1 AND at > $2::timestamptz GROUP BY node, kind
"""


def diagnose(rows: list[dict], *, enabled: bool = True) -> dict:
    """Counts per kind → {verdict, details}. The verdict is the likely reason in one line."""
    if not enabled:
        return {"verdict": "", "details": [], "seen": False}
    total: dict[str, int] = {}
    nodes, dests = set(), 0
    for r in rows:
        total[r["kind"]] = total.get(r["kind"], 0) + int(r["n"])
        nodes.add(r["node"])
        if r["kind"] == "accepted":
            dests += int(r["dests"])
    ok, ends = total.get("accepted", 0), total.get("ends", 0)
    tls = total.get("reality", 0) + total.get("handshake", 0)
    refused = total.get("refused", 0) + total.get("rejected", 0)
    if not total:
        verdict = ("До ноды не дошло ни одного соединения: провайдер не пускает к серверу (IP или порт) "
                   "или приложение так и не подключилось")
    elif refused and not ok:
        verdict = "Нода не принимает ключ: устройство выключено, ключ устарел или приложение взяло старую подписку"
    elif tls and not ok:
        verdict = "Соединение доходит, но рукопожатие не проходит — похоже, провайдер режет протокол (DPI)"
    elif ok and ends >= max(3, ok // 2) and dests <= 5:
        verdict = "Соединения открываются и сразу рвутся — похоже на блокировку после рукопожатия"
    elif ok and dests > 5:
        verdict = "Через ноду идут запросы к сайтам — VPN работает, трафик ещё не дошёл до статистики"
    elif ok:
        verdict = "Соединения есть, но сайтов почти не открывали — возможно, VPN включили и не пользовались"
    else:
        verdict = "В логах только ошибки — смотрите строки ниже"
    details = [f"{KIND_LABELS.get(k, k)}: {v}" for k, v in sorted(total.items(), key=lambda kv: -kv[1])]
    if dests:
        details.append(f"разных адресов: {dests}")
    if nodes:
        details.append("ноды: " + ", ".join(sorted(nodes)))
    return {"verdict": verdict, "details": details, "seen": bool(total)}


def shipping() -> bool:
    """Logs are expected only once a token is set (and the nodes are told to send them)."""
    return bool(str(get_settings().node_logs_token or "").strip())


async def device_summary(device_id: int, hours: int = 6) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = [dict(r) for r in await db._pool_req().fetch(SUMMARY_SQL, int(device_id), since)]
    out = diagnose(rows, enabled=shipping())
    if out["verdict"] and not out["seen"] and not await db._pool_req().fetchval(
            "SELECT EXISTS (SELECT 1 FROM node_log_lines WHERE at > NOW() - INTERVAL '1 hour')"):
        out = {"verdict": "С нод больше часа не приходят логи — проверьте сборщик на нодах", "details": [], "seen": False}
    return out


async def user_view(telegram_id: int) -> dict:
    """The admin's «Логи ноды»: a verdict per device and the latest lines."""
    devices = await db._pool_req().fetch(
        """SELECT d.id, d.title, d.platform, d.client, (w.until_at > NOW()) AS watched FROM devices d
           LEFT JOIN node_log_watch w ON w.device_id = d.id
           WHERE d.telegram_id = $1 AND COALESCE(d.kind, '') <> 'router' ORDER BY d.id""", int(telegram_id))
    items = []
    for d in devices:
        items.append({"id": int(d["id"]), "title": d["title"] or "без названия",
                      "app": " · ".join(x for x in (d["platform"], d["client"]) if x), "watched": bool(d["watched"]),
                      **await device_summary(int(d["id"]), hours=24)})
    return {"enabled": shipping(), "devices": items, "lines": await user_lines(telegram_id)}


async def user_lines(telegram_id: int, limit: int = 200) -> list[dict]:
    from app import ip_isp
    rows = await db._pool_req().fetch(
        """SELECT l.at, l.node, l.ip, l.kind, l.dest, l.raw, l.device_id, d.title FROM node_log_lines l
           LEFT JOIN devices d ON d.id = l.device_id
           WHERE l.telegram_id = $1 ORDER BY l.at DESC, l.id DESC LIMIT $2""", int(telegram_id), int(limit))
    out = []
    for r in rows:
        at = r["at"]
        out.append({"at": at.isoformat() if hasattr(at, "isoformat") else str(at), "node": r["node"], "ip": r["ip"],
                    "isp": ip_isp.text(ip_isp.lookup(r["ip"] or "")),
                    "kind": r["kind"], "label": KIND_LABELS.get(r["kind"], r["kind"]), "dest": r["dest"],
                    "raw": r["raw"], "device": r["title"] or ""})
    return out
