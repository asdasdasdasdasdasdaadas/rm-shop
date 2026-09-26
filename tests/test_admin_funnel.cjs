const test=require('node:test'),assert=require('node:assert/strict');
const modulePromise=import('../admin-ui/src/lib/contracts.mjs');
test('funnel drill-down preserves server cohort boundaries without broad paid filter',async()=>{
 const {funnelRoute}=await modulePromise;
 const route=new URL(funnelRoute('repeat_paid',{from:'2026-09-01T12:00:00+00:00',to:'2026-09-21T12:00:00+00:00'}),'https://example.com');
 assert.equal(route.searchParams.get('funnel_step'),'repeat_paid');
 assert.equal(route.searchParams.get('funnel_from'),'2026-09-01T12:00:00+00:00');
 assert.equal(route.searchParams.get('funnel_to'),'2026-09-21T12:00:00+00:00');
 assert.equal(route.searchParams.has('paid'),false);
});
test('payment details keep Stars distinct from rubles',async()=>{
 const {paymentSummary}=await modulePromise;
 assert.equal(paymentSummary({stars_payment_count:2,paid_stars_amount:200}),'200 Stars · 2 платежа');
 assert.match(paymentSummary({paid_topup_count:1,paid_topup_rub:100,stars_payment_count:1,paid_stars_amount:50}),/100 ₽.*50 Stars/);
});
