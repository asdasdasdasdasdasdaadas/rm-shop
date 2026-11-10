"""Client care widgets: countdown before VPN turns off, a fresh subscription key, setup checklist.

Requests (from the widget):
  r  balance numbers (app.widgets) — the countdown refreshes with it
  o  setup progress: d device added, s link opened in a VPN app, c connected, a device title
"""
from __future__ import annotations

import logging
import time
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

from app import db
from app.widgets import SendWidget, _brand, _json
from app.widgets_more import _fits, _more

logger = logging.getLogger(__name__)
KEY_LINKS = 8
SETUP_CACHE_SECONDS = 20
_setup_cache: dict[int, tuple[float, dict]] = {}

_CARE_CSS = (
    ".br{height:6px;border-radius:99px;background:rgba(255,255,255,.25);margin-top:10px;overflow:hidden}"
    ".br i{display:block;height:100%;width:4%;border-radius:99px;background:#fff;transition:width .6s}"
)

COUNTDOWN_HTML = _more(
    """<div class="cd or" id="cd"><div class="hd"><span>__BRAND__</span><span class="pl" id="pl"></span></div>
<div class="tm" id="tm">—</div><div class="sb" id="sb"></div><div class="br"><i id="bi"></i></div>
<div class="tl"><div>баланс<b id="b">—</b></div><div>в день<b id="p">—</b></div><div><span id="nl">устройств</span><b id="n">—</b></div></div></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """const G=s&&s.g,D=259200;function z(v){return String(v).padStart(2,'0')}
function tick(){if(!s)return;const left=Math.max(0,(s.e||0)-Date.now()/1e3),cd=$('cd');let k='or';
if(!s.n){k='gy';$('pl').textContent='нет устройств';$('tm').textContent='—';$('sb').textContent='Добавьте устройство в кабинете'}
else if(left>D){k='';$('pl').textContent='продлено';$('tm').textContent='до '+dm(s.e);$('sb').textContent='Хватит на '+s.d+' '+pl(s.d,'день','дня','дней')+' — спасибо!'}
else if(left<=0){k='gy';$('pl').textContent='VPN отключён';$('tm').textContent='00:00:00';$('sb').textContent='Пополните баланс — VPN включится сам'}
else{const d=Math.floor(left/86400);$('pl').textContent=G?'подарок заканчивается':'заканчивается';
$('tm').textContent=(d?d+' д ':'')+z(Math.floor(left%86400/3600))+':'+z(Math.floor(left%3600/60))+':'+z(Math.floor(left%60));
$('sb').textContent='до отключения VPN · '+dm(s.e)+' в '+hm(s.e)}
cd.className='cd '+k;$('bi').style.width=Math.max(4,Math.min(100,left/D*100))+'%'}
function draw(){if(!s)return;$('b').textContent=rub(s.b);$('p').textContent=rub(s.p*Math.max(1,s.n));$('n').textContent=s.n;
$('nl').textContent=pl(s.n,'устройство','устройства','устройств');$('u').textContent='Обновлено в '+hm(s.t);tick()}
draw();setInterval(tick,1000);live('r',v=>{const e=s&&s.e;s=Object.assign(s||{},v);if(e&&v.e>e+3600)H('success');draw()});""",
    _CARE_CSS + ".tm{font-size:2.3em;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.15;margin:6px 0 2px}",
)

KEY_HTML = _more(
    """<div class="cd bl"><div class="hd"><span>__BRAND__ · подписка</span><span class="pl">старая отключена</span></div>
<div class="em sm">🔑 Новая ссылка</div><div class="sb">Нажмите, чтобы скопировать, и добавьте её в VPN-приложение</div>
<div id="ls"></div></div><div class="f"><span class="t" id="u"></span></div>""",
    """function draw(){if(!s)return;$('ls').innerHTML='';(s.l||[]).forEach(x=>{const d=el($('ls'),'<span></span><b></b><em>скопировать</em>','lk');
d.children[0].textContent=x[0]||'Ссылка подписки';d.children[1].textContent=x[1].split('://').pop();
d.onclick=()=>{if(W.copyText)W.copyText(x[1]);d.children[2].textContent='скопировано ✓';H('success');
$('u').textContent='В приложении: «+» → «Из буфера обмена»'}});$('u').textContent='Выдана в '+hm(s.t)}
draw();if(W.ready)W.ready();""",
    ".lk{margin-top:8px;padding:9px 11px;border-radius:12px;background:rgba(9,14,50,.25);border:1px dashed rgba(255,255,255,.5);cursor:pointer}"
    ".lk span{display:block;font-size:.75em;opacity:.85}.lk b{display:block;font-size:.85em;word-break:break-all}"
    ".lk em{display:block;font-style:normal;font-size:.75em;font-weight:700;margin-top:3px}",
)

SETUP_HTML = _more(
    """<div class="cd bl" id="cd"><div class="hd"><span>__BRAND__ · подключение</span><span class="pl" id="pg"></span></div>
<div class="em sm" id="hl">—</div><div class="br"><i id="bi"></i></div></div>
<div class="st" id="st"></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """const S=[['Добавить устройство','В кабинете — «Добавить устройство»'],['Добавить ссылку в приложение','Кабинет подскажет, какое приложение скачать'],
['Включить VPN','Нажмите подключение в приложении']];let was=-1;
function draw(){if(!s)return;const f=[s.d,s.s,s.c],n=f.filter(Boolean).length,all=n==3;
$('pg').textContent=n+' из 3';$('bi').style.width=Math.max(4,n/3*100)+'%';$('cd').className='cd'+(all?'':' bl');
$('hl').textContent=all?'VPN работает 🎉':n?'Почти готово':'Подключим за пару минут';$('st').innerHTML='';
S.forEach((x,i)=>{const d=f[i],c=!d&&f.slice(0,i).every(Boolean),r=el($('st'),'<i></i><span><b></b><em></em></span>',d?'dn':c?'nw':'');
r.querySelector('i').textContent=d?'✓':i+1;r.querySelector('b').textContent=x[0];r.querySelector('em').textContent=i==0&&d&&s.a?s.a:x[1]});
if(was>=0&&n>was)H('success');was=n;$('u').textContent='Обновлено в '+hm(s.t)}
draw();live('o',v=>{s=v;draw()});""",
    _CARE_CSS
    + ".st{margin-top:6px}.st div{display:flex;gap:10px;align-items:center;padding:8px 2px}"
    ".st div+div{border-top:1px solid var(--tg-theme-secondary-bg-color)}"
    ".st i{flex:none;width:26px;height:26px;border-radius:99px;display:grid;place-items:center;font-style:normal;font-weight:700;"
    "font-size:.85em;background:var(--tg-theme-secondary-bg-color);color:var(--tg-theme-hint-color)}"
    ".st b{display:block}.st em{display:block;font-style:normal;font-size:.8em;color:var(--tg-theme-hint-color)}"
    ".st .dn i{background:#28a464;color:#fff}.st .dn b{opacity:.65}"
    ".st .nw i{background:#2b7de9;color:#fff;box-shadow:0 0 0 4px rgba(43,125,233,.25)}",
)


def countdown_html() -> str:
    return COUNTDOWN_HTML.replace("__BRAND__", _brand())


def key_html() -> str:
    return KEY_HTML.replace("__BRAND__", _brand())


def setup_html() -> str:
    return SETUP_HTML.replace("__BRAND__", _brand())


# ---------- countdown before VPN turns off ----------

async def countdown_state(telegram_id: int) -> dict[str, Any]:
    """The balance numbers plus g=1 while the customer has never paid: the days left are the gift."""
    from app.widgets import balance_state
    state = await balance_state(telegram_id)
    local = await db.get_user(telegram_id) or {}
    if not local.get("has_paid_topup"):
        state["g"] = 1
    return state


async def send_countdown_widget(bot: Bot, telegram_id: int, *, caption: str,
                                reply_markup: InlineKeyboardMarkup | None = None) -> Message:
    _fits(caption)
    state = await countdown_state(telegram_id)
    return await bot(SendWidget(chat_id=telegram_id, html=countdown_html(), chat_data=_json(state), caption=caption,
                                parse_mode="HTML", allow_queries=True, reply_markup=reply_markup))


# ---------- a fresh subscription link ----------

def key_state(links: list[tuple[str, str]]) -> dict[str, Any]:
    items = [[str(title or "")[:40], str(url)] for title, url in links if url][:KEY_LINKS]
    return {"l": items, "t": int(time.time())}


async def send_key_widget(bot: Bot, telegram_id: int, links: list[tuple[str, str]], *, caption: str,
                          reply_markup: InlineKeyboardMarkup | None = None) -> Message:
    _fits(caption)
    state = key_state(links)
    if not state["l"]:
        raise ValueError("no links to show")
    return await bot(SendWidget(chat_id=telegram_id, html=key_html(), chat_data=_json(state), caption=caption,
                                parse_mode="HTML", reply_markup=reply_markup))


async def notify_new_key(bot: Bot, telegram_id: int, links: list[tuple[str, str]], reply_markup=None) -> Message:
    """A new subscription link: the copy card, or the old text with the links where widgets don't work."""
    from aiogram.exceptions import TelegramForbiddenError
    from app.keyboards import cabinet_keyboard
    from app.texts import subscription_reissued_text
    markup = reply_markup if reply_markup is not None else cabinet_keyboard()
    caption = "🔑 Ссылка подписки обновлена. Старая больше не работает — добавьте новую в VPN-приложение."
    try:
        return await send_key_widget(bot, telegram_id, links, caption=caption, reply_markup=markup)
    except TelegramForbiddenError:
        raise
    except Exception:
        logger.warning("Карточка новой ссылки не отправилась %s, шлём текст", telegram_id, exc_info=True)
    return await bot.send_message(telegram_id, subscription_reissued_text(links), reply_markup=markup)


# ---------- setup checklist ----------

async def setup_state(telegram_id: int) -> dict[str, Any]:
    """Three steps, checked live: a device in the cabinet, its link opened by a VPN app, the first connection."""
    now = time.time()
    cached = _setup_cache.get(telegram_id)
    if cached and now - cached[0] < SETUP_CACHE_SECONDS:
        return cached[1]
    from app.web import _is_router_device
    local = await db.get_user(telegram_id) or {}
    devices = [d for d in await db.list_devices(telegram_id) if not _is_router_device(d)]
    connected = bool(local.get("first_online_at"))
    opened = connected
    if devices and not connected:
        opened, connected = await _panel_progress(devices)
    state = {"d": int(bool(devices or local.get("first_device_at"))), "s": int(opened or connected),
             "c": int(connected), "t": int(now)}
    if devices:
        state["a"] = str(devices[0].get("title") or "")[:40]
    _setup_cache[telegram_id] = (now, state)
    return state


async def _panel_progress(devices: list[dict]) -> tuple[bool, bool]:
    """Ask the panel whether any device's link was opened by an app and whether it ever connected."""
    from app import runtime
    from app.remnawave import panel_first_connected_at, panel_online_at, panel_sub_opened_at
    rw = getattr(runtime, "rw", None)
    opened = connected = False
    if rw is None:
        return opened, connected
    for device in devices[:3]:
        if not device.get("remnawave_id"):
            continue
        try:
            panel = await rw.get_user_by_id(int(device["remnawave_id"]))
        except Exception:
            logger.debug("Панель не ответила для чек-листа", exc_info=True)
            continue
        opened = opened or bool(panel_sub_opened_at(panel))
        connected = connected or bool(panel_first_connected_at(panel) or panel_online_at(panel))
    return opened, connected


async def send_setup_widget(bot: Bot, telegram_id: int, *, caption: str,
                            reply_markup: InlineKeyboardMarkup | None = None) -> Message:
    _fits(caption)
    _setup_cache.pop(telegram_id, None)
    state = await setup_state(telegram_id)
    return await bot(SendWidget(chat_id=telegram_id, html=setup_html(), chat_data=_json(state), caption=caption,
                                parse_mode="HTML", allow_queries=True, reply_markup=reply_markup))
