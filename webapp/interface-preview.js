(() => {
  const $=id=>document.getElementById(id);
  for(const id of ['decoy','boot','intro','fail','maint']) $(id)?.classList.add('hidden');
  $('app').classList.remove('hidden');
  $('avatar').src='/icons/profile-placeholder.svg';
  $('name').textContent='Анна · предпросмотр';$('login').textContent='Демонстрационные данные';
  $('modernRemaining').textContent='5 дней';$('modernRemainingLabel').textContent='Доступ на одном устройстве';
  $('balanceLine').textContent='180 ₽';
  const demo=(host,tag,text,cls)=>{const el=document.createElement(tag);el.textContent=text;el.className=cls || '';$(host)?.append(el);return el;};
  $('topupSum').textContent='180 ₽';$('payAmountNum').textContent='180';
  ['180 ₽','360 ₽','540 ₽'].forEach(text=>demo('topupGrid','button',text,'pay-card'));
  ['СБП','Банковская карта'].forEach(text=>demo('payMethods','button',text,'pay-method'));
  demo('faqList','p','Как подключить VPN? Ответы настраиваются в разделе «Настройки».','section-note');
  demo('supportThread','p','Здравствуйте! Чем можем помочь?','section-note');
  demo('ambassadorContent','p','Здесь пользователь видит условия программы и свою статистику.','section-note');
  let current={step:1,connected:false};
  window.WebappEditor.connect({state:()=>current, action:()=>{}});
  document.addEventListener('click',e=>{e.preventDefault();},true);
  window.addEventListener('message',e=>{
    if(e.origin!==location.origin || e.source!==parent || e.data?.type!=='interface-preview') return;
    const data=e.data;
    document.querySelectorAll('#app > .view').forEach(el=>el.classList.toggle('hidden',el.id!=='view-'+data.screen));
    current={step:data.step || 1,connected:false};
    if(data.screen==='wizard') {
      $('wizTitle').textContent=({1:'Выбор устройства',2:'Установите приложение',4:'Осталось включить VPN'})[current.step];
      $('wizBody').replaceChildren();
      if(current.step===1) {
        const list=demo('wizBody','div','','wiz-radio');
        ['iPhone, iPad','Android','macOS','Windows','Телевизор'].forEach(name=>{const b=document.createElement('button');b.className='wiz-radio-row';b.textContent=name;list.append(b);});
      } else demo('wizBody','p',current.step===2?'Установите VPN-приложение, затем вернитесь сюда.':'Добавьте подписку и включите VPN в приложении.','section-note');
    }
    window.WebappEditor.set(data);
  });
  parent.postMessage({type:'interface-preview-ready'},location.origin);
})();
