from __future__ import annotations

import asyncio
import json
import logging
import re
from html import escape
from typing import Any

from aiogram import Bot, Router
from aiogram.types import ChatMemberUpdated

from app import db, runtime
from app.config import get_settings
from app.button_icons import PINNED_ICONS
from app.remnawave import panel_first_connected_at, panel_online_at, panel_used_traffic_bytes, panel_lifetime_traffic_bytes
from app.tg_err import telegram_fail_reason

logger = logging.getLogger("rm-shop.live")
router = Router()
HINT_KEY = "live_chat_hint"
_C_LINK = re.compile(r"(?:t\.me|telegram\.me)/c/(\d+)", re.I)


def parse_live_chat_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 200:
        raise ValueError("Живой канал: слишком длинная строка")
    low = text.lower()
    if "joinchat" in low or "t.me/+" in low or "telegram.me/+" in low or text.startswith("+"):
        raise ValueError(
            "Приватный канал: ссылка-приглашение не подходит. "
            "Добавьте бота администратором канала — id появится в форме. "
            "Либо вставьте id вида -100... или ссылку t.me/c/..."
        )
    found = _C_LINK.search(text.replace("https://", "").replace("http://", ""))
    if found:
        return "-100" + found.group(1)
    if re.match(r"https?://", text, re.I) or low.startswith("t.me/"):
        path = text.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        text = path
    if text.lstrip("-").isdigit():
        if text.startswith("-"):
            return text
        if text.startswith("100") and len(text) >= 12:
            return "-" + text
        return text
    handle = text[1:] if text.startswith("@") else text
    handle = handle.strip()
    if handle and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,}", handle):
        return "@" + handle
    raise ValueError(
        "Публичный канал: @username. Приватный: id -100... или ссылка t.me/c/.... "
        "Не пригласительная ссылка."
    )


def _chat_id():
    try:
        raw = parse_live_chat_id(getattr(get_settings(), "admin_live_chat_id", "") or "")
    except ValueError:
        raw = str(getattr(get_settings(), "admin_live_chat_id", "") or "").strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        return int(raw)
    return raw


def _who(user: dict | None, telegram_id: int | None = None) -> str:
    data = user or {}
    tid = int(data.get("telegram_id") or telegram_id or 0)
    name = escape(str(data.get("first_name") or "без имени"))
    handle = str(data.get("username") or "").lstrip("@").strip()
    nick = f"@{escape(handle)}" if handle else "нет username"
    if tid:
        mention = f'<a href="tg://user?id={tid}">{name}</a>'
        return f"{mention} · {nick} · <code>{tid}</code>"
    return f"{name} · {nick}"


async def _send(text: str) -> None:
    chat = _chat_id()
    bot: Bot | None = getattr(runtime, "bot", None)
    if not chat:
        return
    if bot is None:
        logger.debug("Живой канал: бот ещё не готов")
        return
    try:
        await bot.send_message(chat, text, parse_mode="HTML")
    except Exception as exc:
        logger.warning("Живой канал: не отправилось (%s)", telegram_fail_reason(exc))


def post(text: str) -> None:
    if not _chat_id():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_send(text))


def _heading(kind: str, emoji: str, title: str) -> str:
    return f'<tg-emoji emoji-id="{PINNED_ICONS[kind]}">{emoji}</tg-emoji> <b>{escape(title)}</b>'


def paid(user: dict | None, *, amount: int, title: str, repeat: bool) -> None:
    heading = _heading("retry", "🔄", "Повторная оплата") if repeat else _heading("pay", "💰", "Первая оплата")
    bits = [heading, "", _who(user)]
    if amount:
        formatted = f"{amount:,}".replace(",", " ")
        bits.extend(["", f"Сумма: <b>{formatted} ₽</b>"])
    elif title:
        bits.extend(["", f"Тариф: <b>{escape(str(title))}</b>"])
    post("\n".join(bits))


_ACTION_TITLES = {
    'invite': ('invite', '👥', 'Пользователь нажал «Пригласить друзей»'),
    'share': ('invite', '👥', 'Пользователь нажал «Поделиться ссылкой»'),
    'copy': ('copy', '📋', 'Пользователь нажал «Скопировать приглашение»'),
    'about': ('about', 'ℹ️', 'Пользователь нажал «О сервисе»'),
    'cabinet': ('cabinet', '👤', 'Пользователь открыл личный кабинет'),
    'gift_view': ('gift', '🎁', 'Пользователь открыл экран подарка'),
}


REFERRAL_ACTIONS = {'invite', 'share', 'copy'}


async def _post_referral_action(user: dict, action: str, source: str) -> None:
    """Every referral click goes to the live channel right away, not only into the daily digest."""
    if not user.get('first_name') and not user.get('username'):
        try:
            user = {**(await db.get_user(int(user['telegram_id'])) or {}), **{k: v for k, v in user.items() if v}}
        except Exception:
            logger.debug('Could not load user for referral notice', exc_info=True)
    kind, emoji, title = _ACTION_TITLES[action]
    where = 'в боте' if source == 'bot' else 'в личном кабинете'
    # Fire and forget: the user's tap must not wait for the channel message.
    post(_heading(kind, emoji, title) + '\n\n' + _who(user) + f'\n<b>Где:</b> {where}')


async def user_action(user: dict, action: str, *, source: str = 'bot') -> None:
    if action not in _ACTION_TITLES:
        return
    if action in {'invite', 'share', 'copy'}:
        try:
            from app.referral_followup import record_interest
            await record_interest(int(user['telegram_id']))
        except Exception:
            logger.exception('Could not record referral interest')
    if not _chat_id():
        return
    if action in REFERRAL_ACTIONS:
        await _post_referral_action(user, action, source)
    try:
        from app.activity_digest import record
        await record(int(user['telegram_id']), action, source)
    except Exception:
        logger.debug('Could not record activity for daily digest', exc_info=True)


async def web_user_action(telegram_id: int, action: str) -> None:
    await user_action({'telegram_id': telegram_id}, action, source='web')


def invited(referrer: dict | None, invitee: dict | None) -> None:
    post(
        _heading("invite", "👥", "Новое приглашение") + "\n\n"
        f"<b>Кто:</b> {_who(referrer)}\n"
        f"<b>Кого:</b> {_who(invitee)}"
    )


def story_posted(user: dict | None) -> None:
    post(_heading("check", "✅", "Выложил историю") + "\n\n" + _who(user))


def acquisition_text(source: dict | None) -> str:
    if source is None:
        return '<b>Источник:</b> не удалось получить данные'
    lines = []
    if source.get('ad_link_id'):
        title = escape(str(source.get('ad_title') or 'Ссылка без названия'))
        slug = escape(str(source.get('ad_slug') or ''))
        label = 'История' if source.get('ad_kind') == 'story' else 'Рекламная ссылка'
        lines.append(f'{label} «{title}»' + (f' · <code>ad_{slug}</code>' if slug else ''))
    for prefix, label in [('referrer', 'Пригласил')]:
        uid = source.get(prefix + '_id')
        if uid:
            person = {'telegram_id': uid, 'first_name': source.get(prefix + '_name'),
                      'username': source.get(prefix + '_username')}
            lines.append(f'{label}: {_who(person)}')
    if not lines:
        lines.append(_untagged(source))
    return '<b>Источник:</b> ' + '\n'.join(lines)


_ENTRY = {'support': 'сначала написал в поддержку', 'report': 'сначала отправил жалобу на VPN',
          'other': 'появился не через /start'}


def _untagged(source: dict) -> str:
    """Why a user has no ad link or inviter: what they opened the bot with, and any friend's link that did not count."""
    via = source.get('first_entry_via')
    payload = str(source.get('first_start_payload') or '').strip()
    code = f' <code>{escape(payload[:64])}</code>' if payload else ''
    if via == 'start':
        if not payload:
            text = 'без метки — открыл бота обычной ссылкой или из поиска (/start без параметра)'
        elif payload.startswith('ad_'):
            text = f'рекламная метка{code}, но такой ссылки нет — удалена или опечатка'
        elif payload.startswith('ref_'):
            text = f'реферальная метка{code} не засчитана — пригласивший не найден или это его собственная ссылка'
        else:
            text = f'без метки источника, /start с параметром{code}'
    elif via == 'app':
        text = 'без метки — сначала открыл мини-приложение, а не /start' + (f', параметр{code}' if payload else '')
    elif via in _ENTRY:
        text = f'без метки — {_ENTRY[via]}'
    else:
        text = 'без метки источника (пришёл до того, как бот начал записывать вход)'
    if source.get('tried_referrer_id'):
        friend = {'telegram_id': source['tried_referrer_id'], 'first_name': source.get('tried_referrer_name'),
                  'username': source.get('tried_referrer_username')}
        text += f'\nПозже переходил по ссылке {_who(friend)}, но уже был в боте — не засчитано'
    return text[0].upper() + text[1:]


async def _first_online_notifications(users: list[dict]) -> None:
    if not users:
        return
    sources = {}
    try:
        rows = await db._pool_req().fetch("""SELECT u.telegram_id,u.ad_link_id,
            a.title AS ad_title,a.slug AS ad_slug,a.kind AS ad_kind,
            u.referred_by AS referrer_id,r.first_name AS referrer_name,r.username AS referrer_username,
            u.first_entry_via,u.first_start_payload,
            t.telegram_id AS tried_referrer_id,t.first_name AS tried_referrer_name,t.username AS tried_referrer_username
            FROM users u LEFT JOIN ad_links a ON a.id=u.ad_link_id
            LEFT JOIN users r ON r.telegram_id=u.referred_by
            LEFT JOIN LATERAL (SELECT x.telegram_id,x.first_name,x.username FROM referral_link_visits v
                JOIN users x ON x.telegram_id=v.referrer_id
                WHERE v.visitor_id=u.telegram_id AND NOT v.attached ORDER BY v.created_at LIMIT 1) t ON TRUE
            WHERE u.telegram_id=ANY($1::bigint[])""", [int(u['telegram_id']) for u in users])
        sources = {int(row['telegram_id']): dict(row) for row in rows}
    except Exception:
        logger.exception('Could not load acquisition source for first connection')
    for user in users:
        first_online(user, source=sources.get(int(user['telegram_id'])))


def first_online(user: dict | None, *, source: dict | None = None) -> None:
    post(_heading("connect", "⚡", "Первое подключение") + "\n\n" + _who(user)
         + "\n\n" + acquisition_text(source))


async def note_panel_online(telegram_id: int, panel: dict | None) -> None:
    if not panel:
        return
    if not (panel_online_at(panel) or panel_first_connected_at(panel) or (panel_used_traffic_bytes(panel) or 0) > 0 or (panel_lifetime_traffic_bytes(panel) or 0) > 0):
        return
    user = await db.claim_first_online(telegram_id)
    if user:
        await _first_online_notifications([user])


async def note_first_online_from_panel_ids(panel_ids: list[int]) -> None:
    ids = [int(x) for x in panel_ids if x]
    if not ids:
        return
    await _first_online_notifications(await db.claim_first_online_for_panel_ids(ids))


async def note_first_online_from_panels(panels: list[dict]) -> None:
    ids: list[int] = []
    for item in panels:
        if not isinstance(item, dict):
            continue
        if not (panel_online_at(item) or panel_first_connected_at(item) or (panel_used_traffic_bytes(item) or 0) > 0 or (panel_lifetime_traffic_bytes(item) or 0) > 0):
            continue
        raw = item.get("id")
        if raw is not None and str(raw).isdigit():
            ids.append(int(raw))
    await note_first_online_from_panel_ids(ids)


async def get_live_chat_hint() -> dict | None:
    raw = (await db.get_kv(HINT_KEY)).strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return data


async def remember_live_chat(chat) -> None:
    if not chat or getattr(chat, "type", "") not in {"channel", "supergroup"}:
        return
    settings = get_settings()
    req = str(settings.required_channel_id or "").strip()
    cid = str(chat.id)
    uname = str(getattr(chat, "username", None) or "").lstrip("@").lower()
    req_name = req.lstrip("@").lower()
    if req and (cid == req or (uname and uname == req_name)):
        return
    try:
        if parse_live_chat_id(req) == cid:
            return
    except ValueError:
        pass
    await db.set_kv(
        HINT_KEY,
        json.dumps(
            {
                "id": cid,
                "title": str(getattr(chat, "title", None) or ""),
                "username": str(getattr(chat, "username", None) or ""),
                "type": str(chat.type),
            },
            ensure_ascii=False,
        ),
    )


async def verify_live_chat(value: str) -> None:
    raw = parse_live_chat_id(value)
    if not raw:
        return
    bot: Bot | None = getattr(runtime, "bot", None)
    if bot is None:
        return
    chat = int(raw) if raw.lstrip("-").isdigit() else raw
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat, me.id)
    except Exception as exc:
        raise ValueError(
            "Бот не видит этот чат. Для приватного канала добавьте бота администратором "
            "(право публиковать сообщения), затем укажите id -100... или ссылку t.me/c/.... "
            f"Telegram: {telegram_fail_reason(exc)}"
        ) from exc
    status = str(getattr(member, "status", "") or "")
    if status not in {"administrator", "creator"}:
        raise ValueError("Бот должен быть администратором канала")
    can_post = getattr(member, "can_post_messages", None)
    if status == "administrator" and can_post is False:
        raise ValueError("Дайте боту в канале право публиковать сообщения")


@router.my_chat_member()
async def on_bot_chat_member(event: ChatMemberUpdated) -> None:
    new = event.new_chat_member
    if str(getattr(new, "status", "") or "") not in {"administrator", "creator"}:
        return
    try:
        await remember_live_chat(event.chat)
    except Exception:
        logger.debug("Не удалось запомнить канал для живых событий", exc_info=True)
