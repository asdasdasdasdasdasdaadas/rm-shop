const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
 for(const [ua,platform] of [['Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)','ios'],['Mozilla/5.0 (Linux; Android 14)','android']]) {
  const context=await browser.newContext({viewport:{width:390,height:844},userAgent:ua,reducedMotion:'reduce'});
  await context.addInitScript(()=>{localStorage.setItem('way_lk_token','test');sessionStorage.setItem('way_intro_v4','1');});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  let claims=0,creates=0,device;
  const me={user:{name:'Тест'},balance_rub:0,balance_enabled:true,trial_available:true,trial_days:3,trial_rub:18,max_devices:6,devices:[],legal:{},vpn_day_price_rub:6,trial_notice:{kind:'claim',days:3}};
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.host!=='cabinet.test') return route.fulfill({body:'',contentType:'application/javascript'});
   if(url.pathname==='/api/trial'){claims++;me.balance_rub=18;me.trial_available=false;me.trial_notice=null;me.trial_waiting_connection=true;return route.fulfill({json:{ok:true,balance_rub:18}});}
   if(url.pathname==='/api/vpn-feedback'){me.vpn_feedback=route.request().postDataJSON().value;return route.fulfill({json:{ok:true}});}
   if(url.pathname==='/api/devices'){
    creates++;device=route.request().postDataJSON();me.devices=[{id:1,...device,subscription_url:'https://sub.test/1',active:true}];
    return route.fulfill({json:{ok:true,subscription_url:'https://sub.test/1',first_device:true}});
   }
   if(url.pathname.startsWith('/api/'))return route.fulfill({json:url.pathname==='/api/me'?me:{ok:true,items:[]}});
   const file=path.resolve(__dirname,'../../webapp',url.pathname==='/'?'index.html':url.pathname.replace(/^\/(static\/)?/,''));
   return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});
  });
  await page.goto('http://cabinet.test/');await page.locator('#app:not(.hidden)').waitFor();
  await page.evaluate(()=>openOffer({instant:true}));
  await page.locator('#offerTry').click();
  await page.getByRole('heading',{name:'Установите приложение',exact:true}).waitFor();
  assert.equal(claims,1);assert.equal(await page.evaluate(()=>wiz.platform),platform);
  assert.equal(await page.locator('#devName').count(),0);
  await page.locator('#appMainBtn').click();
  await page.getByRole('heading',{name:'Осталось включить VPN',exact:true}).waitFor();
  assert.equal(creates,1);assert.equal(device.platform,platform);assert.ok(device.title);
  assert.match(await page.locator('#appMainBtn').textContent(),/Добавить подписку/);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.evaluate(()=>{window.openClient=(client,url)=>window.testOpened={client,url};});
  await page.locator('#appMainBtn').click();assert.equal((await page.evaluate(()=>window.testOpened)).url,'https://sub.test/1');
  await page.evaluate(()=>{openHome();paint(window.__me);});
  assert.match(await page.locator('#connectionGuide').textContent(),/Подарок сохранён/);
  await page.getByRole('button',{name:'Продолжить подключение',exact:true}).last().click();
  await page.getByRole('heading',{name:'Осталось включить VPN',exact:true}).waitFor();
  assert.equal(creates,1);
  await page.evaluate(()=>{window.__me.first_online_at=new Date().toISOString();window.__me.trial_waiting_connection=false;window.__me.hours_left=48;openHome();paint(window.__me);});
  await page.getByRole('button',{name:'Всё работает',exact:true}).click();
  await page.locator('#connectionGuide').waitFor({state:'hidden'});
  assert.equal(me.vpn_feedback,'ok');
  assert.deepEqual(errors,[]);await context.close();
 }
 console.log('Gift → installation → subscription passed on iOS and Android.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
