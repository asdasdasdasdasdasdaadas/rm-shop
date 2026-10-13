const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require('node:path').join(__dirname, '../webapp/app.js'), 'utf8');
for (const [ua, touch, platform] of [
 ['Mozilla Android 14', 5, 'android'], ['iPhone OS 18', 5, 'ios'],
 ['Macintosh', 5, 'ios'], ['Macintosh', 0, 'macos'],
 ['Windows NT 10', 0, 'windows'], ['Linux x86_64', 0, ''],
]) test(`detect ${ua}/${touch}`, () => {
 const ctx = vm.createContext({navigator:{userAgent:ua,maxTouchPoints:touch}});
 vm.runInContext(source.slice(source.indexOf('function currentDevicePlatform()'), source.indexOf('let wizardCreating')),ctx);
 assert.equal(ctx.currentDevicePlatform(),platform);
});
test('device creation is single flight and preserves success when refresh fails', async () => {
 let calls=0, rendered=0, finish;
 const ctx=vm.createContext({wiz:{title:'',platform:'android',client:'alternate',url:''},firstRunBusy:false,
 setMainBusy(){},defaultTitle:()=> 'Android',api:async()=>{calls++;await new Promise(r=>finish=r);return {subscription_url:'https://sub.test/new'};},
 load:async()=>{throw Error('offline');},renderWizard(){rendered++;},showErr(e){throw e;},armThanksOnClose(){}});
 vm.runInContext(source.slice(source.indexOf('let wizardCreating'),source.indexOf('function startWizard')),ctx);
 const pending=ctx.createWizardDevice();await ctx.createWizardDevice();assert.equal(calls,1);
 finish();await pending;assert.equal(rendered,1);assert.equal(ctx.wiz.url,'https://sub.test/new');
 assert.equal(ctx.wiz.client,'alternate');assert.equal(ctx.firstRunBusy,false);
 await ctx.createWizardDevice();assert.equal(calls,1);
});
test('gift is not reclaimed after successful claim and failed refresh',async()=>{
 let claims=0, opened=0;
 const ctx=vm.createContext({window:{__me:{trial_available:true,balance_enabled:true}},firstRunBusy:false,
 $:()=>({}),haptic(){},api:async()=>{claims++;},load:async()=>{throw Error('offline');},
 phoneDevices:()=>[],startWizard(){opened++;},showErr(e){throw e;},markOnboardDone(){},openHome(){}});
 vm.runInContext(source.slice(source.indexOf('async function startOfferTry()'),source.indexOf('async function payPlan')),ctx);
 await ctx.startOfferTry();await ctx.startOfferTry();assert.equal(claims,1);assert.equal(opened,2);
});
