const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}}); const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://finance.test/**',async route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/admin/api/session') return route.fulfill({json:{ok:true,brand:'WAY VPN'}});
  if(url.pathname==='/admin/api/finance') return route.fulfill({json:{ok:true,day_price:6,estimated:0,
   totals:{rub:900,payments:3,stars:50,star_payments:1,payers:3,average_rub:300},
   series:[{day:'2026-10-28',rub:900,payments:3,stars:50,star_payments:1,first:2,repeat:2}],
   history:{total:31,items:[{id:'r1',telegram_id:123,first_name:'Иван',at:'2026-10-28T10:00:00Z',currency:'RUB',amount:300,payment_number:2,plan_code:'b300'}]},
   due:{total:1,series:[{day:'2026-10-28',renewals:1}],items:[{telegram_id:123,first_name:'Иван',balance_rub:12,balance_low:true,balance_days:2,router_due:false,router_expire_at:null}]}}});
  if(url.pathname==='/admin/api/revenue-forecast') return route.fulfill({json:{ok:true,periods:[{days:7,rub:1500,clients:10,covered:10,expected_payments:5},{days:30,rub:null,clients:20,covered:10,expected_payments:null}],average_repeat_rub:300,repeat_amounts:10,sample_intervals:30}});
  if(url.pathname==='/admin/api/funnel-board') return route.fulfill({json:{ok:true,graph:{branches:[]},conditions:[],actions:[],admins:[]}});
  if(url.pathname==='/admin/api/funnel-results') return route.fulfill({json:{ok:true,items:[{step:'invite-followup-1',title:'Приглашение без регистрации',sent:10,failed:2,recipients:10,mature_recipients:8,connected:3,payers:2,payment_rate:20,payments:2,rub:600,stars:0,unknown:0,blocked:1,blocked_rate:8.3}]}});
  const rel=url.pathname.replace('/admin/','').replace(/^static\//,'')||'index.html';
  const file=path.resolve(__dirname,'../../admin',rel);
  return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404});
 });
 await page.goto('http://finance.test/admin/#finance');
 await page.getByRole('tab',{name:'Графики',exact:true}).waitFor();
 await page.getByRole('tab',{name:/Скоро продление/}).click();
 await page.getByRole('button',{name:'Иван',exact:true}).waitFor();
 await page.getByRole('tab',{name:'История',exact:true}).click();
 await page.getByRole('button',{name:'Следующая страница'}).click();
 await page.waitForURL(/#finance/);
 await page.getByText('Повторная',{exact:true}).waitFor();
 assert.equal(await page.getByRole('tab',{name:'История',exact:true}).getAttribute('aria-selected'),'true');
 await page.getByRole('tab',{name:'Калькулятор',exact:true}).click();
 await page.getByText('556',{exact:true}).waitFor();
 await page.waitForTimeout(350);
 await page.screenshot({path:'/tmp/rm-finance-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.getByText('556',{exact:true}).scrollIntoViewIfNeeded();
 await page.waitForTimeout(350);
 await page.screenshot({path:'/tmp/rm-finance-mobile.png'});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile page overflow');
 await page.getByRole('tab',{name:'Прогноз',exact:true}).click();
 await page.getByText('Недостаточно данных',{exact:true}).waitFor();
 await page.screenshot({path:'/tmp/rm-forecast-mobile.png',fullPage:true});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Forecast mobile overflow');
 await page.goto('http://finance.test/admin/#funnel');
 await page.getByRole('button',{name:'Результаты сообщений',exact:true}).click();
 await page.getByText('invite-followup-1',{exact:true}).waitFor();
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Results mobile overflow');
 await page.setViewportSize({width:1440,height:1000});
 await page.screenshot({path:'/tmp/rm-funnel-results.png',fullPage:true});
 assert.deepEqual(errors,[]);console.log('Finance UI: tabs, pagination, calculator, mobile passed');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
