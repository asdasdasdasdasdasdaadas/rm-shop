import { useState } from "react";
import { useResource, money } from "@/lib/api";
import { Choice, DataTable, Empty, Failure, Loading, Panel } from "@/components/workspace";
import { Button } from "@/components/ui/button";

function Results() {
  const [days,setDays]=useState('30');
  const resource=useResource(`funnel-results?days=${days}`);
  return <Panel title="Результаты сообщений" description="Действия в течение 7 дней после последнего доставленного сообщения воронки. Это связь по времени, а не доказанный эффект рассылки.">
    <div className="flex flex-wrap gap-3 mb-4"><Choice label="Период отправки сообщений" value={days} onChange={setDays} options={[["7","7 дней"],["30","30 дней"],["90","90 дней"]]}/><Button variant="outline" onClick={()=>void resource.reload()}>Обновить результаты</Button></div>
    <p className="text-sm text-muted-foreground mb-4">У недавних сообщений окно наблюдения ещё не завершено. Первый онлайн и плательщики — уникальные люди в строке; один платёж относится только к одному сообщению. Люди могут встречаться в разных строках. Доставка не означает прочтение.</p>
    {resource.error?<Failure message={resource.error} retry={resource.reload}/>:!resource.data?<Loading/>:<DataTable rows={resource.data.items} empty={<Empty title="В выбранном периоде сообщений нет"/>} columns={[
      {key:'title',label:'Сообщение',cell:r=><div><p>{r.title || r.step}</p><p className="text-xs text-muted-foreground">{r.step}</p></div>},
      {key:'sent',label:'Доставлено'}, {key:'failed',label:'Ошибки'}, {key:'recipients',label:'Получателей'},
      {key:'mature_recipients',label:'Наблюдение ≥ 7 дней'}, {key:'connected',label:'Первый онлайн'},
      {key:'payers',label:'Оплатили'}, {key:'payment_rate',label:'Доля оплативших',cell:r=>r.payment_rate===null?'—':`${r.payment_rate}%`},
      {key:'payments',label:'Платежей'}, {key:'rub',label:'Поступления, ₽',cell:r=>money(r.rub)},
      {key:'stars',label:'Stars'}, {key:'unknown',label:'Оплат без суммы'},
      {key:'blocked',label:'Обнаружены блокировки'},
      {key:'blocked_rate',label:'Доля блокировок',cell:r=>r.blocked_rate===null?'—':`${r.blocked_rate}%`},
    ]}/>}
    <p className="text-xs text-muted-foreground mt-4">Блокировки — явный ответ Telegram при неудачной отправке; доля от всех людей, которым пытались отправить сообщение. Это не число людей, заблокировавших бота из-за текста. Старые оплаты без сохранённой суммы входят в количество, но не в сумму рублей. Тестовые отправки исключены.</p>
  </Panel>;
}
export function FunnelResults() {
  const [open,setOpen]=useState(false);
  return <div className="space-y-3"><Button variant="outline" aria-expanded={open} onClick={()=>setOpen(!open)}>{open?'Скрыть результаты сообщений':'Результаты сообщений'}</Button>{open&&<Results/>}</div>;
}
