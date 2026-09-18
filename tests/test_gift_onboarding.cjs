const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../webapp/app.js'), 'utf8');
function setup(me, storage = new Map()) {
  const calls = [];
  const button = {disabled: false};
  const ctx = vm.createContext({window: {__me: me}, localStorage: {
    getItem: key => storage.get(key), setItem: (key,value) => storage.set(key,value),
  }, $: () => button, haptic() {}, firstRunBusy: false,
  api: async () => calls.push('claim'), load: async () => calls.push('load'),
  startWizard: opts => calls.push(['wizard',opts.fromOffer]), openHome: () => calls.push('home'),
  showErr: e => {throw e;},
  ONBOARD_KEY:'onboard', OFFER_SKIP_KEY:'skip', COACH_KEY:'coach', WIZ_COACH_KEY:'wiz',
  });
  vm.runInContext(source.slice(source.indexOf('function onboardingStorageKey('), source.indexOf('function maybeOpenFirstRun(')),ctx);
  vm.runInContext(source.slice(source.indexOf('async function startOfferTry('),source.indexOf('async function payPlan(')),ctx);
  return {ctx,calls,button};
}
const newcomer = {user:{id:123}, balance_enabled:true, devices:[], trial_available:false,
  trial_notice:{kind:'granted', days:3}};
test('automatically credited gift is shown to a newcomer', () => {
  const {ctx} = setup(newcomer);
  assert.equal(ctx.shouldShowOffer(newcomer),true);
  assert.equal(ctx.shouldShowOffer({...newcomer,trial_notice:null}),false);
  for(const extra of [{devices:[{id:1}]},{first_online_at:'2026-09-18'},{has_paid_topup:true}])
    assert.equal(ctx.shouldShowOffer({...newcomer,...extra}),false);
});
test('accept gift opens device wizard without granting it again', async () => {
  const {ctx,calls,button} = setup(newcomer);
  await ctx.startOfferTry();
  assert.deepEqual(calls,[['wizard',true]]);
  assert.equal(button.disabled,false);
  assert.equal(ctx.firstRunBusy,false);
});
test('unclaimed trial is claimed before opening device wizard', async () => {
  const {ctx,calls} = setup({...newcomer,trial_available:true});
  await ctx.startOfferTry();
  assert.deepEqual(calls,['claim','load',['wizard',true]]);
});
test('onboarding completion is scoped to the Telegram account', () => {
  const {ctx} = setup(newcomer);
  ctx.markOnboardDone();
  assert.equal(ctx.shouldShowOffer(newcomer),false);
  const other = {...newcomer,user:{id:456}};
  ctx.window.__me = other;
  assert.equal(ctx.shouldShowOffer(other),true);
});
