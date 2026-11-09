"""Balance widget for the private chat (Bot API 10.4 widgets).

aiogram 3.25 doesn't know widgets yet, so the methods are declared here and the
`widget_query` update is caught by an outer middleware before aiogram drops it.
The widget is offline: it draws from its chat state and asks the bot for fresh
numbers when it appears on screen, every 30 seconds while visible, and on «Обновить».
"""
from __future__ import annotations

import html
import json
import logging
import time
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.methods.base import TelegramMethod
from aiogram.types import InlineKeyboardMarkup, Message

from app import db
from app.config import get_settings

logger = logging.getLogger(__name__)

UPDATE_TYPES = ("widget_query",)
REFRESH = "r"


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


WIDGET_HTML = """<style>
body{margin:0;padding:12px 14px max(10px,env(safe-area-inset-bottom))}
.t{color:var(--tg-theme-hint-color);font-size:.85em}
.b{font-size:2em;font-weight:700;font-variant-numeric:tabular-nums;margin:2px 0}
.d{font-weight:600}
.low{color:var(--tg-theme-destructive-text-color)}
.ok{color:var(--tg-theme-accent-text-color)}
.row{display:flex;gap:8px;margin-top:10px}
.c{flex:1;background:var(--tg-theme-secondary-bg-color);border-radius:10px;padding:8px 10px}
.c b{display:block;font-size:1.15em;font-variant-numeric:tabular-nums}
.f{display:flex;align-items:center;justify-content:space-between;margin-top:10px;
padding-right:var(--tg-content-safe-area-corner-right)}
button{padding:6px 14px}
</style>
<div class="t">__BRAND__ · баланс</div>
<div class="b" id="b">—</div>
<div class="d" id="d"></div>
<div class="row">
<div class="c"><span class="t">Устройства</span><b id="n">—</b></div>
<div class="c"><span class="t">В день</span><b id="p">—</b></div>
</div>
<div class="f"><span class="t" id="u"></span><button id="r">Обновить</button></div>
<script>
const W=window.TelegramWidget,$=i=>document.getElementById(i);
let s=null,busy=0;
try{s=JSON.parse(W.chatData)}catch(e){}
function pl(n,a,b,c){n=Math.abs(n)%100;const m=n%10;
return n>10&&n<20?c:m==1?a:m>1&&m<5?b:c}
function rub(v){return String(v).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')+' ₽'}
function draw(){
if(!s){$('d').textContent='Загружаем…';return}
$('b').textContent=rub(s.b);
const d=$('d');
if(!s.n){d.textContent=s.b>0?'Добавьте устройство в кабинете':'Пополните баланс, чтобы подключиться';d.className='d'}
else if(s.h<1){d.textContent='Баланс закончился';d.className='d low'}
else{const x=s.d>0?s.d+' '+pl(s.d,'день','дня','дней'):s.h+' '+pl(s.h,'час','часа','часов');
d.textContent='Хватит на '+x;d.className='d '+(s.d<3?'low':'ok')}
$('n').textContent=s.n;$('p').textContent=rub(s.p*Math.max(1,s.n));
const t=new Date(s.t*1000);
$('u').textContent='Обновлено в '+String(t.getHours()).padStart(2,'0')+':'+String(t.getMinutes()).padStart(2,'0')}
function ask(tap){if(busy)return;busy=1;if(tap)$('r').disabled=true;
W.request('r').then(a=>{try{const v=JSON.parse(a.result);if(v&&!v.e)s=v;else if(v&&v.e)$('u').textContent=v.e}catch(e){}draw()},
e=>{if(tap)$('u').textContent=e.code=='RATE_LIMITED'?'Слишком часто, подождите':'Не удалось обновить'})
.finally(()=>{busy=0;$('r').disabled=false})}
$('r').onclick=()=>{if(W.HapticFeedback)W.HapticFeedback.impactOccurred('light');ask(1)};
draw();if(W.ready)W.ready();
ask(0);setInterval(()=>{if(W.isActive!==false)ask(0)},30000);
</script>"""


def widget_html() -> str:
    return WIDGET_HTML.replace("__BRAND__", html.escape(get_settings().brand_name or "VPN"))


async def balance_state(telegram_id: int) -> dict[str, Any]:
    """Short-key state the widget draws: balance, days/hours left, device count, price per device-day."""
    from app.web import _is_router_device, balance_runway

    local = await db.get_user(telegram_id)
    raw_devices = await db.list_devices(telegram_id)
    balance = int((local or {}).get("balance_rub") or 0)
    days, hours = balance_runway(local, raw_devices, balance)
    return {
        "b": balance,
        "d": days,
        "h": hours,
        "n": sum(1 for item in raw_devices if not _is_router_device(item)),
        "p": max(1, get_settings().vpn_day_price_rub),
        "t": int(time.time()),
    }


def _state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, separators=(",", ":"), ensure_ascii=False)


def balance_widget_keyboard() -> InlineKeyboardMarkup | None:
    from app.keyboards import cabinet_button, payment_nudge_keyboard

    rows = payment_nudge_keyboard(label="Пополнить баланс").inline_keyboard
    cabinet = cabinet_button()
    if cabinet:
        rows = [*rows, [cabinet]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_balance_widget(bot: Bot, telegram_id: int) -> Message:
    state = await balance_state(telegram_id)
    days = state["d"]
    caption = f"Баланс: {state['b']} ₽" + (f" · хватит на {days} дн." if state["n"] and days else "")
    return await bot(SendWidget(
        chat_id=telegram_id,
        html=widget_html(),
        chat_data=_state_json(state),
        caption=caption,
        allow_queries=True,
        reply_markup=balance_widget_keyboard(),
    ))


async def answer_widget_query(bot: Bot, query: dict[str, Any]) -> None:
    query_id = str(query.get("id") or "")
    user_id = int((query.get("from") or {}).get("id") or 0)
    if not query_id:
        return
    if query.get("data") != REFRESH or not user_id:
        await bot(AnswerWidgetQuery(widget_query_id=query_id, data=_state_json({"e": "Неизвестный запрос"})))
        return
    try:
        payload = _state_json(await balance_state(user_id))
    except Exception:
        logger.exception("Не удалось собрать баланс для виджета")
        payload = _state_json({"e": "Не удалось обновить"})
    await bot(AnswerWidgetQuery(widget_query_id=query_id, data=payload))


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
