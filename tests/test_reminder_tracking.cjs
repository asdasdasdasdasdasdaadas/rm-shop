const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../webapp/app.js'),'utf8');
test('opening token is sent only once per authenticated cabinet entry, not on polling',async()=>{
 const requests=[];
 const ctx=vm.createContext({tg:{initData:'signed'},lkToken:'',window:{location:{search:'?screen=topup&nt=token'}},URLSearchParams,FormData,
 fetch:async(path,opts)=>{requests.push({path,opts});return {ok:true,json:async()=>({ok:true})};}});
 vm.runInContext(source.slice(source.indexOf('let reminderEntryTracked'),source.indexOf('let thanksArmed')),ctx);
 await ctx.api('/api/me');await ctx.api('/api/me');await ctx.api('/api/devices');
 assert.equal(requests[0].opts.headers['X-Reminder-Token'],'token');
 assert.equal(requests[0].opts.headers['X-Init-Data'],'signed');
 assert.equal(requests[1].opts.headers['X-Reminder-Token'],undefined);
 assert.equal(requests[2].opts.headers['X-Reminder-Token'],undefined);
});
test('blocked entry does not consume a future valid opening',async()=>{
 let blocked=true;const headers=[];
 const ctx=vm.createContext({tg:{initData:'signed'},lkToken:'',window:{location:{search:'?nt=token'}},URLSearchParams,FormData,
 fetch:async(path,opts)=>{headers.push(opts.headers);return {ok:true,json:async()=>({ok:true,blocked})};}});
 vm.runInContext(source.slice(source.indexOf('let reminderEntryTracked'),source.indexOf('let thanksArmed')),ctx);
 await ctx.api('/api/me');blocked=false;await ctx.api('/api/me');
 assert.equal(headers[1]['X-Reminder-Token'],'token');
});
