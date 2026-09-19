const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../webapp/app.js'), 'utf8');
// Exercise the shipped alert controller with a minimal DOM and no Telegram/network.
function setup() {
  const elements = new Map();
  const el = (id) => {
    if (!elements.has(id)) elements.set(id, {dataset: {}, style: {}, open: false,
      textContent: '', children: [], classList: {toggle() {}}, setAttribute() {},
      replaceChildren() {this.children = [];}, append(...items) {this.children.push(...items);},
      focus() {}, select() {}, addEventListener() {}, showModal() {this.open = true;}, close() {this.open = false;}});
    return elements.get(id);
  };
  const saved = new Map();
  const ctx = vm.createContext({window: {}, screen: 'home', $: el, Date, Set,
    document: {body: {style: {}}, activeElement: null, querySelector: () => null, createElement: () => el(Symbol())},
    localStorage: {getItem: (k) => saved.get(k), setItem: (k, v) => saved.set(k, v)},
    hideCoach() {}, openTopup() {ctx.screen = 'topup';},
    daysLabel: n => `${n} дней`, topupCustomRub: 0,
    currentTopupPlan: () => ({topup_rub: ctx.topupCustomRub}),
    openPayMethod(plan) {ctx.screen = 'pay'; ctx.plan = plan;},
  });
  vm.runInContext(source.slice(source.indexOf('function remainHours('), source.indexOf('function remainLabel(')), ctx);
  vm.runInContext(source.slice(source.indexOf('function balanceAlertState('), source.indexOf('let lowBalanceTouch')), ctx);
  return {ctx, el};
}
const base = {balance_enabled: true, balance_rub: 6, vpn_day_price_rub: 6,
  hours_left: 24, devices: [{kind: ''}], user: {id: 123}};
test('thresholds, prepaid time, trial, routers and paused billing', () => {
  const {ctx} = setup();
  for (const [fields, expected] of [
    [{}, 'low'], [{hours_left: 25, balance_rub: 100}, ''], [{hours_left: 0, balance_rub: 0}, 'empty'],
    [{hours_left: 8, balance_rub: 0}, 'empty'], [{hours_left: 0, balance_rub: -6}, 'empty'],
    [{billing_paused: true, hours_left: 0}, ''], [{balance_enabled: false}, ''],
    [{devices: [{kind: 'router'}], hours_left: 0}, ''],
    [{devices: [], balance_rub: 0, trial_available: true}, 'empty'],
    [{devices: [], balance_rub: 0, trial_available: false}, 'empty'],
  ]) assert.equal(ctx.balanceAlertState({...base, ...fields}), expected);
});
test('low and empty have independent suppression; CTA opens topup', () => {
  const {ctx, el} = setup();
  ctx.window.__me = {...base};
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').dataset.state, 'low');
  el('lowBalanceLater').onclick();
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open, false);
  ctx.window.__me = {...base, hours_left: 0, balance_rub: 0};
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open, true);
  assert.equal(el('lowBalanceSheet').dataset.state, 'empty');
  el('lowBalancePay').onclick();
  assert.equal(ctx.screen, 'pay');
  assert.equal(ctx.plan.topup_rub, 1000);
  assert.equal(el('lowBalanceSheet').open, false);
});
test('payment refresh closes alert and payment view is never interrupted', () => {
  const {ctx, el} = setup();
  ctx.window.__me = {...base};
  ctx.screen = 'pay';
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open, false);
  ctx.screen = 'home';
  ctx.maybeShowLowBalance();
  ctx.window.__me = {...base, hours_left: 240, balance_rub: 60};
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open, false);
});

test('preset limits and device consumption are taken from the account', () => {
  const {ctx, el} = setup();
  const me = {...base, topup_min:400, topup_max:800, balance_rub:-20,
    devices:[{kind:'',active:false,title:'<script>'},{kind:'',active:false},{kind:'router'}]};
  assert.deepEqual(Array.from(ctx.lowBalanceAmounts(me)),[500]);
  ctx.paintLowBalance(me,'empty');
  assert.match(el('lowBalanceRunway').textContent,/40 дней/);
  assert.equal(el('lowBalanceDevices').children.length,2);
  assert.equal(el('lowBalanceDevices').children[0].children[1].textContent,'<script>');
  assert.equal(el('lowBalanceTitle').textContent,'Устройства отключены');
  assert.deepEqual(Array.from(ctx.lowBalanceAmounts({...me,topup_min:2100,topup_max:2200})),[2100]);
});
test('changing amount changes payment, custom amount opens input', () => {
  const {ctx, el} = setup();
  ctx.window.__me = {...base};
  ctx.maybeShowLowBalance();
  el('lowBalanceAmounts').children[0].onclick();
  el('lowBalancePay').onclick();
  assert.equal(ctx.plan.topup_rub,300);
  el('lowBalanceCustom').onclick();
  assert.equal(ctx.screen,'topup');
});

test('new user with exhausted gift is warned in the device wizard', () => {
  const {ctx,el} = setup();
  ctx.screen='wizard';
  ctx.window.__me={...base,devices:[],balance_rub:0,trial_available:false};
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open,true);
});
test('fresh session shows zero balance despite previously dismissed alert', () => {
  const {ctx,el} = setup();
  ctx.localStorage.getItem=()=>String(Date.now());
  ctx.window.__me={...base,balance_rub:0};
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open,true);
});
test('initial unclaimed gift is preserved, admin debt interrupts it', () => {
  const {ctx,el} = setup();
  ctx.screen='offer';
  ctx.window.__me={...base,devices:[],balance_rub:0,trial_notice:{kind:'claim'}};
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open,false);
  ctx.window.__me.balance_rub=-1;
  ctx.maybeShowLowBalance();
  assert.equal(el('lowBalanceSheet').open,true);
});
test('balance refresh runs on visible onboarding but never during payment', async () => {
  const {ctx} = setup();
  ctx.window.__me={...base};ctx.firstRunBusy=false;ctx.document.visibilityState='visible';
  let loads=0;ctx.load=async()=>{loads++;};
  vm.runInContext(source.slice(source.indexOf('let balanceRefreshBusy'),source.indexOf('async function load()')),ctx);
  ctx.screen='wizard';await ctx.refreshVisibleBalance();assert.equal(loads,1);
  ctx.screen='pay';await ctx.refreshVisibleBalance();assert.equal(loads,1);
  ctx.screen='home';ctx.document.visibilityState='hidden';await ctx.refreshVisibleBalance();assert.equal(loads,1);
});

test('cabinet display checks balance synchronously without waiting for polling', () => {
  let checks=0;
  const node={classList:{contains:()=>false,add(){},remove(){}}};
  const ctx=vm.createContext({$:()=>node,hideIntro(){},hideDecoy(){},
    maybeShowLowBalance(){checks++;},scheduleCoach(){}});
  vm.runInContext(source.slice(source.indexOf('function showApp()'),source.indexOf('function introSeen()')),ctx);
  ctx.showApp();
  assert.equal(checks,1);
});
test('intro exit checks balance and low balance skips intro entirely', () => {
  let checks=0;
  const node={inert:false,classList:{contains:()=>false,add(){},remove(){}}};
  const ctx=vm.createContext({$:()=>node,window:{__me:{balance_rub:1}},screen:'home',
    introTimer:0,clearIntroTimers(){},markIntroSeen(){},maybeOpenFirstRun(){},
    hideIntro(){},scheduleCoach(){},reducedMotion:()=>true,
    setTimeout(fn){fn();return 1;},maybeShowLowBalance(){checks++;},
    introSeen:()=>false,balanceAlertState:()=> 'low'});
  vm.runInContext(source.slice(source.indexOf('function finishIntro()'),source.indexOf('function reducedMotion()')),ctx);
  vm.runInContext(source.slice(source.indexOf('function shouldShowIntro()'),source.indexOf('function showIntro(')),ctx);
  assert.equal(ctx.shouldShowIntro(),false);
  ctx.finishIntro();
  assert.equal(checks,1);
  assert.equal(node.inert,false);
});
