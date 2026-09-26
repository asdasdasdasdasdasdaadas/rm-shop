import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Button } from '@/components/ui/button'
import { CommandDialog, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from '@/components/ui/command'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { LayoutDashboard, Users, Handshake, Megaphone, CreditCard, Receipt, LifeBuoy, Send, Newspaper, MessagesSquare, TicketPercent, DatabaseBackup, Settings, Search, ArrowUpRight, type LucideIcon } from 'lucide-react'
import { Toaster, toast as notify } from 'sonner'
import './theme.css'

declare global {
 interface Window {
  switchTab: (tab: string) => void
  confirmAction: (title: string, body: string, danger?: boolean) => Promise<boolean>
  toast: (message: string) => void
 }
}
const sections: { id:string; label:string; lead:string; group:string; icon:LucideIcon }[] = [
 {id:'overview',label:'Обзор',lead:'Показатели сервиса, конверсия и состояние системы',group:'Рабочее пространство',icon:LayoutDashboard},
 {id:'users',label:'Пользователи',lead:'Клиенты, устройства, баланс и активность',group:'Рабочее пространство',icon:Users},
 {id:'tickets',label:'Поддержка',lead:'Обращения клиентов и ответы команды',group:'Рабочее пространство',icon:LifeBuoy},
 {id:'orders',label:'Платежи',lead:'Заказы, успешные оплаты и незавершённые счета',group:'Финансы',icon:CreditCard},
 {id:'billing',label:'Операции',lead:'Списания за VPN, начисления и изменения баланса',group:'Финансы',icon:Receipt},
 {id:'referrals',label:'Рефералы и акции',lead:'Партнёрская программа, запуски акций и результаты',group:'Продвижение',icon:Handshake},
 {id:'promo',label:'Промокоды и подарки',lead:'Пробный доступ, промокоды и лимиты активаций',group:'Продвижение',icon:TicketPercent},
 {id:'ads',label:'Источники трафика',lead:'Рекламные ссылки и привлечённые пользователи',group:'Продвижение',icon:Megaphone},
 {id:'broadcast',label:'Рассылки',lead:'Сообщения для выбранной аудитории',group:'Коммуникации',icon:Send},
 {id:'announcements',label:'Анонсы',lead:'Новости сервиса в боте и кабинете',group:'Коммуникации',icon:Newspaper},
 {id:'messages',label:'Журнал сообщений',lead:'История отправок, статусы и ошибки доставки',group:'Коммуникации',icon:MessagesSquare},
 {id:'settings',label:'Настройки',lead:'Бренд, тарифы, подключения и тексты сервиса',group:'Система',icon:Settings},
 {id:'backups',label:'Резервные копии',lead:'Архивы базы данных и восстановление',group:'Система',icon:DatabaseBackup},
]
const groups = [...new Set(sections.map(s=>s.group))]
function go(id:string) { window.switchTab(id) }
function Sidebar() {
 const [active,setActive]=useState(location.hash.slice(1).split('?')[0] || 'overview')
 useEffect(()=>{ const update=(e:Event)=>setActive((e as CustomEvent).detail || 'overview'); window.addEventListener('admin:navigate',update); return ()=>window.removeEventListener('admin:navigate',update) },[])
 return <TooltipProvider delayDuration={200}>{groups.map(group=><div key={group} className="nav-group">
  <div className="nav-label">{group}</div>
  {sections.filter(s=>s.group===group).map(s=><Tooltip key={s.id}><TooltipTrigger asChild>
   <Button type="button" variant="ghost" className={`admin-nav-item justify-start ${active===s.id?'active bg-accent text-foreground':'text-muted-foreground'}`} data-tab={s.id} data-title={s.label} data-lead={s.lead} aria-current={active===s.id?'page':undefined} onClick={()=>go(s.id)}>
    <s.icon className="nav-ico size-4 shrink-0"/><span className="nav-text">{s.label}</span>
   </Button>
  </TooltipTrigger><TooltipContent side="right">{s.label}</TooltipContent></Tooltip>)}
 </div>)}</TooltipProvider>
}
function CommandSearch() {
 const [open,setOpen]=useState(false)
 useEffect(()=>{ const key=(e:KeyboardEvent)=>{if ((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k' && !document.getElementById('shell')?.classList.contains('hidden')) {e.preventDefault();setOpen(v=>!v)}};document.addEventListener('keydown',key);return ()=>document.removeEventListener('keydown',key)},[])
 return <><Button variant="outline" className="quick-search" onClick={()=>setOpen(true)}><Search className="size-4"/><span>Перейти к разделу</span><kbd>⌘ K</kbd></Button>
  <CommandDialog open={open} onOpenChange={setOpen} title="Перейти к разделу" description="Найдите раздел панели управления">
   <CommandInput placeholder="Пользователи, платежи, промокоды…"/>
   <CommandList><CommandEmpty>Ничего не найдено. Попробуйте другое название.</CommandEmpty>
    {groups.map(group=><CommandGroup key={group} heading={group}>{sections.filter(s=>s.group===group).map(s=><CommandItem key={s.id} value={`${s.label} ${s.lead}`} onSelect={()=>{setOpen(false);go(s.id)}}><s.icon className="size-4"/><span>{s.label}</span><ArrowUpRight className="ml-auto size-3.5 opacity-40"/></CommandItem>)}</CommandGroup>)}
   </CommandList>
  </CommandDialog></>
}
type Confirmation={title:string;body:string;danger:boolean;resolve:(result:boolean)=>void}
function Overlays() {
 const [confirmation,setConfirmation]=useState<Confirmation|null>(null)
 const current=useRef<Confirmation|null>(null)
 const previousFocus=useRef<HTMLElement|null>(null)
 const [theme,setTheme]=useState<'dark'|'light'>(document.documentElement.dataset.theme==='dark'?'dark':'light')
 const finish=(ok:boolean)=>{current.current?.resolve(ok);current.current=null;setConfirmation(null);previousFocus.current?.focus()}
 useEffect(()=>{
  window.confirmAction=(title,body,danger=true)=>new Promise(resolve=>{current.current?.resolve(false);previousFocus.current=document.activeElement as HTMLElement;current.current={title,body,danger,resolve};setConfirmation(current.current)})
  window.toast=(message)=>{if(message)notify(message)}
  const observer=new MutationObserver(()=>setTheme(document.documentElement.dataset.theme==='dark'?'dark':'light'))
  observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']})
  return ()=>observer.disconnect()
 },[])
 return <><Toaster theme={theme} position="bottom-right" closeButton richColors/>
 <Dialog open={!!confirmation} onOpenChange={open=>{if(!open)finish(false)}}>
  <DialogContent className="sm:max-w-md" onCloseAutoFocus={e=>{e.preventDefault();previousFocus.current?.focus()}}>
   <DialogHeader><DialogTitle>{confirmation?.title || 'Подтверждение'}</DialogTitle><DialogDescription className="whitespace-pre-line">{confirmation?.body}</DialogDescription></DialogHeader>
   <DialogFooter><Button variant="outline" autoFocus onClick={()=>finish(false)}>Отмена</Button><Button variant={confirmation?.danger?'destructive':'default'} onClick={()=>finish(true)}>Подтвердить</Button></DialogFooter>
  </DialogContent>
 </Dialog></>
}
const nav=document.querySelector('#sidebar nav')
if(nav)createRoot(nav).render(<Sidebar/> )
const command=document.getElementById('adminCommand')
if(command)createRoot(command).render(<CommandSearch/> )
const overlays=document.getElementById('adminOverlays')
if(overlays)createRoot(overlays).render(<Overlays/> )
// The API controllers keep ownership of form values and table rows.
// React owns only the component roots above; neither side re-renders the other's nodes.
document.documentElement.classList.add('shadcn-ready')
