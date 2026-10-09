const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../webapp/appearance.js'),'utf8');
function setup(saved,{blocked=false,dark=false,telegram=null,elements={}}={}){
 const root={dataset:{theme:'pink'}},storage={way_appearance_v1:saved},callbacks={};
 const media={matches:dark,addEventListener:(name,fn)=>callbacks.media=fn};
 const win={matchMedia:()=>media,dispatchEvent(){},Telegram:telegram?{WebApp:telegram}:undefined};
 const ctx=vm.createContext({document:{documentElement:root,querySelectorAll:()=>[],getElementById:id=>elements[id]||null,addEventListener:(name,fn)=>callbacks[name]=fn},window:win,Event,localStorage:{getItem:key=>{if(blocked)throw Error('blocked');return storage[key]},setItem:(key,value)=>{if(blocked)throw Error('blocked');storage[key]=value}}});
 vm.runInContext(source,ctx);return{api:win.WayAppearance,root,storage,media,callbacks};
}
test('dark modern is the only design, including saved classic and blocked storage',()=>{
 for(const saved of [null,'bad',JSON.stringify({design:'classic',theme:'light'}),JSON.stringify({design:'modern',theme:'system'})]){
  for(const blocked of [false,true]){const s=setup(saved,{blocked});assert.equal(s.root.dataset.design,'modern');assert.equal(s.root.dataset.colorScheme,'dark');assert.equal(s.root.dataset.theme,'black');s.api.choose('design','classic');s.api.choose('theme','light');s.api.assign({active:true,variant:'classic'});assert.equal(s.root.dataset.design,'modern');assert.equal(s.root.dataset.colorScheme,'dark');}
 }
});

test('overview respects gifts, exhausted access, prepaid time, paused billing and separate routers',()=>{
 const elements=Object.fromEntries(['modernRemaining','modernRemainingLabel','modernDeviceRate'].map(id=>[id,{textContent:'',dataset:{}}]));
 const {api}=setup(null,{elements});
 const base={balance_enabled:true,vpn_day_price_rub:6,devices:[{active:true,platform:'ios'}]};
 const value=()=>elements.modernRemaining.textContent,label=()=>elements.modernRemainingLabel.textContent;
 api.paintSummary({...base,devices:[],trial_available:true},{hours:0,empty:false});assert.equal(value(),'Начнём?');assert.match(label(),/подарок/);
 api.paintSummary({...base,balance_rub:0},{hours:12,empty:false});assert.equal(value(),'12');assert.match(label(),/часов/);
 api.paintSummary(base,{hours:0.5,empty:false});assert.equal(value(),'< 1');
 api.paintSummary(base,{hours:0,empty:false});assert.equal(value(),'0');
 api.paintSummary(base,{hours:48,empty:false});assert.equal(value(),'2');assert.match(label(),/дня/);
 api.paintSummary(base,{hours:0,empty:true});assert.equal(value(),'0');assert.match(label(),/Пополните/);
 api.paintSummary({...base,billing_paused:true},{hours:0,empty:false});assert.match(label(),/приостановлены/);
 api.paintSummary({...base,devices:[{platform:'router'}]},{hours:999,empty:false});assert.equal(value(),'Роутер');assert.match(label(),/роутера/);assert.match(elements.modernDeviceRate.textContent,/отдельно/);
 api.paintSummary({...base,devices:[{platform:'ios'},{kind:'router'}]},{hours:72,empty:false});assert.match(elements.modernDeviceRate.textContent,/6 ₽/);
 api.paintSummary({balance_enabled:false,has_access:false},{hours:0,empty:false});assert.equal(value(),'0');assert.match(label(),/Продлите/);
});
