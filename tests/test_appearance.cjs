const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../webapp/appearance.js'),'utf8');
function setup(saved,{blocked=false,dark=false,telegram=null,elements={}}={}){
 const root={dataset:{theme:'pink'}},storage={way_appearance_v1:saved},callbacks={};
 const media={matches:dark,addEventListener:(name,fn)=>callbacks.media=fn};
 const win={matchMedia:()=>media,dispatchEvent(){},Telegram:telegram?{WebApp:telegram}:undefined};
 const ctx=vm.createContext({document:{documentElement:root,querySelectorAll:()=>[],getElementById:id=>elements[id]||null,addEventListener:(name,fn)=>callbacks[name]=fn},window:win,Event,localStorage:{getItem:key=>{if(blocked)throw Error('blocked');return storage[key]},setItem:(key,value)=>{if(blocked)throw Error('blocked');storage[key]=value}}});
 vm.runInContext(source,ctx);return{api:win.WayAppearance,root,storage,media,callbacks};
}
test('classic stays default and invalid settings fall back safely',()=>{for(const value of [null,'bad','{"design":"other","theme":"other"}']){const s=setup(value);assert.equal(s.root.dataset.design,'classic');assert.equal(s.root.dataset.colorScheme,'light');}});
test('modern preferences persist without overwriting classic color',()=>{const s=setup(null);s.api.choose('design','modern');s.api.choose('theme','dark');assert.equal(s.root.dataset.theme,'pink');const restored=setup(s.storage.way_appearance_v1);assert.equal(restored.root.dataset.design,'modern');assert.equal(restored.root.dataset.colorScheme,'dark');restored.api.choose('design','classic');assert.equal(restored.root.dataset.theme,'pink');});
test('storage denial still allows switching for the current session',()=>{const s=setup(null,{blocked:true});s.api.choose('design','modern');s.api.choose('theme','light');assert.equal(s.root.dataset.design,'modern');assert.equal(s.root.dataset.colorScheme,'dark');});
test('system mode follows platform, explicit mode stays fixed',()=>{const s=setup(null);s.media.matches=true;s.callbacks.media();assert.equal(s.root.dataset.colorScheme,'dark');s.api.choose('theme','light');s.callbacks.media();assert.equal(s.root.dataset.colorScheme,'light');const telegram={initData:'signed',colorScheme:'dark'};const t=setup(null,{telegram});assert.equal(t.root.dataset.colorScheme,'dark');telegram.colorScheme='light';t.api.apply();assert.equal(t.root.dataset.colorScheme,'light');});

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

test('experiment pins the server variant, dark-only, and restores preference on stop',()=>{const s=setup(JSON.stringify({design:'modern',theme:'light'}));assert.equal(s.root.dataset.colorScheme,'dark');s.api.assign({active:true,id:'test',variant:'classic'});assert.equal(s.root.dataset.design,'classic');s.api.choose('design','modern');assert.equal(s.root.dataset.design,'classic');s.api.assign({active:true,id:'test',variant:'modern'});assert.equal(s.root.dataset.colorScheme,'dark');s.api.assign({active:false});assert.equal(s.root.dataset.design,'modern');});
