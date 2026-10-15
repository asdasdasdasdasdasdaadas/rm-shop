/* Shared presentation renderer for the cabinet and its admin preview. */
(() => {
  let config = null, catalog = null, adapter = {}, pending = false, customSignature = '';
  const originals = new Map();
  const style = document.createElement('style');
  style.id = 'interface-editor-style';
  document.head.append(style);
  const observer = new MutationObserver(() => schedule());
  const observe = () => observer.observe(document.body, {subtree:true,childList:true,characterData:true});
  function schedule() {
    if (!config || pending) return;
    pending = true;
    requestAnimationFrame(() => { pending=false; render(); });
  }
  function render() {
    if (!catalog || !config) return;
    observer.disconnect();
    try {
      const theme=config.theme || {}, vars={background:'--bg-app',surface:'--bg-surface',text:'--text-primary',muted:'--text-secondary',button:'--editor-button',buttonText:'--editor-button-text'};
      const declarations=Object.entries(vars).filter(([key])=>/^#[0-9a-f]{6}$/i.test(theme[key] || '')).map(([key,name])=>`${name}:${theme[key]} !important;`).join('');
      style.textContent = `html[data-design="modern"]{${declarations}}
        ${theme.background ? 'html[data-design="modern"] body{background:var(--bg-app)!important}' : ''}
        ${theme.button ? 'html[data-design="modern"] :is(.btn-primary,#appMainBtn,.editor-action){background:var(--editor-button)!important}' : ''}
        ${theme.buttonText ? 'html[data-design="modern"] :is(.btn-primary,#appMainBtn,.editor-action){color:var(--editor-button-text)!important}' : ''}
        ${theme.surface ? 'html[data-design="modern"] :is(.section,.topup-card,.editor-card){background:var(--bg-surface)!important}' : ''}
        ${Number.isInteger(theme.radius) ? `html[data-design="modern"] :is(.section,.topup-card,.editor-card){border-radius:${Math.min(40,Math.max(8,theme.radius))}px!important}` : ''}
        .editor-hidden{display:none!important}.editor-custom{min-width:0;overflow-wrap:anywhere;width:100%;box-sizing:border-box;margin:12px 0}.editor-card{padding:20px;border:1px solid var(--divider);border-radius:24px;background:var(--bg-surface)}.editor-custom h2{font-size:20px;line-height:1.3;margin:0 0 10px}.editor-custom p{white-space:pre-wrap;font-size:14px;line-height:1.6;color:var(--text-secondary);margin:0 0 16px}.editor-action{min-height:46px;width:100%;white-space:normal;overflow-wrap:anywhere}.editor-custom-slot{display:contents}`;
      const state=adapter.state?.() || {};
      for(const f of catalog.fields) {
        if(f.step && (state.step!==f.step || state.connected || document.getElementById('view-wizard')?.classList.contains('hidden'))) continue;
        const options=config.styles?.[f.key] || {};
        const allowed={color:'color',background:'background',fontSize:'font-size',borderRadius:'border-radius',padding:'padding',marginTop:'margin-top',textAlign:'text-align'};
        const declarations=Object.entries(options).filter(([k,v])=>allowed[k] && (['color','background'].includes(k)?/^#[0-9a-f]{6}$/i.test(v):k==='textAlign'?['left','center','right'].includes(v):Number.isInteger(v)&&v>=0&&v<=64)).map(([k,v])=>`${allowed[k]}:${typeof v==='number'?v+'px':v}!important`).join(';');
        if(declarations) style.textContent+=`${f.styleSelector || f.selector}{${declarations}}`;
      }
      for(const f of catalog.fields) {
        if(f.step && (state.step!==f.step || state.connected || document.getElementById('view-wizard')?.classList.contains('hidden'))) continue;
        const el=document.querySelector(f.selector);
        if(!el || el.disabled || el.isContentEditable) continue;
        const override=config.texts?.[f.key];
        if(typeof override==='string') {
          if(!originals.has(f.key)) originals.set(f.key,{el,text:el.textContent});
          if(el.textContent!==override) el.textContent=override;
        } else if(originals.has(f.key)) {
          const old=originals.get(f.key);
          if(old.el===el) el.textContent=old.text;
          originals.delete(f.key);
        }
      }
      const parent=document.querySelector('#view-home .home-col-main');
      const desired=(config.blocks || []).map(b=>document.getElementById(b.id)).filter(Boolean);
      const current=parent ? [...parent.children].filter(el=>desired.includes(el)) : [];
      if(parent && current.some((el,i)=>el!==desired[i])) {
        // Only reorder within the existing block positions; keep other content in place.
        const markers=current.map(el=>{const marker=document.createComment('block');el.before(marker);return marker;});
        markers.forEach((marker,i)=>marker.replaceWith(desired[i]));
      }
      for(const b of config.blocks || []) {
        if(!catalog.blocks.some(x=>x.id===b.id)) continue;
        document.getElementById(b.id)?.classList.toggle('editor-hidden',b.visible===false && b.id!=='devicesBlock');
      }
      const signature=JSON.stringify(config.custom || []);
      if(signature!==customSignature) {
        document.querySelectorAll('.editor-custom-slot').forEach(el=>el.remove());
        for(const screen of catalog.screens) {
          const host=screen.id==='home' ? parent : document.getElementById('view-'+screen.id);
          if(!host) continue;
          const slot=document.createElement('div');slot.className='editor-custom-slot';host.append(slot);
          for(const b of (config.custom || []).filter(b=>b.screen===screen.id && b.visible)) {
            const block=document.createElement('section');block.className='editor-custom'+(b.type==='card'?' editor-card':'');block.dataset.editorId=b.id;
            if(b.title && b.type!=='button') {const h=document.createElement('h2');h.textContent=b.title;block.append(h);}
            if(b.text && b.type!=='button') {const p=document.createElement('p');p.textContent=b.text;block.append(p);}
            if(b.label) {const btn=document.createElement('button');btn.type='button';btn.className='btn btn-primary editor-action';btn.textContent=b.label;btn.onclick=()=>adapter.action?.(b.action,b.url);block.append(btn);}
            slot.append(block);
          }
        }
        customSignature=signature;
      }
    } finally { window.dispatchEvent(new Event('interface-rendered')); observe(); }
  }
  window.WebappEditor={set(data){config=data.config;catalog=data.catalog;schedule();},connect(value){adapter=value;schedule();},refresh:schedule};
  observe();
})();
