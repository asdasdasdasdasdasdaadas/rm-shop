const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'webapp/ui-catalog.json')));
const defaults={theme:{},texts:{},blocks:catalog.blocks.map(b=>({id:b.id,visible:true})),custom:[]};
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 let state={draft:structuredClone(defaults),published:structuredClone(defaults),revision:0,can_rollback:false,catalog},previous;
 const errors=[];
 await context.route('**/*',async route=>{
   const url=new URL(route.request().url()),p=url.pathname;
   if(url.host!=='editor.test')return route.fulfill({body:'',contentType:'application/javascript'});
   if(p==='/admin/api/interface') {
     if(route.request().method()==='POST') {
       const body=route.request().postDataJSON();assert.equal(body.revision,state.revision);
       if(body.action==='rollback'){state.draft=structuredClone(previous);state.published=structuredClone(previous);}
       else {state.draft=body.config;if(body.action==='publish'){previous=structuredClone(state.published);state.published=body.config;state.can_rollback=true;}}
       state.revision++;
     }
     return route.fulfill({json:state});
   }
   if(p==='/api/interface')return route.fulfill({json:{catalog,config:state.published}});
   if(p==='/admin/api/session')return route.fulfill({json:{ok:true,brand:'VPN'}});
   if(p==='/api/me')return route.fulfill({json:{user:{name:'Тест'},balance_rub:100,days_left:16,hours_left:384,balance_enabled:true,trial_available:false,max_devices:6,first_online_at:'2026-10-14T12:00:00Z',devices:[{id:1,title:'Телефон',platform:'ios',active:true,last_online_at:'2026-10-14T12:00:00Z',subscription_url:'https://example.test/sub'}],legal:{},vpn_day_price_rub:6}});
   if(p.includes('/api/'))return route.fulfill({json:{ok:true,items:[]}});
   if(p==='/admin/interface-preview') {
     let html=fs.readFileSync(path.join(root,'webapp/index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/g,'').replace('<head>','<head><base href="/static/">').replace('</body>','<script src="/static/interface-editor.js"></script><script src="/static/interface-preview.js"></script></body>');
     return route.fulfill({contentType:'text/html',body:html});
   }
   let file=p==='/admin/'?path.join(root,'admin/index.html'):p.startsWith('/admin/static/')?path.join(root,'admin',p.slice('/admin/static/'.length)):path.join(root,'webapp',p==='/'?'index.html':p.replace(/^\/(static\/)?/,''));
   return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://editor.test/admin/#interface');
 await page.getByText('Слои экрана',{exact:true}).waitFor();
 const preview=page.frameLocator('iframe');
 await preview.locator('#devicesHeading').dblclick();
 await preview.locator('#devicesHeading').fill('Подключитесь за минуту');
 await preview.locator('#devicesHeading').press('Enter');
 await page.getByLabel('Текст элемента',{exact:true}).waitFor();
 await page.waitForFunction(()=>document.querySelector('.canvas-inspector textarea')?.value==='Подключитесь за минуту');
 await page.getByRole('button',{name:'Отменить изменение',exact:true}).click();
 await preview.getByText('Устройства',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Повторить изменение',exact:true}).click();
 await preview.getByText('Подключитесь за минуту',{exact:true}).waitFor();
 await preview.locator('#devicesHeading').dblclick();
 await preview.locator('#devicesHeading').fill('Подключитесь за минуту!');
 await page.getByRole('button',{name:'Сохранить черновик',exact:true}).click();
 await page.getByText('Черновик сохранён',{exact:true}).waitFor();
 assert.equal(state.published.texts.devices_title,undefined);
 assert.equal(state.draft.texts.devices_title,'Подключитесь за минуту!');
 await preview.getByRole('button',{name:'Переместить Устройства',exact:true}).dragTo(preview.locator('#refHomeCard'));
 await preview.locator('.home-col-main > #refHomeCard:first-child').waitFor();
 await page.locator('.canvas-layers').getByRole('button',{name:'Промокод',exact:true}).click();
 await page.getByLabel('Показывать блок',{exact:true}).click();
 await preview.locator('#homePromoCard.editor-hidden').waitFor({state:'attached'});
 await page.getByRole('button',{name:'Карточку',exact:true}).click();
 await preview.locator('[data-editor-id] h2').dblclick();
 await preview.locator('[data-editor-id] h2').fill('Нужна помощь?');
 await preview.locator('[data-editor-id] h2').press('Enter');
 await page.getByLabel('Подпись кнопки',{exact:true}).fill('Написать нам');
 await page.getByLabel('Действие кнопки',{exact:true}).click();
 await page.getByRole('option',{name:'Поддержка',exact:true}).click();
 await preview.getByRole('button',{name:'Написать нам',exact:true}).waitFor();
 await page.getByRole('button',{name:'Цвета и форма',exact:true}).click();
 await page.getByLabel('Фон',{exact:true}).fill('#161b26');
 await page.getByRole('button',{name:'Опубликовать',exact:true}).click();
 await page.getByRole('dialog').getByRole('button',{name:'Опубликовать',exact:true}).click();
 await page.getByText('Интерфейс опубликован',{exact:true}).waitFor();
 assert.equal(state.published.custom[0].action,'support');
 await page.screenshot({path:'/tmp/interface-canvas-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 // Live cabinet consumes publication, invokes existing navigation, and treats markup as text.
 const live=await context.newPage();live.on('pageerror',e=>errors.push(e.message));
 await live.addInitScript(()=>{localStorage.setItem('way_lk_token','test');localStorage.setItem('way_home_coach_v2','1');sessionStorage.setItem('way_intro_v4','1');});
 await live.goto('http://editor.test/');
 await live.getByRole('button',{name:'Написать нам',exact:true}).waitFor();
 await live.getByRole('button',{name:'Написать нам',exact:true}).click();
 await live.locator('#view-support:not(.hidden)').waitFor();
 await live.evaluate(()=>paint(window.__me));
 assert.equal(await live.locator('#deviceCount').count(),1);
 await live.evaluate(({catalog,config})=>WebappEditor.set({catalog,config:{...config,texts:{devices_title:'<img src=x onerror=window.injected=1>'}}}),{catalog,config:state.published});
 await live.waitForFunction(()=>document.querySelector('#devicesHeading').textContent.includes('<img'));
 assert.equal(await live.evaluate(()=>window.injected),undefined);
 assert.deepEqual(errors,[]);
 await page.setViewportSize({width:1440,height:1000});
 await page.getByRole('button',{name:'Откат',exact:true}).click();
 await page.getByRole('dialog').getByRole('button',{name:'Откатить',exact:true}).click();
 await page.getByText('Предыдущий интерфейс восстановлен',{exact:true}).waitFor();
 assert.deepEqual(state.published,defaults);
 console.log('Canvas: inline editing, selection, undo/redo, drag reorder, visibility, custom button, publication and rollback passed.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
