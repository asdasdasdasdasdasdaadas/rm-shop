"""The Telegram Ads cabinet inside «Рост»: what the admin page reads and the buttons it presses.

Reads come from our own tables (tg_ads, tg_ad_stats, users by ad link, payment_receipts), filled by app/tg_ads.py.
Writes go to the Ads API (app/tg_ads.call) and are logged in tg_ad_log. Nothing here adds money to an existing ad:
the only budget moves are a new ad's initial budget (the constructor) and «Вернуть остаток» (back to the account).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import db, tg_ads, tg_autobid
from app.config import get_settings

MSK = tg_autobid.MSK
PERIODS = {"today", "7d", "30d"}
USERNAME_RE = re.compile(r"^@?([A-Za-z][A-Za-z0-9_]{3,31})$")


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _loads(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v


def _n(v) -> str:
    return f"{int(v or 0):,}".replace(",", " ")


def _ts(v) -> datetime | None:
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace(" ", "T"))
        except ValueError:
            return None
    if isinstance(v, datetime) and v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v


def username_of(raw: str) -> str | None:
    """«@name», «t.me/name» or «https://t.me/name» → «name»."""
    s = str(raw or "").strip()
    s = re.sub(r"^(https?://)?(www\.)?(t|telegram)\.me/", "", s).split("?")[0].strip("/")
    m = USERNAME_RE.match(s)
    return m.group(1) if m else None


def target_summary(target) -> dict:
    """{kind, places: [{username, title}], text} from the AdTarget Telegram returns with return_target."""
    t = _loads(target) or {}
    kind = str(t.get("type") or "")
    places, parts = [], []
    for key in ("bots", "channels"):
        for p in t.get(key) or []:
            if isinstance(p, dict):
                places.append({"username": p.get("username") or "", "title": p.get("title") or p.get("name") or "",
                               "kind": key[:-1]})
    if places:
        parts.append(", ".join(p["title"] or ("@" + p["username"]) for p in places[:4])
                     + (f" и ещё {len(places) - 4}" if len(places) > 4 else ""))
    langs = [str(x.get("name") or x.get("code") or "") for x in t.get("languages") or [] if isinstance(x, dict)]
    topics = [str(x.get("name") or "") for x in t.get("topics") or [] if isinstance(x, dict)]
    if langs:
        parts.append(", ".join(langs))
    if topics:
        parts.append(", ".join(topics))
    if kind == "search":
        parts.append(", ".join(t.get("search_queries") or []))
    return {"kind": kind, "places": places, "text": " · ".join(x for x in parts if x)}


def _bounds(period: str, now: datetime) -> tuple[datetime, datetime, timedelta, int]:
    """Start of the period, start of the one before it, the chart step and the number of steps."""
    local = now.astimezone(MSK)
    if period == "today":
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start - timedelta(days=1), timedelta(hours=1), 24
    days = 7 if period == "7d" else 30
    start = (local - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    step = timedelta(hours=6) if days == 7 else timedelta(days=1)
    return start, start - timedelta(days=days), step, int(timedelta(days=days) / step)


async def _tile_data(start: datetime, end: datetime, step: timedelta, steps: int) -> dict:
    pool = db._pool_req()
    secs = int(step.total_seconds())
    stats = await pool.fetch(
        """SELECT FLOOR(EXTRACT(EPOCH FROM (ts - $1)) / $3)::int AS i, SUM(views)::int AS views,
                  SUM(clicks)::int AS clicks, SUM(spent) AS spent
           FROM tg_ad_stats WHERE ts >= $1 AND ts < $2 GROUP BY 1""", start, end, secs)
    users = await pool.fetch(
        """SELECT FLOOR(EXTRACT(EPOCH FROM (u.created_at - $1)) / $3)::int AS i, COUNT(*)::int AS users,
                  COUNT(*) FILTER (WHERE u.first_online_at IS NOT NULL)::int AS connected,
                  COUNT(*) FILTER (WHERE COALESCE(u.has_paid_topup, FALSE))::int AS paid
           FROM users u WHERE u.created_at >= $1 AND u.created_at < $2
             AND u.ad_link_id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL)
           GROUP BY 1""", start, end, secs)
    series = {k: [0] * steps for k in ("views", "clicks", "users")}
    tot = {"views": 0, "clicks": 0, "users": 0, "connected": 0, "paid": 0, "spent": 0.0}
    for r in stats:
        if 0 <= r["i"] < steps:
            series["views"][r["i"]] += r["views"]
            series["clicks"][r["i"]] += r["clicks"]
        tot["views"] += r["views"]
        tot["clicks"] += r["clicks"]
        tot["spent"] += _f(r["spent"])
    for r in users:
        if 0 <= r["i"] < steps:
            series["users"][r["i"]] += r["users"]
        for k in ("users", "connected", "paid"):
            tot[k] += r[k]
    return {"tot": tot, "series": series}


LTV_DAYS = (7, 14, 30)


async def _cohorts(now: datetime | None = None) -> dict[int, dict]:
    """link → {days: {users, revenue}}: what people paid within N days of coming, counting only those who came
    at least N days ago — so a fresh ad is not judged by money its people have not had time to pay."""
    now = now or datetime.now(timezone.utc)
    out: dict[int, dict] = {}
    for days in LTV_DAYS:
        rows = await db._pool_req().fetch(
            """SELECT u.ad_link_id AS link, COUNT(*)::int AS users,
                      COALESCE(SUM((SELECT SUM(r.amount) FROM payment_receipts r WHERE r.telegram_id = u.telegram_id
                                     AND r.created_at < u.created_at + make_interval(days => $2::int))), 0)::int AS revenue
               FROM users u
               WHERE u.ad_link_id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL)
                 AND u.created_at <= $1::timestamptz - make_interval(days => $2::int)
               GROUP BY 1""", now, days)
        for r in rows:
            out.setdefault(int(r["link"]), {})[days] = {"users": r["users"], "revenue": r["revenue"]}
    return out


def ltv_view(ltv: dict, users: int, spent_rub) -> list[dict]:
    """[{days, users, per_user, ok}] for the page: ₽ one person paid within N days vs what one person cost."""
    cost = (spent_rub / users) if spent_rub and users else None
    out = []
    for days in LTV_DAYS:
        c = ltv.get(days) or ltv.get(str(days)) or {}
        n = int(c.get("users") or 0)
        per = round(c["revenue"] / n, 1) if n else None
        out.append({"days": days, "users": n, "per_user": per,
                    "ok": (per >= cost) if per is not None and cost is not None else None})
    return out


async def _links() -> dict[int, dict]:
    """Per ad link tied to Telegram Ads: who came, connected, paid, revenue, spend in ₽ and the payback day."""
    pool = db._pool_req()
    rows = await pool.fetch(
        """SELECT l.id, l.slug, l.title, l.greeting, l.followup,
                  (SELECT COUNT(*) FROM users u WHERE u.ad_link_id = l.id)::int AS users,
                  (SELECT COUNT(*) FROM users u WHERE u.ad_link_id = l.id AND u.first_online_at IS NOT NULL)::int AS connected,
                  (SELECT COUNT(*) FROM users u WHERE u.ad_link_id = l.id AND COALESCE(u.has_paid_topup, FALSE))::int AS paid,
                  COALESCE((SELECT SUM(r.amount) FROM payment_receipts r JOIN users u ON u.telegram_id = r.telegram_id
                            WHERE u.ad_link_id = l.id), 0)::int AS revenue,
                  COALESCE((SELECT SUM(a.spent_rub) FROM tg_ads a WHERE a.ad_link_id = l.id), 0)::int AS spent_rub,
                  (SELECT MIN(a.created_at) FROM tg_ads a WHERE a.ad_link_id = l.id) AS started
           FROM ad_links l WHERE l.id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL)""")
    out = {}
    cohorts = await _cohorts()
    for r in rows:
        d = dict(r)
        d["ltv"] = cohorts.get(int(d["id"]), {})
        d["payback_days"] = None
        if d["spent_rub"] and d["revenue"] >= d["spent_rub"] and d["started"]:
            pays = await pool.fetch(
                """SELECT r.amount, r.created_at FROM payment_receipts r JOIN users u ON u.telegram_id = r.telegram_id
                   WHERE u.ad_link_id = $1 ORDER BY r.created_at""", d["id"])
            acc = 0
            for p in pays:
                acc += int(p["amount"])
                if acc >= d["spent_rub"]:
                    d["payback_days"] = max(0, (_ts(p["created_at"]) - _ts(d["started"])).days)
                    break
        out[int(d["id"])] = d
    return out


async def cabinet(period: str = "7d", now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    period = period if period in PERIODS else "7d"
    pool = db._pool_req()
    start, prev, step, steps = _bounds(period, now)
    cur = await _tile_data(start, now, step, steps)
    before = await _tile_data(prev, start, step, steps)
    report = await db.get_job_report("tg_ads") or {}
    links = await _links()
    ads = await pool.fetch(
        """SELECT a.*, b.enabled AS ab_enabled, b.max_cpm, b.good_cpm, b.floor_cpm, b.floor_until, b.state AS ab_state,
                  b.note AS ab_note, b.refund_at, b.changed_at, b.max_user_rub, b.base_cpm,
                  (SELECT COALESCE(SUM(s.spent), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.ts >= NOW() - INTERVAL '1 day') AS day_spent,
                  (SELECT COALESCE(SUM(s.views), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.ts >= NOW() - INTERVAL '1 hour')::int AS views_hour,
                  (SELECT COALESCE(SUM(s.views), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.ts >= $1)::int AS views_period,
                  (SELECT COALESCE(SUM(s.clicks), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.ts >= $1)::int AS clicks_period,
                  (SELECT COALESCE(SUM(s.spent), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.ts >= $1) AS spent_period,
                  (SELECT MAX(s.ts) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.views > 0) AS last_view_at,
                  (SELECT ARRAY_AGG(v ORDER BY h) FROM (
                       SELECT gs AS h, COALESCE((SELECT SUM(s.views) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id
                              AND s.ts >= NOW() - make_interval(hours => 24 - gs)
                              AND s.ts < NOW() - make_interval(hours => 23 - gs)), 0)::int AS v
                       FROM generate_series(0, 23) gs) x) AS spark
           FROM tg_ads a LEFT JOIN tg_ad_autobid b ON b.ad_id = a.ad_id
           WHERE a.gone_at IS NULL ORDER BY a.created_at DESC NULLS LAST, a.ad_id DESC""", start)
    shared: dict[int, int] = {}
    for a in ads:
        if a["ad_link_id"]:
            shared[a["ad_link_id"]] = shared.get(a["ad_link_id"], 0) + 1
    rate = _f(report.get("rate")) or None
    silent_why = await _silences([dict(a) for a in ads], now)
    rows = []
    for a in ads:
        link = links.get(a["ad_link_id"]) if a["ad_link_id"] else None
        alone = bool(link) and shared.get(link["id"], 1) == 1
        person_rub = round(link["spent_rub"] / link["users"], 1) if alone and link["spent_rub"] and link["users"] else None
        views = int(a["views"] or 0)
        state = a["ab_state"] or "idle"
        if not a["ab_enabled"] and state not in {"review"}:
            state = "idle"
        rows.append({
            "ad_id": int(a["ad_id"]), "title": a["title"], "text": a["ad_text"], "status": a["status"],
            "placement": a["placement"], "currency": a["currency"], "cpm": _f(a["cpm"]), "remaining": _f(a["remaining"]),
            "spent": _f(a["spent"]), "spent_rub": a["spent_rub"], "views": views, "clicks": int(a["clicks"] or 0),
            "actions": int(a["actions"] or 0), "daily_limit": _f(a["daily_limit"]), "is_paused": bool(a["is_paused"]),
            "decline_reason": a["decline_reason"], "promote_url": a["promote_url"], "created_at": a["created_at"],
            "schedule": _loads(a["schedule"]), "target": target_summary(a["target"]),
            "views_hour": a["views_hour"], "views_period": a["views_period"], "clicks_period": a["clicks_period"],
            "spent_period": _f(a["spent_period"]), "last_view_at": a["last_view_at"], "spark": list(a["spark"] or []),
            "day_spent": _f(a["day_spent"]), "days_left": tg_autobid.days_left(a["remaining"], a["day_spent"]),
            "silence": silent_why.get(int(a["ad_id"])), "person_rub": person_rub,
            "autobid": {"enabled": bool(a["ab_enabled"]),
                        "max_cpm": min(_f(a["max_cpm"]), float(tg_autobid.HARD_MAX_CPM)) if a["max_cpm"] else None,
                        "good_cpm": _f(a["good_cpm"]) or None,
                        "floor_cpm": _f(a["floor_cpm"]) if a["floor_until"] and a["floor_until"] > now else None,
                        "state": state, "state_text": tg_autobid.STATE_TEXT.get(state, state), "note": a["ab_note"] or "",
                        "refund_at": a["refund_at"], "changed_at": a["changed_at"], "max_user_rub": a["max_user_rub"],
                        "base_cpm": _f(a["base_cpm"]) or None},
            "link": ({"id": link["id"], "slug": link["slug"], "title": link["title"], "greeting": link["greeting"] or "",
                      "followup": link["followup"] or "",
                      "users": link["users"], "connected": link["connected"], "paid": link["paid"],
                      "revenue": link["revenue"], "spent_rub": link["spent_rub"], "payback_days": link["payback_days"],
                      "ltv": ltv_view(link["ltv"], link["users"], link["spent_rub"]),
                      "shared": shared.get(link["id"], 1) > 1,
                      "per_1000": round(link["users"] * 1000 / views, 1) if views and shared.get(link["id"], 1) == 1 else None}
                     if link else None),
        })
    log = await pool.fetch(
        """SELECT l.*, a.title FROM tg_ad_log l LEFT JOIN tg_ads a ON a.ad_id = l.ad_id ORDER BY l.at DESC LIMIT 60""")
    every = {"users": sum(x["users"] for x in links.values()), "spent_rub": sum(x["spent_rub"] or 0 for x in links.values())}
    merged: dict[int, dict] = {}
    for x in links.values():
        for days, c in (x["ltv"] or {}).items():
            m = merged.setdefault(int(days), {"users": 0, "revenue": 0})
            m["users"] += c["users"]
            m["revenue"] += c["revenue"]
    tot, prev_tot = cur["tot"], before["tot"]
    spent_rub = None
    if report.get("rate"):
        spent_rub = round(tot["spent"] * float(report["rate"]))
    return {
        "ok": True, "configured": bool(tg_ads.token()), "period": period, "report": report,
        "currency": report.get("currency") or (rows[0]["currency"] if rows else "TON"),
        "balance": report.get("remaining"),
        "tiles": {k: {"value": tot[k], "prev": prev_tot[k], "series": cur["series"].get(k, [])}
                  for k in ("views", "clicks", "users")},
        "extra": {"connected": tot["connected"], "paid": tot["paid"], "spent": tot["spent"], "spent_rub": spent_rub,
                  "ctr": round(tot["clicks"] * 100 / tot["views"], 2) if tot["views"] else None,
                  "per_user": tot["spent"] / tot["users"] if tot["users"] else None,
                  "per_paid": tot["spent"] / tot["paid"] if tot["paid"] else None},
        "ltv": ltv_view(merged, every["users"], every["spent_rub"]),
        "person_rub": round(every["spent_rub"] / every["users"], 1) if every["users"] and every["spent_rub"] else None,
        "rate": rate,
        "hard_max_cpm": float(tg_autobid.HARD_MAX_CPM),
        "step_hours": step.total_seconds() / 3600, "start": start,
        "ads": rows,
        "log": [dict(r) for r in log],
        "bot": get_settings().bot_username,
        "brand": getattr(get_settings(), "brand_name", "") or "VPN",
    }


SILENT_AFTER = timedelta(hours=3)


async def _silences(ads: list[dict], now: datetime) -> dict[int, dict]:
    """Why an active ad with money has had no views for SILENT_AFTER: whether raising the CPM already failed,
    and which of its places lost their audience. {ad_id: {hours, text, back_cpm}}."""
    pool = db._pool_req()
    out = {}
    places = {r["username"].lower(): dict(r) for r in await pool.fetch("SELECT * FROM tg_ad_places")}
    for a in ads:
        if a.get("status") != "active" or a.get("is_paused") or _f(a.get("remaining")) <= 0:
            continue
        last = _ts(a.get("last_view_at") or a.get("created_at"))
        if not last or now - last < SILENT_AFTER:
            continue
        hours_ = int((now - last).total_seconds() // 3600)
        why = []
        raised = await pool.fetch(
            "SELECT old_value, new_value FROM tg_ad_log WHERE ad_id = $1 AND action = 'cpm' AND at > $2 ORDER BY at",
            int(a["ad_id"]), last)
        ups = [r for r in raised if r["old_value"] is not None and r["new_value"] is not None and _f(r["new_value"]) > _f(r["old_value"])]
        back = None
        if ups:
            back = _f(ups[0]["old_value"])
            why.append(f"после остановки ставку поднимали с {back:.2f} до {_f(a.get('cpm')):.2f}, а показов нет — дело не в цене")
        lost = []
        for p in target_summary(a.get("target"))["places"]:
            known = places.get((p["username"] or "").lower())
            if not known:
                continue
            now_a, was = known.get("audience"), known.get("prev_audience")
            if now_a is not None and (now_a == 0 or (was and was >= 2 * max(now_a, 1))):
                lost.append(f"@{p['username']}: " + (f"было {_n(was)}, стало {_n(now_a)}" if was else "аудитории нет"))
        if lost:
            why.append("Площадки потеряли аудиторию: " + "; ".join(lost[:4]))
        if not why:
            why.append("Telegram не показывает объявление: площадка перестала крутить рекламу или ставки соседей выше")
        out[int(a["ad_id"])] = {"hours": hours_, "text": ". ".join(w[0].upper() + w[1:] for w in why), "back_cpm": back if back and back < _f(a.get("cpm")) else None}
    return out


async def hours(days: int = 30) -> dict:
    """7×24 (Mon..Sun × hour, Moscow): views, people who came and first payments of people from Telegram Ads."""
    pool = db._pool_req()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = lambda col, src, extra="": f"""SELECT EXTRACT(ISODOW FROM {col} AT TIME ZONE 'Europe/Moscow')::int - 1 AS d,
        EXTRACT(HOUR FROM {col} AT TIME ZONE 'Europe/Moscow')::int AS h, {src} AS v {extra}"""  # noqa: E731
    views = await pool.fetch(q("ts", "SUM(views)::int") + " FROM tg_ad_stats WHERE ts >= $1 GROUP BY 1, 2", since)
    came = await pool.fetch(
        q("u.created_at", "COUNT(*)::int") + """ FROM users u WHERE u.created_at >= $1
           AND u.ad_link_id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL) GROUP BY 1, 2""", since)
    paid = await pool.fetch(
        q("r.created_at", "COUNT(*)::int") + """ FROM payment_receipts r JOIN users u ON u.telegram_id = r.telegram_id
           WHERE r.created_at >= $1 AND r.first_payment
             AND u.ad_link_id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL) GROUP BY 1, 2""", since)

    def grid(rows):
        g = [[0] * 24 for _ in range(7)]
        for r in rows:
            if 0 <= r["d"] < 7 and 0 <= r["h"] < 24:
                g[r["d"]][r["h"]] += int(r["v"] or 0)
        return g
    return {"ok": True, "days": days, "views": grid(views), "users": grid(came), "paid": grid(paid)}


async def places() -> dict:
    """Bots and channels from our ads' targets and from checks, with how our ads did there."""
    pool = db._pool_req()
    ads = await pool.fetch(
        """SELECT a.ad_id, a.title, a.status, a.views, a.clicks, a.spent, a.target, a.ad_link_id, a.gone_at,
                  (SELECT COALESCE(SUM(s.views), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id
                     AND s.ts >= NOW() - INTERVAL '1 day')::int AS views_day
           FROM tg_ads a WHERE a.target IS NOT NULL""")
    found: dict[str, dict] = {}
    for a in ads:
        for p in target_summary(a["target"])["places"]:
            name = (p["username"] or p["title"]).lower()
            if not name:
                continue
            e = found.setdefault(name, {"username": p["username"], "title": p["title"], "kind": p["kind"], "ads": [],
                                        "views": 0, "views_day": 0, "spent": 0.0})
            e["ads"].append({"ad_id": int(a["ad_id"]), "title": a["title"], "status": a["status"], "gone": bool(a["gone_at"])})
            e["views"] += int(a["views"] or 0)
            e["views_day"] += int(a["views_day"] or 0)
            e["spent"] += _f(a["spent"])
    for r in await pool.fetch("SELECT * FROM tg_ad_places ORDER BY checked_at DESC"):
        e = found.setdefault(r["username"].lower(), {"username": r["username"], "title": r["title"], "kind": r["kind"],
                                                     "ads": [], "views": 0, "views_day": 0, "spent": 0.0})
        e.update({"audience": r["audience"], "checked_at": r["checked_at"], "title": e["title"] or r["title"]})
        e.update({"prev_audience": r["prev_audience"]})
    items = sorted(found.values(), key=lambda e: (-(e.get("views_day") or 0), -(e.get("views") or 0)))
    for e in items:
        live = [x for x in e["ads"] if x["status"] == "active" and not x["gone"]]
        e["verdict"] = ("крутится" if e["views_day"] else "молчит" if live else "было" if e["ads"] else "не пробовали")
    # The smallest place where our ads do get views: anything with at least as many people is worth a try.
    bar = min((int(e["audience"]) for e in items if e["verdict"] == "крутится" and e.get("audience")), default=None)
    for e in items:
        if e["verdict"] != "не пробовали":
            continue
        aud = e.get("audience")
        if aud is None:
            e["verdict"] = "не проверено"
        elif aud == 0:
            e["verdict"] = "нет людей"
        elif aud >= (bar or 5000):
            e["verdict"] = "стоит попробовать"
        else:
            e["verdict"] = "мало людей"
    rank = {"стоит попробовать": 0, "крутится": 1, "молчит": 2, "мало людей": 3, "было": 4, "не проверено": 5, "нет людей": 6}
    items.sort(key=lambda e: (rank.get(e["verdict"], 9), -(e.get("audience") or 0), -(e.get("views_day") or 0)))
    return {"ok": True, "items": items, "bar": bar}



def _audience(raw: dict) -> int | None:
    for k in ("monthly_users", "active_users", "subscribers", "users", "participants_count", "members"):
        if isinstance(raw.get(k), (int, float)):
            return int(raw[k])
    return None


async def check_place(text: str) -> dict:
    name = username_of(text)
    if not name:
        raise ValueError("Укажите @username бота или канала")
    raw, kind = None, "bot"
    try:
        raw = await tg_ads.call("getTargetBot", bot_id="@" + name)
    except tg_ads.TgAdsError:
        kind = "channel"
        raw = await tg_ads.call("getTargetChannel", channel_id="@" + name)
    raw = raw or {}
    await db._pool_req().execute(
        """INSERT INTO tg_ad_places (username, kind, title, audience, raw, checked_at) VALUES ($1,$2,$3,$4,$5::jsonb,NOW())
           ON CONFLICT (username) DO UPDATE SET kind=EXCLUDED.kind, title=EXCLUDED.title, audience=EXCLUDED.audience,
               prev_audience = CASE WHEN tg_ad_places.audience IS DISTINCT FROM EXCLUDED.audience
                                    THEN tg_ad_places.audience ELSE tg_ad_places.prev_audience END,
               raw=EXCLUDED.raw, checked_at=NOW()""",
        raw.get("username") or name, kind, str(raw.get("title") or raw.get("name") or ""), _audience(raw),
        json.dumps(raw, ensure_ascii=False))
    return {"ok": True, "kind": kind, "place": raw}


async def check_places(names: list) -> dict:
    """Several places at once (a list pasted from anywhere): checks each, says which failed."""
    wanted, bad = [], []
    for raw in names[:30]:
        n = username_of(raw)
        (wanted if n else bad).append(n or str(raw))
    done, failed = 0, []
    for n in dict.fromkeys(wanted):
        try:
            await check_place(n)
            done += 1
        except Exception as exc:
            failed.append(f"@{n}: {str(exc)[:80]}")
    return {"ok": True, "checked": done, "failed": failed + [f"{b}: не похоже на @username" for b in bad]}


RECHECK_EVERY = timedelta(hours=12)


async def recheck_places() -> int:
    """Places of running ads are checked twice a day, so a place losing its audience shows up by itself."""
    pool = db._pool_req()
    names = set()
    for a in await pool.fetch("SELECT target FROM tg_ads WHERE gone_at IS NULL AND status = 'active' AND target IS NOT NULL"):
        names.update(p["username"] for p in target_summary(a["target"])["places"] if p["username"])
    fresh = {r["username"].lower() for r in await pool.fetch(
        "SELECT username FROM tg_ad_places WHERE checked_at >= $1", datetime.now(timezone.utc) - RECHECK_EVERY)}
    done = 0
    for n in sorted(names):
        if n.lower() in fresh or done >= 8:
            continue
        try:
            await check_place(n)
        except Exception:
            pass
        done += 1
    return done


# ---------------------------------------------------------------------------------------------------- actions

async def _ad_or_fail(ad_id: int) -> dict:
    row = await db._pool_req().fetchrow("SELECT * FROM tg_ads WHERE ad_id = $1", int(ad_id))
    if not row:
        raise ValueError("Объявление не найдено — обновите список")
    return dict(row)


async def _after_edit(ad_id: int, ad: dict) -> dict:
    status = str((ad or {}).get("status") or "")
    if status:
        await db._pool_req().execute(
            "UPDATE tg_ads SET status = $2, is_paused = $3, daily_limit = $4, schedule = $5::jsonb WHERE ad_id = $1",
            int(ad_id), status, bool(ad.get("is_paused")), Decimal(str(ad.get("daily_budget_limit") or 0)),
            json.dumps(ad["schedule"]) if ad.get("schedule") else None)
    return {"ok": True, "status": status,
            "review": status in {"in_review", "ready_for_review"}}


async def set_cpm(ad_id: int, cpm) -> dict:
    await _ad_or_fail(ad_id)
    await tg_autobid.ensure_row(ad_id)
    ad = await tg_autobid.set_cpm(ad_id, cpm, who="admin", note="вручную")
    return await _after_edit(ad_id, ad)


async def set_autobid(ad_id: int, enabled: bool, max_cpm=None, max_user_rub=...) -> dict:
    ad = await _ad_or_fail(ad_id)
    row = await tg_autobid.ensure_row(ad_id)
    top = Decimal(str(max_cpm)) if max_cpm not in (None, "") else None
    if top is not None and top <= 0:
        raise ValueError("Потолок должен быть больше нуля")
    if top is not None and top > tg_autobid.HARD_MAX_CPM:
        raise ValueError(f"Потолок автоставки — не выше {tg_autobid.HARD_MAX_CPM}")
    person = row.get("max_user_rub")
    if max_user_rub is not ...:
        person = int(Decimal(str(max_user_rub))) if max_user_rub not in (None, "", 0, "0") else None
        if person is not None and person <= 0:
            raise ValueError("Цена человека должна быть больше нуля")
    if enabled and top is None:
        top = tg_autobid.ceiling({}, Decimal(str(ad["cpm"] or 0)))
    await db._pool_req().execute(
        """UPDATE tg_ad_autobid SET enabled = $2, max_cpm = COALESCE($3, max_cpm), updated_at = NOW(),
               state = CASE WHEN $2 THEN 'watching' ELSE 'idle' END,
               note = CASE WHEN $2 THEN 'включена — первая проверка через 10 минут' ELSE '' END,
               good_cpm = CASE WHEN $2 THEN NULL ELSE good_cpm END,
               base_cpm = CASE WHEN $2 THEN $4 ELSE base_cpm END,
               max_user_rub = $5
           WHERE ad_id = $1""", int(ad_id), bool(enabled), top, Decimal(str(ad["cpm"] or 0)) or None, person)
    note = f"потолок {top}" + (f", человек не дороже {person} ₽" if person else "") if enabled else ""
    await tg_autobid.log(ad_id, "autobid_on" if enabled else "autobid_off", who="admin", new=top, note=note)
    out = {"ok": True, "max_cpm": float(top) if top is not None else None}
    limit = tg_autobid.suggested_limit(ad["remaining"])
    if enabled and not _f(ad.get("daily_limit")) and limit:
        # Autobid on an ad without a daily limit: cap a day at half of what is left.
        try:
            edited = await tg_ads.call("editAd", ad_id=int(ad_id), daily_budget_limit=float(limit)) or {}
            await tg_autobid.log(ad_id, "daily_limit", who="admin", new=limit, note="поставлен вместе с автоставкой")
            out.update(await _after_edit(ad_id, edited), daily_limit=float(limit))
        except tg_ads.TgAdsError as exc:
            out["limit_error"] = f"Дневной лимит не поставился: {exc}"
    return out


async def set_daily_limit(ad_id: int, limit) -> dict:
    await _ad_or_fail(ad_id)
    value = Decimal(str(limit or 0))
    if value < 0:
        raise ValueError("Лимит не может быть отрицательным")
    ad = await tg_ads.call("editAd", ad_id=int(ad_id), daily_budget_limit=float(value))
    await tg_autobid.log(ad_id, "daily_limit", who="admin", new=value, note="0 — без лимита" if not value else "")
    return await _after_edit(ad_id, ad or {})


async def set_paused(ad_id: int, paused: bool) -> dict:
    await _ad_or_fail(ad_id)
    ad = await tg_ads.call("editAd", ad_id=int(ad_id), is_paused=bool(paused))
    await tg_autobid.log(ad_id, "pause" if paused else "resume", who="admin")
    return await _after_edit(ad_id, ad or {})


async def refund(ad_id: int) -> dict:
    """Pause the ad and, ten minutes later (the API's rule), return its remaining budget to the account."""
    ad = await _ad_or_fail(ad_id)
    if Decimal(str(ad["remaining"] or 0)) <= 0:
        raise ValueError("В бюджете объявления ничего не осталось")
    await tg_autobid.ensure_row(ad_id)
    got = await tg_ads.call("editAd", ad_id=int(ad_id), is_paused=True)
    at = datetime.now(timezone.utc) + tg_autobid.REFUND_AFTER
    await db._pool_req().execute(
        """UPDATE tg_ad_autobid SET refund_at = $2, enabled = FALSE, state = 'paused',
               note = 'на паузе — остаток вернётся на баланс через 10 минут' WHERE ad_id = $1""", int(ad_id), at)
    await tg_autobid.log(ad_id, "refund_asked", who="admin", old=ad["remaining"], note="пауза, возврат через 10 минут")
    out = await _after_edit(ad_id, got or {})
    return {**out, "refund_at": at.isoformat()}


async def set_schedule(ad_id: int, mask) -> dict:
    await _ad_or_fail(ad_id)
    if mask:
        if not (isinstance(mask, list) and len(mask) == 7 and all(isinstance(x, int) and 0 <= x < 1 << 24 for x in mask)):
            raise ValueError("Расписание: 7 чисел, по одному на день недели")
        if not any(mask):
            raise ValueError("Отметьте хотя бы один час")
        schedule = {"week_hours_mask": mask, "timezone": 10800}
    else:
        schedule = False
    ad = await tg_ads.call("editAd", ad_id=int(ad_id), schedule=schedule)
    on = sum(bin(x).count("1") for x in mask) if mask else 168
    await tg_autobid.log(ad_id, "schedule", who="admin", new=on, note=f"{on} ч в неделю" if mask else "без расписания")
    return await _after_edit(ad_id, ad or {})


async def set_greeting(link_id: int, text: str, followup=...) -> dict:
    """The link's greeting and, when given, its «дожим» (app/ad_followup.py)."""
    value = str(text or "").strip()
    if len(value) > 700:
        raise ValueError("Приветствие длиннее 700 знаков")
    later = None if followup is ... else str(followup or "").strip()
    if later is not None and len(later) > 700:
        raise ValueError("Дожим длиннее 700 знаков")
    done = await db._pool_req().fetchval(
        """UPDATE ad_links SET greeting = $2, followup = CASE WHEN $3 THEN $4 ELSE followup END
           WHERE id = $1 RETURNING id""", int(link_id), value or None, later is not None, later or None)
    if not done:
        raise ValueError("Ссылка не найдена")
    return {"ok": True}


async def targets() -> dict:
    """Languages and topics for the constructor, kept for a day."""
    cached = await db.get_job_report("tg_ads_targets") or {}
    if cached.get("at") and datetime.fromisoformat(cached["at"]) > datetime.now(timezone.utc) - timedelta(days=1):
        return {"ok": True, **cached}
    langs = await tg_ads.call("getTargetLanguagesList") or []
    topics = await tg_ads.call("getTargetTopicsList") or []
    data = {"languages": langs, "topics": topics, "at": datetime.now(timezone.utc).isoformat()}
    await db.set_job_report("tg_ads_targets", data)
    return {"ok": True, **data}


async def create(body: dict) -> dict:
    """A new ad from the admin: makes (or reuses) the ad link first, so every start from it is counted."""
    title = str(body.get("title") or "").strip()
    text = str(body.get("text") or "").strip()
    if not title or not text:
        raise ValueError("Нужны название и текст объявления")
    if len(text) > 160:
        raise ValueError("Текст объявления — до 160 знаков")
    cpm = Decimal(str(body.get("cpm") or 0))
    budget = Decimal(str(body.get("budget") or 0))
    if cpm <= 0:
        raise ValueError("Укажите ставку CPM")
    if budget < 0:
        raise ValueError("Бюджет не может быть отрицательным")
    if body.get("autobid") and body.get("max_cpm") not in (None, "") and Decimal(str(body["max_cpm"])) > tg_autobid.HARD_MAX_CPM:
        raise ValueError(f"Потолок автоставки — не выше {tg_autobid.HARD_MAX_CPM}")
    daily = Decimal(str(body.get("daily_limit") or 0))
    if body.get("autobid") and not daily and budget > 0:
        daily = tg_autobid.suggested_limit(budget) or Decimal(0)
    kind = str(body.get("kind") or "bots")
    if kind == "bots":
        names = [username_of(x) for x in body.get("places") or []]
        if not names or None in names:
            raise ValueError("Укажите ботов: @username, по одному в строке")
        target = {"type": "bots", "bot_ids": ["@" + n for n in names][:100]}
        placement = "bot_banner"
    elif kind == "channels":
        names = [username_of(x) for x in body.get("places") or [] if str(x).strip()]
        if None in names:
            raise ValueError("Каналы: @username, по одному в строке")
        if names:
            target = {"type": "channels", "channel_ids": ["@" + n for n in names][:100]}
        else:
            lang = str(body.get("language") or "").strip()
            topics = [int(t) for t in body.get("topics") or []]
            if not lang:
                raise ValueError("Выберите язык каналов или перечислите каналы")
            target = {"type": "channels", "language_codes": [lang], **({"topic_ids": topics[:20]} if topics else {})}
        placement = "channel_post"
    else:
        raise ValueError("Неизвестный тип площадок")
    slug = str(body.get("slug") or "").strip().lower().removeprefix("ad_")
    link = await db._pool_req().fetchrow("SELECT * FROM ad_links WHERE slug = $1", slug) if slug else None
    if link is None:
        link = await db.create_ad_link(str(body.get("link_title") or title)[:80], slug)
    if body.get("greeting") or body.get("followup"):
        await set_greeting(int(link["id"]), str(body.get("greeting") or link.get("greeting") or ""),
                           str(body.get("followup") or "") or ...)
    url = f"https://t.me/{get_settings().bot_username}?start=ad_{link['slug']}"
    ad = await tg_ads.call(
        "createAd", title=title[:128], text=text, promote_url=url, cpm=float(cpm), placement=placement, target=target,
        initial_budget=float(budget), is_paused=bool(body.get("paused")),
        daily_budget_limit=float(daily),
        idempotency_key=f"rmshop-{link['slug']}-{abs(hash((title, text, float(cpm)))) % 10**12}") or {}
    ad_id = int(ad.get("ad_id") or 0)
    if ad_id:
        await tg_autobid.log(ad_id, "created", who="admin", new=cpm, note=f"бюджет {budget}, ссылка ad_{link['slug']}")
        if body.get("autobid"):
            await tg_autobid.ensure_row(ad_id)
            await db._pool_req().execute(
                "UPDATE tg_ad_autobid SET enabled = TRUE, max_cpm = $2, base_cpm = $3, state = 'watching' WHERE ad_id = $1",
                ad_id, tg_autobid.ceiling({"max_cpm": body.get("max_cpm")}, cpm), cpm)
    try:
        await tg_ads.sync_locked()
    except Exception:
        pass
    return {"ok": True, "ad_id": ad_id, "status": ad.get("status"), "slug": link["slug"], "url": url}
