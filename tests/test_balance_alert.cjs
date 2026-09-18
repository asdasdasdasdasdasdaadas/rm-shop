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
      textContent: '', addEventListener() {}, showModal() {this.open = true;}, close() {this.open = false;}});
    return elements.get(id);
  };
  const saved = new Map();
  const ctx = vm.createContext({window: {}, screen: 'home', $: el, Date, Set,
    document: {body: {style: {}}, activeElement: null, querySelector: () => null},
    localStorage: {getItem: (k) => saved.get(k), setItem: (k, v) => saved.set(k, v)},
    hideCoach() {}, openTopup() {ctx.screen = 'topup';},
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
    [{}, 'low'], [{hours_left: 25}, ''], [{hours_left: 0, balance_rub: 0}, 'empty'],
    [{hours_left: 8, balance_rub: 0}, 'low'], [{hours_left: 0, balance_rub: -6}, 'empty'],
    [{billing_paused: true, hours_left: 0}, ''], [{balance_enabled: false}, ''],
    [{devices: [{kind: 'router'}], hours_left: 0}, ''],
    [{devices: [], balance_rub: 0, trial_available: true}, ''],
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
  assert.equal(ctx.screen, 'topup');
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
