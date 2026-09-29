const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
  const page=await browser.newPage();
  await page.setContent('<style>.hidden{display:none}</style><section id="notificationSettings"><p id="notificationSummary"></p><button id="notificationToggle"></button><p id="notificationResult"></p></section>');
  const src=fs.readFileSync(path.join(__dirname,'../../webapp/app.js'),'utf8');
  await page.addScriptTag({content:`
   const $=id=>document.getElementById(id);
   window.__me={notification_settings_available:false,quiet_notifications:false};
   window.calls=[];window.confirmed=false;window.asks=0;
   const tg={showConfirm:(text,done)=>{window.asks++;done(window.confirmed)}};
   const showErr=e=>{throw e};
   async function api(url,opts){const body=JSON.parse(opts.body);window.calls.push(body);return {quiet_notifications:body.quiet}}
   ${src.slice(src.indexOf('let notificationSaving = false;'),src.indexOf('function openSettings()'))}
   paintNotificationSettings();
  `});
  assert.equal(await page.locator('#notificationSettings').isVisible(),false);
  await page.evaluate(()=>{window.__me.notification_settings_available=true;paintNotificationSettings()});
  await page.getByRole('button',{name:'Отключить необязательные уведомления'}).click();
  assert.equal(await page.evaluate(()=>window.calls.length),0);
  await page.evaluate(()=>window.confirmed=true);
  await page.getByRole('button',{name:'Отключить необязательные уведомления'}).click();
  await page.getByRole('button',{name:'Включить все уведомления'}).click();
  assert.deepEqual(await page.evaluate(()=>window.calls),[{quiet:true,confirmed:true},{quiet:false,confirmed:false}]);
  assert.equal(await page.evaluate(()=>window.asks),2);
  console.log('Notification settings: paid gate, confirmation, cancellation and re-enable passed');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
