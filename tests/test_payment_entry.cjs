const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../webapp/app.js'),'utf8');
test('reminder opens topup on initial authenticated load only',async()=>{
  let opened=0,painted=0,introSeen=0;
  const ctx=vm.createContext({window:{location:{search:'?screen=topup'}},tg:{initData:'signed'},lkToken:'',loadSeq:0,
    URLSearchParams,screen:'home',api:async()=>({balance_enabled:true}),paint(){painted++;},
    markIntroSeen(){introSeen++;},openTopup(){opened++;},showLogin(){throw Error('unexpected login');}});
  vm.runInContext(source.slice(source.indexOf('let paymentEntryHandled'),source.indexOf('function closeMenu()')),ctx);
  await ctx.load();
  assert.equal(opened,1);assert.equal(introSeen,1);assert.equal(ctx.screen,'topup');
  ctx.screen='home';await ctx.load();assert.equal(opened,1);assert.equal(painted,2);
});

for (const [entry,me,expected] of [
  ['gift',{trial_available:true,balance_enabled:true},'offer'],
  ['gift',{trial_available:false,balance_enabled:true,devices:[{id:7}]},'device'],
  ['connect',{balance_enabled:true,devices:[{id:7}]},'device'],
  ['connect',{balance_enabled:true,devices:[]},'wizard'],
]) test(`${entry} reminder opens ${expected} once`,async()=>{
  const opened=[];
  const ctx=vm.createContext({window:{location:{search:`?screen=${entry}`}},tg:{initData:'signed'},lkToken:'',loadSeq:0,
    URLSearchParams,screen:'home',api:async()=>me,paint(){},markIntroSeen(){},
    openOffer(){opened.push('offer');},showDevice(d){assert.equal(d.id,7);opened.push('device');},
    startWizard(){opened.push('wizard');},openHome(){opened.push('home');},showLogin(){throw Error('unexpected login');}});
  vm.runInContext(source.slice(source.indexOf('let paymentEntryHandled'),source.indexOf('function closeMenu()')),ctx);
  await ctx.load();
  assert.deepEqual(opened,[expected]);
  ctx.screen='home';await ctx.load();assert.deepEqual(opened,[expected]);
});
