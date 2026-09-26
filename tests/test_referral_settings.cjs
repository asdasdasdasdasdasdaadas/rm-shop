const test=require('node:test'),assert=require('node:assert/strict');
const modulePromise=import('../admin-ui/src/lib/contracts.mjs');
test('referral settings use isolated endpoint and preserve unrelated settings',async()=>{
 const {saveSettingsPatchWith}=await modulePromise;const calls=[];
 const result=await saveSettingsPatchWith(async(path,body)=>{calls.push({path,body});if(path==='settings')return {balance_enabled:true,values:{brand_name:'VPN',referral_program_enabled:false,referral_mode:'classic',referral_payout_min:2000}};assert.equal(path,'settings/referrals');assert.equal(body.brand_name,undefined);return {values:{...body,referral_reward_rub:50}}},{referral_program_enabled:true});
 assert.equal(calls.length,2);assert.equal(result.values.brand_name,'VPN');assert.equal(result.values.referral_program_enabled,true);
});
test('settings save merges only edited fields into fresh server snapshot',async()=>{
 const {saveSettingsPatchWith}=await modulePromise;
 const result=await saveSettingsPatchWith(async(path,body)=>body?{values:body}:{values:{brand_name:'Old',router_rub:590,promo_enabled:false}},{brand_name:'New'});
 assert.equal(result.values.router_rub,590);assert.equal(result.values.brand_name,'New');assert.equal(result.values.promo_enabled,true);
});
test('failed settings save is propagated, never reported as success',async()=>{
 const {saveSettingsPatchWith}=await modulePromise;
 await assert.rejects(()=>saveSettingsPatchWith(async(path,body)=>{if(body)throw Error('Ошибка сервера');return {values:{referral_program_enabled:false,referral_mode:'classic'}}},{referral_program_enabled:true}),/Ошибка сервера/);
});
