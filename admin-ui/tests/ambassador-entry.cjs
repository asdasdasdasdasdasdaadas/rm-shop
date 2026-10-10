const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const shots=fs.mkdtempSync(path.join(os.tmpdir(),'neutral-beta-'));
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const context=await browser.newContext({viewport:{width:390,height:844},colorScheme:'light',reducedMotion:'reduce'});
 await context.addInitScript(()=>{localStorage.setItem('way_appearance_v1',JSON.stringify({design:'classic',theme:'light'}));localStorage.setItem('way_theme_v1','pink');localStorage.setItem('way_lk_token','test');sessionStorage.setItem('way_intro_v4','1');localStorage.setItem('way_home_coach_v2','1');});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const me={user:{name:'Александр',username:'alex'},balance_rub:360,topup_min:50,topup_max:10000,topup_step:50,balance_enabled:true,days_left:30,day_price_rub:6,vpn_day_price_rub:6,has_paid_topup:true,has_access:true,trial_available:false,promo_enabled:true,notification_settings_available:true,devices:[],legal:{offer:'#',privacy:'#'},invite_url:'https://t.me/test?start=ref_1',referral_program_enabled:true,referral_terms:{note:'50 ₽ за друга и 5% от пополнений'},topup_plans:[{code:'topup_300',title:'300 ₽',rub:300,amount:300}],trust:{enabled:false}};
 await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.host!=='cabinet.test')return route.fulfill({body:'',contentType:'application/javascript'});if(url.pathname.startsWith('/api/'))return route.fulfill({json:url.pathname==='/api/me'?me:{ok:true,items:[]}});const rel=url.pathname==='/'?'index.html':url.pathname.replace(/^\/(static\/)?/,'');const file=path.resolve(__dirname,'../../webapp',rel);return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});});
 me.ambassador={status:null,recruitment:true,accruing:true,invitation_available:true,first_percent:100,first_cap:500,recurring_percent:5,payout_min:2000};
 await page.route('**/api/ambassador',route=>route.fulfill({json:{ok:true,settings:{...me.ambassador,hold_days:14,budget:10000},member:null,wallet:{},capacity:{}}}));
 await page.goto('http://cabinet.test/');await page.locator('#app:not(.hidden)').waitFor();
 await page.evaluate(()=>openHome());
 assert.equal(await page.locator('#homeAmbassadorCard').isVisible(),true);
 assert.match(await page.locator('#homeAmbassadorNote').textContent(),/500 ₽/);
 assert.ok((await page.locator('#homeAmbassadorCard').boundingBox()).y>(await page.locator('#homePromoCard').boundingBox()).y);
 await page.locator('#homeAmbassadorOpen').click();await page.locator('#ambApplication').waitFor();
 for(const [status,label] of [['pending','Заявка на рассмотрении'],['approved','Ваше амбассадорство'],['suspended','Участие приостановлено']]) {
  await page.evaluate(status=>{window.__me.ambassador.status=status;paint(window.__me);openHome();},status);
  assert.equal(await page.locator('#homeAmbassadorTitle').textContent(),label);
 }
 await page.evaluate(()=>{Object.assign(window.__me.ambassador,{status:null,invitation_available:false,recruitment:false});paint(window.__me);});
 assert.match(await page.locator('#homeAmbassadorNote').textContent(),/Набор сейчас закрыт/);
 await page.setViewportSize({width:320,height:740});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.goto('http://cabinet.test/?screen=ambassador');await page.locator('#ambApplication').waitFor();
 assert.equal(await page.locator('#view-ambassador').isVisible(),true);
 assert.deepEqual(errors,[]);console.log('Ambassador home card, membership states, closed recruitment and direct entry passed. '+shots);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
