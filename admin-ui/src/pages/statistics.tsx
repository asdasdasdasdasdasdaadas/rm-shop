import { useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Choice,
  DataTable,
  Failure,
  Loading,
  Panel,
} from "@/components/workspace";
import { money, useResource, type Data } from "@/lib/api";
import { OverviewPage } from "./overview";
import { Download, RefreshCw } from "lucide-react";

const metrics: Record<string, string> = {
  registered: "Регистрации",
  started: "Первые запуски бота",
  connected: "Первые подключения",
  referred: "Пришли по приглашению",
  devices: "Добавленные устройства",
  promo: "Активации промокодов",
  payments: "Оплаты в рублях",
  rub: "Сумма оплат, ₽",
  stars: "Оплачено Stars",
  star_payments: "Оплаты Stars",
};
const number = (v: unknown) => Number(v || 0).toLocaleString("ru-RU");
function HistoryChart({
  title,
  description,
  rows,
  keys,
}: {
  title: string;
  description: string;
  rows: Data[];
  keys: string[];
}) {
  const colors = ["var(--foreground)", "#3b82f6", "#14b8a6"];
  return (
    <Panel title={title} description={description}>
      <ChartContainer
        className="h-64 w-full min-w-0 aspect-auto"
        config={Object.fromEntries(
          keys.map((key, i) => [
            key,
            { label: metrics[key], color: colors[i] },
          ]),
        )}
      >
        <BarChart accessibilityLayer data={rows} margin={{ left: 0, right: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="day"
            tickLine={false}
            axisLine={false}
            minTickGap={36}
            tickFormatter={(v) =>
              `${String(v).slice(8)}.${String(v).slice(5, 7)}`
            }
          />
          <YAxis
            width={48}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            tickFormatter={(v) =>
              Intl.NumberFormat("ru", { notation: "compact" }).format(v)
            }
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(v) => String(v).split("-").reverse().join(".")}
              />
            }
          />
          <ChartLegend
            content={
              <ChartLegendContent className="flex-wrap gap-x-4 gap-y-1" />
            }
          />
          {keys.map((key) => (
            <Bar
              key={key}
              dataKey={key}
              fill={`var(--color-${key})`}
              radius={[3, 3, 0, 0]}
            />
          ))}
        </BarChart>
      </ChartContainer>
      {!rows.some((row) => keys.some((key) => row[key] > 0)) && (
        <p className="mt-3 text-sm text-muted-foreground">
          За этот период событий нет.
        </p>
      )}
    </Panel>
  );
}
export function StatisticsPage() {
  const [days, setDays] = useState("30");
  const history = useResource(`statistics?days=${days}`),
    snapshot = useResource("stats");
  const [details, setDetails] = useState(false);
  const rows: Data[] = history.data?.series || [],
    totals = history.data?.totals || {};
  const exportCsv = () => {
    const keys = Object.keys(metrics);
    const csv = [
      ["Дата · МСК", ...keys.map((k) => metrics[k])],
      ...rows.map((r) => [r.day, ...keys.map((k) => r[k] || 0)]),
    ]
      .map((r) => r.join(";"))
      .join("\r\n");
    const url = URL.createObjectURL(
      new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `statistics-${days}days.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const s = snapshot.data || {};
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">Динамика по дням</h2>
          <p className="text-sm text-muted-foreground">
            Календарные дни по Москве, включая сегодняшний неполный день. Данные
            удалённых пользователей и устройств могут отсутствовать.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Choice
            label="Период статистики"
            value={days}
            onChange={setDays}
            options={[
              ["7", "7 дней"],
              ["30", "30 дней"],
              ["90", "90 дней"],
              ["365", "Год"],
            ]}
          />
          <Button
            variant="outline"
            disabled={!history.data || history.loading}
            onClick={exportCsv}
          >
            <Download />
            CSV
          </Button>
          <Button
            variant="outline"
            aria-label="Обновить статистику"
            onClick={() => {
              void history.reload();
              void snapshot.reload();
            }}
          >
            <RefreshCw />
          </Button>
        </div>
      </div>
      {history.error ? (
        <Failure message={history.error} retry={history.reload} />
      ) : !history.data ? (
        <Loading />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ["registered", "Новые пользователи"],
              ["connected", "Впервые подключились"],
              ["rub", "Оплачено в рублях"],
              ["payments", "Успешные рублёвые оплаты"],
            ].map(([key, label]) => (
              <Card key={key}>
                <CardContent className="pt-5">
                  <p className="text-sm text-muted-foreground">{label}</p>
                  <p className="text-3xl font-semibold my-2">
                    {key === "rub" ? money(totals[key]) : number(totals[key])}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    За выбранный период
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Рубли рассчитаны по кодам успешных платежей. Для старых тарифных
            кодов используется текущая цена тарифа. Stars учитываются отдельно;
            бонусы и ручные начисления не включены.
          </p>
          <div className="grid gap-5 xl:grid-cols-2">
            <HistoryChart
              title="Привлечение и подключение"
              description="События в день совершения. Это не конверсия одной когорты."
              rows={rows}
              keys={["registered", "started", "connected"]}
            />
            <HistoryChart
              title="Оплаты в рублях"
              description="Успешные платежи по дате оплаты; при отсутствии даты — по дате создания счёта."
              rows={rows}
              keys={["rub"]}
            />
            <HistoryChart
              title="Приглашения и промокоды"
              description="Новые регистрации по приглашению и использования промокодов."
              rows={rows}
              keys={["referred", "promo"]}
            />
            <HistoryChart
              title="Количество оплат"
              description="Рублёвые платежи и платежи Stars считаются отдельно."
              rows={rows}
              keys={["payments", "star_payments"]}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              [
                "Средний рублёвый платёж",
                totals.payments ? money(totals.rub / totals.payments) : "—",
              ],
              ["Оплачено Stars", number(totals.stars) + " Stars"],
              ["Добавлено устройств", number(totals.devices)],
            ].map(([label, value]) => (
              <Card key={label}>
                <CardContent className="pt-5">
                  <p className="text-sm text-muted-foreground">{label}</p>
                  <p className="mt-2 text-2xl font-semibold">{value}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <Button
            variant="outline"
            aria-expanded={details}
            onClick={() => setDetails(!details)}
          >
            {details ? "Скрыть" : "Показать"} данные по дням
          </Button>
          {details && (
            <DataTable
              rows={rows}
              columns={[
                { key: "day", label: "Дата · МСК" },
                ...Object.entries(metrics).map(([key, label]) => ({
                  key,
                  label,
                })),
              ]}
            />
          )}
        </>
      )}
      <Panel
        title="Состояние сервиса сейчас"
        description="Текущий срез и накопленные показатели. Выбор периода выше на этот блок не влияет."
      >
        {snapshot.error ? (
          <Failure message={snapshot.error} retry={snapshot.reload} />
        ) : !snapshot.data ? (
          <Loading />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ["Всего пользователей", s.users?.users_total],
              ["Пользовались за 24 часа", s.online?.day],
              ["Пользовались за 7 дней", s.online?.week],
              ["Пользовались за 30 дней", s.online?.month],
              ["Забрали подарок", s.users?.trial_used],
              ["Пришли по приглашению", s.users?.referred],
              ["Заблокировали бота", s.users?.bot_blocked],
              ["Блокировки сервиса", s.users?.blocked],
              ["Плательщики в рублях", s.topups?.payers],
              ["Всего оплат Stars", s.stars_payments],
              ["Активации промокодов", s.promo_uses],
              ["Открытые обращения", s.tickets_open],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="text-2xl font-semibold mt-1">{number(value)}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>
      {history.data && (
        <Panel
          title="Устройства и трафик сейчас"
          description="Накопленные счётчики сохранившихся пользователей и устройств; история трафика по дням не ведётся."
        >
          <div className="flex flex-wrap gap-8">
            <div>
              <p className="text-sm text-muted-foreground">Всего устройств</p>
              <p className="text-2xl font-semibold">
                {number(history.data.snapshot?.devices_total)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">
                Накопленный трафик
              </p>
              <p className="text-2xl font-semibold">
                {(
                  Number(history.data.snapshot?.traffic_bytes || 0) / 1073741824
                ).toLocaleString("ru-RU", { maximumFractionDigits: 1 })}{" "}
                ГБ
              </p>
            </div>
          </div>
        </Panel>
      )}
      <OverviewPage analyticsOnly statsResource={snapshot} />
    </div>
  );
}
