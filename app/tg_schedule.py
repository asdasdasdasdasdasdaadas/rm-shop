"""«Часы показа»: once a week the bot offers to switch off the hours that bring nobody from Telegram Ads.

It looks at the last 30 days by Moscow hour: views (what was paid for), people who came by the ads' links and their
first payments. Hours that had views but brought nobody, while at least MIN_PEOPLE came overall, are offered for
switching off on every running ad without a schedule of its own. The admin gets one message on Monday after 10:00
with «Применить» — the bot never applies it by itself, and Telegram may send an ad to moderation after the change.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import db, tg_autobid

logger = logging.getLogger("rm-shop.tg-schedule")

MIN_PEOPLE = 30       # people from the ads in 30 days before the hours mean anything
MIN_HOURS_KEPT = 8    # never offer to keep fewer hours than this a day
REPORT = "tg_ads_schedule_offer"


def offer_from(views_by_hour: list[int], people_by_hour: list[int], spent_by_hour: list[float]) -> dict | None:
    """{off: [hours], views, spent} — hours with views and nobody who came; None when there is nothing to offer."""
    if sum(people_by_hour) < MIN_PEOPLE:
        return None
    off = [h for h in range(24) if views_by_hour[h] > 0 and people_by_hour[h] == 0]
    if not off or 24 - len(off) < MIN_HOURS_KEPT:
        return None
    return {"off": off, "views": sum(views_by_hour[h] for h in off), "spent": round(sum(spent_by_hour[h] for h in off), 2)}


def mask_without(off: list[int]) -> list[int]:
    keep = sum(1 << h for h in range(24) if h not in off)
    return [keep] * 7


def ranges(hours: list[int]) -> str:
    """[2, 3, 4, 7] → «2:00–5:00, 7:00–8:00»."""
    out, start = [], None
    for h in range(25):
        if h < 24 and h in hours:
            start = h if start is None else start
        elif start is not None:
            out.append(f"{start}:00–{h}:00")
            start = None
    return ", ".join(out)


async def current_offer() -> dict | None:
    pool = db._pool_req()
    since = datetime.now(timezone.utc) - timedelta(days=30)
    hour = "EXTRACT(HOUR FROM {} AT TIME ZONE 'Europe/Moscow')::int"
    views, people, spent = [0] * 24, [0] * 24, [0.0] * 24
    for r in await pool.fetch(f"SELECT {hour.format('ts')} AS h, SUM(views)::int AS v, SUM(spent) AS s "
                              "FROM tg_ad_stats WHERE ts >= $1 GROUP BY 1", since):
        views[r["h"]] += int(r["v"] or 0)
        spent[r["h"]] += float(r["s"] or 0)
    for r in await pool.fetch(
            f"""SELECT {hour.format('u.created_at')} AS h, COUNT(*)::int AS n FROM users u WHERE u.created_at >= $1
                AND u.ad_link_id IN (SELECT ad_link_id FROM tg_ads WHERE ad_link_id IS NOT NULL) GROUP BY 1""", since):
        people[r["h"]] += int(r["n"])
    offer = offer_from(views, people, spent)
    if not offer:
        return None
    ads = await pool.fetch(
        """SELECT ad_id, title FROM tg_ads WHERE gone_at IS NULL AND status = 'active' AND schedule IS NULL
           ORDER BY ad_id""")
    if not ads:
        return None
    currency = await pool.fetchval("SELECT MIN(currency) FROM tg_ads") or "TON"
    return {**offer, "currency": currency, "ads": [{"ad_id": int(a["ad_id"]), "title": a["title"]} for a in ads]}


def offer_text(o: dict) -> str:
    names = ", ".join(a["title"] or str(a["ad_id"]) for a in o["ads"][:6]) + (" и др." if len(o["ads"]) > 6 else "")
    return (f"🕒 <b>Часы показа</b>\n\nЗа 30 дней в {ranges(o['off'])} по Москве с рекламы не пришёл никто, а показов было "
            f"{o['views']:,}".replace(",", " ") + f" — это {o['spent']} {o['currency']}.\n\nОтключить эти часы у объявлений"
            f" без расписания: {names}?\n\nTelegram может отправить объявления на модерацию после смены расписания.")


async def run_offer(bot, now: datetime | None = None) -> bool:
    now = (now or datetime.now(timezone.utc)).astimezone(tg_autobid.MSK)
    if now.weekday() != 0 or now.hour < 10:
        return False
    week = now.date().isoformat()
    last = await db.get_job_report(REPORT) or {}
    if last.get("week") == week:
        return False
    offer = await current_offer()
    await db.set_job_report(REPORT, {"week": week, "offer": offer, "applied": False})
    if not offer:
        return False
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Применить", callback_data="tga_sched:apply"),
        InlineKeyboardButton(text="Не надо", callback_data="tga_sched:skip"),
    ]])
    for chat in await tg_autobid._targets():
        try:
            await bot.send_message(chat, offer_text(offer), parse_mode="HTML", reply_markup=markup)
        except Exception:
            logger.warning("Предложение расписания не ушло в %s", chat, exc_info=True)
    return True


async def apply_offer() -> str:
    """Puts the offered hours on the ads from the offer. Returns what to say under the message."""
    from app import tg_cabinet
    saved = await db.get_job_report(REPORT) or {}
    offer = saved.get("offer")
    if not offer:
        return "Предложение устарело"
    if saved.get("applied"):
        return "Уже применено"
    mask = mask_without(offer["off"])
    done, review, failed = 0, 0, []
    for a in offer["ads"]:
        try:
            got = await tg_cabinet.set_schedule(a["ad_id"], mask)
            done += 1
            review += bool(got.get("review"))
        except Exception as exc:
            failed.append(f"{a['title'] or a['ad_id']}: {str(exc)[:60]}")
    await db.set_job_report(REPORT, {**saved, "applied": True})
    text = f"Расписание поставлено у {done} объявлений"
    if review:
        text += f", {review} ушли на модерацию"
    if failed:
        text += ". Не вышло: " + "; ".join(failed)
    return text


async def skip_offer() -> str:
    saved = await db.get_job_report(REPORT) or {}
    await db.set_job_report(REPORT, {**saved, "applied": True})
    return "Оставлено круглосуточно"
