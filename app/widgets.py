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

import asyncio
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
if(v&&typeof v.e=='string'){$('u').textContent=v.e}else if(v){ok(v)}},
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
    """<div class="cd"><div class="sp"></div><div class="tp"><span class="gi">🎁</span><span>Друзья</span><span class="pi" id="pi" hidden></span></div>
<div class="em" id="m">—</div><div class="sl" id="sl">заработано на друзьях</div>
<div class="gl"><div class="gt"><span id="gn"></span><b id="gp"></b></div><div class="gb"><i id="gi"></i></div></div>
<div class="ts"><span><b id="i">—</b> <span id="il">пришли по ссылке</span></span><span><b id="w">—</b> <span id="wl">получили бонус</span></span></div>
<div class="lk" id="lk" hidden><span id="ln"></span><svg width="18" height="18" viewBox="0 0 24 24"><rect x="8" y="3" width="12" height="15" rx="2.5" fill="#fff"/><rect x="4" y="7" width="12" height="15" rx="2.5" fill="#fff" opacity=".6"/></svg></div>
<button id="cp" class="pb">Скопировать приглашение</button></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """let seen=s?s.i:0,shown=0;const G=[1,3,5,10,25,50,100,250,500,1000];
function link(){const m=s&&s.c&&s.c.match(/https?:\\/\\/\\S+/);return m?m[0]:''}
function count(to){const e=$('m'),from=shown,t0=performance.now();shown=to;
(function f(t){const k=Math.min(1,(t-t0)/900),v=Math.round(from+(to-from)*(1-Math.pow(1-k,3)));e.textContent='+'+rub(v);if(k<1)requestAnimationFrame(f)})(t0)}
function draw(){if(!s)return;const i=$('i');i.textContent=s.i;$('il').textContent=pl(s.i,'пришёл','пришли','пришли')+' по ссылке';
if(s.i>seen){i.className='pop';$('u').textContent='+'+(s.i-seen)+' '+pl(s.i-seen,'друг','друга','друзей')+' 🎉';
if(W.HapticFeedback)W.HapticFeedback.notificationOccurred('success')}
else $('u').textContent='Обновлено в '+hm(s.t);seen=s.i;
$('w').textContent=s.w;$('wl').textContent=pl(s.w,'получил','получили','получили')+' бонус';
const m=$('m');if(s.m>0){m.className='em';$('sl').textContent='заработано на друзьях';if(s.m!=shown)count(s.m)}
else{m.className='em sm';m.textContent=s.r?'+'+rub(s.r)+' за друга':'Зовите друзей';$('sl').textContent=s.r?(s.q?'а другу — '+rub(s.q)+', когда он откроет бота':'на баланс за каждого, кто придёт по ссылке'):'вместе пользоваться приятнее'}
if(s.r){$('pi').hidden=s.m<=0;$('pi').textContent='+'+rub(s.r)+' за друга'}
const g=G.find(x=>x>s.i)||s.i+1;
$('gn').textContent=s.i?'Цель — '+g+' '+pl(g,'друг','друга','друзей'):'Пригласите первого друга';
$('gp').textContent=s.i+' из '+g;$('gi').style.width=Math.max(6,s.i/g*100)+'%';
const l=link();if(l){$('lk').hidden=false;$('ln').textContent=l.replace(/^https?:\\/\\//,'')}}
function copy(t,m){if(!t)return;W.copyText(t);$('u').textContent=m;if(W.HapticFeedback)W.HapticFeedback.impactOccurred('light')}
$('cp').onclick=()=>copy(s&&s.c,'Приглашение скопировано — отправьте его другу');
$('lk').onclick=()=>copy(link(),'Ссылка скопирована');
draw();live('f',v=>{v.c=v.c||(s&&s.c);s=v;draw()});""",
    ".cd{position:relative;overflow:hidden;border-radius:22px;padding:14px 14px 12px;color:#fff;text-align:center;"
    "background:linear-gradient(180deg,#26307a 0%,#3d4ea3 55%,#6177cc 100%);animation:in .5s cubic-bezier(.2,.8,.2,1)}"
    "@keyframes in{from{transform:translateY(10px) scale(.97)}}"
    ".sp{position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 15% 12%,rgba(255,255,255,.22) 0 1.5px,transparent 2px),"
    "radial-gradient(circle at 85% 20%,rgba(255,255,255,.3) 0 1.5px,transparent 2px),radial-gradient(circle at 70% 8%,rgba(255,255,255,.18) 0 1px,transparent 1.5px),"
    "radial-gradient(circle at 50% 0,rgba(140,160,255,.35),transparent 60%)}"
    ".tp{position:relative;display:flex;align-items:center;gap:8px;font-weight:700;font-size:.95em;text-align:left}"
    ".gi{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:rgba(255,255,255,.18);font-size:17px}"
    ".pi{margin-left:auto;background:rgba(255,255,255,.2);border-radius:99px;padding:4px 10px;font-size:.8em;white-space:nowrap}"
    ".em{position:relative;font-size:2.4em;font-weight:800;margin-top:8px;line-height:1.05;font-variant-numeric:tabular-nums;letter-spacing:-.02em}"
    ".em.sm{font-size:1.75em}.sl{position:relative;font-size:.85em;opacity:.85;margin-top:4px}"
    ".gl{position:relative;margin-top:12px;text-align:left}.gt{display:flex;justify-content:space-between;font-size:.8em;opacity:.95}"
    ".gb{height:8px;border-radius:99px;background:rgba(9,14,50,.35);margin-top:6px;overflow:hidden}"
    ".gb i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#8fe3b0,#3ccf74);box-shadow:0 0 12px rgba(60,207,116,.7);"
    "transition:width .9s cubic-bezier(.2,.8,.2,1)}"
    ".ts{position:relative;display:flex;justify-content:space-between;gap:8px;margin-top:6px;font-size:.8em}.ts>span{opacity:.92}"
    ".ts b{font-variant-numeric:tabular-nums;font-size:1.15em}"
    ".lk{position:relative;display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px;padding:9px 12px 9px 14px;"
    "border-radius:14px;background:rgba(9,14,50,.32);border:1px dashed rgba(255,255,255,.4);font-weight:600;font-size:.85em;cursor:pointer}"
    ".lk span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.lk svg{flex-shrink:0}"
    ".pb{position:relative;width:100%;margin-top:8px;padding:11px 0;font-weight:700;border-radius:99px;background:#fff!important;color:#1f2a6b!important}"
    ".pb:active,.lk:active{transform:scale(.97)}"
    ".rl{font-size:.82em;color:var(--tg-theme-hint-color);margin-top:10px;line-height:1.35}"
    ".rf{width:32px;height:32px;padding:0;border-radius:99px}"
    ".pop{display:inline-block;animation:pop .6s ease}@keyframes pop{40%{transform:scale(1.35)}}",
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
    """<div class="hc"><div class="hd"><span>__BRAND__ · сегодня</span><span class="dl" id="dl"></span></div>
<div class="em" id="v">—</div><div class="pc" id="pc"></div></div>
<div class="sw"><button id="t0" class="on">Оплаты</button><button id="t1">Новички</button><button id="t2">Платящие</button><button id="t3">Сейчас</button></div>
<div class="pn" id="p0"><div class="ch" id="ch"></div><div class="ax"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
<div class="mx" id="mx"></div><div class="lg" id="lg"></div></div>
<div class="pn" id="p1" hidden><table class="nt" id="fn"></table></div>
<div class="pn" id="p2" hidden><div class="gr"><div><b id="pa">—</b><span>платили всего</span></div><div><b id="px">—</b><span>с доступом</span></div>
<div><b id="pr">—</b><span>платили 2+ раз</span></div><div><b id="pt">—</b><span>сегодня</span></div><div><b id="py">—</b><span>вчера</span></div>
<div><b id="pm">—</b><span>за 30 дней</span></div></div><div class="pq" id="pq"></div></div>
<div class="pn" id="p3" hidden><div class="gr"><div><b id="on">—</b><span>в сети</span></div><div><b id="ad">—</b><span>за день</span></div>
<div><b id="tr">—</b><span>трафик</span></div><div><b id="x">—</b><span>с доступом</span></div>
<div><b id="a">—</b><span>всего</span></div><div id="kk"><b id="k">—</b><span>обращения</span></div></div></div>
<div class="f"><span class="t" id="u"></span><button id="r" class="rf" aria-label="Обновить">↻</button></div>""",
    """let tab=0,shown=0;const M={order:['Карта/СБП','#3ccf74'],sbp:['СБП','#3ccf74'],card:['Карта','#8c7bff'],crypto:['Крипта','#26a17b'],stars:['Звёзды','#ffb800'],ton:['Gram','#2ea6ff']};
function n(v){return String(v).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')}
function gb(b){const u=['Б','КБ','МБ','ГБ','ТБ'];let i=0;while(b>=1024&&i<4){b/=1024;i++}return (i>2?b.toFixed(1):Math.round(b)).toString().replace('.',',')+' '+u[i]}
function count(to){const e=$('v'),from=shown,t0=performance.now();shown=to;
(function f(t){const k=Math.min(1,(t-t0)/900);e.textContent=rub(Math.round(from+(to-from)*(1-Math.pow(1-k,3))));if(k<1)requestAnimationFrame(f)})(t0)}
function bars(id,d,money){const mx=Math.max(1,...d),now=new Date(Date.now()+108e5).getUTCHours();
$(id).innerHTML=d.map((v,i)=>'<i class="'+(i==now?'nw':i>now?'ft':'')+'" style="--d:'+i*15+'ms;height:'+(v?Math.max(6,v/mx*100):3)+'%" title="'+i+':00 — '+(money?rub(v):v)+'"></i>').join('')}
function show(t){tab=t;[0,1,2,3].forEach(i=>{$('t'+i).className=i==t?'on':'';$('p'+i).hidden=i!=t});draw()}
function draw(){if(!s)return;if(s.v!=shown)count(s.v);
const dl=$('dl');if(s.y>0){const p=Math.round((s.v-s.y)/s.y*100);dl.textContent=(p>=0?'▲ ':'▼ ')+Math.abs(p)+'% к вчера';dl.className='dl '+(p>=0?'up':'dn')}
else{dl.textContent=s.v?'вчера 0 ₽':'';dl.className='dl'}
$('pc').textContent=s.p?s.p+' '+pl(s.p,'оплата','оплаты','оплат')+' · '+s.f+' '+pl(s.f,'первая','первые','первых')+' · чек '+rub(Math.round(s.v/s.p)):'Оплат пока нет';
if(tab==0){bars('ch',s.h,1);const m=Object.entries(s.m||{}),tot=m.reduce((a,e)=>a+e[1],0)||1,c=e=>(M[e[0]]||['','#8b95a5'])[1];
$('mx').innerHTML=m.map(e=>'<i style="flex:'+e[1]+';background:'+c(e)+'"></i>').join('');
$('lg').innerHTML=m.map(e=>'<span><b style="background:'+c(e)+'"></b>'+(M[e[0]]||[e[0]])[0]+' '+Math.round(e[1]/tot*100)+'%</span>').join('')}
if(tab==1&&s.c){const L=['Пришли','по ссылке','по рекламе','взяли подарок','устройство','подключились','оплатили','блок бота','₽ с них'];
$('fn').innerHTML='<tr><td></td><th>сегодня</th><th>вчера к '+hm(s.t)+'</th><th>вчера</th></tr>'+L.map((l,i)=>'<tr class="r'+i+'"><td>'+l+'</td>'
+s.c.map(k=>'<td>'+(i>7?rub(k[8]):k[i])+(i&&i<8&&k[0]?'<em>'+Math.round(k[i]/k[0]*100)+'%</em>':'')+'</td>').join('')+'</tr>').join('')}
if(s.P){const P=s.P;'axrtym'.split('').forEach(k=>$('p'+k).textContent=n(P[k]));
$('pq').textContent=(s.a?Math.round(P.a/s.a*100):0)+'% пользователей платили · '+(P.a?Math.round(P.r/P.a*100):0)+'% из них повторно · '
+rub(P.m?Math.round(P.v/P.m):0)+' на платящего за 30 дней'}
$('on').textContent=n(s.on);$('ad').textContent=n(s.ad);$('tr').textContent=gb(s.tb);$('x').textContent=n(s.x);$('a').textContent=n(s.a);$('k').textContent=s.k;
$('kk').className=s.k?'al':'';
const ds=new Date(Date.now()+108e5);ds.setUTCHours(0,0,0,0);const nt=[];if(!s.an)nt.push('«в сети» — по последней сверке с панелью');
if(s.ts&&s.ts*1e3-(ds-108e5)>9e5)nt.push('трафик с '+hm(s.ts));$('p3').title=nt.join(' · ');
$('u').textContent='Обновлено в '+hm(s.t)}
[0,1,2,3].forEach(i=>$('t'+i).onclick=()=>{if(W.HapticFeedback)W.HapticFeedback.selectionChanged&&W.HapticFeedback.selectionChanged();show(i)});
draw();live('s',v=>{s=v;draw()});""",
    ".hc{border-radius:20px;padding:12px 14px;color:#fff;background:linear-gradient(160deg,#5fd38d 0%,#28a464 58%,#16804a 100%);"
    "animation:in .5s cubic-bezier(.2,.8,.2,1)}@keyframes in{from{transform:translateY(8px) scale(.97)}}"
    ".hd{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:.82em;font-weight:600}"
    ".dl{font-size:.9em;font-weight:700;padding:2px 8px;border-radius:99px;background:rgba(255,255,255,.22)}.dl:empty{display:none}"
    ".dl.dn{background:rgba(120,10,10,.35)}"
    ".em{font-size:2.2em;font-weight:800;margin-top:4px;line-height:1.05;font-variant-numeric:tabular-nums;letter-spacing:-.02em}"
    ".pc{font-size:.8em;opacity:.9;margin-top:2px}"
    ".sw{display:flex;gap:2px;margin:10px 0 8px;padding:3px;border-radius:99px;background:var(--tg-theme-secondary-bg-color)}"
    ".sw button{flex:1;padding:5px 0;font-size:.8em;font-weight:600;border-radius:99px;background:none;color:var(--tg-theme-text-color)}"
    ".sw .on{background:#28a464;color:#fff}"
    ".pn{min-height:118px;animation:pf .3s ease}@keyframes pf{from{transform:translateY(4px)}}"
    ".ch{display:flex;align-items:flex-end;gap:2px;height:62px}.ch i{flex:1;border-radius:3px 3px 1px 1px;background:#28a464;opacity:.6;"
    "transform-origin:bottom;animation:gr .45s var(--d) cubic-bezier(.2,.8,.2,1) both}.ch .nw{opacity:1;box-shadow:0 0 8px rgba(60,207,116,.8)}"
    ".ch .ft{opacity:.15}@keyframes gr{from{transform:scaleY(0)}}"
    ".ax{display:flex;justify-content:space-between;font-size:.66em;color:var(--tg-theme-hint-color);margin-top:3px}"
    ".mx{display:flex;height:8px;border-radius:99px;overflow:hidden;margin-top:10px;gap:2px}"
    ".lg{display:flex;flex-wrap:wrap;gap:2px 10px;font-size:.75em;margin-top:5px}"
    ".lg b{display:inline-block;width:7px;height:7px;border-radius:99px;margin-right:4px}"
    ".gr{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}"
    ".gr div{background:var(--tg-theme-secondary-bg-color);border-radius:12px;padding:9px 4px;text-align:center;min-width:0}"
    ".gr b{display:block;font-size:1.05em;font-variant-numeric:tabular-nums;white-space:nowrap}"
    ".gr span{display:block;font-size:.66em;color:var(--tg-theme-hint-color);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    ".nt{width:100%;border-collapse:collapse;font-size:.74em;font-variant-numeric:tabular-nums}"
    ".nt td,.nt th{padding:1px 3px;text-align:right;white-space:nowrap}.nt th{font-weight:600;font-size:.9em}"
    ".nt th,.nt td:first-child{color:var(--tg-theme-hint-color)}.nt td:first-child{text-align:left}"
    ".nt em{font-style:normal;font-size:.82em;color:#28a464;margin-left:3px}.nt .r0,.nt .r5,.nt .r6{font-weight:700}"
    ".nt .r0 td,.nt .r5 td,.nt .r6 td{color:var(--tg-theme-text-color)}.nt .r1 td:first-child,.nt .r2 td:first-child{padding-left:10px}"
    ".pq{font-size:.72em;color:var(--tg-theme-hint-color);margin-top:6px}.gr .al{background:rgba(236,57,66,.16)}.gr .al b{color:var(--tg-theme-destructive-text-color)}"
    ".f{margin-top:6px}.rf{width:30px;height:30px;padding:0;border-radius:99px}",
)


TON_PAY_HTML = _page(
    """<div class="cd" id="cd"><div class="rb" id="rb">к оплате</div>
<svg width="52" height="52" viewBox="0 0 100 100"><path fill="#fff" d="M66.523 11.333H33.477c-4.401 0-6.601 0-8.592.616a13.792 13.792 0 0 0-4.808 2.625c-1.594 1.341-2.784 3.192-5.164 6.894L4.408 37.81c-1.572 2.446-2.358 3.67-2.572 4.956a6.322 6.322 0 0 0 .362 3.37c.482 1.212 1.51 2.24 3.567 4.296l39.033 39.034c1.821 1.82 2.731 2.731 3.781 3.072.924.3 1.918.3 2.842 0 1.05-.34 1.96-1.251 3.78-3.072l39.035-39.034c2.056-2.056 3.084-3.084 3.566-4.296a6.32 6.32 0 0 0 .362-3.37c-.214-1.287-1-2.51-2.572-4.956L85.087 21.47c-2.38-3.703-3.57-5.554-5.164-6.895a13.792 13.792 0 0 0-4.808-2.625c-1.99-.616-4.191-.616-8.592-.616z"/><path class="st" d="M60.268 24.224c.537-1.45 2.59-1.45 3.126 0l3.71 10.027a2.2 2.2 0 0 0 1.3 1.3l10.027 3.71c1.451.537 1.451 2.59 0 3.126l-10.027 3.71a2.2 2.2 0 0 0-1.3 1.3l-3.71 10.027c-.537 1.451-2.59 1.451-3.126 0l-3.71-10.027a2.2 2.2 0 0 0-1.3-1.3l-10.027-3.71c-1.451-.537-1.451-2.589 0-3.126l10.027-3.71a2.2 2.2 0 0 0 1.3-1.3l3.71-10.027z"/></svg>
<div class="am" id="am"></div><div class="sb" id="sb"></div>
<div class="mn">Лягушка&nbsp;VPN</div><div class="mn ad" id="ad">__ADDR__</div></div>
<button id="pay" class="pb">Оплатить</button><button id="ed" class="lk">Изменить сумму</button>
<div class="t" id="u" style="margin-top:8px;text-align:center"></div>""",
    """let ord=s&&s.w,poll=0,was=s&&s.ok;const A=$('ad').textContent,R=requestAnimationFrame;
function tn(n){return (n/1e9).toFixed(9).replace(/\\.?0+$/,'').replace('.',',')}
function msg(t){$('u').textContent=t}
$('ad').innerHTML=A.match(/.{1,4}/g).map((g,i)=>g+(i%6==5?'<br>':' ')).join('');
$('ad').onclick=()=>{if(W.copyText){W.copyText(A);msg('Адрес скопирован')}};
function draw(){if(!s)return;
if(s.ok){const c=s.ok.c,t0=performance.now(),go=!was;was=1;$('cd').className='cd dn'+(go?' go':'');$('rb').textContent='зачислено';
(function f(){const k=go?Math.min(1,(performance.now()-t0)/800):1;$('am').textContent='+'+rub(Math.round(c*(1-(1-k)**3)));if(k<1)R(f)})();
$('sb').textContent='Баланс: '+rub(s.ok.b);$('pay').hidden=true;$('ed').hidden=true;msg('Счёт '+s.ok.o+' оплачен');stop();
if(go){if(W.HapticFeedback)W.HapticFeedback.notificationOccurred('success');boom()}return}
$('am').textContent=tn(s.n)+' Gram';
$('sb').textContent='≈ '+rub(s.c)+' на баланс'+(s.d>0?' · '+s.d+' '+pl(s.d,'день','дня','дней')+' VPN':'');
$('pay').textContent='Оплатить '+tn(s.n)+' Gram';$('ed').hidden=!!ord;if(ord){$('rb').textContent='ждём';$('cd').className='cd wt'}}
function boom(){const e=document.createElement('canvas'),x=e.getContext('2d'),w=e.width=innerWidth,h=e.height=innerHeight,P=[];let t=0;
e.style.cssText='position:fixed;inset:0;pointer-events:none';document.body.appendChild(e);
for(let i=0;i<70;i++)P.push([w/2,h*.35,Math.random()*9-4.5,-Math.random()*7-2,['#5ad48f','#fff','#30a1f5','#ffd84d'][i%4]]);
(function f(){x.clearRect(0,0,w,h);for(const p of P){p[0]+=p[2];p[1]+=p[3];p[3]+=.22;x.fillStyle=p[4];x.fillRect(p[0],p[1],5,6)}if(++t<100)R(f);else e.remove()})()}
function stop(){if(poll)clearInterval(poll);poll=0}
function check(){msg('Ищем перевод в блокчейне, обычно 5–15 секунд…');$('rb').textContent='ждём';if(!(s&&s.ok))$('cd').className='cd wt';$('pay').disabled=true;$('ed').hidden=true;if(poll)return;
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
    "[hidden]{display:none!important}"
    ".cd{position:relative;z-index:0;overflow:hidden;border-radius:18px;padding:16px 16px 14px;color:#fff;text-align:center;"
    "background:linear-gradient(160deg,#5fb4ff 0%,#2f86f0 55%,#1d63d6 100%)}"
    ".cd:before,.cd:after{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none}"
    ".cd:before{background:linear-gradient(160deg,#5ad48f 0%,#27a865 60%,#17864d 100%);opacity:0;transition:opacity .6s}.dn:before{opacity:1}"
    ".wt:after{background:linear-gradient(100deg,transparent 35%,rgba(255,255,255,.3),transparent 65%);animation:sh 1.5s infinite}"
    "@keyframes sh{0%{transform:translateX(-100%)}to{transform:translateX(100%)}}"
    ".go{animation:pp .8s ease-out}.go svg{animation:pp .8s .1s ease-out}"
    "@keyframes pp{30%{transform:scale(1.06);box-shadow:0 0 30px 6px rgba(70,220,130,.7)}}"
    ".st{fill:#30a1f5;transition:fill .6s}.dn .st{fill:#27a865}"
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


async def note_traffic_baseline() -> None:
    """Remember the total device traffic once per Moscow day; the first call after midnight sets the baseline."""
    try:
        await db._pool_req().execute(
            """INSERT INTO traffic_days (day, start_bytes)
               SELECT (NOW() AT TIME ZONE 'Europe/Moscow')::date, COALESCE(SUM(lifetime_traffic_bytes), 0)::bigint
               FROM devices ON CONFLICT (day) DO NOTHING""")
    except Exception:
        logger.debug("Отметка трафика за день не записана", exc_info=True)


async def panel_online_now() -> int | None:
    """Users connected right now, from the Remnawave system stats; None when the panel doesn't say."""
    from app import runtime
    if runtime.rw is None:
        return None
    try:
        data = await asyncio.wait_for(runtime.rw.safe_get("/system/stats"), timeout=4)
        value = ((data or {}).get("onlineStats") or {}).get("onlineNow")
        return int(value) if value is not None else None
    except Exception:
        logger.debug("Онлайн из панели не получен", exc_info=True)
        return None


async def stats_state() -> dict[str, Any]:
    """Today in Moscow time for the admin widget; cheap enough to run every 30 seconds.

    v/y — rubles credited today and yesterday by this time, p/f — payments and first payments,
    m — rubles by provider, h — rubles per hour. c — newcomers (first contact with the bot) for today,
    yesterday by this time and all of yesterday: [came, by invitation, by ad link, took the gift,
    added a device, connected, paid, blocked the bot, rubles they paid]; conversions are as of now.
    P — paying users: a ever paid, x paid and have access, r paid twice or more, t/y/m paid today,
    yesterday and in 30 days, v rubles in 30 days. o — online in the last hour,
    x — with access (balance and a device), a — all users, k — open support tickets,
    on — connected right now (an=1 when the panel said so, else seen in the last 15 minutes),
    ad — people online at some point today, tb — traffic today in bytes, counted since ts."""
    pool = db._pool_req()
    day = _DAY_START
    row = dict(await pool.fetchrow(
        f"""
        SELECT
            (SELECT COUNT(*)::int FROM users) AS a,
            (SELECT COUNT(DISTINCT telegram_id)::int FROM devices WHERE last_online_at >= NOW() - INTERVAL '15 minutes') AS o,
            (SELECT COUNT(DISTINCT telegram_id)::int FROM devices WHERE last_online_at >= {day}) AS ad,
            (SELECT COUNT(*)::int FROM users u WHERE COALESCE(u.balance_rub, 0) > 0
                AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)) AS x,
            (SELECT COUNT(*)::int FROM tickets WHERE status = 'open') AS k
        """
    ) or {})
    # Same cohort rules everywhere: a device counts even if it was deleted later, «paid» is any credited payment.
    cohorts = await pool.fetch(
        f"""
        WITH k(i, a, b) AS (VALUES (0, {day}, NOW()),
                                   (1, {day} - INTERVAL '1 day', NOW() - INTERVAL '1 day'),
                                   (2, {day} - INTERVAL '1 day', {day}))
        SELECT k.i, COUNT(u.telegram_id)::int AS n,
            COUNT(*) FILTER (WHERE u.referred_by IS NOT NULL)::int AS r,
            COUNT(*) FILTER (WHERE u.ad_link_id IS NOT NULL)::int AS l,
            COUNT(*) FILTER (WHERE u.trial_used)::int AS g,
            COUNT(*) FILTER (WHERE u.first_device_at IS NOT NULL
                OR EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id))::int AS d,
            COUNT(*) FILTER (WHERE u.first_online_at IS NOT NULL)::int AS c,
            COUNT(*) FILTER (WHERE u.has_paid_topup)::int AS p,
            COUNT(*) FILTER (WHERE u.bot_blocked_at IS NOT NULL)::int AS b,
            COALESCE((SELECT SUM(r.amount) FROM payment_receipts r JOIN users v ON v.telegram_id = r.telegram_id
                      WHERE v.created_at >= k.a AND v.created_at < k.b), 0)::int AS s
        FROM k LEFT JOIN users u ON u.created_at >= k.a AND u.created_at < k.b
        GROUP BY k.i, k.a, k.b ORDER BY k.i
        """
    )
    payers = dict(await pool.fetchrow(
        f"""
        SELECT
            (SELECT COUNT(*)::int FROM users WHERE has_paid_topup) AS a,
            (SELECT COUNT(*)::int FROM users u WHERE u.has_paid_topup AND COALESCE(u.balance_rub, 0) > 0
                AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)) AS x,
            (SELECT COUNT(*)::int FROM (SELECT 1 FROM payment_receipts GROUP BY telegram_id HAVING COUNT(*) > 1) z) AS r,
            COUNT(DISTINCT telegram_id) FILTER (WHERE created_at >= {day})::int AS t,
            COUNT(DISTINCT telegram_id) FILTER (WHERE created_at >= {day} - INTERVAL '1 day'
                AND created_at < {day})::int AS y,
            COUNT(DISTINCT telegram_id)::int AS m,
            COALESCE(SUM(amount), 0)::int AS v
        FROM payment_receipts WHERE created_at >= NOW() - INTERVAL '30 days'
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
        f"""SELECT COALESCE(o.method, split_part(r.payment_key, ':', 1)) AS m, SUM(r.amount)::int AS rub
            FROM payment_receipts r LEFT JOIN pay_orders o ON r.payment_key = 'order:' || o.order_id
            WHERE r.created_at >= {day} GROUP BY 1"""
    )
    hours_rub = await pool.fetch(
        f"""SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'Europe/Moscow')::int AS h, SUM(amount)::int AS n
            FROM payment_receipts WHERE created_at >= {day} GROUP BY 1"""
    )

    await note_traffic_baseline()
    traffic = dict(await pool.fetchrow(
        """SELECT (SELECT COALESCE(SUM(lifetime_traffic_bytes), 0)::bigint FROM devices) - t.start_bytes AS tb,
                  EXTRACT(EPOCH FROM t.taken_at)::bigint AS ts
           FROM traffic_days t WHERE t.day = (NOW() AT TIME ZONE 'Europe/Moscow')::date"""
    ) or {})
    online = await panel_online_now()

    def by_hour(rows) -> list[int]:
        out = [0] * 24
        for r in rows:
            if 0 <= int(r["h"]) < 24:
                out[int(r["h"])] = int(r["n"] or 0)
        return out

    state: dict[str, Any] = {k: int(pay.get(k) or 0) for k in ("v", "y", "p", "f")}
    state["m"] = {str(r["m"]): int(r["rub"] or 0) for r in methods if int(r["rub"] or 0)}
    state["h"] = by_hour(hours_rub)
    rows = {int(r["i"]): r for r in cohorts}
    state["c"] = [[int((rows.get(i) or {}).get(k) or 0) for k in "nrlgdcpbs"] for i in range(3)]
    state["P"] = {k: int(payers.get(k) or 0) for k in "axrtymv"}
    state.update({k: int(row.get(k) or 0) for k in ("x", "a", "k", "ad")})
    state["on"], state["an"] = (online, 1) if online is not None else (int(row.get("o") or 0), 0)
    state["tb"], state["ts"] = max(0, int(traffic.get("tb") or 0)), int(traffic.get("ts") or 0)
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
    if data == "F" or data[:2] in ("z:", "k:", "v:", "A:", "C:", "W:"):
        from app import widgets_more
        return await widgets_more.handle_query(bot, user_id, data)
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
