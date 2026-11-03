import {useState} from "react";
import {useResource,money,date,who} from "@/lib/api";
import {DataTable,Empty,Failure,Loading,Pager,Panel} from "@/components/workspace";
import {Button} from "@/components/ui/button";
const statuses:Record<string,string>={pending:'Ожидает перевода',confirmed:'Зачисляется',granted:'Оплачено',expired:'Истёк',review:'Требует проверки'};
export function GramPayments(){
 const [page,setPage]=useState(1);const resource=useResource(`gram-payments?page=${page}`);const data=resource.data;
 return <Panel title="Оплата GRAM (TON)" description="Прямые переводы на кошелёк. Поздние переводы, недоплаты и повторные платежи требуют проверки по хешу транзакции.">
 <Button variant="outline" onClick={()=>void resource.reload()}>Обновить GRAM</Button>
 {resource.error?<Failure message={resource.error} retry={resource.reload}/>:!data?<Loading/>:<div className="space-y-4 mt-4">
 <DataTable rows={data.items} empty={<Empty title="Счетов GRAM пока нет"/>} columns={[
 {key:'created_at',label:'Создан',cell:r=>date(r.created_at)}, {key:'telegram_id',label:'Клиент',cell:r=>`${who(r)} · ${r.telegram_id}`},
 {key:'status',label:'Статус',cell:r=>statuses[r.status]||r.status},{key:'rub',label:'На баланс',cell:r=>money(r.rub)},
 {key:'gram',label:'GRAM'},{key:'rate',label:'Курс, ₽'},{key:'comment',label:'Комментарий'},
 {key:'tx_hash',label:'Транзакция',cell:r=>r.tx_hash?<a className="underline" href={`https://tonviewer.com/transaction/${r.tx_hash}`} target="_blank" rel="noreferrer">Посмотреть</a>:'—'}]}/>
 <Pager page={page} total={data.total} limit={30} onChange={setPage}/>
 <h3 className="font-semibold">Последние 30 переводов для проверки</h3>
 <DataTable rows={data.deposits} empty={<Empty title="Нет переводов для проверки"/>} columns={[
 {key:'paid_at',label:'Дата',cell:r=>date(r.paid_at)},{key:'order_id',label:'Счёт'},
 {key:'reason',label:'Причина',cell:r=>({unmatched:'Нет подходящего комментария',review:'Сумма или срок не совпали',duplicate:'Повторный перевод'} as Record<string,string>)[r.reason]||r.reason},
 {key:'nano_amount',label:'Получено, nanoGRAM'},
 {key:'tx_hash',label:'Транзакция',cell:r=><a className="underline" href={`https://tonviewer.com/transaction/${r.tx_hash}`} target="_blank" rel="noreferrer">Посмотреть</a>}]}/>
 <p className="text-sm text-muted-foreground">Возврат выполняется владельцем кошелька вручную после проверки. Сервис не хранит ключи и не отправляет криптовалюту.</p>
 </div>}
 </Panel>;
}
