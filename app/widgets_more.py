"""More chat widgets: payment receipt, support ticket (client and admin), daily results and revenue forecast.

Requests (1-64 bytes, from the widget):
  z:<id>  ticket state for its owner      k:<id>  owner closes the ticket     v:<id>:<n>  owner rates it
  A:<id>  ticket card for an admin         C:<id>  admin closes the ticket     W:<id>      admin answers in this chat
  F       revenue forecast, admins only
The receipt refreshes with the balance request «r» from app.widgets.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import db
from app.config import get_settings
from app.widgets import CAPTION_LIMIT, SendWidget, _brand, _json, _page

logger = logging.getLogger(__name__)
MSK = ZoneInfo("Europe/Moscow")
REPLY_SECONDS = 15 * 60

# Gradient cards with white text, stat tiles and a full-width button: shared by every page here.
_CSS = """[hidden]{display:none!important}
.cd{position:relative;overflow:hidden;border-radius:18px;padding:14px 16px;color:#fff;
background:linear-gradient(150deg,#45c97f,#1f9d5a 60%,#147a45)}
.bl{background:linear-gradient(150deg,#5aa9ff,#2b7de9 60%,#1c5fc9)}
.gy{background:linear-gradient(150deg,#7d8794,#56606d 60%,#424a55)}
.or{background:linear-gradient(150deg,#f08a2c,#d9650f 60%,#b4500a)}
.vi{background:linear-gradient(150deg,#8c7bff,#6150e6 60%,#4a3bc4)}
.hd{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:.85em}
.pl{background:rgba(255,255,255,.22);border-radius:99px;padding:2px 9px;font-size:.88em;font-weight:600;white-space:nowrap}
.em{font-size:2.1em;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.15;margin:6px 0 2px}
.sm{font-size:1.35em}.sb{font-size:.9em}
.tl{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px}
.tl div{background:rgba(255,255,255,.17);border-radius:12px;padding:7px 9px;font-size:.78em;min-width:0}
.tl b{display:block;font-size:1.3em;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pb{width:100%;margin-top:10px;padding:11px 0;font-weight:600;border-radius:12px}
.rf{width:30px;height:30px;padding:0;border-radius:99px}
.f{margin-top:6px}"""

_JS = """function up(e,to,pre){const t0=performance.now();(function f(t){const k=Math.min(1,(t-t0)/900);
e.textContent=(pre||'')+rub(Math.round(to*(1-Math.pow(1-k,3))));if(k<1)requestAnimationFrame(f)})(t0)}
function dm(t,m){return new Date(t*1000).toLocaleDateString('ru-RU',{day:'numeric',month:m||'long'}).replace('.','')}
function el(p,h,c){const d=document.createElement('div');d.innerHTML=h;if(c)d.className=c;p.appendChild(d);return d}
const H=t=>{if(W.HapticFeedback)W.HapticFeedback.notificationOccurred(t)};"""


def _more(body: str, script: str, css: str = "") -> str:
    return _page(body, _JS + "\n" + script, _CSS + css)


RECEIPT_HTML = _more(
    """<div class="cd"><div class="hd"><span>__BRAND__ · оплата</span><span class="pl" id="mt"></span></div>
<div class="em" id="a">—</div><div class="sb" id="b"></div>
<div class="tl"><div>хватит до<b id="e">—</b></div><div><span id="dl">дней</span><b id="d">—</b></div>
<div><span id="nl">устройств</span><b id="n">—</b></div></div></div>
<div class="nx" id="nx"></div>
<div class="iv" id="iv" hidden><span>🎁 <b id="ir"></b> за каждого друга</span><button id="cp">Пригласить</button></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """const M={order:'Карта/СБП',sbp:'СБП',card:'Карта',stars:'Звёзды',ton:'Gram',crypto:'Крипта'},
N={ok:'✓ VPN уже работает — больше ничего делать не нужно',nd:'📱 Добавьте устройство — покажем, как подключить VPN',
su:'📱 Осталось добавить ссылку в VPN-приложение и включить VPN'};let go=1;
function draw(){if(!s)return;$('mt').textContent=M[s.m]||'оплачено';
if(go){go=0;up($('a'),s.a,'+');H('success')}
$('b').textContent='Баланс: '+rub(s.b);const on=s.n>0&&s.e>s.t;
$('e').textContent=on?dm(s.e,'short'):'—';$('d').textContent=on?s.d:'—';$('dl').textContent=pl(s.d,'день','дня','дней');
$('n').textContent=s.n;$('nl').textContent=pl(s.n,'устройство','устройства','устройств');
$('nx').textContent=N[s.k]||'';if(s.r&&s.c){$('iv').hidden=false;$('ir').textContent='+'+rub(s.r)}
$('u').textContent='Обновлено в '+hm(s.t)}
$('cp').onclick=()=>{if(W.copyText&&s){W.copyText(s.c);$('u').textContent='Приглашение скопировано'}};
draw();live('r',v=>{Object.assign(s,{b:v.b,d:v.d,n:v.n,e:v.e,t:v.t});draw()});""",
    ".nx{margin-top:10px;font-weight:600;font-size:.95em}"
    ".iv{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:10px;padding:8px 10px;"
    "border-radius:12px;background:var(--tg-theme-secondary-bg-color);font-size:.9em}.iv button{padding:6px 12px}",
)

TICKET_HTML = _more(
    """<div class="cd bl" id="cd"><div class="hd"><span>Поддержка · №<b id="id"></b></span><span class="pl" id="st"></span></div>
<div class="em sm" id="h"></div><div class="sb" id="sb"></div></div>
<button id="k" class="pb">Закрыть обращение</button>
<div id="rt" hidden><div class="t" id="rq" style="margin-top:10px"></div><div class="sr" id="sr"></div></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """const V={u:['ждём ответа','Обращение отправлено','Ответим в этом чате. Можно дописать детали или прислать скриншот.','bl'],
a:['ответили','Поддержка ответила','Ответ — выше в чате. Если вопрос решён, закройте обращение.',''],
c:['закрыто','Обращение закрыто','Если проблема вернётся — просто напишите снова.','gy']};let arm=0;
function stars(){const e=$('sr');e.innerHTML='';for(let i=1;i<=5;i++){const b=document.createElement('button');
b.textContent='★';b.className=s.r&&i<=s.r?'on':'';b.disabled=!!s.r;b.setAttribute('aria-label',i+' из 5');
b.onclick=()=>ask('v:'+s.i+':'+i,1,v=>{s=v;H('success');draw()});e.appendChild(b)}}
function draw(){if(!s)return;const x=V[s.o?(s.w=='admin'?'a':'u'):'c'];
$('id').textContent=s.i;$('st').textContent=x[0];$('h').textContent=x[1];$('sb').textContent=x[2];$('cd').className='cd '+x[3];
$('k').hidden=!s.o;if(!arm)$('k').textContent='Закрыть обращение';$('rt').hidden=!!s.o;
if(!s.o){stars();$('rq').textContent=s.r?'Ваша оценка: '+s.r+' из 5. Спасибо!':'Как вам помощь поддержки?'}
$('u').textContent='Обновлено в '+hm(s.t)}
$('k').onclick=()=>{if(!s)return;if(!arm){arm=1;$('k').textContent='Точно закрыть? Нажмите ещё раз';
setTimeout(()=>{arm=0;draw()},3500);return}arm=0;ask('k:'+s.i,1,v=>{s=v;draw()})};
draw();live('z:'+(s?s.i:0),v=>{s=v;draw()});""",
    ".sr{display:flex;gap:6px;margin-top:6px}.sr button{flex:1;font-size:1.45em;padding:5px 0;border-radius:10px;border:0;"
    "background:var(--tg-theme-secondary-bg-color);color:var(--tg-theme-hint-color)}.sr .on{color:#e89a00}",
)

ADMIN_TICKET_HTML = _more(
    """<div class="cd or" id="cd"><div class="hd"><span id="hd"></span><span class="pl" id="st"></span></div>
<div class="em sm" id="nm"></div><div class="sb" id="sb"></div>
<div class="tl"><div>баланс<b id="b"></b></div><div>в сети<b id="n"></b></div><div>оплатил<b id="p"></b></div></div></div>
<div class="ms" id="ms"></div>
<div class="bt"><button id="w" class="pb">Ответить здесь</button><button id="c" class="pb">Закрыть</button></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """let arm=0;
function draw(){if(!s)return;const k=!s.o?['закрыто','gy']:s.w=='admin'?['ответили','']:['ждёт ответа','or'];
$('hd').textContent='Обращение #'+s.i+(s.f?' · из кабинета':'');$('st').textContent=k[0];$('cd').className='cd '+k[1];
$('nm').textContent=s.nm;$('sb').textContent=(s.un?'@'+s.un+' · ':'')+'с нами '+s.dd+' '+pl(s.dd,'день','дня','дней');
$('b').textContent=rub(s.b);$('n').textContent=s.on+' из '+s.n;$('p').textContent=rub(s.p);$('ms').textContent=s.ms||'Вложение';
$('w').hidden=$('c').hidden=!s.o;$('w').textContent=s.rm?'Отменить ответ':'Ответить здесь';if(!arm)$('c').textContent='Закрыть';
$('u').textContent=s.rm?'Напишите ответ следующим сообщением в этот чат':'Обновлено в '+hm(s.t)}
$('w').onclick=()=>ask('W:'+s.i,1,v=>{s=v;draw()});
$('c').onclick=()=>{if(!arm){arm=1;$('c').textContent='Точно?';setTimeout(()=>{arm=0;draw()},3500);return}
arm=0;ask('C:'+s.i,1,v=>{s=v;H('success');draw()})};
draw();live('A:'+(s?s.i:0),v=>{s=v;draw()});""",
    ".ms{margin-top:10px;padding:9px 11px;border-radius:12px;background:var(--tg-theme-secondary-bg-color);font-size:.92em;"
    "white-space:pre-wrap;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}"
    ".bt{display:flex;gap:8px}.bt .pb+.pb{flex:0 0 34%}",
)

DIGEST_HTML = _more(
    """<div class="cd vi"><div class="hd"><span id="dt"></span><span class="pl" id="dl" hidden></span></div>
<div class="em" id="v">—</div><div class="sb" id="pc"></div>
<div class="tl"><div>новичков<b id="n"></b></div><div>устройство<b id="nd"></b></div><div>оплатили<b id="np"></b></div></div></div>
<div class="t" id="ah" style="margin-top:10px"></div><div id="ac"></div>
<div class="t" style="margin-top:8px">__BRAND__ · 00:00–24:00 МСК</div>""",
    """function draw(){if(!s)return;$('dt').textContent='Итоги · '+dm(s.d);up($('v'),s.v);
if(s.y>0){const p=Math.round((s.v-s.y)/s.y*100),e=$('dl');e.hidden=false;e.textContent=(p>=0?'▲ ':'▼ ')+Math.abs(p)+'% к прошлому дню'}
$('pc').textContent=s.p+' '+pl(s.p,'оплата','оплаты','оплат')+(s.f?' · '+s.f+' '+pl(s.f,'первая','первые','первых'):'')
+(s.p?' · средний чек '+rub(Math.round(s.v/s.p)):'');
$('n').textContent=s.n;$('nd').textContent=s.nd;$('np').textContent=s.np;
const ac=$('ac'),m=Math.max(1,...s.r.map(r=>r[1]));
$('ah').textContent=s.r.length?'Активность в боте и кабинете · '+s.u+' '+pl(s.u,'человек','человека','человек'):'';
for(const r of s.r){const d=el(ac,'<span></span><i><b></b></i><em></em>','ar');d.children[0].textContent=r[0];
d.querySelector('b').style.width=Math.max(4,r[1]/m*100)+'%';d.children[2].textContent=r[1]+' · '+r[2]+' чел.'}}
draw();if(W.ready)W.ready();""",
    ".ar{display:grid;grid-template-columns:42% 1fr auto;align-items:center;gap:8px;margin-top:6px;font-size:.85em}"
    ".ar span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    ".ar i{height:8px;border-radius:9px;background:var(--tg-theme-secondary-bg-color);overflow:hidden}"
    ".ar b{display:block;height:100%;border-radius:9px;background:#6150e6;animation:gw .9s ease-out both;transform-origin:left}"
    ".ar em{font-style:normal;color:var(--tg-theme-hint-color);font-variant-numeric:tabular-nums}"
    "@keyframes gw{from{transform:scaleX(0)}}",
)

FORECAST_HTML = _more(
    """<div class="cd or"><div class="hd"><span>__BRAND__ · прогноз</span><span class="pl" id="av" hidden></span></div>
<div class="em" id="r7">—</div><div class="sb" id="s7"></div><div class="sb" id="r30"></div></div>
<div class="t" id="c7" style="margin-top:10px"></div><div class="ch" id="ch"></div>
<div id="ls"></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """let go=1;
function draw(){if(!s)return;const r7=$('r7');
if(s.r7!=null){if(go)up(r7,s.r7,'≈ ');else r7.textContent='≈ '+rub(s.r7);
$('s7').textContent='за 7 дней · примерно '+String(s.x7).replace('.',',')+' '+pl(Math.round(s.x7),'оплата','оплаты','оплат')}else{r7.textContent='—';$('s7').textContent='Пока мало повторных оплат для прогноза'}go=0;
$('r30').textContent=s.r30!=null?'за 30 дней ≈ '+rub(s.r30):'';
$('c7').textContent=s.c7?'Баланс кончится за неделю у '+s.c7+' '+pl(s.c7,'клиента','клиентов','клиентов'):'За неделю ни у кого не кончится баланс';
const av=$('av');av.hidden=!s.av;if(s.av)av.textContent='чек '+rub(s.av);
const ch=$('ch'),mx=Math.max(1,...s.s);ch.innerHTML='';s.s.forEach((n,i)=>{const c=el(ch,'<em></em><i></i><span></span>');
c.children[0].textContent=n||'';c.children[1].style.height=Math.max(3,n/mx*52)+'px';c.children[1].style.animationDelay=i*40+'ms';
c.children[2].textContent=i?i==1?'завтра':new Date((s.t+i*86400)*1000).getDate():'сегодня'});
const ls=$('ls');ls.innerHTML='';for(const p of s.l){const d=el(ls,'<span></span><em></em><b></b>','pr');d.children[0].textContent=p[0];
d.children[1].textContent=p[1]<1?'сегодня':'через '+p[1]+' '+pl(p[1],'день','дня','дней');d.children[2].textContent=rub(p[2])}
$('u').textContent='Обновлено в '+hm(s.t)}
draw();live('F',v=>{s=v;draw()});""",
    ".ch{display:flex;align-items:flex-end;gap:5px;height:84px;margin-top:6px}"
    ".ch div{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:3px;font-size:.7em;min-width:0}"
    ".ch i{width:100%;border-radius:6px 6px 3px 3px;background:linear-gradient(#ff9f43,#e8731a);animation:gh .7s ease-out both;transform-origin:bottom}"
    ".ch em{font-style:normal;font-weight:600}.ch span{color:var(--tg-theme-hint-color);white-space:nowrap}"
    "@keyframes gh{from{transform:scaleY(0)}}"
    ".pr{display:grid;grid-template-columns:1fr auto auto;gap:10px;margin-top:6px;font-size:.88em;padding:6px 10px;"
    "border-radius:10px;background:var(--tg-theme-secondary-bg-color)}"
    ".pr span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pr em{font-style:normal;color:var(--tg-theme-hint-color)}",
)


def receipt_html() -> str:
    return RECEIPT_HTML.replace("__BRAND__", _brand())


def ticket_html() -> str:
    return TICKET_HTML


def admin_ticket_html() -> str:
    return ADMIN_TICKET_HTML


def digest_html() -> str:
    return DIGEST_HTML.replace("__BRAND__", _brand())


def forecast_html() -> str:
    return FORECAST_HTML.replace("__BRAND__", _brand())


def _fits(caption: str | None) -> None:
    if caption is not None and len(caption) > CAPTION_LIMIT:
        raise ValueError("caption is too long for a widget")


# ---------- payment receipt ----------

async def receipt_state(telegram_id: int, receipt: dict, step: str) -> dict[str, Any]:
    """a — credited rubles, m — provider, k — next step (ok / nd — no device / su — finish setup),
    r/c — reward per invited friend and the invitation text, plus the live balance numbers."""
    from app.widgets import balance_state
    state = await balance_state(telegram_id)
    key = str(receipt.get("payment_key") or "")
    method = key.split(":", 1)[0]
    if method == "order":
        order = await db.get_pay_order(key.split(":", 1)[1])
        method = str((order or {}).get("method") or method)
    state.update(a=int(receipt.get("amount") or 0), m=method, k=step)
    settings = get_settings()
    if settings.referral_program_enabled and int(settings.referral_reward_rub or 0) > 0:
        from app.keyboards import invite_copy_text
        state.update(r=int(settings.referral_reward_rub), c=invite_copy_text(telegram_id))
    return state


async def send_receipt_widget(bot: Bot, telegram_id: int, receipt: dict, *, step: str, caption: str,
                              reply_markup: InlineKeyboardMarkup | None = None) -> Message:
    _fits(caption)
    state = await receipt_state(telegram_id, receipt, step)
    return await bot(SendWidget(chat_id=telegram_id, html=receipt_html(), chat_data=_json(state), caption=caption,
                                parse_mode="HTML", allow_queries=True, reply_markup=reply_markup))


# ---------- support ticket ----------

async def _ticket(ticket_id: int) -> dict | None:
    row = await db._pool_req().fetchrow(
        """SELECT t.*,
             (SELECT m.author FROM ticket_messages m WHERE m.ticket_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_author,
             (SELECT m.body FROM ticket_messages m WHERE m.ticket_id = t.id AND m.author = 'user'
               ORDER BY m.id DESC LIMIT 1) AS last_user_body,
             (SELECT COUNT(*) FROM ticket_messages m WHERE m.ticket_id = t.id)::int AS messages
           FROM tickets t WHERE t.id = $1""", int(ticket_id))
    return dict(row) if row else None


def _ticket_base(row: dict) -> dict[str, Any]:
    return {"i": int(row["id"]), "o": 0 if row.get("status") == "closed" else 1,
            "w": str(row.get("last_author") or "user"), "t": int(time.time())}


async def ticket_state(ticket_id: int, telegram_id: int | None = None) -> dict[str, Any]:
    """i — ticket, o — open, w — who wrote last (user / admin), r — the owner's rating."""
    row = await _ticket(ticket_id)
    if not row or (telegram_id is not None and int(row["telegram_id"]) != int(telegram_id)):
        return {"e": "Обращение не найдено"}
    state = _ticket_base(row)
    state["r"] = int(row.get("support_rating") or 0)
    return state


async def send_ticket_widget(bot: Bot, telegram_id: int, ticket_id: int, *, caption: str) -> Message:
    _fits(caption)
    state = await ticket_state(ticket_id, telegram_id)
    if "e" in state:
        raise KeyError(state["e"])
    return await bot(SendWidget(chat_id=telegram_id, html=ticket_html(), chat_data=_json(state), caption=caption,
                                parse_mode="HTML", allow_queries=True))


# Admin id -> (ticket id, deadline): the admin's next chat message goes to that ticket as the reply.
_replying: dict[int, tuple[int, float]] = {}


def reply_target(admin_id: int) -> int | None:
    item = _replying.get(int(admin_id))
    if not item:
        return None
    if item[1] < time.monotonic():
        _replying.pop(int(admin_id), None)
        return None
    return item[0]


def stop_reply(admin_id: int) -> None:
    _replying.pop(int(admin_id), None)


async def admin_ticket_state(ticket_id: int, admin_id: int | None = None) -> dict[str, Any]:
    """nm/un — name and username, dd — days with the service, b — balance, n/on — devices and online now,
    p — rubles paid in total, ms — the client's last message, f — written from the cabinet, rm — reply mode."""
    row = await _ticket(ticket_id)
    if not row:
        return {"e": "Обращение не найдено"}
    uid = int(row["telegram_id"])
    user = await db.get_user(uid) or {}
    devices = await db.list_devices(uid)
    paid = await db._pool_req().fetchval(
        "SELECT COALESCE(SUM(amount), 0)::int FROM payment_receipts WHERE telegram_id = $1", uid)
    now = datetime.now(timezone.utc)
    recent = now - timedelta(minutes=15)

    def aware(value):
        if not isinstance(value, datetime):
            return None
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    since = aware(user.get("created_at")) or aware(row.get("created_at")) or now
    online = sum(1 for d in devices if (aware(d.get("last_online_at")) or now - timedelta(days=1)) >= recent)
    state = _ticket_base(row)
    body = str(row.get("last_user_body") or "").strip()
    state.update(
        nm=str(row.get("first_name") or user.get("first_name") or "Без имени")[:64],
        un=str(row.get("username") or user.get("username") or "")[:64],
        dd=max(0, (now - since).days), b=int(user.get("balance_rub") or 0),
        n=len(devices), on=online, p=int(paid or 0),
        ms=body[:280] + ("…" if len(body) > 280 else ""),
        f=1 if str(row.get("source") or "") == "app" else 0,
        rm=1 if admin_id is not None and reply_target(admin_id) == int(row["id"]) else 0,
    )
    return state


def admin_ticket_keyboard() -> InlineKeyboardMarkup | None:
    base = (get_settings().webapp_public_url or "").rstrip("/")
    if not base:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть в админке", url=f"{base}/admin")]])


async def send_admin_ticket_widget(bot: Bot, admin_id: int, ticket_id: int, *, caption: str, source: str = "bot") -> Message:
    _fits(caption)
    state = await admin_ticket_state(ticket_id, admin_id)
    if "e" in state:
        raise KeyError(state["e"])
    state["f"] = 1 if source == "app" else state.get("f", 0)
    return await bot(SendWidget(chat_id=admin_id, html=admin_ticket_html(), chat_data=_json(state), caption=caption,
                                parse_mode="HTML", allow_queries=True, reply_markup=admin_ticket_keyboard()))


# ---------- daily results ----------

SHORT_LABELS = {"invite": "Пригласить друзей", "share": "Поделиться", "copy": "Копировали приглашение",
                "about": "О сервисе", "cabinet": "Открыли кабинет", "gift_view": "Смотрели подарок"}


async def digest_state(day: date, rows=(), users: int = 0) -> dict[str, Any]:
    """d — the day's start, v/y — rubles that day and the day before, p/f — payments and first payments,
    n/nd/np — newcomers, of them with a device and paid, r — [label, events, people], u — active people."""
    start = datetime.combine(day, datetime.min.time(), MSK)
    end, before = start + timedelta(days=1), start - timedelta(days=1)
    pool = db._pool_req()
    pay = dict(await pool.fetchrow(
        """SELECT COALESCE(SUM(amount) FILTER (WHERE created_at >= $1), 0)::int AS v,
                  COUNT(*) FILTER (WHERE created_at >= $1)::int AS p,
                  COUNT(*) FILTER (WHERE created_at >= $1 AND first_payment)::int AS f,
                  COALESCE(SUM(amount) FILTER (WHERE created_at < $1), 0)::int AS y
           FROM payment_receipts WHERE created_at >= $3 AND created_at < $2""", start, end, before) or {})
    new = dict(await pool.fetchrow(
        """SELECT COUNT(*)::int AS n,
                  COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id))::int AS nd,
                  COUNT(*) FILTER (WHERE COALESCE(u.has_paid_topup, FALSE))::int AS np
           FROM users u WHERE u.created_at >= $1 AND u.created_at < $2""", start, end) or {})
    state: dict[str, Any] = {k: int(pay.get(k) or 0) for k in ("v", "p", "f", "y")}
    state.update({k: int(new.get(k) or 0) for k in ("n", "nd", "np")})
    activity = sorted(([SHORT_LABELS.get(r["action"], r["action"]), int(r["events"]), int(r["users"])] for r in rows),
                      key=lambda r: -r[1])
    state.update(d=int(start.timestamp()), r=activity[:6], u=int(users or 0))
    return state


async def activity_rows(day: date) -> tuple[list, int]:
    pool = db._pool_req()
    rows = await pool.fetch("""SELECT action, SUM(events)::bigint AS events, COUNT(DISTINCT telegram_id)::int AS users
        FROM admin_activity_daily WHERE day = $1 GROUP BY action ORDER BY action""", day)
    users = await pool.fetchval("SELECT COUNT(DISTINCT telegram_id) FROM admin_activity_daily WHERE day = $1", day)
    return [dict(r) for r in rows], int(users or 0)


def digest_caption(state: dict) -> str:
    day = datetime.fromtimestamp(state["d"], MSK).strftime("%d.%m.%Y")
    return f"Итоги {day}: {state['v']} ₽, {state['p']} оплат, {state['n']} новых пользователей"


async def send_digest_widget(bot: Bot, chat_id: int, day: date, rows=None, users: int | None = None) -> Message:
    if rows is None or users is None:
        rows, users = await activity_rows(day)
    state = await digest_state(day, rows, users)
    return await bot(SendWidget(chat_id=chat_id, html=digest_html(), chat_data=_json(state),
                                caption=digest_caption(state)), request_timeout=30)


# ---------- revenue forecast ----------

async def forecast_state() -> dict[str, Any]:
    """r7/x7/c7 and r30/x30/c30 — expected rubles, payments and clients due in 7 and 30 days,
    av — average repeat payment, s — clients whose balance ends on each of the next 8 days,
    l — the soonest three as [name, days left, balance]."""
    from app.finance import DUE_SQL
    from app.revenue_forecast import report

    rep = await report()
    state: dict[str, Any] = {"t": int(time.time())}
    for period in rep.get("periods") or []:
        n = int(period["days"])
        state[f"r{n}"] = period.get("rub")
        state[f"x{n}"] = period.get("expected_payments")
        state[f"c{n}"] = int(period.get("clients") or 0)
    avg = rep.get("average_repeat_rub")
    state["av"] = round(avg) if avg else 0
    price = max(1, int(get_settings().vpn_day_price_rub))
    now = datetime.now(timezone.utc)
    today = now.astimezone(MSK).date()
    series, people = [0] * 8, []
    for row in await db._pool_req().fetch(DUE_SQL, price, 7):
        left = []
        count = int(row["device_count"] or 0)
        if row["balance_low"] and count:
            left.append(max(0, int(row["balance_rub"])) // (price * count))
        if row["router_due"] and row["router_expire_at"]:
            left.append(max(0, (row["router_expire_at"].astimezone(MSK).date() - today).days))
        if not left:
            continue
        days = min(7, min(left))
        series[days] += 1
        name = str(row["first_name"] or (f"@{row['username']}" if row["username"] else row["telegram_id"]))[:40]
        people.append([name, days, int(row["balance_rub"] or 0)])
    people.sort(key=lambda p: (p[1], p[2]))
    state.update(s=series, l=people[:3])
    return state


async def send_forecast_widget(bot: Bot, chat_id: int) -> Message:
    state = await forecast_state()
    caption = (f"Прогноз: ≈{state['r7']} ₽ за 7 дней" if state.get("r7") is not None
               else "Прогноз выручки: пока мало повторных оплат")
    return await bot(SendWidget(chat_id=chat_id, html=forecast_html(), chat_data=_json(state), caption=caption,
                                allow_queries=True))


# ---------- requests ----------

def _id(raw: str) -> int | None:
    return int(raw) if raw.isdigit() else None


async def handle_query(bot: Bot, user_id: int, data: str) -> dict[str, Any]:
    head, _, rest = data.partition(":")
    admin = user_id in get_settings().admin_id_set
    if head in ("z", "k", "v"):
        raw_id, _, raw_score = rest.partition(":")
        tid = _id(raw_id)
        if tid is None:
            return {"e": "Обращение не найдено"}
        if head == "k":
            if await db.close_user_ticket(user_id, tid):
                from app.handlers.tickets import close_support
                close_support(user_id)
        elif head == "v":
            if not raw_score.isdigit() or not 1 <= int(raw_score) <= 5:
                return {"e": "Выберите оценку от 1 до 5"}
            if not await db.rate_user_ticket(user_id, tid, int(raw_score)):
                return {"e": "Оценка уже поставлена"}
        return await ticket_state(tid, user_id)
    if not admin:
        return {"e": "Нет доступа"}
    if data == "F":
        return await forecast_state()
    tid = _id(rest)
    if head not in ("A", "C", "W") or tid is None:
        return {"e": "Неизвестный запрос"}
    if head == "C":
        from app.tickets import close_ticket
        await close_ticket(bot, tid)
        stop_reply(user_id)
    elif head == "W":
        if reply_target(user_id) == tid:
            stop_reply(user_id)
        else:
            _replying[user_id] = (tid, time.monotonic() + REPLY_SECONDS)
    return await admin_ticket_state(tid, user_id)
