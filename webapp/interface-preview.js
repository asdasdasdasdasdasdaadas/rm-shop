(() => {
  const $=id=>document.getElementById(id);
  for(const id of ['decoy','boot','intro','fail','maint']) $(id)?.classList.add('hidden');
  $('app').classList.remove('hidden');
  $('avatar').src='/icons/profile-placeholder.svg';
  $('name').textContent='Анна · предпросмотр';$('login').textContent='Демонстрационные данные';
  $('modernRemaining').textContent='5 дней';$('modernRemainingLabel').textContent='Доступ на одном устройстве';
  $('balanceLine').textContent='180 ₽';
  const demo=(host,tag,text,cls)=>{const el=document.createElement(tag);el.textContent=text;el.className=cls || '';$(host)?.append(el);return el;};
  $('devTitle').textContent='iPhone';$('devUrl').textContent='https://example.com/subscription/personal';$('devUrl').classList.remove('is-empty');
  $('topupSum').textContent='180 ₽';$('payAmountNum').textContent='180';
  ['180 ₽','360 ₽','540 ₽'].forEach(text=>demo('topupGrid','button',text,'pay-card'));
  ['СБП','Банковская карта'].forEach(text=>demo('payMethods','button',text,'pay-method'));
  demo('faqList','p','Как подключить VPN? Ответы настраиваются в разделе «Настройки».','section-note');
  demo('supportThread','p','Здравствуйте! Чем можем помочь?','section-note');
  demo('ambassadorContent','p','Здесь пользователь видит условия программы и свою статистику.','section-note');
  let current={step:1,connected:false};
  window.WebappEditor.connect({state:()=>current, action:()=>{}});
  let model=null, selected=null, dragged=null, editing=null, reveal=false;
  const send=(type,payload={})=>parent.postMessage({type,...payload},location.origin);
  const css=document.createElement('style');
  css.textContent=`[data-canvas-kind]{cursor:pointer;outline-offset:3px} [data-canvas-kind]:hover{outline:1px dashed #60a5fa!important} .canvas-selected{outline:2px solid #60a5fa!important} [contenteditable=true]{outline:2px solid #a78bfa!important;cursor:text!important;min-height:1em;white-space:pre-wrap} .canvas-drop{outline:3px solid #a78bfa!important} .canvas-handle{position:absolute;top:6px;right:6px;z-index:10;border:0;border-radius:6px;background:#2563eb;color:white;padding:4px 8px;font:11px sans-serif;cursor:grab} [data-canvas-kind=block],[data-canvas-kind=custom]{position:relative}`;
  document.head.append(css);
  const identify=el=>({kind:el.dataset.canvasKind,id:el.dataset.canvasId,property:el.dataset.canvasProperty});
  function decorate() {
    if(!model) return;
    document.querySelectorAll('[data-canvas-kind]').forEach(el=>{delete el.dataset.canvasKind;delete el.dataset.canvasId;delete el.dataset.canvasProperty;el.classList.remove('canvas-selected');});
    const tag=(el,kind,id,property)=>{if(!el)return;el.tabIndex=0;el.dataset.canvasKind=kind;el.dataset.canvasId=id;if(property)el.dataset.canvasProperty=property;if(selected?.kind===kind&&selected.id===id&&(!property||selected.property===property))el.classList.add('canvas-selected');};
    for(const f of model.catalog.fields.filter(f=>f.screen===model.screen&&(!f.step||f.step===current.step))) tag(document.querySelector(f.selector),'field',f.key);
    for(const b of model.catalog.blocks) {const el=$(b.id);tag(el,'block',b.id);handle(el,b.label);}
    document.querySelectorAll('[data-editor-id]').forEach(el=>{
      tag(el,'custom',el.dataset.editorId);handle(el,'Блок');
      for(const [selector,prop] of [['h2','title'],['p','text'],['.editor-action','label']]) tag(el.querySelector(selector),'custom',el.dataset.editorId,prop);
    });
    if(reveal && selected && !editing) {
      reveal=false;
      const target=[...document.querySelectorAll('[data-canvas-kind]')].find(el=>el.dataset.canvasKind===selected.kind&&el.dataset.canvasId===selected.id);
      target?.scrollIntoView({block:'nearest'});
    }
  }
  function handle(el,label) {
    if(!el || el.querySelector(':scope > .canvas-handle')) return;
    const h=document.createElement('button');h.type='button';h.className='canvas-handle';h.textContent='⠿ '+label;h.draggable=true;h.setAttribute('aria-label','Переместить '+label);el.append(h);
  }
  function edit(el) {
    const info=identify(el);
    if(info.kind!=='field'&&!info.property) return;
    if(model.catalog.fields.find(f=>f.key===info.id)?.kind==='dynamic') return;
    if(editing) editing.blur();
    editing=el;const before=el.textContent;el.contentEditable='true';el.focus();
    const range=document.createRange();range.selectNodeContents(el);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
    const finish=()=>{el.removeEventListener('blur',finish);el.removeEventListener('keydown',key);el.removeEventListener('paste',paste);const value=el.textContent;el.contentEditable='false';editing=null;el.textContent=before;send('interface-edit',{selection:info,value});};
    const key=e=>{if(e.key==='Escape'){e.preventDefault();el.textContent=before;el.blur();}else if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();el.blur();}};
    const paste=e=>{e.preventDefault();document.execCommand('insertText',false,e.clipboardData.getData('text/plain'));};
    el.addEventListener('blur',finish);el.addEventListener('keydown',key);el.addEventListener('paste',paste);
  }
  document.addEventListener('click',e=>{
    if(e.target.isContentEditable)return;
    e.preventDefault();e.stopPropagation();
    const el=e.target.closest('[data-canvas-kind]');
    if(el){selected=identify(el);send('interface-select',{selection:selected});decorate();}
    else send('interface-select',{selection:null});
  },true);
  document.addEventListener('keydown',e=>{if(!e.defaultPrevented&&e.key==='Enter'&&!e.target.isContentEditable&&e.target.dataset.canvasKind){e.preventDefault();edit(e.target);}});
  document.addEventListener('input',e=>{if(e.target.isContentEditable)send('interface-editing');});
  document.addEventListener('dblclick',e=>{const el=e.target.closest('[data-canvas-kind]');if(el){e.preventDefault();edit(el);}},true);
  document.addEventListener('dragstart',e=>{const h=e.target.closest('.canvas-handle');if(!h)return;dragged=identify(h.parentElement);e.dataTransfer.setData('text/plain',dragged.id);e.dataTransfer.effectAllowed='move';});
  document.addEventListener('dragover',e=>{const el=e.target.closest('[data-canvas-kind=block],section[data-canvas-kind=custom]');if(el&&dragged&&identify(el).kind===dragged.kind){e.preventDefault();el.classList.add('canvas-drop');}});
  document.addEventListener('dragleave',e=>e.target.closest('.canvas-drop')?.classList.remove('canvas-drop'));
  document.addEventListener('drop',e=>{const el=e.target.closest('[data-canvas-kind=block],section[data-canvas-kind=custom]');if(el&&dragged){e.preventDefault();send('interface-move',{source:dragged,target:identify(el)});}dragged=null;document.querySelectorAll('.canvas-drop').forEach(el=>el.classList.remove('canvas-drop'));});
  document.addEventListener('dragend',()=>{dragged=null;document.querySelectorAll('.canvas-drop').forEach(el=>el.classList.remove('canvas-drop'));});
  window.addEventListener('interface-rendered',decorate);

  window.addEventListener('message',e=>{
    if(e.origin!==location.origin || e.source!==parent) return;
    if(e.data?.type==='interface-flush'){if(editing)editing.blur();send('interface-flushed');return;}
    if(e.data?.type!=='interface-preview')return;
    const data=e.data;
    reveal=JSON.stringify(selected)!==JSON.stringify(data.selection);model=data;selected=data.selection;
    document.querySelectorAll('#app > .view').forEach(el=>el.classList.toggle('hidden',el.id!=='view-'+data.screen));
    current={step:Number(data.step) || 1,connected:false};
    $('appMainBar').classList.toggle('hidden',data.screen!=='wizard');
    document.body.classList.toggle('has-main-btn',data.screen==='wizard');
    if(data.screen==='wizard') {
      $('wizTitle').textContent=({1:'Выбор устройства',2:'Установите приложение',4:'Осталось включить VPN'})[current.step];
      $('wizStep').textContent=current.step===4?'':'Шаг '+current.step+' из 3';
      $('wizBody').replaceChildren();
      if(current.step===1) {
        const list=demo('wizBody','div','','wiz-radio');
        ['iPhone, iPad','Android','macOS','Windows','Телевизор'].forEach(name=>{const b=document.createElement('button');b.className='wiz-radio-row';b.textContent=name;list.append(b);});
      } else if(current.step===2) demo('wizBody','p','Установите VPN-приложение, затем вернитесь сюда.','section-note');
      else {
        demo('wizBody','div','iPhone · iOS','wiz-recap');
        const steps=demo('wizBody','ol','','wiz-connect-steps');
        ['Нажмите «Добавить подписку» внизу и подтвердите добавление в приложении.','Включите VPN в приложении. Если появится запрос на VPN-подключение — разрешите его.'].forEach(text=>{const li=document.createElement('li');li.textContent=text;steps.append(li);});
        const manual=demo('wizBody','details','','wiz-connect-manual');manual.open=true;
        const add=(tag,text,cls)=>{const el=document.createElement(tag);el.textContent=text;el.className=cls;manual.append(el);return el;};
        add('summary','Добавить ссылку вручную','');add('div','Ссылка подписки','dev-label');
        const link=add('div','','dev-link');const url=document.createElement('a');url.className='dev-link-text';url.textContent='https://example.com/subscription/personal';link.append(url);
        const copy=document.createElement('button');copy.className='dev-lbtn';const label=document.createElement('span');label.textContent='Копировать';copy.append(label);link.append(copy);
        demo('wizBody','button','Не получилось — помогите','btn btn-ghost').id='wizHelp';
      }
      $('appMainBtn').textContent=({1:'Продолжить',2:'Приложение установлено →',4:'Добавить подписку'})[current.step];
      $('appMainBtn').classList.remove('hidden');
    }
    window.WebappEditor.set(data);
  });
  parent.postMessage({type:'interface-preview-ready'},location.origin);
})();
