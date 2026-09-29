const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="supportActions"></div>');
    const source = fs.readFileSync(path.join(__dirname,'../../webapp/app.js'),'utf8');
    const start = source.indexOf('let supportActionBusy = false;');
    const end = source.indexOf('function paintSupportChrome(', start);
    await page.addScriptTag({content: `
      const $ = id => document.getElementById(id);
      window.calls=[]; window.confirmed=false; window.current={id:1,status:'open'};
      const tg={showConfirm: (text, done)=>done(window.confirmed)};
      const showErr=e=>{throw e};
      async function api(url, options) {
        const body=JSON.parse(options.body); window.calls.push({url,...body});
        window.current={...window.current,status:'closed',support_rating:body.rating || null};
      }
      async function loadSupport(){paintSupportActions(window.current)};
      ${source.slice(start,end)}
      paintSupportActions(window.current);
    `});
    await page.getByRole('button',{name:'Вопрос решён — закрыть обращение'}).click();
    assert.equal(await page.evaluate(()=>window.calls.length),0);
    await page.evaluate(()=>window.confirmed=true);
    await page.getByRole('button',{name:'Вопрос решён — закрыть обращение'}).click();
    await page.getByRole('button',{name:'Оценить поддержку на 5 из 5'}).click();
    await page.getByText('Спасибо! Ваша оценка: 5 из 5.').waitFor();
    assert.deepEqual(await page.evaluate(()=>window.calls),[
      {url:'/api/tickets/1/action',action:'close'},
      {url:'/api/tickets/1/action',action:'rate',rating:5},
    ]);
    assert.equal(await page.getByRole('button').count(),0);
    console.log('Support close confirmation and rating UI passed');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
