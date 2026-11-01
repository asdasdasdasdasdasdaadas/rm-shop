import { useResource, money } from "@/lib/api";
import { Failure, Loading, Panel } from "@/components/workspace";
import { Button } from "@/components/ui/button";
export function RevenueForecast() {
  const resource=useResource('revenue-forecast');
  const data=resource.data;
  return <Panel title="Прогноз повторных поступлений" description="Оценка на 7 и 30 дней по текущему состоянию доступа и истории рублёвых оплат за год. Не гарантированный доход.">
    <Button variant="outline" onClick={()=>void resource.reload()}>Обновить прогноз</Button>
    {resource.error?<Failure message={resource.error} retry={resource.reload}/>:!data?<Loading/>:<>
    <div className="grid gap-4 md:grid-cols-2 mt-4">{data.periods.map((p:any)=><div key={p.days} className="rounded-xl border p-5 space-y-3"><h3 className="font-semibold">Ближайшие {p.days} дней</h3><p className="text-3xl font-semibold">{p.rub===null?'Недостаточно данных':`≈ ${money(p.rub)}`}</p><p>Клиентов с заканчивающимся доступом: <b>{p.clients}</b></p><p>Хватает истории для оценки: {p.covered} из {p.clients}</p>{p.expected_payments!==null&&<p>Ожидается оплативших: ≈ {p.expected_payments}</p>}</div>)}</div>
    <p className="text-sm mt-4">Средняя повторная оплата: {data.average_repeat_rub===null?'недостаточно данных':money(data.average_repeat_rub)} · платежей с известной суммой: {data.repeat_amounts} · интервалов наблюдения: {data.sample_intervals}.</p>
    </>}
    <div className="text-sm text-muted-foreground mt-4 space-y-2"><p>В расчёт входят ранее платившие клиенты, чей баланс или подписка закончатся в выбранный срок, включая уже истёкший доступ. Срок по балансу приблизительный: текущий расход по устройствам, без остатка уже оплаченного периода.</p><p>Вероятность новой оплаты оценивается по интервалам между рублёвыми платежами с учётом времени после последней оплаты. Незавершённые наблюдения не считаются отказом. Для оценки нужны минимум 10 сопоставимых интервалов и 3 повторных платежа с известной суммой; при неполном покрытии общая сумма не выводится.</p><p>Один клиент — не более одной ожидаемой оплаты за срок. Новые клиенты, Stars, комиссии и будущие изменения тарифов не учтены. Расчёт использует общую историю сервиса и предполагает, что поведение клиентов сохранится.</p></div>
  </Panel>;
}
