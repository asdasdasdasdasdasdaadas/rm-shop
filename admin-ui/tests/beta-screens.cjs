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
 await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.host!=='cabinet.test')return route.fulfill({body:'',contentType:'application/javascript'});if(url.pathname.startsWith('/api/'))return route.fulfill({json:url.pathname==='/api/me'?me:{ok:true,items:[]}});const rel=url.pathname==='/'?'index.html':url.pathname.replace(/^\/(static\/)?/,'');const file=path.resolve(__dirname,'../../webapp',rel);return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});});

 await page.goto('http://cabinet.test/');await page.locator('#app:not(.hidden)').waitFor();
 await page.evaluate(()=>{
  WayAppearance.choose('design','modern');
  Object.assign(window.__me,{hours_left:720,days_left:30,devices:[{id:1,title:'Мой iPhone',platform:'ios',active:true,subscription_url:'https://example.test/sub/long-personal-subscription-link'}],pay_methods:[{id:'sbp',title:'СБП'},{id:'card',title:'Банковская карта'}],faq:[{q:'Как подключить VPN?',a:'Добавьте устройство в кабинете и откройте ссылку в приложении.'}]});paint(window.__me);
 });
 async function shot(name){
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,name+' overflow');
  await page.screenshot({path:path.join(shots,name+'.png'),fullPage:true});
 }
 for(const theme of ['light','dark']) {
  await page.evaluate(theme=>WayAppearance.choose('theme',theme),theme);
  await page.evaluate(()=>openSettings());await shot(theme+'-settings');
  await page.evaluate(()=>openTopup());assert.equal(await page.locator('#topupGrid button').count(),4);await page.locator('#topupGrid button').first().click();assert.equal(await page.locator('#topupGrid button').first().getAttribute('aria-pressed'),'true');await shot(theme+'-topup');
  await page.evaluate(()=>openPayMethod({code:'topup_300',rub:300,amount:300}));await shot(theme+'-pay');
  await page.evaluate(()=>startWizard({instant:true}));await shot(theme+'-wizard-1');
  await page.locator('#appMainBtn').click();await shot(theme+'-wizard-2');
  await page.locator('#appMainBtn').click();await shot(theme+'-wizard-3');
  await page.evaluate(()=>{wiz.url='https://example.test/sub/test';wiz.title='Мой iPhone';renderWizard();});await shot(theme+'-wizard-ready');
  await page.evaluate(()=>showDevice(window.__me.devices[0]));await shot(theme+'-device');
  await page.evaluate(()=>openReferrals());await shot(theme+'-referrals');
  await page.evaluate(()=>openPromo());await shot(theme+'-promo');
  await page.evaluate(()=>openBilling());await page.locator('#billingSummary:not(.hidden)').waitFor();await shot(theme+'-billing-empty');
  await page.evaluate(()=>paintBilling({charged_rub:12,items:[{kind:'charge',amount:-6,created_at:'2026-10-08T10:00:00Z',title:'Списание за устройство'},{kind:'topup',amount:300,created_at:'2026-10-08T09:00:00Z',title:'Пополнение'}]}));await shot(theme+'-billing');
  await page.evaluate(()=>openFaq('home'));await page.locator('#faqList button').click();assert.equal(await page.locator('#faqList button').getAttribute('aria-expanded'),'true');await shot(theme+'-faq');
  await page.evaluate(()=>openSupport());await page.locator('#supportThread .support-empty').waitFor();await shot(theme+'-support-empty');
  await page.evaluate(()=>paintSupportThread({id:1,status:'open',messages:[{author:'user',body:'Не получается подключиться на iPhone.',created_at:'2026-10-08T09:00:00Z'},{author:'admin',body:'Здравствуйте! Поможем. Подскажите, какое приложение вы установили?',created_at:'2026-10-08T09:01:00Z'}]}));await shot(theme+'-support');
  await page.evaluate(()=>paintSupportThread({id:1,status:'closed',messages:[]}));await shot(theme+'-support-closed');
  await page.evaluate(()=>{stopSupportPoll();screen='ambassador';switchView('view-ambassador');setMain('');paintAmbassador({settings:{first_percent:100,first_cap:300,recurring_percent:5,payout_min:2000,hold_days:7,budget:50000,accruing:true,recruitment:true},member:null,wallet:{}});});await shot(theme+'-ambassador');
  await page.evaluate(()=>{window.__me.router={enabled:true,active:false,rub:500,days:30};openRouter();});await shot(theme+'-router');
  await page.evaluate(()=>{screen='article';switchView('view-article');setMain('');paintArticle({title:'Обновили кабинет',lead:'Подключайтесь и управляйте VPN в одном месте.',items:['Новый интерфейс','Быстрое подключение'],closing:'Спасибо, что вы с нами!'});});await shot(theme+'-article');
  await page.evaluate(()=>{window.__me.trial_available=true;window.__me.trial_days=3;window.__me.trial_rub=18;openOffer({instant:true});});await shot(theme+'-gift');
  await page.evaluate(()=>{window.__me.trial_available=false;openHome();paintLowBalance({...window.__me,balance_rub:0,hours_left:0},'empty');document.getElementById('lowBalanceSheet').showModal();});await shot(theme+'-low-balance');
  await page.evaluate(()=>document.getElementById('lowBalanceSheet').close());
 }
 await page.setViewportSize({width:320,height:740});await page.evaluate(()=>openPromo());await shot('small-promo');
 await page.evaluate(()=>showDevice(window.__me.devices[0]));await shot('small-device');
 await page.evaluate(()=>openSettings());await shot('small-settings');
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>openTopup());
 await page.evaluate(()=>{window.__me.topup_min=210;window.__me.topup_max=250;renderTopup(window.__me);});
 assert.equal(await page.locator('#topupGrid button').count(),1);assert.match(await page.locator('#topupGrid button').textContent(),/210/);
 await page.evaluate(()=>{window.__me.topup_min=50;window.__me.topup_max=10000;WayAppearance.choose('design','classic');renderTopup(window.__me);});
 assert.equal(await page.locator('#topupGrid button').count(),9);
 await page.evaluate(()=>{WayAppearance.choose('design','modern');renderTopup(window.__me);});
 const bar=await page.locator('#appMainBar').boundingBox();assert.ok(bar.width<=480);
 await shot('desktop-topup');
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>showLogin('Введите логин Telegram'));await shot('login');
 await page.evaluate(()=>showFail('Не удалось загрузить данные. Попробуйте ещё раз.'));await shot('error');assert.equal(await page.locator('#appMainBar').isVisible(),false);
 await page.evaluate(()=>showMaint('Скоро вернёмся. Обновляем сервис.'));await shot('maintenance');
 assert.deepEqual(errors,[]);console.log('Beta interior screens passed. '+shots);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
