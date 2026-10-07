const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../webapp/appearance.js'),'utf8');
function setup(saved,{blocked=false,dark=false,telegram=null}={}){
 const root={dataset:{theme:'pink'}},storage={way_appearance_v1:saved},callbacks={};
 const media={matches:dark,addEventListener:(name,fn)=>callbacks.media=fn};
 const win={matchMedia:()=>media,dispatchEvent(){},Telegram:telegram?{WebApp:telegram}:undefined};
 const ctx=vm.createContext({document:{documentElement:root,querySelectorAll:()=>[],getElementById:()=>null,addEventListener:(name,fn)=>callbacks[name]=fn},window:win,Event,localStorage:{getItem:key=>{if(blocked)throw Error('blocked');return storage[key]},setItem:(key,value)=>{if(blocked)throw Error('blocked');storage[key]=value}}});
 vm.runInContext(source,ctx);return{api:win.WayAppearance,root,storage,media,callbacks};
}
test('classic stays default and invalid settings fall back safely',()=>{for(const value of [null,'bad','{"design":"other","theme":"other"}']){const s=setup(value);assert.equal(s.root.dataset.design,'classic');assert.equal(s.root.dataset.colorScheme,'light');}});
test('modern preferences persist without overwriting classic color',()=>{const s=setup(null);s.api.choose('design','modern');s.api.choose('theme','dark');assert.equal(s.root.dataset.theme,'pink');const restored=setup(s.storage.way_appearance_v1);assert.equal(restored.root.dataset.design,'modern');assert.equal(restored.root.dataset.colorScheme,'dark');restored.api.choose('design','classic');assert.equal(restored.root.dataset.theme,'pink');});
test('storage denial still allows switching for the current session',()=>{const s=setup(null,{blocked:true});s.api.choose('design','modern');s.api.choose('theme','light');assert.equal(s.root.dataset.design,'modern');assert.equal(s.root.dataset.colorScheme,'light');});
test('system mode follows platform, explicit mode stays fixed',()=>{const s=setup(null);s.media.matches=true;s.callbacks.media();assert.equal(s.root.dataset.colorScheme,'dark');s.api.choose('theme','light');s.callbacks.media();assert.equal(s.root.dataset.colorScheme,'light');const telegram={initData:'signed',colorScheme:'dark'};const t=setup(null,{telegram});assert.equal(t.root.dataset.colorScheme,'dark');telegram.colorScheme='light';t.api.apply();assert.equal(t.root.dataset.colorScheme,'light');});
