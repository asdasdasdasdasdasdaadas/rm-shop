const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 await page.setContent('<html><head><style>body{font:16px system-ui;margin:16px}button{padding:12px}p{margin:0}</style></head><body><h2>Пополнение баланса</h2><p id="payMethodNote"></p></body></html>');
 const source=fs.readFileSync(require('node:path').join(__dirname,'../../webapp/app.js'),'utf8');
 await page.addScriptTag({content:`const $=id=>document.getElementById(id);let payMethod='gram',pendingPayPlan={code:'topup_300'},screen='pay';let opened=null;const tg={openLink:u=>opened=u,openTelegramLink:u=>opened=u};const showErr=e=>{throw e};const load=async()=>{};let status='pending';const fixture={id:'abc',rub:300,gram:'3.092857879',rate:'97.03',address:'UQBuU8RCIxH121MjJofAC2xyvn-7pr2LmdqIiO5d_xVkkGgT',comment:'gram_abc',expires_at:new Date(Date.now()+600000).toISOString(),telegram_wallet_url:'https://t.me/sendgrams?to=test&amount=3.092857879',wallet_url:'https://app.tonkeeper.com/transfer/test?amount=3092857879&text=gram_abc'};const api=async()=>({gram_order:{...fixture,status}});`+source.slice(source.indexOf('let gramQuoteSequence'),source.indexOf('async function payPlan('))});
 await page.evaluate(()=>previewGramQuote());
 await page.getByText('К оплате: 3.092857879 GRAM → 300 ₽ на баланс',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Открыть GRAM-кошелёк',exact:true}).click();
 assert((await page.evaluate(()=>opened)).includes('t.me/sendgrams?to=test&amount=3.092857879'));
 await page.screenshot({path:'/tmp/gram-checkout-mobile.png',fullPage:true});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.evaluate(()=>{status='review'});
 await page.getByRole('button',{name:'Проверить оплату'}).click();
 await page.getByText('Перевод требует проверки. Не платите повторно, обратитесь в поддержку.',{exact:true}).waitFor();
 assert(await page.getByRole('button',{name:'Открыть GRAM-кошелёк',exact:true}).isDisabled());
 await page.evaluate(()=>{status='pending';fixture.expires_at=new Date(Date.now()-1000).toISOString();showGramOrder({...fixture,status});});
 assert(await page.getByRole('button',{name:'Открыть GRAM-кошелёк',exact:true}).isDisabled());
 // Switching methods invalidates an unfinished quote request.
 await page.evaluate(()=>{payMethod='card';previewGramQuote()});
 assert.equal(await page.locator('#gramOrderPanel').count(),0);
 console.log('GRAM checkout: quote, transfer URL, review, expiry and method switch passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
