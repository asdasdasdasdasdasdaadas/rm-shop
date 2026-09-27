const test=require('node:test'), assert=require('node:assert/strict'), vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../webapp/app.js'),'utf8');
test('onboarding telemetry deduplicates per account and retries failures without blocking navigation', async()=>{
  const calls=[];
  let fail=true;
  const ctx=vm.createContext({Set,window:{__me:{user:{id:1}}},api:async(p,o)=>{calls.push(JSON.parse(o.body).stage); if(fail) throw Error('offline');}});
  vm.runInContext(source.slice(source.indexOf('const onboardingEventsSent'),source.indexOf('function openOffer(opts)')),ctx);
  ctx.trackOnboarding('gift_view');ctx.trackOnboarding('gift_view');
  await new Promise(setImmediate);
  assert.equal(calls.length,1);
  fail=false;ctx.trackOnboarding('gift_view');await new Promise(setImmediate);
  ctx.trackOnboarding('gift_view');assert.equal(calls.length,2);
  ctx.window.__me.user.id=2;ctx.trackOnboarding('gift_view');await new Promise(setImmediate);
  assert.equal(calls.length,3);
});
