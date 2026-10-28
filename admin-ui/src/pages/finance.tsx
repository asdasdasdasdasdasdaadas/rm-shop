import { useState } from "react";
import { useResource, money, date, who, type Data } from "@/lib/api";
import { requiredUsers } from "@/lib/finance-calculator.mjs";
import { Choice, DataTable, Empty, Failure, Loading, Pager, Panel, useNavigate } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RefreshCw, Calculator, Users, History, ChartNoAxesCombined } from "lucide-react";
import { HistoryChart } from "./statistics";

function IncomeCalculator({dayPrice}: {dayPrice:number}) {
  const [mode,setMode]=useState("revenue");
  const [fields,setFields]=useState({target:"100000",arpu:String(dayPrice*30),fee:"0",fixed:"0",variable:"0"});
  const profit=mode==="profit";
  const result=requiredUsers({...Object.fromEntries(Object.entries(fields).map(([k,v])=>[k,v.trim()===""?NaN:Number(v)])) as Record<keyof typeof fields,number>,profit});
  const inputs=[['target','Цель в месяц, ₽'],['arpu','Средняя выручка с пользователя в месяц, ₽'],...(profit ? [['fee','Комиссии и налоги, % от выручки'],['fixed','Постоянные расходы в месяц, ₽'],['variable','Расходы на пользователя в месяц, ₽']] : [])];
  return <Panel title="Сколько нужно платящих пользователей" description="Плановый расчёт на месяц. Введите свои средние показатели и расходы.">
    <Choice label="Цель расчёта" value={mode} onChange={setMode} options={[["revenue","Выручка"],["profit","Прибыль после указанных расходов"]]} />
    <div className="mt-5 grid gap-6 lg:grid-cols-2">
      <div className="space-y-4">{inputs.map(([key,label])=><label key={key} className="block space-y-2 text-sm"><span>{label}</span><Input type="number" min="0" step="any" max={key==="fee"?100:undefined} value={fields[key as keyof typeof fields]} onChange={e=>setFields({...fields,[key]:e.target.value})}/></label>)}
        <p className="text-xs text-muted-foreground">Начальная выручка на пользователя: одно устройство × {money(dayPrice)} × 30 дней. Это предположение, не фактический средний доход. Stars в рубли не пересчитываются.</p>
      </div>
      <div className="rounded-xl bg-muted/50 p-6 space-y-3" aria-live="polite">{result ? <><p className="text-sm text-muted-foreground">Нужно активных платящих пользователей</p><p className="text-4xl font-semibold">{result.users.toLocaleString('ru-RU')}</p><p>Выручка: <b>{money(result.revenue)}</b> / месяц</p>{profit && <p>Прибыль: <b>{money(result.result)}</b> / месяц</p>}<p className="text-xs text-muted-foreground">Округлено вверх. Отток, сезонность и расходы, которые вы не указали, не учтены.</p></> : <p role="alert">Введите корректные суммы. Для прибыли доход на пользователя после комиссий должен превышать переменные расходы.</p>}</div>
    </div>
  </Panel>;
}

export function FinancePage() {
  const [tab,setTab]=useState('charts');
  const [days,setDays]=useState('30'),[page,setPage]=useState(1),[duePage,setDuePage]=useState(1),[horizon,setHorizon]=useState('3');
  const nav=useNavigate();
  const resource=useResource(`finance?days=${days}&page=${page}&horizon=${horizon}&due_page=${duePage}`);
  const data=resource.data;
  const client={key:'user',label:'Клиент',cell:(r:Data)=><Button variant="link" className="p-0 h-auto" onClick={()=>nav(`users?q=${r.telegram_id}`)}>{who(r)}</Button>};
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-muted-foreground">Успешные платежи · московское время</p><div className="flex gap-2"><Choice label="Период финансов" value={days} onChange={v=>{setDays(v);setPage(1);}} options={[["7","7 дней"],["30","30 дней"],["90","90 дней"],["365","Год"]]}/><Button variant="outline" aria-label="Обновить финансы" onClick={()=>void resource.reload()}><RefreshCw/></Button></div></div>
    {resource.error ? <Failure message={resource.error} retry={resource.reload}/> : !data ? <Loading/> : <>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[['Получено, ₽',money(data.totals.rub)],['Успешных платежей',data.totals.payments+data.totals.star_payments],['Уникальных плательщиков',data.totals.payers],['Средний платёж, ₽',money(data.totals.average_rub)]].map(([label,value])=><div key={String(label)} className="rounded-xl border p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="text-3xl font-semibold mt-2">{value}</p></div>)}</div>
    {data.estimated>0 && <p className="text-xs text-muted-foreground">Для {data.estimated} старых оплат сумма восстановлена из тарифа: историческая сумма отсутствует. Такие записи отмечены «≈».</p>}
    <Tabs value={tab} onValueChange={setTab}><TabsList className="flex flex-wrap h-auto justify-start"><TabsTrigger value="charts"><ChartNoAxesCombined className="size-4 mr-2"/>Графики</TabsTrigger><TabsTrigger value="due"><Users className="size-4 mr-2"/>Скоро продление · {data.due.total}</TabsTrigger><TabsTrigger value="history"><History className="size-4 mr-2"/>История</TabsTrigger><TabsTrigger value="calculator"><Calculator className="size-4 mr-2"/>Калькулятор</TabsTrigger></TabsList>
    <TabsContent value="charts"><div className="grid gap-5 lg:grid-cols-2"><HistoryChart title="Поступления в рублях" description="Бонусы и ручные начисления исключены. Выручка до комиссий." rows={data.series} keys={['rub']}/><HistoryChart title="Число успешных платежей" description="Рубли и Stars показаны отдельно." rows={data.series} keys={['payments','star_payments']}/><HistoryChart title="Первые и повторные оплаты" description="Первая оплата определяется по всей истории клиента, а не только по выбранному периоду." rows={data.series} keys={['first','repeat']}/><HistoryChart title="Поступления Stars" description="В единицах Stars, без пересчёта в рубли." rows={data.series} keys={['stars']}/></div></TabsContent>
    <TabsContent value="due" className="space-y-5"><HistoryChart title="Ожидаемые продления" description="Оценка по текущему балансу и окончанию подписки. Нулевой баланс и истёкшие подписки показаны на сегодня. Один человек учитывается один раз." rows={data.due.series} keys={["renewals"]}/><Panel title="Клиенты, которым скоро понадобится продление" description="Только ранее платившие. Это возможное продление, не задолженность. Остаток по балансу приблизительный и не включает уже оплаченный период устройства."><div className="mb-4"><Choice label="Горизонт продления" value={horizon} onChange={v=>{setHorizon(v);setDuePage(1);}} options={[["1","В течение суток"],["3","В течение 3 дней"],["7","В течение недели"],["14","В течение 2 недель"]]}/></div><DataTable rows={data.due.items} empty={<Empty title="Нет клиентов для продления"/>} columns={[client,{key:'balance_rub',label:'Баланс',cell:r=>money(r.balance_rub)},{key:'reason',label:'Причина',cell:r=>[r.balance_low?'Баланс заканчивается':'',r.router_due?'Подписка роутера':''].filter(Boolean).join(' · ')},{key:'remaining',label:'Остаток баланса',cell:r=>r.balance_low?`${r.balance_days} дн. (оценка)`:'—'},{key:'router_expire_at',label:'Роутер до · МСК',cell:r=>date(r.router_expire_at)}]}/><Pager page={duePage} total={data.due.total} limit={30} onChange={setDuePage}/></Panel></TabsContent>
    <TabsContent value="history"><Panel title="История успешных платежей" description="Все способы оплаты. Неоплаченные счета и операции по балансу доступны по кнопкам ниже."><div className="flex gap-2 mb-4"><Button variant="outline" onClick={()=>nav('orders')}>Все счета</Button><Button variant="outline" onClick={()=>nav('billing')}>Операции по балансу</Button></div><DataTable rows={data.history.items} empty={<Empty title="За период оплат нет"/>} columns={[{key:'at',label:'Дата · МСК',cell:r=>date(r.at)},client,{key:'amount',label:'Сумма',cell:r=>`${r.estimated?'≈ ':''}${r.currency==='RUB'?money(r.amount):r.amount+' Stars'}`},{key:'type',label:'Оплата',cell:r=>r.payment_number===1?'Первая':'Повторная'},{key:'plan_code',label:'Тариф'},{key:'id',label:'Идентификатор'}]}/><Pager page={page} total={data.history.total} limit={30} onChange={setPage}/></Panel></TabsContent>
    <TabsContent value="calculator"><IncomeCalculator dayPrice={data.day_price}/></TabsContent>
    </Tabs></>}
  </div>;
}
