"""NFT gifts for real friends: real Telegram collectibles the owner transfers by hand.

A friend counts only when they are real: new to the bot via the link, paid VPN themselves with real money
(at least `min_rub`, from payment_receipts — never bonuses or gifts), then used VPN at least `online_days`
days out of the first `check_days` after paying and did not get the money back. Until then the friend is
«на проверке». The admin can reject any friend with a reason (same person, same card…): earned gifts that
are not given yet are then cancelled if the count drops below their step.

At 5 / 10 / 15 / 25 / 40 counted friends the person earns the gift shown on that step. The showcase rotates
every `period_days`: steps not earned yet get the next set, earned ones keep the gift they had. The gift waits
in the admin queue; the admin transfers it in Telegram and marks it «Выдано» with the NFT link.

The whole config lives in app_flags under `friend_nft` (JSON), edited in the admin. Turning it off brings the old
invite screen back in the cabinet; gifts already earned stay and can still be given.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html import escape

from app import db

logger = logging.getLogger("rm-shop.friend-nft")

KEY = "friend_nft"
PERIOD_KEY = "friend_nft_period"
LOOP_SECONDS = 600
F = "https://nft.fragment.com/gift/"

# Gifts on a black backdrop are shown really black, not Telegram's greyish Onyx Black.
BLACK = ["#2a2a2d", "#0e0e10", "#000000"]


def is_black(gift: dict) -> bool:
    return any(len(x) > 1 and x[0] == "Фон" and "black" in str(x[1]).lower() for x in (gift.get("a") or []))


def paint(gift: dict) -> dict:
    """The black backdrop is always pure black, also for gifts saved before."""
    if isinstance(gift, dict) and is_black(gift):
        gift = {**gift, "bg": list(BLACK)}
    return gift


def _g(slug: str, name: str, ton: int, bg: list[str], model: tuple, backdrop: tuple, symbol: tuple) -> dict:
    no = slug.rsplit("-", 1)[1]
    return {
        "slug": slug, "name": name, "no": no, "ton": ton, "bg": bg,
        "a": [["Модель", *model], ["Фон", *backdrop], ["Узор", *symbol]],
        "link": f"https://t.me/nft/{name.replace(' ', '').replace('-', '')}-{no}",
    }


# Cheap real collectibles (≈5–7 TON on Fragment); the last step is always the cheapest one on Onyx Black.
DEFAULT_SETS = [
    [
        _g("icecream-162005", "Ice Cream", 5, ["#b48ad6", "#794da0", "#3f2457"], ("Trio Scoop", "3%"), ("Grape", "1,5%"), ("Maple Leaf", "0,7%")),
        _g("instantramen-182697", "Instant Ramen", 5, ["#c48c74", "#73443b", "#3c221d"], ("Sewing Stew", "3%"), ("Chocolate", "1%"), ("Pickaxe", "0,5%")),
        _g("happybrownie-103336", "Happy Brownie", 6, ["#7dd0e0", "#528bc1", "#2a4a6e"], ("Toilet Bot", "2%"), ("Sky Blue", "1,2%"), ("Cactus", "0,2%")),
        _g("candycane-155038", "Candy Cane", 5, ["#a3abf8", "#855ed3", "#42297a"], ("Colorfunk", "2,6%"), ("Cyberpunk", "1,5%"), ("Champagne", "1,6%")),
        _g("lolpop-207408", "Lol Pop", 10, BLACK, ("Cappuccino", "1,2%"), ("Onyx Black", "1,5%"), ("Burger", "0,5%")),
    ],
    [
        _g("lunarsnake-185259", "Lunar Snake", 5, ["#72d4bb", "#3d95b9", "#1f4f66"], ("Blue Boa", "1,5%"), ("Pacific Cyan", "2%"), ("Shooting Star", "1,8%")),
        _g("spicedwine-2877", "Spiced Wine", 6, ["#c99490", "#814b51", "#44262b"], ("Color Theory", "1,3%"), ("Rosewood", "1,5%"), ("Pear", "0,4%")),
        _g("xmasstocking-72071", "Xmas Stocking", 5, ["#8fadff", "#6762e3", "#33307a"], ("Fresh Lemon", "2,2%"), ("Neon Blue", "1,2%"), ("Trophy", "0,5%")),
        _g("bigyear-62366", "Big Year", 5, ["#adc495", "#5b814b", "#2f4527"], ("Christmas Carol", "2,3%"), ("Pistachio", "1%"), ("Key", "0,5%")),
        _g("whipcupcake-247087", "Whip Cupcake", 10, BLACK, ("High Five", "3%"), ("Onyx Black", "1,2%"), ("Toy Bucket", "0,5%")),
    ],
    [
        _g("bdaycandle-257800", "B-Day Candle", 6, ["#adc495", "#5b814b", "#2f4527"], ("Cheers", "1,5%"), ("Pistachio", "1%"), ("Okami Wolf", "0,5%")),
        _g("petsnake-188646", "Pet Snake", 6, ["#e88a5a", "#b54a2c", "#5e2414"], ("King Cobra", "2%"), ("Burnt Sienna", "1,2%"), ("Candle", "0,6%")),
        _g("snakebox-123774", "Snake Box", 5, ["#7dd0e0", "#528bc1", "#2a4a6e"], ("Raspberry", "3%"), ("Sky Blue", "1,5%"), ("Thunderbird", "0,8%")),
        _g("deskcalendar-156558", "Desk Calendar", 7, ["#86c497", "#3d7970", "#1e3f3a"], ("The Nineties", "1,3%"), ("Pine Green", "2%"), ("Thief", "0,3%")),
        _g("vicecream-194020", "Vice Cream", 10, BLACK, ("Birthday", "3%"), ("Onyx Black", "1%"), ("Bottle", "0,4%")),
    ],
]

DEFAULT = {
    "enabled": False,
    "steps": [5, 10, 15, 25, 40],
    "period_days": 3,
    "min_rub": 100,
    "online_days": 3,
    "check_days": 7,
    "sets": DEFAULT_SETS,
    "epoch": None,  # start of the showcase rotation (ISO)
    "since": None,  # friends who came to the bot before this moment do not count (ISO)
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        when = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _dt(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)
    return _ts(str(value).replace("Z", "+00:00"))


def _iso(when) -> str | None:
    when = _dt(when)
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.isoformat()


def plural(n: int, one: str, few: str, many: str) -> str:
    m, h = n % 10, n % 100
    return one if m == 1 and h != 11 else few if 2 <= m <= 4 and not 12 <= h <= 14 else many


def friends_word(n: int) -> str:
    return f"{n} {plural(n, 'друг', 'друга', 'друзей')}"


# ---------------------------------------------------------------- config

def normalize(raw: dict | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT))
    for key, value in (raw or {}).items():
        if key in cfg:
            cfg[key] = value
    if isinstance(cfg.get("sets"), list):
        cfg["sets"] = [[paint(g) for g in gifts] if isinstance(gifts, list) else gifts for gifts in cfg["sets"]]
    return cfg


def validate(cfg: dict) -> dict:
    """Raise ValueError with a Russian message if the config can't be used."""
    try:
        steps = [int(x) for x in cfg.get("steps") or []]
    except (TypeError, ValueError):
        raise ValueError("Шаги — целые числа")
    if not steps or len(steps) > 8 or any(b <= a for a, b in zip(steps, steps[1:])) or steps[0] < 1:
        raise ValueError("Шаги должны расти: например 5, 10, 15, 25, 40")
    sets = cfg.get("sets") or []
    if not sets:
        raise ValueError("Нужен хотя бы один набор подарков")
    for n, gifts in enumerate(sets, 1):
        if not isinstance(gifts, list) or len(gifts) != len(steps):
            raise ValueError(f"В наборе {n} должно быть {len(steps)} подарков — по одному на шаг")
        for gift in gifts:
            if not isinstance(gift, dict) or not gift.get("slug") or not gift.get("name"):
                raise ValueError(f"В наборе {n} есть подарок без ссылки")
    out = dict(cfg)
    out["steps"] = steps
    out["period_days"] = max(1, min(30, int(cfg.get("period_days") or 3)))
    out["check_days"] = max(1, min(30, int(cfg.get("check_days") or 7)))
    out["online_days"] = max(0, min(out["check_days"], int(cfg.get("online_days") or 0)))
    out["min_rub"] = max(1, int(cfg.get("min_rub") or 100))
    out["enabled"] = bool(cfg.get("enabled"))
    return out


async def config() -> dict:
    raw = await db.get_kv(KEY)
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        logger.warning("Настройки NFT-подарков не читаются, беру по умолчанию")
        data = {}
    return normalize(data if isinstance(data, dict) else {})


async def save_config(patch: dict) -> dict:
    cfg = await config()
    for key in ("enabled", "steps", "period_days", "min_rub", "online_days", "check_days", "sets"):
        if key in patch:
            cfg[key] = patch[key]
    cfg = validate(cfg)
    now = _iso(_now())
    if cfg["enabled"]:
        cfg["since"] = cfg.get("since") or now
        cfg["epoch"] = cfg.get("epoch") or now
    await db.set_kv(KEY, json.dumps(cfg, ensure_ascii=False))
    return cfg


async def rotate_now() -> dict:
    """Start the next showcase right now (the admin's «Обновить витрину»)."""
    cfg = await config()
    period, _, _ = rotation(cfg)
    days = int(cfg["period_days"])
    cfg["epoch"] = _iso(_now() - timedelta(days=days * (period + 1), seconds=1))
    await db.set_kv(KEY, json.dumps(cfg, ensure_ascii=False))
    return cfg


def rotation(cfg: dict, now: datetime | None = None) -> tuple[int, int, datetime]:
    """(period number, index of the current set, when the next set comes)."""
    now = now or _now()
    epoch = _ts(cfg.get("epoch")) or now
    span = timedelta(days=max(1, int(cfg.get("period_days") or 3)))
    period = max(0, int((now - epoch) / span))
    return period, period % max(1, len(cfg.get("sets") or [1])), epoch + span * (period + 1)


def showcase(cfg: dict, now: datetime | None = None) -> list[dict]:
    _, idx, _ = rotation(cfg, now)
    return list(cfg["sets"][idx])


# ---------------------------------------------------------------- gifts from links

def parse_link(link: str) -> tuple[str, str] | None:
    """t.me/nft/IceCream-162005 or nft.fragment.com/gift/icecream-162005… → (slug, page name)."""
    text = (link or "").strip()
    m = re.search(r"(?:t\.me/nft/|fragment\.com/gift/)([A-Za-z0-9]+)-(\d+)", text)
    if not m:
        m = re.fullmatch(r"([A-Za-z0-9]+)-(\d+)", text)
    if not m:
        return None
    return f"{m.group(1).lower()}-{m.group(2)}", f"{m.group(1)}-{m.group(2)}"


def _hex(rgb: list[float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def backdrop_colors(lottie: dict) -> list[str] | None:
    """The gift's Telegram backdrop: the gradient of the Background layer → [light, middle, dark]."""
    stops: list[float] | None = None

    def walk(node) -> None:
        nonlocal stops
        if stops is not None:
            return
        if isinstance(node, dict):
            if node.get("ty") == "gf":
                k = ((node.get("g") or {}).get("k") or {}).get("k")
                if isinstance(k, list) and len(k) >= 8 and all(isinstance(x, (int, float)) for x in k[:8]):
                    stops = k
                    return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for layer in lottie.get("layers") or []:
        if layer.get("nm") == "Background":
            walk(layer)
    if not stops:
        return None
    a = [c * 255 for c in stops[1:4]]
    b = [c * 255 for c in stops[5:8]]
    return [_hex([c + (255 - c) * 0.15 for c in a]), _hex(b), _hex([c * 0.5 for c in b])]


def page_attrs(html: str) -> tuple[str | None, list[list[str]]]:
    title = None
    m = re.search(r'og:title" content="([^"#]+)#?', html)
    if m:
        title = m.group(1).strip()
    names = {"Model": "Модель", "Backdrop": "Фон", "Symbol": "Узор"}
    attrs = []
    for key, value, pct in re.findall(r"<th>(Model|Backdrop|Symbol)</th><td>([^<]*?)\s*<mark>([^<]*)</mark>", html):
        attrs.append([names[key], value.strip(), pct.strip().replace(".", ",")])
    return title, attrs


async def fetch_gift(link: str, ton: int | None = None) -> dict:
    """Everything the cabinet shows for one gift, read from its Telegram page and Fragment animation."""
    import aiohttp

    parsed = parse_link(link)
    if not parsed:
        raise ValueError("Нужна ссылка вида t.me/nft/IceCream-162005")
    slug, page = parsed
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.get(f"https://t.me/nft/{page}") as resp:
            html = await resp.text() if resp.status == 200 else ""
        async with http.get(f"{F}{slug}.lottie.json") as resp:
            if resp.status != 200:
                raise ValueError(f"Fragment не отдал подарок {slug}")
            lottie = await resp.json(content_type=None)
    title, attrs = page_attrs(html)
    if not attrs:
        raise ValueError(f"Не нашёл подарок по ссылке {link}: проверьте номер")
    name = title or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", page.rsplit("-", 1)[0])
    return paint({
        "slug": slug, "name": name, "no": slug.rsplit("-", 1)[1], "ton": int(ton or 0),
        "bg": backdrop_colors(lottie) or BLACK, "a": attrs, "link": f"https://t.me/nft/{page}",
    })


# ---------------------------------------------------------------- data

CHECKS_INSERT = """
WITH paid AS (
    SELECT r.telegram_id, MIN(r.created_at) FILTER (WHERE r.run >= $2) AS paid_at
    FROM (
        SELECT p.telegram_id, p.created_at,
               SUM(p.amount) OVER (PARTITION BY p.telegram_id ORDER BY p.created_at, p.payment_key) AS run
        FROM payment_receipts p JOIN users x ON x.telegram_id = p.telegram_id
        WHERE x.referred_by IS NOT NULL AND x.created_at >= $1
    ) r
    GROUP BY r.telegram_id
)
INSERT INTO friend_nft_checks (invitee_id, referrer_id, paid_at)
SELECT u.telegram_id, u.referred_by, p.paid_at
FROM users u
JOIN paid p ON p.telegram_id = u.telegram_id
JOIN users ref ON ref.telegram_id = u.referred_by
WHERE p.paid_at IS NOT NULL AND u.referred_by <> u.telegram_id AND u.created_at >= $1
ON CONFLICT DO NOTHING
RETURNING invitee_id, referrer_id, paid_at
"""

CHECKS_DUE = """
SELECT c.invitee_id, c.referrer_id, c.paid_at, u.first_name, u.blocked_at,
       (SELECT COUNT(*) FROM online_days o
        WHERE o.telegram_id = c.invitee_id
          AND o.day >= (c.paid_at AT TIME ZONE 'UTC')::date
          AND o.day < (c.paid_at AT TIME ZONE 'UTC')::date + $1::int)::int AS online,
       EXISTS (SELECT 1 FROM pay_orders o WHERE o.telegram_id = c.invitee_id AND o.status = 'refunded') AS refunded
FROM friend_nft_checks c JOIN users u ON u.telegram_id = c.invitee_id
WHERE c.status = 'check' AND c.paid_at <= NOW() - $1::int * INTERVAL '1 day'
ORDER BY c.paid_at
LIMIT 200
"""


def verdict(row: dict, cfg: dict) -> tuple[str, str | None]:
    if row.get("blocked_at"):
        return "bad", "аккаунт заблокирован"
    if row.get("refunded"):
        return "bad", "платёж вернули"
    need, days, online = int(cfg["online_days"]), int(cfg["check_days"]), int(row.get("online") or 0)
    if online < need:
        if not online:
            return "bad", f"за {days} {plural(days, 'день', 'дня', 'дней')} ни разу не включал VPN"
        return "bad", f"включал VPN {online} {plural(online, 'день', 'дня', 'дней')} из {days}, нужно {need}"
    return "ok", None


async def counted(telegram_id: int) -> int:
    return int(await db._pool_req().fetchval(
        "SELECT COUNT(*) FROM friend_nft_checks WHERE referrer_id = $1 AND status = 'ok'", int(telegram_id)) or 0)


async def rewards_of(telegram_id: int) -> list[dict]:
    rows = await db._pool_req().fetch(
        """SELECT id, need, gift, status, nft_link, created_at, given_at FROM friend_nft_rewards
           WHERE telegram_id = $1 AND status <> 'cancelled' ORDER BY need""", int(telegram_id))
    out = []
    for r in rows:
        gift = r["gift"]
        out.append({
            "id": int(r["id"]), "need": int(r["need"]),
            "gift": paint(json.loads(gift) if isinstance(gift, str) else dict(gift)),
            "status": r["status"], "nft_link": r["nft_link"],
            "created_at": _iso(r["created_at"]), "given_at": _iso(r["given_at"]),
        })
    return out


async def grant_due(telegram_id: int, cfg: dict) -> list[dict]:
    """Create the rewards for every step the person reached and does not have yet."""
    n = await counted(telegram_id)
    have = {r["need"] for r in await rewards_of(telegram_id)}
    gifts = showcase(cfg)
    made = []
    for i, need in enumerate(cfg["steps"]):
        if n < need or need in have:
            continue
        gift = gifts[i]
        row = await db._pool_req().fetchrow(
            """INSERT INTO friend_nft_rewards (telegram_id, need, gift) VALUES ($1, $2, $3::jsonb)
               ON CONFLICT (telegram_id, need) WHERE status <> 'cancelled' DO NOTHING RETURNING id""",
            int(telegram_id), int(need), json.dumps(gift, ensure_ascii=False))
        if row:
            made.append({"id": int(row["id"]), "need": need, "gift": gift})
    return made


async def cancel_unreachable(telegram_id: int) -> list[dict]:
    """After a friend is taken off: gifts not given yet above the new count are cancelled."""
    n = await counted(telegram_id)
    rows = await db._pool_req().fetch(
        """UPDATE friend_nft_rewards SET status = 'cancelled', cancelled_at = NOW()
           WHERE telegram_id = $1 AND status = 'wait' AND need > $2 RETURNING id, need, gift""",
        int(telegram_id), n)
    return [dict(r) for r in rows]


def _gift_of(row: dict) -> dict:
    gift = row.get("gift")
    return json.loads(gift) if isinstance(gift, str) else dict(gift or {})


# ---------------------------------------------------------------- what the cabinet gets

async def user_view(telegram_id: int, cfg: dict | None = None) -> dict:
    cfg = cfg or await config()
    rewards = await rewards_of(telegram_id)
    if not cfg["enabled"]:
        return {"enabled": False, "rewards": rewards}
    now = _now()
    period, _, next_at = rotation(cfg, now)
    gifts = showcase(cfg, now)
    by_need = {r["need"]: r for r in rewards}
    steps = []
    for i, need in enumerate(cfg["steps"]):
        r = by_need.get(need)
        steps.append({
            "need": need,
            "gift": r["gift"] if r else gifts[i],
            "state": ("got" if r["status"] == "given" else "wait") if r else "none",
            "reward_id": r["id"] if r else None,
            "nft_link": r["nft_link"] if r else None,
        })
    since = _ts(cfg.get("since"))
    rows = await db._pool_req().fetch(
        """SELECT u.telegram_id, u.first_name, u.created_at, c.status, c.reason, c.paid_at
           FROM users u LEFT JOIN friend_nft_checks c ON c.invitee_id = u.telegram_id
           WHERE u.referred_by = $1 AND u.telegram_id <> $1
           ORDER BY COALESCE(c.paid_at, u.created_at) DESC LIMIT 60""", int(telegram_id))
    days = int(cfg["check_days"])
    friends = []
    for r in rows:
        name = (str(r["first_name"] or "").strip() or "Друг")[:40]
        if r["status"]:
            paid = _dt(r["paid_at"]) or now
            day = max(0, min(days, int((now - paid).total_seconds() // 86400)))
            friends.append({"name": name, "st": r["status"], "day": day, "reason": r["reason"]})
        else:
            created = _dt(r["created_at"])
            old = bool(since and created and created < since)
            friends.append({"name": name, "st": "old" if old else "pay", "day": 0, "reason": None})
    checking = [f for f in friends if f["st"] == "check"]
    return {
        "enabled": True,
        "steps": steps,
        "counted": sum(1 for f in friends if f["st"] == "ok"),
        "checking": len(checking),
        "checking_left": min((days - f["day"] for f in checking), default=0),
        "friends": friends,
        "rewards": rewards,
        "period": period,
        "period_days": int(cfg["period_days"]),
        "next_at": _iso(next_at),
        "check_days": days,
        "online_days": int(cfg["online_days"]),
        "min_rub": int(cfg["min_rub"]),
    }


# ---------------------------------------------------------------- bot messages

def _button(text: str = "🎁 Подарки за друзей"):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from app.keyboards import mini_app_screen

    app = mini_app_screen("friends")
    if not app:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, web_app=app, style="success")]])


async def _say(bot, chat: int, text: str, markup=None) -> bool:
    if bot is None:
        return False
    try:
        await bot.send_message(int(chat), text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        return True
    except Exception:
        logger.info("NFT-сообщение не дошло до %s", chat, exc_info=True)
        return False


def _next_line(n: int, cfg: dict, gifts: list[dict]) -> str:
    for i, need in enumerate(cfg["steps"]):
        if n < need:
            return f"До подарка «{escape(gifts[i]['name'])}» — ещё {friends_word(need - n)}."
    return "Все подарки собраны — спасибо, что зовёте друзей 💚"


def text_checking(name: str, cfg: dict) -> str:
    days = int(cfg["check_days"])
    return (f"🕐 <b>{escape(name)} оплатил(а) VPN по вашей ссылке.</b>\n"
            f"Засчитаем через {days} {plural(days, 'день', 'дня', 'дней')}, если {escape(name)} будет пользоваться VPN.")


def text_counted(names: list[str], n: int, cfg: dict, gifts: list[dict]) -> str:
    head = "Засчитан" if len(names) == 1 else "Засчитаны"
    return (f"✅ <b>{head}: {escape(', '.join(names))}.</b> Всего настоящих друзей: {n}.\n"
            + _next_line(n, cfg, gifts))


def text_rejected(name: str, reason: str) -> str:
    return f"ℹ️ <b>{escape(name)}</b> не засчитан(а): {escape(reason)}."


def text_earned(need: int, gift: dict) -> str:
    return (f"🎉 <b>Это ваш {need}-й настоящий друг!</b>\n"
            f"Вам положен NFT-подарок <b>«{escape(gift['name'])}»</b>. Отправим его в ваш профиль Telegram в течение суток.")


def text_given(gift: dict) -> str:
    return f"💎 <b>Подарок у вас!</b> «{escape(gift['name'])} #{escape(str(gift.get('no') or ''))}» уже в профиле Telegram."


def text_rotated(names: list[str], cfg: dict) -> str:
    days = int(cfg["period_days"])
    return (f"🔄 <b>Новые NFT-подарки за друзей!</b>\nТеперь можно получить: {escape(', '.join(names))}.\n"
            f"Следующее обновление через {days} {plural(days, 'день', 'дня', 'дней')}.")


async def _admin_alert(bot, telegram_id: int, need: int, gift: dict) -> None:
    from app.stuck_alert import _targets

    user = await db._pool_req().fetchrow("SELECT telegram_id, first_name, username FROM users WHERE telegram_id=$1", int(telegram_id))
    from app.live import _who

    text = (f"💎 <b>Выдать NFT-подарок</b>\n\n{_who(dict(user) if user else None, telegram_id)}\n"
            f"Заработал «{escape(gift['name'])} #{escape(str(gift.get('no') or ''))}» за {friends_word(need)}"
            + (f" · ~{int(gift['ton'])} TON" if gift.get("ton") else "")
            + f"\n{escape(gift.get('link') or '')}\n\nПосле передачи отметьте «Выдано» в админке → Подарки за друзей.")
    for chat in await _targets():
        await _say(bot, chat, text)


# ---------------------------------------------------------------- the loop

async def run_once(bot) -> dict:
    cfg = await config()
    stats = {"checks": 0, "ok": 0, "bad": 0, "rewards": 0}
    if not cfg["enabled"]:
        return stats
    pool = db._pool_req()
    since = _ts(cfg.get("since")) or _now()
    for row in await pool.fetch(CHECKS_INSERT, since, int(cfg["min_rub"])):
        stats["checks"] += 1
        name = await pool.fetchval("SELECT first_name FROM users WHERE telegram_id=$1", row["invitee_id"]) or "Друг"
        await _say(bot, row["referrer_id"], text_checking(str(name), cfg), _button())
    counted_by: dict[int, list[str]] = {}
    for row in await pool.fetch(CHECKS_DUE, int(cfg["check_days"])):
        status, reason = verdict(dict(row), cfg)
        done = await pool.fetchval(
            """UPDATE friend_nft_checks SET status = $2, reason = $3, decided_at = NOW()
               WHERE invitee_id = $1 AND status = 'check' RETURNING invitee_id""",
            row["invitee_id"], status, reason)
        if not done:
            continue
        name = (str(row["first_name"] or "").strip() or "Друг")
        if status == "ok":
            stats["ok"] += 1
            counted_by.setdefault(int(row["referrer_id"]), []).append(name)
        else:
            stats["bad"] += 1
            await _say(bot, row["referrer_id"], text_rejected(name, reason or "не прошёл проверку"))
    gifts = showcase(cfg)
    for referrer, names in counted_by.items():
        made = await grant_due(referrer, cfg)
        n = await counted(referrer)
        if not made:
            await _say(bot, referrer, text_counted(names, n, cfg, gifts), _button())
        for item in made:
            stats["rewards"] += 1
            await _say(bot, referrer, text_earned(item["need"], item["gift"]), _button("🎁 Посмотреть подарок"))
            await _admin_alert(bot, referrer, item["need"], item["gift"])
    await _rotation_tick(bot, cfg)
    return stats


async def _rotation_tick(bot, cfg: dict) -> None:
    period, _, _ = rotation(cfg)
    last = await db.get_kv(PERIOD_KEY)
    if last == str(period):
        return
    await db.set_kv(PERIOD_KEY, str(period))
    if last == "":
        return  # the first run only remembers the period
    asyncio.create_task(announce(bot, cfg), name="friend-nft-announce")


async def announce(bot, cfg: dict) -> int:
    """Tell people who invite friends that the showcase changed (only the steps they still can earn)."""
    gifts = showcase(cfg)
    rows = await db._pool_req().fetch(
        """SELECT u.telegram_id,
                  ARRAY(SELECT r.need FROM friend_nft_rewards r WHERE r.telegram_id = u.telegram_id AND r.status <> 'cancelled') AS have
           FROM users u
           WHERE EXISTS (SELECT 1 FROM users f WHERE f.referred_by = u.telegram_id)
             AND u.blocked_at IS NULL AND u.bot_blocked_at IS NULL AND u.tg_deleted_at IS NULL
             AND u.quiet_notifications = FALSE""")
    sent = 0
    for row in rows:
        have = set(row["have"] or [])
        names = [gifts[i]["name"] for i, need in enumerate(cfg["steps"]) if need not in have]
        if not names:
            continue
        if await _say(bot, row["telegram_id"], text_rotated(names, cfg), _button("🎁 Посмотреть подарки")):
            sent += 1
        await asyncio.sleep(0.05)
    return sent


async def loop(bot) -> None:
    while True:
        try:
            await run_once(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("NFT-подарки за друзей")
        await asyncio.sleep(LOOP_SECONDS)


# ---------------------------------------------------------------- admin

async def admin_overview() -> dict:
    cfg = await config()
    period, idx, next_at = rotation(cfg)
    pool = db._pool_req()
    queue = await pool.fetch(
        """SELECT r.id, r.telegram_id, r.need, r.gift, r.status, r.nft_link, r.created_at, r.given_at,
                  u.first_name, u.username,
                  (SELECT COUNT(*) FROM friend_nft_checks c WHERE c.referrer_id = r.telegram_id AND c.status = 'ok')::int AS counted
           FROM friend_nft_rewards r JOIN users u ON u.telegram_id = r.telegram_id
           WHERE r.status = 'wait' OR r.given_at > NOW() - INTERVAL '30 days'
           ORDER BY (r.status = 'wait') DESC, r.created_at DESC LIMIT 200""")
    checks = await pool.fetch(
        """SELECT c.invitee_id, c.referrer_id, c.paid_at, c.status, c.reason, c.by_admin, c.decided_at,
                  f.first_name AS friend_name, f.username AS friend_username,
                  r.first_name AS referrer_name, r.username AS referrer_username,
                  (SELECT COALESCE(SUM(p.amount), 0) FROM payment_receipts p WHERE p.telegram_id = c.invitee_id)::int AS paid_rub,
                  (SELECT COUNT(*) FROM online_days o WHERE o.telegram_id = c.invitee_id
                     AND o.day >= (c.paid_at AT TIME ZONE 'UTC')::date)::int AS online
           FROM friend_nft_checks c
           JOIN users f ON f.telegram_id = c.invitee_id
           JOIN users r ON r.telegram_id = c.referrer_id
           ORDER BY c.created_at DESC LIMIT 300""")
    totals = await pool.fetchrow(
        """SELECT COUNT(*) FILTER (WHERE status='check')::int AS checking,
                  COUNT(*) FILTER (WHERE status='ok')::int AS ok,
                  COUNT(*) FILTER (WHERE status='bad')::int AS bad FROM friend_nft_checks""")
    given = await pool.fetchrow(
        """SELECT COUNT(*) FILTER (WHERE status='wait')::int AS wait,
                  COUNT(*) FILTER (WHERE status='given')::int AS given,
                  COALESCE(SUM((gift->>'ton')::numeric) FILTER (WHERE status='given'), 0)::int AS ton
           FROM friend_nft_rewards""")

    def rec(row) -> dict:
        out = dict(row)
        for key, value in list(out.items()):
            if isinstance(value, datetime) or key.endswith("_at"):
                out[key] = _iso(value)
        if "gift" in out:
            out["gift"] = _gift_of(out)
        return out

    return {
        "config": cfg,
        "rotation": {"period": period, "index": idx, "next_at": _iso(next_at),
                     "next_index": (idx + 1) % max(1, len(cfg["sets"]))},
        "queue": [rec(r) for r in queue],
        "checks": [rec(r) for r in checks],
        "totals": {**dict(totals or {}), **dict(given or {})},
    }


async def give(bot, reward_id: int, link: str) -> dict:
    link = (link or "").strip()
    if link and not re.match(r"^https?://", link):
        link = "https://" + link
    row = await db._pool_req().fetchrow(
        """UPDATE friend_nft_rewards SET status = 'given', given_at = NOW(), nft_link = NULLIF($2, '')
           WHERE id = $1 AND status = 'wait' RETURNING telegram_id, gift, nft_link""", int(reward_id), link)
    if not row:
        raise ValueError("Этот подарок уже выдан или отменён")
    gift = _gift_of(dict(row))
    markup = None
    if row["nft_link"]:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Открыть подарок", url=row["nft_link"])]])
    await _say(bot, row["telegram_id"], text_given(gift), markup or _button("Пригласить ещё"))
    return {"ok": True}


async def cancel_reward(reward_id: int, note: str = "") -> dict:
    row = await db._pool_req().fetchrow(
        """UPDATE friend_nft_rewards SET status = 'cancelled', cancelled_at = NOW(), note = NULLIF($2, '')
           WHERE id = $1 AND status = 'wait' RETURNING id""", int(reward_id), (note or "").strip()[:300])
    if not row:
        raise ValueError("Этот подарок уже выдан или отменён")
    return {"ok": True}


async def set_friend(bot, invitee_id: int, status: str, reason: str = "") -> dict:
    """The admin counts a friend or takes them off with a reason; earned gifts follow the new count."""
    if status not in {"ok", "bad"}:
        raise ValueError("Статус: ok или bad")
    reason = (reason or "").strip()[:200]
    if status == "bad" and not reason:
        raise ValueError("Напишите причину — её увидит пригласивший")
    row = await db._pool_req().fetchrow(
        """UPDATE friend_nft_checks SET status = $2, reason = $3, by_admin = TRUE, decided_at = NOW()
           WHERE invitee_id = $1 RETURNING referrer_id,
           (SELECT first_name FROM users WHERE telegram_id = $1) AS name""",
        int(invitee_id), status, reason if status == "bad" else None)
    if not row:
        raise ValueError("Такого друга нет в проверке")
    referrer, name = int(row["referrer_id"]), str(row["name"] or "").strip() or "Друг"
    cfg = await config()
    if status == "bad":
        cancelled = await cancel_unreachable(referrer)
        await _say(bot, referrer, text_rejected(name, reason)
                   + ("\nПодарок за этот шаг снят." if cancelled else ""), _button())
        return {"ok": True, "cancelled": len(cancelled)}
    made = await grant_due(referrer, cfg) if cfg["enabled"] else []
    for item in made:
        await _say(bot, referrer, text_earned(item["need"], item["gift"]), _button("🎁 Посмотреть подарок"))
    if not made:
        await _say(bot, referrer, text_counted([name], await counted(referrer), cfg, showcase(cfg)), _button())
    return {"ok": True, "rewards": len(made)}
