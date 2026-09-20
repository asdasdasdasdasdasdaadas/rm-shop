const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname,'../admin/app.js'),'utf8');
const handler = source.slice(source.indexOf('if ($("refModeSave"))'),source.indexOf('async function saveShopSettings'));
test('referral save uses only own controls and shows success/failure',async () => {
  const elements = Object.fromEntries(['refModeSave','refModeOut','setRefProgramOn','setRefModePayout','setRefInviteeRub','setRefPayoutMin','setRefDays','setRefInvitee'].map(id=>[id,{value:'',checked:false}]));
  elements.setRefProgramOn.checked=true;
  elements.setRefInviteeRub.value='30';
  let calls=0;
  const context = { $:id=>{assert.ok(elements[id],id);return elements[id]}, toast:()=>{}, api:async (path,opts)=> {
    calls++;
    assert.equal(path,'/admin/api/settings/referrals');
    assert.equal(JSON.parse(opts.body).referral_program_enabled,true);
    return {values:{referral_program_enabled:true}};
  }};
  vm.runInNewContext(handler,context);
  await elements.refModeSave.onclick();
  assert.equal(calls,1);
  assert.match(elements.refModeOut.textContent,/начисления включены/);
  assert.equal(elements.refModeSave.disabled,false);
  context.api=async()=>{throw Error('Ошибка сервера')};
  await elements.refModeSave.onclick();
  assert.equal(elements.refModeOut.textContent,'Ошибка сервера');
  assert.equal(elements.refModeSave.disabled,false);
});
