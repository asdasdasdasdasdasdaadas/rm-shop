const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../admin/app.js'),'utf8');
test('funnel drill-down uses server cohort boundaries and selected card',async()=>{
  let requested;
  const nodes={funnelClientRows:{appendChild(){}},funnelClientHint:{},funnelCardMain:{}};
  const ctx=vm.createContext({$:id=>nodes[id],funnelStep:'repeat_paid',funnelSelectionCard:'leak',
    packFor:card=>{assert.equal(card,'leak');return {from:'2026-09-01T12:00:00+00:00',to:'2026-09-21T12:00:00+00:00'};},
    FUNNEL_MAIN:[],FUNNEL_SOURCE:[],FUNNEL_LEAK:[],FUNNEL_INV:[],emptyRow(){},
    queryString:v=>new URLSearchParams(v).toString(),api:async url=>{requested=new URL(url,'https://example.com');return {items:[]};}});
  vm.runInContext(source.slice(source.indexOf('async function loadFunnelClients'),source.indexOf('function paidLine')),ctx);
  await ctx.loadFunnelClients();
  assert.equal(requested.searchParams.get('funnel_step'),'repeat_paid');
  assert.equal(requested.searchParams.get('funnel_from'),'2026-09-01T12:00:00+00:00');
  assert.equal(requested.searchParams.has('paid'),false);
});
test('payment details show Stars without treating them as rubles',()=>{
  const ctx=vm.createContext({});
  vm.runInContext(source.slice(source.indexOf('function paidLine'),source.indexOf('function paintModalPaid')),ctx);
  assert.equal(ctx.paidLine({stars_payment_count:2,paid_stars_amount:200}),'200 Stars · 2 платеж(ей)');
  assert.match(ctx.paidLine({paid_topup_count:1,paid_topup_rub:100,stars_payment_count:1,paid_stars_amount:50}),/100 ₽.*50 Stars/);
});
