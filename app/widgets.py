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
    """<div class="cd"><div class="tp"><span>Приглашайте друзей</span><span class="pi" id="pi" hidden></span></div>
<div class="em" id="m">—</div><div class="sl">заработано на приглашениях</div>
<div class="ts"><div><b id="i">—</b><span id="il">пришли по ссылке</span></div><div><b id="w">—</b><span id="wl">получили бонус</span></div></div>
<div class="gl"><div class="gt"><span id="gn"></span><span id="gp"></span></div><div class="gb"><i id="gi"></i></div></div></div>
<div class="rl" id="rl" hidden></div>
<div class="lk" id="lk" hidden><span id="ln"></span><b>копировать</b></div>
<button id="cp" class="pb">Скопировать приглашение</button>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf">↻</button></div>""",
    """let seen=s?s.i:0;const G=[1,3,5,10,25,50,100,250,500,1000];
function link(){const m=s&&s.c&&s.c.match(/https?:\\/\\/\\S+/);return m?m[0]:''}
function draw(){if(!s)return;const i=$('i');i.textContent=s.i;$('il').textContent=pl(s.i,'пришёл','пришли','пришли')+' по ссылке';
if(s.i>seen){i.className='pop';$('u').textContent='+'+(s.i-seen)+' '+pl(s.i-seen,'друг','друга','друзей')+' 🎉';
if(W.HapticFeedback)W.HapticFeedback.notificationOccurred('success')}
else $('u').textContent='Обновлено в '+hm(s.t);seen=s.i;
$('w').textContent=s.w;$('wl').textContent=pl(s.w,'получил','получили','получили')+' бонус';$('m').textContent=rub(s.m);
if(s.r){$('pi').hidden=false;$('pi').textContent='+'+rub(s.r)+' за друга';$('rl').hidden=false;
$('rl').textContent='Друг открывает бота по вашей ссылке — '+(s.q?'он получает '+rub(s.q)+', а ':'')+'вам приходит '+rub(s.r)+' на баланс.'}
const g=G.find(x=>x>s.i)||s.i+1,p=G.filter(x=>x<=s.i).pop()||0;
$('gn').textContent=s.i?'Цель: '+g+' '+pl(g,'друг','друга','друзей'):'Пригласите первого друга';
$('gp').textContent=s.i+' / '+g;$('gi').style.width=Math.max(4,(s.i-p)/(g-p)*100)+'%';
const l=link();if(l){$('lk').hidden=false;$('ln').textContent=l.replace(/^https?:\\/\\//,'')}}
function copy(t,m){if(!t)return;W.copyText(t);$('u').textContent=m;if(W.HapticFeedback)W.HapticFeedback.impactOccurred('light')}
$('cp').onclick=()=>copy(s&&s.c,'Приглашение скопировано — отправьте его другу');
$('lk').onclick=()=>copy(link(),'Ссылка скопирована');
draw();live('f',v=>{v.c=v.c||(s&&s.c);s=v;draw()});""",
    ".cd{border-radius:18px;padding:14px 16px 16px;color:#fff;background:linear-gradient(155deg,#5fd38d 0%,#28a464 55%,#16804a 100%)}"
    ".tp{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:600;font-size:.92em}"
    ".pi{background:rgba(255,255,255,.22);border-radius:10px;padding:2px 8px;font-size:.85em;white-space:nowrap}"
    ".em{font-size:2.2em;font-weight:800;margin-top:10px;line-height:1.1;font-variant-numeric:tabular-nums}"
    ".sl{font-size:.82em;opacity:.85}"
    ".ts{display:flex;gap:8px;margin-top:12px}.ts div{flex:1;background:rgba(255,255,255,.16);border-radius:12px;padding:8px 10px}"
    ".ts b{display:block;font-size:1.35em;font-variant-numeric:tabular-nums}.ts span{font-size:.78em;opacity:.9}"
    ".gl{margin-top:12px}.gt{display:flex;justify-content:space-between;font-size:.8em;opacity:.92}"
    ".gb{height:6px;border-radius:3px;background:rgba(255,255,255,.22);margin-top:4px;overflow:hidden}"
    ".gb i{display:block;height:100%;background:#fff;border-radius:3px;transition:width .6s}"
    ".rl{font-size:.85em;color:var(--tg-theme-hint-color);margin-top:10px;line-height:1.35}"
    ".lk{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px;padding:8px 10px;border-radius:10px;"
    "background:var(--tg-theme-secondary-bg-color);font-family:ui-monospace,Menlo,monospace;font-size:.8em;cursor:pointer}"
    ".lk span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.lk b{font-family:inherit;font-size:.9em;"
    "color:var(--tg-theme-link-color);font-weight:600}"
    ".pb{width:100%;margin-top:10px;padding:11px 0;font-weight:600;border-radius:12px}.rf{padding:4px 10px}"
    ".pop{animation:pop .6s ease}@keyframes pop{40%{transform:scale(1.3)}}",
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
    """<div class="hd"><span class="t">__BRAND__ · сегодня</span><span class="dl" id="dl"></span></div>
<div class="big" id="v">—</div><div class="t" id="pc"></div>
<div class="sw"><button id="ta" class="on">Пополнения</button><button id="tb">Новые</button></div>
<div class="ch" id="ch"></div><div class="ax"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
<div class="mx" id="mx"></div><div class="lg" id="lg"></div>
<div class="sec">Новички сегодня</div><div id="fn"></div>
<div class="sec">Сейчас</div>
<div class="row" style="margin-top:0"><div class="c"><span class="t">В сети за час</span><b id="o">—</b></div>
<div class="c"><span class="t">С доступом</span><b id="x">—</b></div><div class="c"><span class="t">Всего</span><b id="a">—</b></div></div>
<div class="tk" id="k"></div>
<div class="f"><span class="t" id="u"></span><button id="r">Обновить</button></div>""",
    """let tab=0;const M={rollypay:['Карта/СБП','#34c759'],stars:['Звёзды','#ffb800'],ton:['Gram','#2ea6ff']};
function n(v){return String(v).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')}
function chart(){const d=tab?s.g:s.h,mx=Math.max(1,...d),now=new Date(Date.now()+108e5).getUTCHours();
$('ch').innerHTML=d.map((v,i)=>'<i class="'+(i==now?'nw':i>now?'ft':'')+'" style="height:'+(v?Math.max(6,v/mx*100):2)+'%" title="'+i+':00 — '+(tab?v:rub(v))+'"></i>').join('');
$('ta').className=tab?'':'on';$('tb').className=tab?'on':''}
function draw(){if(!s)return;$('v').textContent=rub(s.v);
const dl=$('dl');if(s.y>0){const p=Math.round((s.v-s.y)/s.y*100);dl.textContent=(p>=0?'+':'')+p+'% к вчера';dl.className='dl '+(p>=0?'up':'dn')}
else dl.textContent=s.v?'вчера к этому часу 0 ₽':'';
$('pc').textContent=s.p?s.p+' '+pl(s.p,'оплата','оплаты','оплат')+' · '+s.f+' '+pl(s.f,'первая','первые','первых')+' · средний чек '+rub(Math.round(s.v/s.p)):'Оплат пока нет';
chart();const m=Object.entries(s.m||{}),tot=m.reduce((a,e)=>a+e[1],0)||1;
$('mx').innerHTML=m.map(e=>'<i style="flex:'+e[1]+';background:'+(M[e[0]]||['','#999'])[1]+'"></i>').join('');
$('lg').innerHTML=m.map(e=>'<span><b style="background:'+(M[e[0]]||['','#999'])[1]+'"></b>'+(M[e[0]]||[e[0]])[0]+' '+n(e[1])+' ₽ · '+Math.round(e[1]/tot*100)+'%</span>').join('');
const st=[['Пришли в бота',s.n,s.nr?s.nr+' по приглашению':''],['Добавили устройство',s.nd],['Подключились',s.nc],['Оплатили',s.np]];
$('fn').innerHTML=st.map(e=>'<div class="fr"><div class="fl"><span>'+e[0]+(e[2]?' <span class="t">· '+e[2]+'</span>':'')+'</span><b>'+e[1]+(s.n&&e!==st[0]?' <span class="t">'+Math.round(e[1]/s.n*100)+'%</span>':'')+'</b></div><div class="fb"><i style="width:'+(s.n?e[1]/s.n*100:0)+'%"></i></div></div>').join('');
$('o').textContent=n(s.o);$('x').textContent=n(s.x);$('a').textContent=n(s.a);
const k=$('k');k.textContent=s.k?'Открытых обращений: '+s.k+' — ответьте в админке':'Открытых обращений нет';k.className='tk'+(s.k?' low':'');
$('u').textContent='Обновлено в '+hm(s.t)}
$('ta').onclick=()=>{tab=0;chart()};$('tb').onclick=()=>{tab=1;chart()};
draw();live('s',v=>{s=v;draw()});""",
    ".hd{display:flex;justify-content:space-between;align-items:center;gap:8px}"
    ".dl{font-size:.78em;font-weight:600;padding:2px 8px;border-radius:10px;background:var(--tg-theme-secondary-bg-color)}"
    ".dl.up{color:#2fa84f}.dl.dn{color:var(--tg-theme-destructive-text-color)}"
    ".sw{display:flex;gap:4px;margin:12px 0 6px}.sw button{flex:1;padding:5px 0;font-size:.85em;border-radius:8px;"
    "background:var(--tg-theme-secondary-bg-color);color:var(--tg-theme-text-color)}"
    ".sw .on{background:var(--tg-theme-button-color);color:var(--tg-theme-button-text-color)}"
    ".ch{display:flex;align-items:flex-end;gap:2px;height:64px}.ch i{flex:1;border-radius:3px 3px 0 0;"
    "background:var(--tg-theme-button-color);opacity:.55}.ch .nw{opacity:1}.ch .ft{opacity:.15}"
    ".ax{display:flex;justify-content:space-between;font-size:.68em;color:var(--tg-theme-hint-color);margin-top:3px}"
    ".mx{display:flex;height:8px;border-radius:4px;overflow:hidden;margin-top:12px;gap:2px}"
    ".lg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:.78em;margin-top:6px}"
    ".lg b{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px}"
    ".sec{font-weight:600;margin:16px 0 6px}"
    ".fr{margin-bottom:8px}.fl{display:flex;justify-content:space-between;font-size:.9em;gap:8px}"
    ".fb{height:6px;border-radius:3px;background:var(--tg-theme-secondary-bg-color);margin-top:3px;overflow:hidden}"
    ".fb i{display:block;height:100%;background:var(--tg-theme-accent-text-color);border-radius:3px}"
    ".row .c b{font-size:1.05em}.tk{font-size:.85em;margin-top:10px;color:var(--tg-theme-hint-color)}"
    ".tk.low{color:var(--tg-theme-destructive-text-color)}",
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
    settings = get_settings()
    state = {"i": int(refs.get("invited") or 0), "w": int(refs.get("rewarded") or 0), "m": earned, "t": int(time.time())}
    if settings.referral_program_enabled:
        # r — what the inviter gets per friend, q — what the friend gets.
        state["r"] = max(0, int(settings.referral_reward_rub or 0))
        state["q"] = max(0, int(settings.referral_invitee_reward_rub or 0))
    if with_link:
        from app.keyboards import invite_copy_text
        state["c"] = invite_copy_text(telegram_id)
    return state


_DAY_START = "(date_trunc('day', NOW() AT TIME ZONE 'Europe/Moscow') AT TIME ZONE 'Europe/Moscow')"


async def stats_state() -> dict[str, Any]:
    """Today in Moscow time for the admin widget; cheap enough to run every 30 seconds.

    v/y — rubles credited today and yesterday by this time, p/f — payments and first payments,
    m — rubles by provider, h/g — rubles and new users per hour, n/nr/nd/nc/np — today's newcomers:
    all, by invitation, added a device, connected, paid. o — online in the last hour,
    x — with access (balance and a device), a — all users, k — open support tickets."""
    pool = db._pool_req()
    day = _DAY_START
    row = dict(await pool.fetchrow(
        f"""
        SELECT
            (SELECT COUNT(*)::int FROM users) AS a,
            (SELECT COUNT(DISTINCT telegram_id)::int FROM devices WHERE last_online_at >= NOW() - INTERVAL '1 hour') AS o,
            (SELECT COUNT(*)::int FROM users u WHERE COALESCE(u.balance_rub, 0) > 0
                AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)) AS x,
            (SELECT COUNT(*)::int FROM tickets WHERE status = 'open') AS k,
            COUNT(*)::int AS n,
            COUNT(*) FILTER (WHERE u.referred_by IS NOT NULL)::int AS nr,
            COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id))::int AS nd,
            COUNT(*) FILTER (WHERE u.first_online_at IS NOT NULL)::int AS nc,
            COUNT(*) FILTER (WHERE COALESCE(u.has_paid_topup, FALSE))::int AS np
        FROM users u WHERE u.created_at >= {day}
        """
    ) or {})
    pay = dict(await pool.fetchrow(
        f"""
        SELECT
            COALESCE(SUM(amount) FILTER (WHERE created_at >= {day}), 0)::int AS v,
            COUNT(*) FILTER (WHERE created_at >= {day})::int AS p,
            COUNT(*) FILTER (WHERE created_at >= {day} AND first_payment)::int AS f,
            COALESCE(SUM(amount) FILTER (WHERE created_at < NOW() - INTERVAL '1 day'), 0)::int AS y
        FROM payment_receipts WHERE created_at >= {day} - INTERVAL '1 day'
        """
    ) or {})
    methods = await pool.fetch(
        f"""SELECT split_part(payment_key, ':', 1) AS m, SUM(amount)::int AS rub FROM payment_receipts
            WHERE created_at >= {day} GROUP BY 1"""
    )
    hours_rub = await pool.fetch(
        f"""SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'Europe/Moscow')::int AS h, SUM(amount)::int AS n
            FROM payment_receipts WHERE created_at >= {day} GROUP BY 1"""
    )
    hours_new = await pool.fetch(
        f"""SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'Europe/Moscow')::int AS h, COUNT(*)::int AS n
            FROM users WHERE created_at >= {day} GROUP BY 1"""
    )

    def by_hour(rows) -> list[int]:
        out = [0] * 24
        for r in rows:
            if 0 <= int(r["h"]) < 24:
                out[int(r["h"])] = int(r["n"] or 0)
        return out

    state: dict[str, Any] = {k: int(pay.get(k) or 0) for k in ("v", "y", "p", "f")}
    state["m"] = {str(r["m"]): int(r["rub"] or 0) for r in methods if int(r["rub"] or 0)}
    state["h"], state["g"] = by_hour(hours_rub), by_hour(hours_new)
    state.update({k: int(row.get(k) or 0) for k in ("n", "nr", "nd", "nc", "np", "o", "x", "a", "k")})
    state["t"] = int(time.time())
    return state


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
        caption=f"Сегодня: {state['v']} ₽ пополнений, {state['p']} оплат, {state['n']} новых пользователей",
        allow_queries=True,
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
