const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('webapp/app.js','utf8').split('let promoSubmitting = false;')[1].split('$("promoBtn").onclick')[0];
test('promo success shows credited balance even when refresh fails',async()=>{
 const elements={input:{value:' GIFT ',focus(){}},button:{textContent:'Применить'},result:{textContent:'',classList:{add(){},remove(){}}}};
 const ctx={$:id=>elements[id],haptic(){},api:async()=>({credited_rub:54,balance_rub:180}),load:async()=>{throw Error('network')},tg:{showAlert(){}},showErr(){}};
 vm.createContext(ctx);vm.runInContext('let promoSubmitting=false;'+source,ctx);
 await ctx.applyPromo('input','button','result');
 assert.match(elements.result.textContent,/Начислено 54 ₽. Баланс: 180 ₽/);
 assert.equal(elements.input.value,'');assert.equal(elements.button.disabled,false);
});
