"""«Дожим с рекламы»: one message to a newcomer from a Telegram Ads link who has not connected an hour later.

The text is per ad link (Рост → Telegram Ads → объявление → «Приветствие и дожим»), so it carries on the ad's own
promise: whoever came from «соцсети не грузятся» reads about social networks. A link without the text sends nothing.
Only people who came between one and six hours ago are taken, so a deploy does not write to old ones; each person
gets it at most once. It goes through the same daily budget of optional messages as the other reminders.
"""
from __future__ import annotations

import logging

from app import db

logger = logging.getLogger("rm-shop.ad-followup")

AFTER_HOURS = 1
WITHIN_HOURS = 6
BATCH = 30

CLAIM_SQL = f"""
UPDATE users u SET ad_followup_at = NOW()
WHERE u.ad_followup_at IS NULL AND u.telegram_id IN (
    SELECT x.telegram_id FROM users x JOIN ad_links l ON l.id = x.ad_link_id
    WHERE x.ad_followup_at IS NULL AND COALESCE(TRIM(l.followup), '') <> ''
      AND x.first_online_at IS NULL AND x.blocked_at IS NULL AND x.bot_blocked_at IS NULL
      AND x.created_at <= NOW() - INTERVAL '{AFTER_HOURS} hours'
      AND x.created_at > NOW() - INTERVAL '{WITHIN_HOURS} hours'
      AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = x.telegram_id AND d.last_online_at IS NOT NULL)
    LIMIT {BATCH})
RETURNING u.telegram_id, u.first_name, u.ad_link_id,
          (SELECT l.followup FROM ad_links l WHERE l.id = u.ad_link_id) AS text,
          EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id) AS has_device
"""


def render(text: str, first_name: str | None) -> str:
    return str(text or "").replace("{name}", first_name or "").strip()


async def send_due(bot) -> int:
    from app.keyboards import onboarding_keyboard
    from app.nudge import _deliver
    sent = 0
    for r in await db._pool_req().fetch(CLAIM_SQL):
        body = render(r["text"], r["first_name"])
        if not body:
            continue
        try:
            ok = await _deliver(bot, kind="nudge_ad_followup", telegram_id=int(r["telegram_id"]),
                                first_name=r["first_name"], title="Дожим с рекламы", body=body,
                                reply_markup=onboarding_keyboard(has_device=bool(r["has_device"])),
                                extra={"ad_link_id": r["ad_link_id"]}, preserve=True)
        except Exception:
            logger.warning("Дожим с рекламы не ушёл tg %s", r["telegram_id"], exc_info=True)
            ok = False
        sent += bool(ok)
    return sent
