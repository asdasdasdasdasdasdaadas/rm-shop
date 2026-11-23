"""Telegram Ads autobid and watch, run after every sync (app/tg_ads.py, every 10 minutes).

Autobid keeps an ad on the lowest CPM at which it is still shown:
  * no views for QUIET after the last change → CPM up by STEP_UP, never above the ceiling: max_cpm, by default
    the starting CPM + 30%, and never above HARD_MAX_CPM whatever is set; a CPM above the ceiling is brought down;
  * views flowing for PROBE_EVERY → try STEP_DOWN lower;
  * the views stopped after lowering → back to the last CPM that worked, and that CPM is the floor for a day;
  * at the ceiling with no views for DEAD → «не крутится», with an alert: the place is dead, not the price.
    The CPM goes back to the last one that worked (or the one it started from) and stays there: raising more
    would only cost money once the place comes back;
  * «человек не дороже N ₽»: once an ad has brought a few people, the CPM is kept at or below
    N ÷ rate × people per 1000 views, so a person from it costs no more than N.
Budgets are never added to. The only money that moves is «Вернуть остаток», pressed by hand: the ad is paused and
ten minutes later (the API's rule) its remaining budget goes back to the account.

The same pass sends alerts (ad declined, passed moderation, the first 100 views, dead at the ceiling, budget almost
spent, people from it pay less than they cost — with «На паузу» / «Вернуть остаток» buttons) and the morning digest.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app import db

logger = logging.getLogger("rm-shop.tg-autobid")

MSK = ZoneInfo("Europe/Moscow")
WAIT = timedelta(minutes=40)          # after a change Telegram needs time to show the ad at the new price
QUIET = timedelta(minutes=40)         # no views this long → the price is too low
PROBE_EVERY = timedelta(hours=2)      # views this long since the last change → try cheaper
DEAD = timedelta(hours=3)
FLOOR_FOR = timedelta(hours=24)
STEP_UP = Decimal("1.15")
STEP_DOWN = Decimal("0.93")
MIN_STEP = Decimal("0.05")
MIN_CPM = Decimal("0.1")
REFUND_AFTER = timedelta(minutes=11)
CEILING_STEP = Decimal("1.3")         # the default ceiling: the CPM the autobid started from + 30%
HARD_MAX_CPM = Decimal("5")           # the autobid never sets a CPM above this, whatever ceiling is given
PERSON_WINDOW = timedelta(days=14)    # people per 1000 views are counted over this
PERSON_MIN_USERS = 3                  # fewer people than this — too early to judge the price of one
PERSON_DRY_VIEWS = 5000               # this many views and nobody came → do not raise the CPM

STATE_TEXT = {
    "idle": "выключена",
    "watching": "ждёт реакцию",
    "searching": "подбирает",
    "holding": "держит",
    "probing": "пробует дешевле",
    "ceiling": "на потолке",
    "dead": "не крутится",
    "review": "на модерации",
    "paused": "на паузе",
    "empty": "бюджет кончился",
    "expensive": "дорогие люди",
}


def _d(v) -> Decimal:
    try:
        return Decimal(str(v if v is not None else 0))
    except Exception:
        return Decimal(0)


def _round(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ceiling(ab: dict, cpm: Decimal) -> Decimal:
    """The highest CPM the autobid may set: as given, else the CPM it started from + 30%; never above HARD_MAX_CPM."""
    given = _d(ab.get("max_cpm"))
    top = given if given > 0 else _round(max(cpm, MIN_CPM) * CEILING_STEP)
    return min(top, HARD_MAX_CPM)


def suggested_limit(remaining) -> Decimal | None:
    """A daily limit for an ad that has none: half of what is left, so the budget lasts at least two days."""
    rest = _d(remaining)
    if rest <= 0:
        return None
    return min(rest, max(Decimal("0.5"), _round(rest / 2)))


def person_cap(max_user_rub, rate, views: int, users: int) -> tuple[Decimal | None, str]:
    """The highest CPM at which one person from the ad costs at most max_user_rub, from people per 1000 views.
    (None, why) while there is no target, no rate or too little data; (0, why) when many views brought nobody."""
    target, rate = _d(max_user_rub), _d(rate)
    if target <= 0 or rate <= 0:
        return None, ""
    if users < PERSON_MIN_USERS:
        if users == 0 and views >= PERSON_DRY_VIEWS:
            return Decimal(0), f"{views:,} показов и ни одного человека".replace(",", " ")
        return None, "мало данных, чтобы считать цену человека"
    per_1000 = Decimal(users) * 1000 / Decimal(max(views, 1))
    cap = _round(target / rate * per_1000)
    return cap, f"при {_round(per_1000)} чел. на 1000 показов человек выходит не дороже {int(target)} ₽ до ставки {cap}"


def decide(ab: dict, ad: dict, views: list[tuple[datetime, int]], now: datetime,
           cap: Decimal | None = None, cap_note: str = "") -> dict:
    """What to do with one ad now. `views` are (start of 5 minutes, views) for the last hours; `cap` is the CPM
    from person_cap (None — no limit by the price of a person).
    Returns {action: none|set, cpm, state, note, good_cpm?, floor_cpm?, floor_until?}."""
    cpm = _d(ad.get("cpm"))
    status = str(ad.get("status") or "")
    out = {"action": "none", "cpm": cpm, "state": ab.get("state") or "watching", "note": ""}
    if status in {"in_review", "ready_for_review"}:
        return {**out, "state": "review", "note": "объявление на модерации — ставку не трогаю"}
    if status == "declined":
        return {**out, "state": "review", "note": "объявление отклонено"}
    if ad.get("is_paused") or status in {"on_hold", "stopped"}:
        if _d(ad.get("remaining")) <= 0:
            return {**out, "state": "empty", "note": "бюджет объявления кончился"}
        return {**out, "state": "paused", "note": "объявление на паузе"}
    if status != "active":
        return {**out, "state": "paused", "note": f"статус {status or 'неизвестен'}"}

    def seen(since: datetime, until: datetime | None = None) -> int:
        return sum(v for ts, v in views if ts >= since and (until is None or ts < until))

    changed = ab.get("changed_at")
    if changed and now - changed < WAIT:
        return {**out, "state": out["state"] if out["state"] in {"searching", "probing", "dead", "expensive"} else "watching",
                "note": (ab.get("note") or "") if out["state"] in {"dead", "expensive"} else "ждёт, как Telegram отреагирует на новую ставку"}
    top = ceiling(ab, cpm)
    if cpm > top:
        return {"action": "set", "cpm": top, "state": "searching", "note": f"ставка {cpm} выше потолка {top} — опускаю"}
    if cap is not None:
        if cap > 0 and cpm > cap:
            new = max(cap, MIN_CPM)
            if new < cpm:
                return {"action": "set", "cpm": new, "state": "expensive", "note": f"люди выходят дороже цели — снижаю: {cap_note}"}
        top = min(top, max(cap, MIN_CPM)) if cap > 0 else min(top, cpm)
    if seen(now - QUIET) == 0:
        if ab.get("state") == "dead":
            # Already went back to a working price: wait for the place to come back, do not raise again.
            return {**out, "state": "dead", "note": ab.get("note") or "площадка не крутит рекламу"}
        if cap is not None and cap == 0 and cpm >= top:
            return {**out, "state": "expensive", "note": f"{cap_note} — ставку не поднимаю"}
        good = _d(ab.get("good_cpm"))
        if ab.get("state") == "probing" and good > cpm:
            return {"action": "set", "cpm": good, "state": "holding", "floor_cpm": good, "floor_until": now + FLOOR_FOR,
                    "note": f"после снижения до {cpm} показы пропали — вернул {good}"}
        if cpm < top:
            new = min(top, _round(max(cpm * STEP_UP, cpm + MIN_STEP)))
            return {"action": "set", "cpm": new, "state": "searching",
                    "note": f"нет показов {int(QUIET.total_seconds() // 60)} мин — поднимаю"}
        last = max((ts for ts, v in views if v > 0), default=None)
        quiet_since = last or changed
        if quiet_since is None or now - quiet_since >= DEAD:
            note = (f"на потолке {top} и без показов больше {int(DEAD.total_seconds() // 3600)} ч — дело не в цене,"
                    " площадка не крутит рекламу")
            base = _d(ab.get("base_cpm"))
            back = good if 0 < good < cpm else base if 0 < base < cpm else None
            if back is not None:
                return {"action": "set", "cpm": back, "state": "dead", "note": f"{note}; вернул ставку {back}, выше не поднимаю"}
            return {**out, "state": "dead", "note": note}
        return {**out, "state": "ceiling", "note": f"упёрлась в потолок {top}"}
    hour = timedelta(hours=1)
    steady = seen(now - 2 * hour, now - hour) > 0 and seen(now - hour) > 0
    if (changed is None or now - changed >= PROBE_EVERY) and steady:
        floor = _d(ab.get("floor_cpm")) if ab.get("floor_until") and ab["floor_until"] > now else Decimal(0)
        new = max(floor, MIN_CPM, _round(cpm * STEP_DOWN))
        if new < cpm:
            return {"action": "set", "cpm": new, "state": "probing", "good_cpm": cpm,
                    "note": "показы идут 2 ч — пробую дешевле"}
    return {**out, "state": "holding", "good_cpm": cpm, "note": "показы идут"}


# ---------------------------------------------------------------------------------------------------- storage

async def log(ad_id: int, action: str, *, who: str = "bot", old=None, new=None, note: str = "") -> None:
    await db._pool_req().execute(
        "INSERT INTO tg_ad_log (ad_id, who, action, old_value, new_value, note) VALUES ($1,$2,$3,$4,$5,$6)",
        int(ad_id), who, action, _d(old) if old is not None else None, _d(new) if new is not None else None, note[:300])


async def ensure_row(ad_id: int) -> dict:
    pool = db._pool_req()
    await pool.execute("INSERT INTO tg_ad_autobid (ad_id) VALUES ($1) ON CONFLICT DO NOTHING", int(ad_id))
    return dict(await pool.fetchrow("SELECT * FROM tg_ad_autobid WHERE ad_id = $1", int(ad_id)))


async def set_cpm(ad_id: int, cpm, *, who: str = "admin", note: str = "") -> dict:
    """Change the CPM in Telegram Ads. Returns the ad as Telegram gives it back."""
    from app import tg_ads
    pool = db._pool_req()
    old = await pool.fetchval("SELECT cpm FROM tg_ads WHERE ad_id = $1", int(ad_id))
    new = _round(_d(cpm))
    if new <= 0:
        raise ValueError("Ставка должна быть больше нуля")
    ad = await tg_ads.call("editAd", ad_id=int(ad_id), cpm=float(new)) or {}
    status = str(ad.get("status") or "")
    await pool.execute("UPDATE tg_ads SET cpm = $2, status = COALESCE(NULLIF($3, ''), status) WHERE ad_id = $1",
                       int(ad_id), _d(ad.get("cpm") or new), status)
    await pool.execute("UPDATE tg_ad_autobid SET changed_at = NOW(), updated_at = NOW() WHERE ad_id = $1", int(ad_id))
    await log(ad_id, "cpm", who=who, old=old, new=new, note=note)
    if status in {"in_review", "ready_for_review"}:
        # The API sent the ad back to moderation for a price change: stop doing that to it.
        await pool.execute(
            """UPDATE tg_ad_autobid SET enabled = FALSE, state = 'review', updated_at = NOW(),
                   note = 'после смены ставки Telegram отправил объявление на модерацию — автоставка выключена'
               WHERE ad_id = $1""", int(ad_id))
        await log(ad_id, "autobid_off", note="смена ставки отправила объявление на модерацию")
    return ad


async def _recent_views(hours: int = 6) -> dict[int, list[tuple[datetime, int]]]:
    rows = await db._pool_req().fetch(
        "SELECT ad_id, ts, views FROM tg_ad_stats WHERE ts >= NOW() - make_interval(hours => $1)", hours)
    out: dict[int, list[tuple[datetime, int]]] = {}
    for r in rows:
        ts = r["ts"]
        if isinstance(ts, str):   # some drivers hand timestamps back as text
            ts = datetime.fromisoformat(ts.replace(" ", "T"))
        out.setdefault(int(r["ad_id"]), []).append((ts, int(r["views"])))
    return out


async def _people(now: datetime) -> dict[int, tuple[int, int]]:
    """ad_id → (views, people who came by its link) over PERSON_WINDOW, for ads whose link is theirs alone."""
    since = now - PERSON_WINDOW
    rows = await db._pool_req().fetch(
        """SELECT a.ad_id,
                  (SELECT COALESCE(SUM(s.views), 0) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id AND s.ts >= $1)::int AS views,
                  (SELECT COUNT(*) FROM users u WHERE u.ad_link_id = a.ad_link_id AND u.created_at >= $1)::int AS users
           FROM tg_ads a
           WHERE a.ad_link_id IS NOT NULL AND a.gone_at IS NULL
             AND (SELECT COUNT(*) FROM tg_ads o WHERE o.ad_link_id = a.ad_link_id AND o.gone_at IS NULL) = 1""", since)
    return {int(r["ad_id"]): (int(r["views"]), int(r["users"])) for r in rows}


def days_left(remaining, day_spent) -> float | None:
    """How many days the ad's budget lasts at the last day's spend."""
    rest, spent = _d(remaining), _d(day_spent)
    if rest <= 0 or spent <= 0:
        return None
    return float(rest / spent)


async def run_autobid(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    pool = db._pool_req()
    rows = await pool.fetch(
        """SELECT b.*, a.cpm, a.status, a.is_paused, a.remaining, a.title FROM tg_ad_autobid b
           JOIN tg_ads a ON a.ad_id = b.ad_id WHERE b.enabled AND a.gone_at IS NULL""")
    views = await _recent_views()
    people = await _people(now)
    rate = ((await db.get_job_report("tg_ads")) or {}).get("rate")
    changed = 0
    for r in rows:
        ab, ad = dict(r), {"cpm": r["cpm"], "status": r["status"], "is_paused": r["is_paused"], "remaining": r["remaining"]}
        if not _d(ab.get("base_cpm")):
            ab["base_cpm"] = _d(r["cpm"])
            await pool.execute("UPDATE tg_ad_autobid SET base_cpm = $2 WHERE ad_id = $1", r["ad_id"], ab["base_cpm"])
        if not _d(ab.get("max_cpm")):
            # The ceiling is fixed once, from the CPM the autobid started at; otherwise it would climb with the CPM.
            ab["max_cpm"] = ceiling(ab, _d(r["cpm"]))
            await pool.execute("UPDATE tg_ad_autobid SET max_cpm = $2 WHERE ad_id = $1", r["ad_id"], ab["max_cpm"])
        seen_views, came = people.get(int(r["ad_id"]), (0, 0))
        cap, cap_note = person_cap(ab.get("max_user_rub"), rate, seen_views, came)
        step = decide(ab, ad, views.get(int(r["ad_id"]), []), now, cap, cap_note)
        if step["action"] == "set" and step["cpm"] != _d(r["cpm"]):
            try:
                await set_cpm(r["ad_id"], step["cpm"], who="bot", note=step["note"])
                changed += 1
            except Exception as exc:
                logger.warning("Автоставка %s: %s", r["ad_id"], exc)
                await pool.execute("UPDATE tg_ad_autobid SET note = $2, updated_at = NOW() WHERE ad_id = $1",
                                   r["ad_id"], f"Telegram не принял ставку {step['cpm']}: {str(exc)[:160]}")
                if "cpm" in str(exc).lower() and step["cpm"] < _d(r["cpm"]):
                    # Below the minimum for this ad: remember the current CPM as the floor.
                    await pool.execute("UPDATE tg_ad_autobid SET floor_cpm = $2, floor_until = $3 WHERE ad_id = $1",
                                       r["ad_id"], _d(r["cpm"]), now + FLOOR_FOR)
                continue
        state = await pool.fetchval("SELECT state FROM tg_ad_autobid WHERE ad_id = $1", r["ad_id"])
        if state == "review" and not await pool.fetchval("SELECT enabled FROM tg_ad_autobid WHERE ad_id = $1", r["ad_id"]):
            continue   # set_cpm switched it off just now and said why
        await pool.execute(
            """UPDATE tg_ad_autobid SET state = $2, note = $3, updated_at = NOW(),
                   good_cpm = COALESCE($4, good_cpm),
                   floor_cpm = COALESCE($5, floor_cpm), floor_until = COALESCE($6, floor_until)
               WHERE ad_id = $1""",
            r["ad_id"], step["state"], step["note"], step.get("good_cpm"), step.get("floor_cpm"), step.get("floor_until"))
    return changed


async def run_refunds(now: datetime | None = None) -> int:
    from app import tg_ads
    now = now or datetime.now(timezone.utc)
    pool = db._pool_req()
    done = 0
    for r in await pool.fetch("SELECT ad_id FROM tg_ad_autobid WHERE refund_at IS NOT NULL AND refund_at <= $1", now):
        ad_id = int(r["ad_id"])
        try:
            got = await tg_ads.call("getAdsById", ad_ids=[ad_id]) or []
            rest = _d((got[0] if got else {}).get("remaining_budget"))
            if rest > 0:
                await tg_ads.call("decreaseAdBudget", ad_id=ad_id, amount=float(rest))
                await log(ad_id, "refund", who="admin", old=rest, new=0, note="остаток вернулся на баланс кабинета")
                await pool.execute("UPDATE tg_ads SET remaining = 0 WHERE ad_id = $1", ad_id)
                done += 1
            await pool.execute("UPDATE tg_ad_autobid SET refund_at = NULL, note = $2 WHERE ad_id = $1", ad_id,
                               f"вернули {rest} на баланс" if rest > 0 else "остатка нет")
        except Exception as exc:
            # Most likely «inactive for at least 10 minutes» is not met yet: try again later.
            logger.warning("Возврат остатка объявления %s: %s", ad_id, exc)
            await pool.execute("UPDATE tg_ad_autobid SET refund_at = $2, note = $3 WHERE ad_id = $1", ad_id,
                               now + timedelta(minutes=5), f"возврат не прошёл, повторю: {str(exc)[:160]}")
    return done


# ---------------------------------------------------------------------------------------------------- alerts

LOSS_MIN_PEOPLE = 5      # people who came 14+ days ago before «не окупается» is said
LOSS_DAYS = 14
FIRST_VIEWS = 100
REVIEW = {"in_review", "ready_for_review"}


def loss_of(link: dict | None) -> dict | None:
    """{cost, paid, people}: one person from the link costs more than people who came LOSS_DAYS+ ago paid in that
    time. None while the link is shared, has no spend in ₽ or too few people had the time."""
    if not link or link.get("shared") or not link.get("spent_rub") or not link.get("users"):
        return None
    c = (link.get("ltv") or {}).get(LOSS_DAYS) or (link.get("ltv") or {}).get(str(LOSS_DAYS)) or {}
    people = int(c.get("users") or 0)
    if people < LOSS_MIN_PEOPLE:
        return None
    cost = link["spent_rub"] / link["users"]
    paid = (c.get("revenue") or 0) / people
    return {"cost": round(cost), "paid": round(paid), "people": people} if paid < cost else None


def alerts_for(ad: dict, ab: dict, day_spent: Decimal, link: dict | None = None) -> dict[str, str]:
    """Which alerts hold now for one ad: key → text. A key alerts once and again only after it went away;
    keys starting with «once:» alert once for the ad's whole life."""
    title = ad.get("title") or f"Объявление {ad['ad_id']}"
    out: dict[str, str] = {}
    live = ad.get("status") == "active" and not ad.get("is_paused")
    loss = loss_of(link) if live else None
    if loss:
        out["loss"] = (f"📉 <b>{title}</b> не окупается: человек с него стоит {loss['cost']} ₽, а за {LOSS_DAYS} дней"
                       f" приносит {loss['paid']} ₽ (по {loss['people']} пришедшим). Поставить на паузу?")
    if int(ad.get("views") or 0) >= FIRST_VIEWS:
        views, clicks = int(ad.get("views") or 0), int(ad.get("clicks") or 0)
        people = (link or {}).get("since_ad")
        ctr = f"{clicks * 100 / views:.1f}".replace(".", ",")
        out["once:first100"] = (f"👀 <b>{title}</b>: первые {views} показов — {clicks} кликов (CTR {ctr}%)"
                                + (f", пришли в бота {people}" if people is not None else "")
                                + f", потрачено {_round(_d(ad.get('spent')))} {ad.get('currency') or ''}")
    if ad.get("status") == "declined":
        reason = ad.get("decline_reason") or "без причины"
        out["declined"] = f"⛔️ <b>{title}</b> отклонено модерацией: {reason}"
    if ab.get("state") == "dead":
        out["dead"] = f"🪦 <b>{title}</b> не крутится: {ab.get('note') or 'нет показов на потолке'}"
    rest = _d(ad.get("remaining"))
    if ad.get("status") == "active" and rest > 0 and day_spent > 0 and rest < day_spent / 4:
        hours = max(1, int(rest / day_spent * 24))
        out["low"] = (f"🪫 <b>{title}</b>: в бюджете {rest} {ad.get('currency') or ''} — хватит примерно на {hours} ч."
                      " Пополнить можно в Telegram Ads")
    return out


async def _targets() -> list:
    from app.stuck_alert import _targets as targets
    return await targets()


def alert_buttons(key: str, ad_id: int):
    """«На паузу» and «Вернуть остаток» under the alerts where the next move is to stop the ad."""
    if key not in {"loss", "dead"}:
        return None
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏸ На паузу", callback_data=f"tga_pause:{ad_id}"),
        InlineKeyboardButton(text="↩️ Вернуть остаток", callback_data=f"tga_refund:{ad_id}"),
    ]])


async def _send(bot, text: str, markup=None) -> None:
    for chat in await _targets():
        try:
            await bot.send_message(chat, text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            logger.warning("Тревога Telegram Ads не ушла в %s", chat, exc_info=True)


async def run_alerts(bot) -> int:
    from app import tg_cabinet
    pool = db._pool_req()
    ads = await pool.fetch(
        """SELECT a.*, COALESCE((SELECT SUM(s.spent) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id
                                  AND s.ts >= NOW() - INTERVAL '1 day'), 0) AS day_spent,
                  (SELECT COUNT(*) FROM users u WHERE u.ad_link_id = a.ad_link_id AND u.created_at >= a.created_at)::int AS since_ad,
                  (SELECT COUNT(*) FROM tg_ads o WHERE o.ad_link_id = a.ad_link_id AND o.gone_at IS NULL)::int AS link_ads
           FROM tg_ads a WHERE a.gone_at IS NULL AND a.created_at >= NOW() - INTERVAL '60 days'""")
    links = await tg_cabinet._links() if ads else {}
    sent = 0
    for a in ads:
        ab = await ensure_row(a["ad_id"])
        sent_before = ab.get("alerted") or {}
        if isinstance(sent_before, str):
            sent_before = json.loads(sent_before or "{}")
        link = links.get(a["ad_link_id"]) if a["ad_link_id"] else None
        if link is not None:
            link = {**link, "shared": a["link_ads"] > 1, "since_ad": a["since_ad"] if a["link_ads"] == 1 else None}
        now_alerts = alerts_for(dict(a), ab, _d(a["day_spent"]), link)
        first_look = ab.get("last_status") is None
        if first_look:
            # The first pass after a deploy: what already happened is not news.
            sent_before = {**sent_before, **{k: "seen" for k in now_alerts if k.startswith("once:")}}
        elif ab.get("last_status") in REVIEW and a["status"] == "active":
            await _send(bot, f"✅ <b>{a['title'] or a['ad_id']}</b> прошло модерацию и пошло в показ")
            sent += 1
        fresh = {k: v for k, v in now_alerts.items() if k not in sent_before}
        keep = {k: sent_before[k] for k in sent_before if k in now_alerts or k.startswith("once:")}
        for key, text in fresh.items():
            await _send(bot, text, alert_buttons(key, int(a["ad_id"])))
            keep[key] = datetime.now(timezone.utc).isoformat()
            sent += 1
        if keep != sent_before or first_look or ab.get("last_status") != a["status"]:
            await pool.execute("UPDATE tg_ad_autobid SET alerted = $2::jsonb, last_status = $3 WHERE ad_id = $1",
                               a["ad_id"], json.dumps(keep), a["status"])
    return sent


# ---------------------------------------------------------------------------------------------------- digest

async def digest_data(day) -> dict:
    """Yesterday (Moscow day) of Telegram Ads: spend, views, clicks, who came, who paid, best and worst link."""
    start = datetime(day.year, day.month, day.day, tzinfo=MSK)
    end = start + timedelta(days=1)
    pool = db._pool_req()
    tot = await pool.fetchrow(
        """SELECT COALESCE(SUM(views),0)::int AS views, COALESCE(SUM(clicks),0)::int AS clicks,
                  COALESCE(SUM(spent),0) AS spent FROM tg_ad_stats WHERE ts >= $1 AND ts < $2""", start, end)
    links = await pool.fetch(
        """WITH spend AS (
               SELECT a.ad_link_id AS link, SUM(s.spent) AS spent FROM tg_ad_stats s JOIN tg_ads a ON a.ad_id = s.ad_id
               WHERE s.ts >= $1 AND s.ts < $2 AND a.ad_link_id IS NOT NULL GROUP BY a.ad_link_id)
           SELECT l.id, l.title, COALESCE(sp.spent, 0) AS spent,
                  (SELECT COUNT(*) FROM users u WHERE u.ad_link_id = l.id AND u.created_at >= $1 AND u.created_at < $2)::int AS users,
                  (SELECT COUNT(DISTINCT r.telegram_id) FROM payment_receipts r JOIN users u ON u.telegram_id = r.telegram_id
                    WHERE u.ad_link_id = l.id AND r.first_payment AND r.created_at >= $1 AND r.created_at < $2)::int AS paid
           FROM ad_links l LEFT JOIN spend sp ON sp.link = l.id
           WHERE l.id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL)""", start, end)
    moves = await pool.fetchval(
        "SELECT COUNT(*) FROM tg_ad_log WHERE who = 'bot' AND action = 'cpm' AND at >= $1 AND at < $2", start, end)
    rated = [dict(r) for r in links if _d(r["spent"]) > 0]
    for r in rated:
        r["per_user"] = _d(r["spent"]) / r["users"] if r["users"] else None
    with_users = sorted((r for r in rated if r["per_user"] is not None), key=lambda r: r["per_user"])
    no_users = [r for r in rated if r["per_user"] is None]
    currency = await pool.fetchval("SELECT MIN(currency) FROM tg_ads") or "TON"
    ending = []
    for a in await pool.fetch(
            """SELECT a.title, a.remaining, COALESCE((SELECT SUM(s.spent) FROM tg_ad_stats s WHERE s.ad_id = a.ad_id
                                                     AND s.ts >= $1::timestamptz - INTERVAL '1 day' AND s.ts < $1::timestamptz), 0) AS day_spent
               FROM tg_ads a WHERE a.gone_at IS NULL AND a.status = 'active' AND NOT COALESCE(a.is_paused, FALSE)""", end):
        left = days_left(a["remaining"], a["day_spent"])
        if left is not None and left < 2:
            ending.append({"title": a["title"], "days": left, "remaining": _d(a["remaining"])})
    return {"day": day, "views": tot["views"], "clicks": tot["clicks"], "spent": _d(tot["spent"]), "currency": currency,
            "users": sum(r["users"] for r in links), "paid": sum(r["paid"] for r in links), "moves": int(moves or 0),
            "ending": sorted(ending, key=lambda e: e["days"]),
            "best": with_users[0] if with_users else None,
            "worst": (no_users and max(no_users, key=lambda r: _d(r["spent"]))) or (with_users[-1] if len(with_users) > 1 else None)}


def format_digest(d: dict) -> str | None:
    if d["spent"] <= 0 and not d["users"]:
        return None
    cur = d["currency"]
    money = lambda v: f"{_round(_d(v))} {cur}"  # noqa: E731
    lines = [f"📣 <b>Реклама за {d['day'].strftime('%d.%m')}</b>", "",
             f"Потрачено: <b>{money(d['spent'])}</b>",
             f"Показы: <b>{d['views']:,}</b> · клики: <b>{d['clicks']:,}</b>".replace(",", " "),
             f"Пришли в бота: <b>{d['users']}</b> · оплатили впервые: <b>{d['paid']}</b>"]
    if d["users"] and d["spent"] > 0:
        lines.append(f"Цена человека: <b>{money(d['spent'] / d['users'])}</b>")
    if d.get("best"):
        b = d["best"]
        lines.append(f"\n👍 Лучшее: {b['title']} — {money(b['per_user'])} за человека")
    if d.get("worst"):
        w = d["worst"]
        tail = f"{money(w['per_user'])} за человека" if w.get("per_user") else f"{money(w['spent'])} и никого"
        lines.append(f"👎 Хуже всех: {w['title']} — {tail}")
    if d.get("ending"):
        lines.append("\n🪫 Скоро кончится бюджет:")
        for e in d["ending"]:
            left = f"~{max(1, round(e['days'] * 24))} ч" if e["days"] < 1 else f"~{round(e['days'], 1)} дн".replace(".", ",")
            lines.append(f"• {e['title']} — {money(e['remaining'])}, хватит на {left}")
    if d["moves"]:
        lines.append(f"\n🤖 Автоставка меняла цену {d['moves']} раз")
    return "\n".join(lines)


async def run_digest(bot, now: datetime | None = None) -> bool:
    now = (now or datetime.now(timezone.utc)).astimezone(MSK)
    if now.hour < 9:
        return False
    day = (now - timedelta(days=1)).date()
    sent = await db.get_job_report("tg_ads_digest") or {}
    if sent.get("day") == day.isoformat():
        return False
    text = format_digest(await digest_data(day))
    if text:
        for chat in await _targets():
            try:
                await bot.send_message(chat, text, parse_mode="HTML")
            except Exception:
                logger.warning("Сводка рекламы не ушла в %s", chat, exc_info=True)
    await db.set_job_report("tg_ads_digest", {"day": day.isoformat(), "sent": bool(text)})
    return bool(text)


async def tick() -> None:
    from app import runtime
    from app import tg_cabinet
    for name, step in (("автоставка", run_autobid), ("возврат остатков", run_refunds),
                       ("проверка площадок", tg_cabinet.recheck_places)):
        try:
            await step()
        except Exception:
            logger.exception("Telegram Ads: %s", name)
    bot = getattr(runtime, "bot", None)
    if bot is None:
        return
    from app import ad_followup
    for name, step in (("тревоги", run_alerts), ("сводка", run_digest), ("дожим с рекламы", ad_followup.send_due)):
        try:
            await step(bot)
        except Exception:
            logger.exception("Telegram Ads: %s", name)
