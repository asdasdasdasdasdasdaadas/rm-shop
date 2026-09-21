const test=require('node:test');const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../webapp/app.js'),'utf8');
function setup(api=async()=>({ok:true})){
 const nodes=new Map(),buttons=['expensive','not_working','not_needed','other'].map(reason=>({dataset:{exitReason:reason}}));
 let opened=0,support=0,calls=0;
 function $(id){if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',open:false,addEventListener(){},showModal(){this.open=true;opened++;},close(){this.open=false;}});return nodes.get(id);}
 const ctx=vm.createContext({$,window:{__me:{devices:[]}},document:{querySelectorAll:()=>buttons},api:async(...args)=>{calls++;return api(...args);},showToast(){},openSupport(){support++;},resizeSupportText(){}});
 vm.runInContext(source.slice(source.indexOf('let exitFeedbackToken'),source.indexOf('async function deleteDevice()')),ctx);
 return {ctx,$,buttons,get opened(){return opened;},get support(){return support;},get calls(){return calls;}};
}
test('survey only opens after last deletion and skip sends nothing',()=>{
 const s=setup();s.ctx.showExitFeedback(null);assert.equal(s.opened,0);
 s.ctx.window.__me.devices=[{id:1}];s.ctx.showExitFeedback('token');assert.equal(s.opened,0);
 s.ctx.window.__me.devices=[];s.ctx.showExitFeedback('token');assert.equal(s.opened,1);
 s.$('exitFeedbackSkip').onclick();assert.equal(s.calls,0);assert.equal(s.$('exitFeedbackSheet').open,false);
});
test('technical problem opens support and preserves an existing draft even on save failure',async()=>{
 const s=setup(async()=>{throw Error('offline');});s.$('supportText').value='Мой вопрос';
 s.ctx.showExitFeedback('token');await s.ctx.answerExitFeedback('not_working');
 assert.equal(s.support,1);assert.equal(s.$('supportText').value,'Мой вопрос');
 assert.equal(s.$('exitFeedbackSheet').open,false);
});
test('other answers save once and do not open support',async()=>{
 let resolve;const s=setup(()=>new Promise(r=>resolve=r));
 s.ctx.showExitFeedback('token');const pending=s.ctx.answerExitFeedback('expensive');
 await s.ctx.answerExitFeedback('other');assert.equal(s.calls,1);
 resolve({ok:true});await pending;assert.equal(s.support,0);assert.equal(s.$('exitFeedbackSheet').open,false);
 await s.ctx.answerExitFeedback('other');assert.equal(s.calls,1);
});
test('dismissal during a request does not navigate after completion',async()=>{
 let resolve;const s=setup(()=>new Promise(r=>resolve=r));
 s.ctx.showExitFeedback('token');const pending=s.ctx.answerExitFeedback('not_working');
 s.ctx.closeExitFeedback();resolve({ok:true});await pending;assert.equal(s.support,0);
});
test('failed optional answer remains skippable and can be retried',async()=>{
 let failed=true;const s=setup(async()=>{if(failed)throw Error('offline');return {ok:true};});
 s.ctx.showExitFeedback('token');await s.ctx.answerExitFeedback('other');
 assert.equal(s.$('exitFeedbackSheet').open,true);assert.match(s.$('exitFeedbackError').textContent,/повторить/);
 assert.equal(s.buttons.some(b=>b.disabled),false);
 failed=false;await s.ctx.answerExitFeedback('other');assert.equal(s.$('exitFeedbackSheet').open,false);
});
