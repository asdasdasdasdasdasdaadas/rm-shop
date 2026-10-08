const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const shots=fs.mkdtempSync(path.join(os.tmpdir(),'neutral-beta-'));
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const context=await browser.newContext({viewport:{width:390,height:844},colorScheme:'light',reducedMotion:'reduce'});
 await context.addInitScript(()=>{localStorage.setItem('way_lk_token','test');sessionStorage.setItem('way_intro_v4','1');localStorage.setItem('way_home_coach_v2','1');});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const me={user:{name:'Александр',username:'alex'},balance_rub:360,topup_min:50,topup_max:10000,topup_step:50,balance_enabled:true,days_left:30,day_price_rub:6,vpn_day_price_rub:6,has_paid_topup:true,has_access:true,trial_available:false,promo_enabled:true,notification_settings_available:true,devices:[],legal:{offer:'#',privacy:'#'},invite_url:'https://t.me/test?start=ref_1',referral_program_enabled:true,referral_terms:{note:'50 ₽ за друга и 5% от пополнений'},topup_plans:[{code:'topup_300',title:'300 ₽',rub:300,amount:300}],trust:{enabled:false}};
 await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.host!=='cabinet.test')return route.fulfill({body:'',contentType:'application/javascript'});if(url.pathname.startsWith('/api/'))return route.fulfill({json:url.pathname==='/api/me'?me:{ok:true,items:[]}});const rel=url.pathname==='/'?'index.html':url.pathname.replace(/^\/(static\/)?/,'');const file=path.resolve(__dirname,'../../webapp',rel);return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});});
 await page.goto('http://cabinet.test/');await page.locator('#app:not(.hidden)').waitFor();
 await page.evaluate(()=>openSettings());
 await page.getByRole('button',{name:'Новый Бета'}).click();
 await page.getByRole('button',{name:'Светлая',exact:true}).click();
 assert.equal(await page.evaluate(()=>document.documentElement.dataset.design),'modern');
 assert.equal(await page.locator('#classicThemeSettings').isVisible(),false);
 await page.screenshot({path:path.join(shots,'settings-light.png'),fullPage:true});
 await page.evaluate(()=>openHome());
 assert.equal(await page.locator('.frog-avatar').isVisible(),false);
 assert.equal(await page.locator('.app-bg').isVisible(),false);
 assert.equal(await page.locator('.modern-frog').isVisible(),true);
 assert.equal(await page.locator('.modern-frog').evaluate(el=>el.complete && el.naturalWidth>0),true);
 assert.equal((await page.locator('.modern-frog').boundingBox()).width,32);
 assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(246, 247, 249)');
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:path.join(shots,'home-light.png'),fullPage:true});
 await page.locator('#menuBtn').click();await page.locator('#menuSettings').click();
 await page.locator('#view-settings:not(.hidden)').waitFor();
 await page.evaluate(()=>openHome());
 const material=await page.locator('#view-home .status-card').evaluate(el=>({radius:getComputedStyle(el).borderRadius,filter:getComputedStyle(el).backdropFilter}));
 assert.equal(material.radius,'28px');assert.ok(material.filter.includes('blur'));

 await page.reload();await page.locator('#app:not(.hidden)').waitFor();assert.equal(await page.evaluate(()=>document.documentElement.dataset.design),'modern');
 await page.evaluate(()=>openSettings());await page.getByRole('button',{name:'Тёмная',exact:true}).click();
 await page.evaluate(()=>openHome());assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),'rgb(16, 17, 20)');
 await page.screenshot({path:path.join(shots,'home-dark.png'),fullPage:true});
 await page.locator('#topupBtn').click();

 await page.screenshot({path:path.join(shots,'topup-dark.png'),fullPage:true});
 await page.evaluate(()=>openSettings());await page.getByRole('button',{name:'Авто',exact:true}).click();
 await page.emulateMedia({colorScheme:'light'});await page.waitForFunction(()=>document.documentElement.dataset.colorScheme==='light');
 await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.colorScheme==='dark');
 await page.getByRole('button',{name:'Привычный',exact:true}).click();
 assert.equal(await page.locator('#themeList').isVisible(),true);

 await page.getByRole('button',{name:'Розовая',exact:true}).click();
 await page.getByRole('button',{name:'Новый Бета'}).click();await page.getByRole('button',{name:'Привычный',exact:true}).click();
 assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),'pink');
 await page.evaluate(()=>openHome());assert.equal(await page.locator('.frog-avatar').isVisible(),true);assert.equal(await page.locator('.modern-frog').isVisible(),false);
 await page.evaluate(()=>openSettings());await page.getByRole('button',{name:'Новый Бета'}).click();await page.getByRole('button',{name:'Светлая',exact:true}).click();
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>openHome());
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:path.join(shots,'desktop-light.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>{window.__me.trial_available=true;window.__me.trial_days=3;window.__me.trial_rub=18;openOffer({instant:true});});
 await page.screenshot({path:path.join(shots,'gift-light.png'),fullPage:true});
 await page.evaluate(()=>{window.__me.trial_available=false;window.__me.balance_rub=0;window.__me.hours_left=0;paint(window.__me);openHome();});
 await page.screenshot({path:path.join(shots,'zero-light.png'),fullPage:true});
 // Test the real daily balance presentation with a configured device.
 await page.evaluate(()=>{const me=window.__me;me.balance_rub=180;me.hours_left=720;me.days_left=30;me.devices=[{id:1,title:'Мой iPhone',platform:'ios',active:true,subscription_url:'https://example.test/sub'}];paint(me);openHome();});
 assert.equal(await page.locator('#modernRemaining').textContent(),'30');
 assert.match(await page.locator('#modernRemainingLabel').textContent(),/дней/);
 assert.equal(await page.locator('#ctaAdd').isVisible(),false);
 await page.screenshot({path:path.join(shots,'active-light.png'),fullPage:true});
 const hero=await page.locator('.modern-overview').boundingBox();const wallet=await page.locator('#view-home .status-card').boundingBox();assert.ok(Math.abs(hero.width-wallet.width)<2);
 await page.locator('#modernReferralDetails').click();await page.locator('#view-referrals:not(.hidden)').waitFor();await page.evaluate(()=>openHome());
 await page.locator('#devicesBody .device-row').click();await page.locator('#view-device:not(.hidden)').waitFor();

 await page.evaluate(()=>openHome());await page.locator('#addDevice').click();await page.locator('#view-wizard:not(.hidden)').waitFor();
 await page.evaluate(()=>openHome());await page.locator('#homePromoOpen').click();await page.locator('#view-promo:not(.hidden)').waitFor();
 await page.evaluate(()=>{WayAppearance.choose('theme','dark');openHome();});
 await page.screenshot({path:path.join(shots,'active-dark.png'),fullPage:true});
 await page.screenshot({path:path.join(shots,'preview-dark.png')});
 await page.setViewportSize({width:320,height:740});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.evaluate(()=>{WayAppearance.choose('design','classic');openHome();});
 assert.equal(await page.locator('.modern-overview').isVisible(),false);
 assert.equal(await page.locator('#statusNote').isVisible(),true);
 assert.deepEqual(errors,[]);console.log('Classic/modern, light/dark/system, saved preferences, classic color restoration and responsive screens passed. '+shots);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
