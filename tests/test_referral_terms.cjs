const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../webapp/app.js'),'utf8');
test('cabinet replaces active referral promises with server pause terms',()=>{
 const nodes=new Map();
 const ctx=vm.createContext({$:id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',classList:{toggle(){}}});return nodes.get(id);},
 friendsWord:()=>'',daysWord:()=>'',paintRefFriends(){},paintPayout(){}});
 vm.runInContext(source.slice(source.indexOf('function paintReferrals('),source.indexOf('function paintRefFriends(')),ctx);
 ctx.paintReferrals({balance_enabled:true,referral_program_enabled:true,referral_terms:{note:'Активна',when:'50 ₽ и 5%',how:'Пример',friend:'Другу бонус'}});
 assert.equal(nodes.get('refFaqWhen').textContent,'50 ₽ и 5%');
 ctx.paintReferrals({balance_enabled:true,referral_program_enabled:false,referral_terms:{note:'Приостановлена',when:'Начислений нет',how:'Без выплат за паузу',friend:''}});
 assert.equal(nodes.get('refFaqWhen').textContent,'Начислений нет');
 assert.equal(nodes.get('refFaqHow').textContent,'Без выплат за паузу');
 assert.equal(nodes.get('refStatsNote').textContent,'Приостановлена');
});
