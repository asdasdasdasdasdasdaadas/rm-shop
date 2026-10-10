const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const shots=fs.mkdtempSync(path.join(os.tmpdir(),'beta-screens-'));
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const context=await browser.newContext({viewport:{width:390,height:844},colorScheme:'light',reducedMotion:'reduce'});
 await context.addInitScript(()=>{localStorage.setItem('way_lk_token','test');sessionStorage.setItem('way_intro_v4','1');localStorage.setItem('way_home_coach_v2','1');});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const me={user:{name:'Александр',username:'alex'},balance_rub:360,topup_min:50,topup_max:10000,topup_step:50,balance_enabled:true,days_left:30,day_price_rub:6,vpn_day_price_rub:6,has_paid_topup:true,has_access:true,trial_available:false,promo_enabled:true,notification_settings_available:true,devices:[],legal:{offer:'#',privacy:'#'},invite_url:'https://t.me/test?start=ref_1',referral_program_enabled:true,referral_terms:{note:'50 ₽ за друга и 5% от пополнений'},topup_plans:[{code:'topup_300',title:'300 ₽',rub:300,amount:300}],trust:{enabled:false}};
 me.faq=[{q:'Как подключить VPN?',a:'Добавьте устройство в кабинете и откройте ссылку в приложении.'}];
 await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.host!=='cabinet.test')return route.fulfill({body:'',contentType:'application/javascript'});if(url.pathname.startsWith('/api/'))return route.fulfill({json:url.pathname==='/api/me'?me:{ok:true,items:[]}});const rel=url.pathname==='/'?'index.html':url.pathname.replace(/^\/(static\/)?/,'');const file=path.resolve(__dirname,'../../webapp',rel);return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});});

 await page.goto('http://cabinet.test/');await page.locator('#app:not(.hidden)').waitFor();

 for (const [system, controls] of [[47,56],[59,56],[0,0]]) {
  await page.evaluate(({system,controls})=>{
   tg.initData='telegram-test';tg.isFullscreen=system>0;
   tg.safeAreaInset={top:system,bottom:34};tg.contentSafeAreaInset={top:controls};applyViewport();
  },{system,controls});
  for(const action of ['openSettings()','openTopup()','openPayMethod({code:"topup_300",rub:300,amount:300})','startWizard({instant:true})','showDevice({id:1,title:"Мой iPhone",platform:"ios",active:true,subscription_url:"https://example.test/sub/test"})','openReferrals()','openPromo()','openFaq("home")','openSupport()','openHome()']) {
   await page.evaluate(action);
   const header=page.locator('.view:not(.hidden) .view-head');
   const top=await header.evaluate(el=>{
    const child=Array.from(el.children).find(n=>n.getClientRects().length);
    return child.getBoundingClientRect().top;
   });
   assert.ok(top>=system+controls,`${action}: ${top} overlaps ${system+controls}`);
   assert.ok(top<system+controls+65,`${action}: doubled inset ${top}`);
   if(action.startsWith('startWizard') && system===47) await page.screenshot({path:path.join(shots,'telegram-wizard.png')});
  }
  await page.evaluate(()=>{window.__me.trial_available=true;window.__me.trial_days=3;window.__me.trial_rub=18;openOffer({instant:true});});
  const offer=await page.locator('#view-offer .offer-stage').boundingBox();
  assert.ok(offer.y>=system+controls,'Gift overlaps native controls');
  await page.evaluate(()=>{window.__me.trial_available=false;});
 }
 await page.evaluate(()=>{tg.initData='';tg.isFullscreen=false;tg.safeAreaInset={top:0};tg.contentSafeAreaInset={top:0};applyViewport();openSettings();});
 assert.equal(await page.locator('#webBack').isVisible(),true);
 const title=await page.locator('#view-settings h1').boundingBox();
 assert.ok(title.y<100,'Browser header has unnecessary Telegram spacing');
 assert.deepEqual(errors,[]);
 console.log('Telegram safe insets, changing viewport and browser layout passed. '+shots);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
