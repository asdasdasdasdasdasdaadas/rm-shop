"""Message widgets for the private chat (Bot API 10.4).

aiogram 3.25 doesn't know widgets yet, so the methods are declared here and the
`widget_query` update is caught by an outer middleware before aiogram drops it.
Widgets run offline: each draws from its chat state and asks the bot for fresh
numbers when it appears on screen, every 30 seconds while visible, and on a tap.

Requests (1-64 bytes, from the widget):
  r       balance and how long it lasts
  f       referral numbers
  g:<id>  claim a gift from the «+3 дня всем» broadcast
  s       service stats, admins only
"""
from __future__ import annotations

import html
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.methods.base import TelegramMethod
from aiogram.types import InlineKeyboardMarkup, Message

from app import db
from app.config import get_settings

logger = logging.getLogger(__name__)

UPDATE_TYPES = ("widget_query",)
CAPTION_LIMIT = 1024


class SendWidget(TelegramMethod[Message]):
    __returning__ = Message
    __api_method__ = "sendWidget"

    chat_id: int | str
    html: str
    width: int | None = None
    height: int | None = None
    public_data: str | None = None
    chat_data: str | None = None
    caption: str | None = None
    parse_mode: str | None = None
    allow_queries: bool | None = None
    reply_markup: InlineKeyboardMarkup | None = None


class AnswerWidgetQuery(TelegramMethod[bool]):
    __returning__ = bool
    __api_method__ = "answerWidgetQuery"

    widget_query_id: str
    data: str | None = None


class EditMessageWidgetData(TelegramMethod[bool]):
    __returning__ = bool
    __api_method__ = "editMessageWidgetData"

    chat_id: int | str
    message_id: int
    chat_data: str | None = None
    public_data: str | None = None


# Shared bits of every widget: theme-aware styles, plural forms, rubles, «Обновлено в HH:MM».
_BASE_CSS = """body{margin:0;padding:12px 14px max(10px,env(safe-area-inset-bottom))}
.t{color:var(--tg-theme-hint-color);font-size:.85em}
.big{font-size:2em;font-weight:700;font-variant-numeric:tabular-nums;margin:2px 0}
.low{color:var(--tg-theme-destructive-text-color)}
.ok{color:var(--tg-theme-accent-text-color)}
.row{display:flex;gap:8px;margin-top:10px}
.c{flex:1;background:var(--tg-theme-secondary-bg-color);border-radius:10px;padding:8px 10px}
.c b{display:block;font-size:1.15em;font-variant-numeric:tabular-nums}
.f{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:10px;
padding-right:var(--tg-content-safe-area-corner-right)}
button{padding:6px 14px}"""

_BASE_JS = """const W=window.TelegramWidget,$=i=>document.getElementById(i);
let s=null,busy=0;try{s=JSON.parse(W.chatData)}catch(e){}
function pl(n,a,b,c){n=Math.abs(n)%100;const m=n%10;return n>10&&n<20?c:m==1?a:m>1&&m<5?b:c}
function rub(v){return String(v).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')+' ₽'}
function hm(t){const d=new Date(t*1000);return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}
function ask(q,tap,ok){if(busy)return;busy=1;const b=$('r');if(tap&&b)b.disabled=true;
W.request(q).then(a=>{let v=null;try{v=JSON.parse(a.result)}catch(e){}
if(v&&v.e){$('u').textContent=v.e}else if(v){ok(v)}},
e=>{if(tap)$('u').textContent=e.code=='RATE_LIMITED'?'Слишком часто, подождите':'Не удалось обновить'})
.finally(()=>{busy=0;if(b)b.disabled=false})}
function live(q,ok){const go=t=>ask(q,t,ok);const b=$('r');
if(b)b.onclick=()=>{if(W.HapticFeedback)W.HapticFeedback.impactOccurred('light');go(1)};
if(W.ready)W.ready();go(0);setInterval(()=>{if(W.isActive!==false)go(0)},30000)}"""


def _page(body: str, script: str, css: str = "") -> str:
    return f"<style>{_BASE_CSS}{css}</style>{body}<script>{_BASE_JS}\n{script}</script>"


BALANCE_HTML = _page(
    """<div class="t">__BRAND__ · баланс</div>
<div class="big" id="b">—</div><div id="d" style="font-weight:600"></div>
<div class="row"><div class="c"><span class="t">Устройства</span><b id="n">—</b></div>
<div class="c"><span class="t">В день</span><b id="p">—</b></div></div>
<div class="f"><span class="t" id="u"></span><button id="r">Обновить</button></div>""",
    """function left(sec){const d=Math.floor(sec/86400),h=Math.floor(sec%86400/3600),m=Math.floor(sec%3600/60);
return (d?d+' д ':'')+(d||h?h+' ч ':'')+m+' мин'}
function draw(){if(!s){$('d').textContent='Загружаем…';return}
$('b').textContent=rub(s.b);const d=$('d'),sec=(s.e||0)-Date.now()/1000;
if(!s.n){d.textContent=s.b>0?'Добавьте устройство в кабинете':'Пополните баланс, чтобы подключиться';d.className=''}
else if(sec<=0){d.textContent='Баланс закончился';d.className='low'}
else if(sec<259200){d.textContent='Отключится через '+left(sec);d.className='low'}
else{d.textContent='Хватит на '+s.d+' '+pl(s.d,'день','дня','дней');d.className='ok'}
$('n').textContent=s.n;$('p').textContent=rub(s.p*Math.max(1,s.n));$('u').textContent='Обновлено в '+hm(s.t)}
draw();setInterval(draw,20000);live('r',v=>{s=v;draw()});""",
)

REFERRAL_HTML = _page(
    """<div class="t">Ваша реферальная программа</div>
<div class="row" style="margin-top:6px"><div class="c"><span class="t">Приглашено</span><b id="i">—</b></div>
<div class="c"><span class="t">Получили бонус</span><b id="w">—</b></div></div>
<div class="c" style="margin-top:8px"><span class="t">Заработано</span><b id="m" class="ok">—</b></div>
<div class="f"><span class="t" id="u"></span><span><button id="cp">Скопировать ссылку</button> <button id="r">↻</button></span></div>""",
    """let seen=s?s.i:0;
function draw(){if(!s)return;const i=$('i');i.textContent=s.i;
if(s.i>seen){i.className='pop';$('u').textContent='+'+(s.i-seen)+' '+pl(s.i-seen,'друг','друга','друзей')+' 🎉'}
else $('u').textContent='Обновлено в '+hm(s.t);seen=s.i;
$('w').textContent=s.w;$('m').textContent=rub(s.m)}
$('cp').onclick=()=>{if(s&&s.c){W.copyText(s.c);$('u').textContent='Ссылка скопирована'}};
draw();live('f',v=>{v.c=v.c||(s&&s.c);s=v;draw()});""",
    ".pop{animation:pop .6s ease}@keyframes pop{40%{transform:scale(1.25)}}",
)

GIFT_HTML = _page(
    """<div style="text-align:center;padding:6px 0">
<div style="font-size:2.4em" id="ic">🎁</div>
<div class="big" style="font-size:1.4em" id="h">__DAYS__ VPN в подарок</div>
<div class="t" id="u">Начислим на баланс для всех ваших устройств</div>
<div style="margin-top:12px"><button id="g" style="padding:10px 22px;font-weight:600">Забрать __DAYS__</button></div></div>""",
    """function draw(){if(!s)return;
if(s.s){$('ic').textContent='✅';$('h').textContent='Получено +'+rub(s.a);$('h').className='big ok';
$('u').textContent=s.b!=null?'Баланс: '+rub(s.b)+'. Включите VPN — доступ уже работает':'Подарок уже на балансе';
$('g').style.display='none'}}
$('g').onclick=()=>{if(!s||s.s||busy)return;busy=1;$('g').disabled=true;$('u').textContent='Начисляем…';
W.request('g:'+s.g).then(a=>{let v={};try{v=JSON.parse(a.result)}catch(e){}
if(v.e){$('u').textContent=v.e;if(v.done){s.s=1;s.a=v.a||0;s.b=null;draw()}}
else{s=Object.assign(s,v,{s:1});if(W.HapticFeedback)W.HapticFeedback.notificationOccurred('success');draw()}},
e=>{$('u').textContent=e.code=='TIMEOUT'?'Бот не ответил, нажмите ещё раз':'Не получилось, попробуйте ещё раз'})
.finally(()=>{busy=0;$('g').disabled=false})};
draw();if(W.ready)W.ready();""",
    ".big{margin:4px 0}",
)

STATS_HTML = _page(
    """<div class="t">__BRAND__ · сегодня</div>
<div class="big ok" id="v">—</div><div class="t" id="pc"></div>
<div class="row"><div class="c"><span class="t">Новые</span><b id="nu">—</b></div>
<div class="c"><span class="t">В сети за час</span><b id="on">—</b></div></div>
<div class="row" style="margin-top:8px"><div class="c"><span class="t">С доступом</span><b id="ac">—</b></div>
<div class="c"><span class="t">Обращения</span><b id="tk">—</b></div></div>
<div class="f"><span class="t" id="u"></span><button id="r">Обновить</button></div>""",
    """function draw(){if(!s)return;$('v').textContent=rub(s.v);
$('pc').textContent=s.p+' '+pl(s.p,'оплата','оплаты','оплат')+' · всего '+s.a+' '+pl(s.a,'пользователь','пользователя','пользователей');
$('nu').textContent='+'+s.n;$('on').textContent=s.o;$('ac').textContent=s.x;$('tk').textContent=s.k;
$('tk').className=s.k?'low':'';$('u').textContent='Обновлено в '+hm(s.t)}
draw();live('s',v=>{s=v;draw()});""",
)


TON_PAY_HTML = _page(
    """<div class="cd" id="cd"><div class="rb" id="rb">к оплате</div>
<svg width="52" height="52" viewBox="0 0 100 100"><path fill="#fff" d="M66.523 11.333H33.477c-4.401 0-6.601 0-8.592.616a13.792 13.792 0 0 0-4.808 2.625c-1.594 1.341-2.784 3.192-5.164 6.894L4.408 37.81c-1.572 2.446-2.358 3.67-2.572 4.956a6.322 6.322 0 0 0 .362 3.37c.482 1.212 1.51 2.24 3.567 4.296l39.033 39.034c1.821 1.82 2.731 2.731 3.781 3.072.924.3 1.918.3 2.842 0 1.05-.34 1.96-1.251 3.78-3.072l39.035-39.034c2.056-2.056 3.084-3.084 3.566-4.296a6.32 6.32 0 0 0 .362-3.37c-.214-1.287-1-2.51-2.572-4.956L85.087 21.47c-2.38-3.703-3.57-5.554-5.164-6.895a13.792 13.792 0 0 0-4.808-2.625c-1.99-.616-4.191-.616-8.592-.616z"/><path class="st" d="M60.268 24.224c.537-1.45 2.59-1.45 3.126 0l3.71 10.027a2.2 2.2 0 0 0 1.3 1.3l10.027 3.71c1.451.537 1.451 2.59 0 3.126l-10.027 3.71a2.2 2.2 0 0 0-1.3 1.3l-3.71 10.027c-.537 1.451-2.59 1.451-3.126 0l-3.71-10.027a2.2 2.2 0 0 0-1.3-1.3l-10.027-3.71c-1.451-.537-1.451-2.589 0-3.126l10.027-3.71a2.2 2.2 0 0 0 1.3-1.3l3.71-10.027z"/></svg>
<div class="am" id="am"></div><div class="sb" id="sb"></div>
<div class="mn">Лягушка&nbsp;VPN</div><div class="mn ad" id="ad">__ADDR__</div></div>
<button id="pay" class="pb">Оплатить</button><button id="ed" class="lk">Изменить сумму</button>
<div class="t" id="u" style="margin-top:8px;text-align:center"></div>""",
    """let ord=s&&s.w,poll=0;const A=$('ad').textContent;
function tn(n){return (n/1e9).toFixed(9).replace(/\\.?0+$/,'').replace('.',',')}
function msg(t){$('u').textContent=t}
$('ad').innerHTML=A.match(/.{1,4}/g).map((g,i)=>g+(i%6==5?'<br>':' ')).join('');
$('ad').onclick=()=>{if(W.copyText){W.copyText(A);msg('Адрес скопирован')}};
function draw(){if(!s)return;
if(s.ok){$('cd').className='cd dn';$('rb').textContent='зачислено';$('am').textContent='+'+rub(s.ok.c);
$('sb').textContent='Баланс: '+rub(s.ok.b);$('pay').hidden=true;$('ed').hidden=true;msg('Счёт '+s.ok.o+' оплачен');stop();return}
$('am').textContent=tn(s.n)+' Gram';
$('sb').textContent='≈ '+rub(s.c)+' на баланс'+(s.d>0?' · '+s.d+' '+pl(s.d,'день','дня','дней')+' VPN':'');
$('pay').textContent='Оплатить '+tn(s.n)+' Gram';$('ed').hidden=!!ord;if(ord)$('rb').textContent='ждём'}
function stop(){if(poll)clearInterval(poll);poll=0}
function check(){msg('Ищем перевод в блокчейне, обычно 5–15 секунд…');$('rb').textContent='ждём';$('pay').disabled=true;$('ed').hidden=true;if(poll)return;
poll=setInterval(()=>{if(!busy&&W.isActive!==false)ask('q:'+ord,0,v=>{if(v.ok){s.ok=v.ok;draw()}})},6000)}
const ERR={REJECTED:'Оплата отменена',BAD_REQUEST:'Кошелёк отклонил перевод',NOT_ALLOWED:'Оплата здесь недоступна',RATE_LIMITED:'Слишком часто, подождите'};
$('pay').onclick=()=>{if(busy||!s)return;if(!W.wallet){msg('Кошелёк Telegram недоступен в этой версии приложения');return}
busy=1;$('pay').disabled=true;msg('Фиксируем курс…');if(W.HapticFeedback)W.HapticFeedback.impactOccurred('light');
W.request('t:'+s.n,{wallet:true}).then(a=>{const v=JSON.parse(a.result||'{}');if(v.e)throw{m:v.e};ord=v.o;s.c=v.c;draw();
msg('Подтвердите перевод в кошельке');return W.wallet.sendTransaction(v.tx,'p:'+v.o)})
.then(()=>{if(W.HapticFeedback)W.HapticFeedback.notificationOccurred('success');check()},
e=>{if(e&&e.m){msg(e.m);$('pay').disabled=false}else if(e&&(e.code=='TIMEOUT'||e.code=='FAILED')&&ord)check();
else{msg(ERR[e&&e.code]||'Не получилось, попробуйте ещё раз');$('pay').disabled=false}})
.finally(()=>{busy=0})};
$('ed').onclick=()=>{if(busy)return;busy=1;msg('');
W.request('x:').then(a=>{const v=JSON.parse(a.result||'{}');if(v.e)msg(v.e);else{$('cd').style.opacity=.5;$('pay').hidden=true;$('ed').hidden=true;msg('Напишите в чат новую сумму')}},
()=>msg('Не получилось, попробуйте ещё раз')).finally(()=>{busy=0})};
W.onEvent('chatDataChanged',()=>{try{s=JSON.parse(W.chatData)}catch(e){}if(s&&s.w)ord=s.w;draw()});
draw();if(W.ready)W.ready();if(ord&&!(s&&s.ok))check();""",
    ".cd{position:relative;overflow:hidden;border-radius:18px;padding:16px 16px 14px;color:#fff;text-align:center;"
    "background:linear-gradient(160deg,#5fb4ff 0%,#2f86f0 55%,#1d63d6 100%);transition:background .4s}"
    ".cd.dn{background:linear-gradient(160deg,#5ad48f 0%,#27a865 60%,#17864d 100%)}.st{fill:#30a1f5;transition:fill .4s}.dn .st{fill:#27a865}"
    ".rb{position:absolute;top:14px;right:-34px;width:120px;transform:rotate(45deg);background:rgba(255,255,255,.22);"
    "font-size:.7em;font-weight:600;padding:3px 0;letter-spacing:.02em}"
    ".am{font-size:2.1em;font-weight:800;font-variant-numeric:tabular-nums;margin:6px 0 0;line-height:1.15}"
    ".sb{opacity:.85;font-size:.9em;margin-bottom:12px}"
    ".mn{font-family:ui-monospace,Menlo,monospace;font-size:.82em;opacity:.92;line-height:1.5}"
    ".ad{margin-top:6px;letter-spacing:.04em;cursor:pointer}"
    ".pb{width:100%;margin-top:10px;padding:11px 0;font-weight:600;border-radius:12px}"
    ".lk{display:block;margin:6px auto 0;background:none;border:0;color:var(--tg-theme-link-color);font-size:.9em}",
)


def _brand() -> str:
    return html.escape(get_settings().brand_name or "VPN")


def _json(state: dict[str, Any]) -> str:
    return json.dumps(state, separators=(",", ":"), ensure_ascii=False)


def widget_html() -> str:
    return BALANCE_HTML.replace("__BRAND__", _brand())


def referral_html() -> str:
    return REFERRAL_HTML


def gift_html(days: int) -> str:
    from app.texts import days_text
    return GIFT_HTML.replace("__DAYS__", html.escape(days_text(days)))


def stats_html() -> str:
    return STATS_HTML.replace("__BRAND__", _brand())


def ton_pay_html() -> str:
    return TON_PAY_HTML.replace("Лягушка&nbsp;VPN", _brand().replace(" ", "&nbsp;")).replace(
        "__ADDR__", html.escape(get_settings().ton_wallet or ""))


# ---------- state ----------

def _aware(value) -> datetime | None:
    from app.web import parse_dt
    dt = value if isinstance(value, datetime) else parse_dt(value)
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


async def balance_state(telegram_id: int) -> dict[str, Any]:
    """Balance, days/hours left, billable devices, price per device-day and the moment access ends («e»)."""
    from app.web import _is_router_device, balance_runway

    local = await db.get_user(telegram_id)
    raw_devices = await db.list_devices(telegram_id)
    balance = int((local or {}).get("balance_rub") or 0)
    days, hours = balance_runway(local, raw_devices, balance)
    price = max(1, get_settings().vpn_day_price_rub)
    billable = [item for item in raw_devices if not _is_router_device(item)]
    now = int(time.time())
    ends = now + hours * 3600
    # Billing is daily: access lasts until the next charge plus every full day the balance still covers.
    if billable and not (local or {}).get("trial_waiting_connection"):
        charges = [_aware(item.get("last_billed_at")) for item in billable]
        charges = [dt + timedelta(hours=24) for dt in charges if dt]
        if charges:
            full_days = max(0, balance) // (price * len(billable))
            ends = int((min(charges) + timedelta(days=full_days)).timestamp())
    return {"b": balance, "d": days, "h": hours, "n": len(billable), "p": price, "t": now, "e": ends}


async def referral_state(telegram_id: int, *, with_link: bool = False) -> dict[str, Any]:
    refs = await db.referral_stats(telegram_id)
    wallet = await db.referral_wallet(telegram_id)
    earned = max(int((wallet or {}).get("referral_earned") or 0), await db.referral_credit_sum(telegram_id))
    state = {"i": int(refs.get("invited") or 0), "w": int(refs.get("rewarded") or 0), "m": earned, "t": int(time.time())}
    if with_link:
        from app.keyboards import invite_copy_text
        state["c"] = invite_copy_text(telegram_id)
    return state


async def stats_state() -> dict[str, Any]:
    """Light numbers for the admin widget: cheap enough to run every 30 seconds."""
    pool = db._pool_req()
    row = await pool.fetchrow(
        """
        WITH day AS (
            SELECT (date_trunc('day', NOW() AT TIME ZONE 'Europe/Moscow') AT TIME ZONE 'Europe/Moscow') AS start
        )
        SELECT
            (SELECT COUNT(*)::int FROM users) AS users_total,
            (SELECT COUNT(*)::int FROM users, day WHERE created_at >= day.start) AS new_today,
            (SELECT COUNT(DISTINCT telegram_id)::int FROM devices WHERE last_online_at >= NOW() - INTERVAL '1 hour') AS online,
            (SELECT COUNT(*)::int FROM users u WHERE COALESCE(u.balance_rub, 0) > 0
                AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)) AS with_access,
            (SELECT COUNT(*)::int FROM tickets WHERE status = 'open') AS tickets
        """
    )
    orders = await pool.fetch(
        """
        SELECT plan_code, COUNT(*)::int AS n FROM rollypay_orders
        WHERE status = 'granted'
          AND created_at >= (date_trunc('day', NOW() AT TIME ZONE 'Europe/Moscow') AT TIME ZONE 'Europe/Moscow')
        GROUP BY plan_code
        """
    )
    ton_paid = await pool.fetchrow(
        """
        SELECT COUNT(*)::int AS n, COALESCE(SUM(credited_rub), 0)::int AS rub FROM ton_orders
        WHERE status = 'paid'
          AND paid_at >= (date_trunc('day', NOW() AT TIME ZONE 'Europe/Moscow') AT TIME ZONE 'Europe/Moscow')
        """
    )
    settings = get_settings()
    revenue = sum(settings.topup_rub_for_code(r["plan_code"]) * int(r["n"] or 0) for r in orders)
    revenue += int((ton_paid or {}).get("rub") or 0)
    row = dict(row or {})
    return {
        "v": int(revenue),
        "p": sum(int(r["n"] or 0) for r in orders) + int((ton_paid or {}).get("n") or 0),
        "a": int(row.get("users_total") or 0),
        "n": int(row.get("new_today") or 0),
        "o": int(row.get("online") or 0),
        "x": int(row.get("with_access") or 0),
        "k": int(row.get("tickets") or 0),
        "t": int(time.time()),
    }


# ---------- sending ----------

def _fits(caption: str | None) -> bool:
    return caption is None or len(caption) <= CAPTION_LIMIT


def balance_widget_keyboard() -> InlineKeyboardMarkup | None:
    from app.keyboards import cabinet_button, payment_nudge_keyboard

    rows = payment_nudge_keyboard(label="Пополнить баланс").inline_keyboard
    cabinet = cabinet_button()
    if cabinet:
        rows = [*rows, [cabinet]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_balance_widget(
    bot: Bot, telegram_id: int, *, caption: str | None = None, reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    state = await balance_state(telegram_id)
    if caption is None:
        days = state["d"]
        caption = f"Баланс: {state['b']} ₽" + (f" · хватит на {days} дн." if state["n"] and days else "")
    if not _fits(caption):
        raise ValueError("caption is too long for a widget")
    return await bot(SendWidget(
        chat_id=telegram_id, html=widget_html(), chat_data=_json(state), caption=caption, parse_mode="HTML",
        allow_queries=True, reply_markup=reply_markup if reply_markup is not None else balance_widget_keyboard(),
    ))


async def send_referral_widget(bot: Bot, telegram_id: int, *, caption: str, reply_markup=None) -> Message:
    if not _fits(caption):
        raise ValueError("caption is too long for a widget")
    state = await referral_state(telegram_id, with_link=True)
    return await bot(SendWidget(
        chat_id=telegram_id, html=referral_html(), chat_data=_json(state), caption=caption, parse_mode="HTML",
        allow_queries=True, reply_markup=reply_markup,
    ))


async def send_gift_widget(bot: Bot, telegram_id: int, gift_id: int, *, caption: str, reply_markup=None) -> Message:
    from app.funnel_gifts import GIFT_DAYS
    if not _fits(caption):
        raise ValueError("caption is too long for a widget")
    return await bot(SendWidget(
        chat_id=telegram_id, html=gift_html(GIFT_DAYS), chat_data=_json({"g": int(gift_id), "s": 0}),
        caption=caption, parse_mode="HTML", allow_queries=True, reply_markup=reply_markup,
    ))


async def send_stats_widget(bot: Bot, telegram_id: int) -> Message:
    state = await stats_state()
    return await bot(SendWidget(
        chat_id=telegram_id, html=stats_html(), chat_data=_json(state),
        caption=f"Сегодня: {state['v']} ₽, оплат {state['p']}, новых {state['n']}", allow_queries=True,
    ))


async def mark_gift_claimed(bot: Bot, chat_id: int, message_id: int, gift_id: int, result: dict) -> None:
    """Put the claimed state into the widget and drop the fallback button under it. Not a widget: nothing happens."""
    state = {"g": int(gift_id), "s": 1, "a": int(result.get("gift_rub") or 0), "b": result.get("balance_rub")}
    try:
        await bot(EditMessageWidgetData(chat_id=chat_id, message_id=message_id, chat_data=_json(state)))
    except Exception:
        logger.debug("Состояние виджета подарка не обновлено", exc_info=True)
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
    except Exception:
        logger.debug("Кнопка подарка не убрана", exc_info=True)


# ---------- requests from widgets ----------

async def _claim_gift(bot: Bot, query: dict[str, Any], user_id: int, raw: str) -> dict[str, Any]:
    from app import funnel_gifts
    if not raw.isdigit():
        return {"e": "Подарок не найден"}
    try:
        result = await funnel_gifts.claim(user_id, int(raw))
    except ValueError as exc:
        message = str(exc)
        return {"e": message, "done": 1} if "уже получен" in message else {"e": message}
    chat_id = (query.get("chat") or {}).get("id")
    message_id = query.get("message_id")
    if chat_id and message_id:
        await mark_gift_claimed(bot, int(chat_id), int(message_id), int(raw), result)
    return {"a": int(result["gift_rub"]), "b": int(result["balance_rub"]), "d": int(result["days"])}


async def handle_query(bot: Bot, query: dict[str, Any]) -> dict[str, Any]:
    user_id = int((query.get("from") or {}).get("id") or 0)
    data = str(query.get("data") or "")
    if not user_id:
        return {"e": "Неизвестный пользователь"}
    if data == "r":
        return await balance_state(user_id)
    if data == "f":
        return await referral_state(user_id)
    if data.startswith("g:"):
        return await _claim_gift(bot, query, user_id, data[2:])
    if data == "s":
        if user_id not in get_settings().admin_id_set:
            return {"e": "Нет доступа"}
        return await stats_state()
    if data[:2] in ("t:", "p:", "q:", "x:"):
        from app import ton
        return await ton.handle_query(bot, query, user_id, data)
    return {"e": "Неизвестный запрос"}


async def answer_widget_query(bot: Bot, query: dict[str, Any]) -> None:
    query_id = str(query.get("id") or "")
    if not query_id:
        return
    try:
        payload = await handle_query(bot, query)
    except Exception:
        logger.exception("Запрос виджета %r не обработан", query.get("data"))
        payload = {"e": "Не удалось обновить"}
    await bot(AnswerWidgetQuery(widget_query_id=query_id, data=_json(payload)))


def _extra(update: Any, name: str) -> Any:
    value = getattr(update, name, None)
    if value is None:
        value = (getattr(update, "model_extra", None) or {}).get(name)
    if value is not None and hasattr(value, "model_dump"):
        value = value.model_dump()
    return value


class WidgetQueryMiddleware(BaseMiddleware):
    """Answer `widget_query` updates, which aiogram 3.25 would otherwise skip as unknown."""

    async def __call__(self, handler, event, data):
        query = _extra(event, "widget_query")
        if not query:
            return await handler(event, data)
        try:
            await answer_widget_query(data["bot"], query)
        except Exception:
            logger.exception("Ответ на запрос виджета не удался")
        return None
