import React, { useMemo, useState, type ReactNode } from "react";
import { Area, Bar, BarChart, Cell, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";
import { CountUp, Delta, Spark } from "@/components/widgets";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { Button } from "@/components/ui/button";
import {
  Choice,
  DataTable,
  Failure,
  Loading,
  Panel,
  Pager,
  useNavigate,
} from "@/components/workspace";
import { change, compact, date, money, useHashParam, useResource, who, type Data } from "@/lib/api";
import { OverviewPage } from "./overview";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Download, RefreshCw, UserPlus, PlugZap, BadgeRussianRuble, Receipt, Star, Smartphone, GitCompareArrows, Waves, CalendarDays } from "lucide-react";

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
  renewals: "Клиенты к продлению",
  first: "Первые оплаты",
  repeat: "Повторные оплаты",
};
const number = (v: unknown) => Number(v || 0).toLocaleString("ru-RU");
const STAT_TONE: Record<string, string> = { registered: "#3e88f7", connected: "#5856d6", rub: "#2fbf6f", payments: "#ff9500" };
const STAT_ICON: Record<string, React.ReactNode> = {
  registered: <UserPlus />,
  connected: <PlugZap />,
  rub: <BadgeRussianRuble />,
  payments: <Receipt />,
};
/** Trailing 7-day average, so weekly swings do not hide the trend. */
function smooth(rows: Data[], keys: string[], prefix = "") {
  return rows.map((row, i) => {
    const out: Data = { ...row };
    for (const key of keys) {
      const window = rows.slice(Math.max(0, i - 6), i + 1);
      out[prefix + key] = window.reduce((a, r) => a + Number(r[prefix + key] || 0), 0) / window.length;
    }
    return out;
  });
}
/** Animate charts only for someone watching: hidden tabs freeze frames, and some people turn motion off. */
const motion = () => !document.hidden && !matchMedia("(prefers-reduced-motion: reduce)").matches;
const dm = (v: unknown) => `${String(v).slice(8)}.${String(v).slice(5, 7)}`;
export function HistoryChart({
  title,
  description,
  rows,
  keys,
  compare,
  smoothed = false,
  money: isMoney = false,
  action,
}: {
  title: string;
  description: string;
  rows: Data[];
  keys: string[];
  /** Previous period, day by day, laid over the current one as a dashed line. */
  compare?: Data[];
  smoothed?: boolean;
  money?: boolean;
  action?: ReactNode;
}) {
  const colors = ["#2fbf6f", "#3e88f7", "#af52de"];
  let data: Data[] = rows.map((row, i) => {
    const point: Data = { ...row };
    if (compare) for (const key of keys) {
      point["prev_" + key] = compare[i]?.[key] ?? null;
      point["prev_day_" + key] = compare[i]?.day;
    }
    return point;
  });
  if (smoothed) data = smooth(smooth(data, keys), compare ? keys : [], "prev_");
  const config = Object.fromEntries(
    keys.flatMap((key, i) => [
      [key, { label: metrics[key] || key, color: colors[i] }],
      ["prev_" + key, { label: `${metrics[key] || key} · прошлый период`, color: colors[i] }],
    ]),
  );
  const fmt = (v: unknown) =>
    isMoney ? money(Math.round(Number(v || 0))) : Number(v || 0).toLocaleString("ru-RU", { maximumFractionDigits: smoothed ? 1 : 0 });
  return (
    <Panel title={title} description={description} action={action}>
      <ChartContainer className="h-64 w-full min-w-0 aspect-auto" config={config}>
        <ComposedChart accessibilityLayer data={data} margin={{ left: 4, right: 8, top: 8 }}>
          <defs>
            {keys.map((key) => (
              <linearGradient key={key} id={"hg-" + key} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={`var(--color-${key})`} stopOpacity={0.4} />
                <stop offset="100%" stopColor={`var(--color-${key})`} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="3 6" />
          <XAxis dataKey="day" tickLine={false} axisLine={false} minTickGap={36} tickFormatter={dm} />
          <YAxis width={64} tickLine={false} axisLine={false} allowDecimals={false} tickFormatter={compact} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(v) => String(v).split("-").reverse().join(".")}
                formatter={(value, name, item) => {
                  const key = String(name), prev = key.startsWith("prev_");
                  const base = prev ? key.slice(5) : key;
                  return (
                    <div className="flex w-full items-center justify-between gap-4">
                      <span className="flex items-center gap-2 text-muted-foreground">
                        <i className="inline-block h-2.5 w-2.5 rounded-[3px]" style={{ background: `var(--color-${base})`, opacity: prev ? 0.45 : 1 }} />
                        {prev ? `Было ${dm(item?.payload?.["prev_day_" + base])}` : metrics[base] || base}
                      </span>
                      <b className="font-mono tabular-nums">{fmt(value)}</b>
                    </div>
                  );
                }}
              />
            }
          />
          <ChartLegend content={<ChartLegendContent className="flex-wrap gap-x-4 gap-y-1" />} />
          {keys.map((key) => (
            <Area key={key} type="monotone" dataKey={key} stroke={`var(--color-${key})`} strokeWidth={2.5}
              fill={`url(#hg-${key})`} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--card)" }} animationDuration={600} isAnimationActive={motion()} />
          ))}
          {compare && keys.map((key) => (
            <Line key={"prev_" + key} type="monotone" dataKey={"prev_" + key} stroke={`var(--color-${key})`} strokeOpacity={0.45}
              strokeWidth={1.75} strokeDasharray="5 5" dot={false} activeDot={{ r: 3 }} animationDuration={500} isAnimationActive={motion()} legendType="plainline" />
          ))}
        </ComposedChart>
      </ChartContainer>
      {!rows.some((row) => keys.some((key) => row[key] > 0)) && (
        <p className="mt-3 text-sm text-muted-foreground">За этот период событий нет.</p>
      )}
    </Panel>
  );
}
const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const WEEKDAYS_FULL = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"];
/** Average per weekday: when people come and pay, to time broadcasts and ads. Today is left out — it is not over. */
function WeekdayPattern({ rows, metric, days, isMoney }: { rows: Data[]; metric: string; days: number; isMoney: boolean }) {
  const data = useMemo(() => {
    const sums = Array(7).fill(0), counts = Array(7).fill(0);
    rows.slice(0, -1).forEach((row) => {
      const wd = (new Date(row.day + "T12:00:00Z").getUTCDay() + 6) % 7;
      sums[wd] += Number(row[metric] || 0);
      counts[wd] += 1;
    });
    return WEEKDAYS.map((name, i) => ({ name, value: counts[i] ? sums[i] / counts[i] : 0, days: counts[i] }));
  }, [rows, metric]);
  const total = data.reduce((a, d) => a + d.value, 0);
  const best = data.reduce((b, d, i) => (d.value > data[b].value ? i : b), 0);
  const worst = data.reduce((b, d, i) => (d.value < data[b].value ? i : b), 0);
  const fmt = (v: number) => (isMoney ? money(Math.round(v)) : v.toLocaleString("ru-RU", { maximumFractionDigits: 1 }));
  const lift = data[worst].value ? Math.round((data[best].value / data[worst].value - 1) * 100) : null;
  return (
    <Panel
      title={`По дням недели · ${metrics[metric] || metric}`}
      description="Среднее за один день недели в выбранном периоде, без сегодняшнего неполного дня. Помогает выбрать день для рассылки и рекламы."
    >
      {days < 14 ? (
        <p className="text-sm text-muted-foreground">Выберите период от 30 дней: за неделю у каждого дня всего одно значение.</p>
      ) : !total ? (
        <p className="text-sm text-muted-foreground">За этот период событий нет.</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_260px] items-center">
          <ChartContainer className="h-48 w-full min-w-0 aspect-auto" config={{ value: { label: "В среднем за день", color: "#3e88f7" } }}>
            <BarChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 6" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} />
              <YAxis width={64} tickLine={false} axisLine={false} tickFormatter={compact} />
              <ChartTooltip cursor={{ fill: "var(--secondary)" }} content={<ChartTooltipContent hideIndicator formatter={(v, _n, item) => (
                <div className="flex w-full justify-between gap-4"><span className="text-muted-foreground">В среднем · {item?.payload?.days} дн.</span><b className="tabular-nums">{fmt(Number(v))}</b></div>
              )} />} />
              <Bar dataKey="value" radius={[8, 8, 4, 4]} animationDuration={500} isAnimationActive={motion()}>
                {data.map((d, i) => (
                  <Cell key={d.name} fill={i === best ? "#2fbf6f" : i === worst ? "#ff9500" : "#3e88f7"} fillOpacity={i === best || i === worst ? 1 : 0.55} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
          <div className="space-y-3 text-sm">
            <div className="adm-mini !p-3"><span className="adm-tile" style={{ background: "#2fbf6f" }}><CalendarDays /></span>
              <div><p>Лучший день</p><b>{WEEKDAYS[best]} · {fmt(data[best].value)}</b></div></div>
            <div className="adm-mini !p-3"><span className="adm-tile" style={{ background: "#ff9500" }}><CalendarDays /></span>
              <div><p>Слабый день</p><b>{WEEKDAYS[worst]} · {fmt(data[worst].value)}</b></div></div>
            {lift != null && lift > 0 && (
              <p className="text-muted-foreground">В {WEEKDAYS_FULL[best]} в среднем на {lift}% больше, чем в {WEEKDAYS_FULL[worst]}.</p>
            )}
          </div>
        </div>
      )}
    </Panel>
  );
}
export function StatisticsPage() {
  const navigate = useNavigate();
  const [days, setDays] = useHashParam("days", "30");
  const [tab, setTab] = useHashParam("tab", "dynamics");
  const [chart, setChart] = useHashParam("chart", "acquisition");
  const [compareOn, setCompareOn] = useHashParam("compare", "1");
  const [smoothOn, setSmoothOn] = useHashParam("smooth", "0");
  const [tablePage, setTablePage] = useState(1);
  const charts: Record<
    string,
    { title: string; description: string; keys: string[] }
  > = {
    acquisition: {
      title: "Привлечение и подключение",
      description:
        "Регистрации и первые подключения в день события. Конверсия одной группы клиентов — во вкладке «Воронка».",
      keys: ["registered", "connected"],
    },
    revenue: {
      title: "Оплаты в рублях",
      description:
        "Суммы успешных платежей по дням. Бонусы и ручные начисления исключены.",
      keys: ["rub"],
    },
    payments: {
      title: "Количество оплат",
      description:
        "Число успешных платежей. Один клиент может оплатить несколько раз.",
      keys: ["payments", "star_payments"],
    },
    referrals: {
      title: "Приглашения",
      description: "Новые регистрации по приглашению в день события.",
      keys: ["referred"],
    },
  };
  const history = useResource(`statistics?days=${days}`),
    snapshot = useResource("stats");
  const [details, setDetails] = useState(false);
  const rows: Data[] = history.data?.series || [],
    totals = history.data?.totals || {},
    previous: Data = history.data?.previous || {},
    prevTotals: Data = previous.totals || {};
  const periodWord = { "7": "7 дней", "30": "30 дней", "90": "90 дней", "365": "год" }[days] || `${days} дней`;
  const avgNow = totals.payments ? totals.rub / totals.payments : 0,
    avgPrev = prevTotals.payments ? prevTotals.rub / prevTotals.payments : 0;
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
    <Tabs value={tab} onValueChange={setTab} className="space-y-6">
      <TabsList className="h-auto w-full grid grid-cols-2 sm:grid-cols-5">
        <TabsTrigger value="dynamics">Динамика</TabsTrigger>
        <TabsTrigger value="funnel">Воронка</TabsTrigger>
        <TabsTrigger value="onboarding">Первый вход</TabsTrigger>
        <TabsTrigger value="retention">Возврат клиентов</TabsTrigger>
        <TabsTrigger value="current">Сервис сейчас</TabsTrigger>
      </TabsList>
      <TabsContent value="dynamics" className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold">Динамика по дням</h2>
            <p className="text-sm text-muted-foreground">
              Даты по Москве · сегодняшний день ещё не завершён.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="w-36">
            <Choice
              label="Период статистики"
              value={days}
              onChange={(v) => {
                setDays(v);
                setTablePage(1);
              }}
              options={[
                ["7", "7 дней"],
                ["30", "30 дней"],
                ["90", "90 дней"],
                ["365", "Год"],
              ]}
            />
            </div>
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
            <div className="adm-stats">
              {[
                ["registered", "Новые пользователи"],
                ["connected", "Впервые подключились"],
                ["rub", "Оплачено в рублях"],
                ["payments", "Успешные рублёвые оплаты"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  className="adm-stat"
                  style={{ ["--tone" as string]: STAT_TONE[key] }}
                  aria-pressed={
                    chart ===
                    (key === "rub"
                      ? "revenue"
                      : key === "payments"
                        ? "payments"
                        : "acquisition")
                  }
                  onClick={() =>
                    setChart(
                      key === "rub"
                        ? "revenue"
                        : key === "payments"
                          ? "payments"
                          : "acquisition",
                    )
                  }
                >
                  <span className="adm-stat-top">
                    <span className="adm-tile" style={{ background: STAT_TONE[key] }}>{STAT_ICON[key]}</span>
                    <span className="adm-stat-label">{label}</span>
                  </span>
                  <b>
                    <CountUp value={Number(totals[key] || 0)} format={(n) => (key === "rub" ? money(Math.round(n)) : number(Math.round(n)))} />
                  </b>
                  <Spark values={rows.map((r) => Number(r[key] || 0))} color={STAT_TONE[key]} />
                  <small className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <Delta now={Number(totals[key] || 0)} prev={Number(prevTotals[key] || 0)} suffix={`к предыдущим ${periodWord}`} />
                    {prevTotals[key] != null
                      ? <span>было {key === "rub" ? money(prevTotals[key]) : number(prevTotals[key])}</span>
                      : <span>за выбранный период</span>}
                  </small>
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
            <div
                className="adm-seg"
                role="group"
                aria-label="Показатель графика"
              >
                {Object.entries(charts).map(([key, value]) => (
                  <Button
                    key={key}
                    variant={chart === key ? "secondary" : "outline"}
                    aria-pressed={chart === key}
                    onClick={() => setChart(key)}
                  >
                    {value.title}
                  </Button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Вид графика">
                <button type="button" className="adm-toggle" aria-pressed={compareOn === "1"}
                  onClick={() => setCompareOn(compareOn === "1" ? "0" : "1")} disabled={!previous.series}
                  title="Пунктир — те же дни предыдущего периода">
                  <GitCompareArrows />Прошлый период
                </button>
                <button type="button" className="adm-toggle" aria-pressed={smoothOn === "1"}
                  onClick={() => setSmoothOn(smoothOn === "1" ? "0" : "1")}
                  title="Скользящее среднее: сглаживает разницу будней и выходных">
                  <Waves />Среднее за 7 дней
                </button>
              </div>
            </div>
            <HistoryChart {...(charts[chart] || charts.acquisition)} rows={rows} money={chart === "revenue"}
              compare={compareOn === "1" ? previous.series : undefined} smoothed={smoothOn === "1"} />
            <WeekdayPattern rows={rows} metric={(charts[chart] || charts.acquisition).keys[0]} days={Number(days)} isMoney={chart === "revenue"} />
            <Panel
              title="Плашка «Пригласить друга»"
              description="Нажатия в кабинете за выбранный период. Сбор начинается после обновления. Нажатие «Отправить» не подтверждает отправку сообщения, «Скопировать» — успешное копирование."
            >
              <div className="mb-4 text-sm text-muted-foreground">
                Всего нажатий:{" "}
                <b>{number(history.data?.invitation_card?.clicks)}</b> ·
                Уникальных пользователей:{" "}
                <b>{number(history.data?.invitation_card?.users)}</b>
              </div>
              <DataTable
                rows={[
                  {
                    id: "share",
                    label: "Отправить",
                    clicks: history.data?.invitation_card?.share || 0,
                    users: history.data?.invitation_card?.share_users || 0,
                  },
                  {
                    id: "copy",
                    label: "Скопировать",
                    clicks: history.data?.invitation_card?.copy || 0,
                    users: history.data?.invitation_card?.copy_users || 0,
                  },
                ]}
                columns={[
                  { key: "label", label: "Кнопка" },
                  { key: "clicks", label: "Нажатия" },
                  { key: "users", label: "Пользователи" },
                ]}
              />
            </Panel>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() =>
                  navigate(
                    chart === "revenue" || chart === "payments"
                      ? "orders?status=granted"
                      : "ads",
                  )
                }
              >
                {chart === "revenue" || chart === "payments"
                  ? "Открыть успешные платежи"
                  : "Сравнить источники трафика"}
              </Button>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                [
                  "Средний рублёвый платёж",
                  totals.payments ? money(avgNow) : "—",
                  <Delta key="d" now={avgNow} prev={avgPrev} suffix={`к предыдущим ${periodWord}`} />,
                ],
                ["Оплачено Stars", number(totals.stars) + " Stars", <Delta key="d" now={Number(totals.stars || 0)} prev={Number(prevTotals.stars || 0)} suffix={`к предыдущим ${periodWord}`} />],
                ["Добавлено устройств", number(totals.devices), <Delta key="d" now={Number(totals.devices || 0)} prev={Number(prevTotals.devices || 0)} suffix={`к предыдущим ${periodWord}`} />],
              ].map(([label, value, delta], i) => (
                <div key={String(label)} className="adm-mini">
                  <span className="adm-tile" style={{ background: ["#22975a", "#f5a70f", "#5856d6"][i] }}>
                    {[<Receipt key="r" />, <Star key="s" />, <Smartphone key="d" />][i]}
                  </span>
                  <div>
                    <p>{label}</p>
                    <b>{value}</b> {delta}
                  </div>
                </div>
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
              <>
                <DataTable
                  rows={[...rows]
                    .reverse()
                    .slice((tablePage - 1) * 14, tablePage * 14)}
                  columns={[
                    { key: "day", label: "Дата · МСК" },
                    ...Object.entries(metrics).map(([key, label]) => ({
                      key,
                      label,
                    })),
                  ]}
                />
                <Pager
                  page={tablePage}
                  total={rows.length}
                  limit={14}
                  onChange={setTablePage}
                />
              </>
            )}
          </>
        )}
        <details className="rounded-lg border p-4 text-sm">
          <summary className="cursor-pointer font-medium">
            Как считаются показатели
          </summary>
          <div className="mt-3 space-y-2 text-muted-foreground">
            <p>
              Период включает сегодняшний неполный день. Регистрации и
              подключения относятся к дате события: делить эти числа друг на
              друга для расчёта конверсии нельзя. Для конверсии откройте
              «Воронку».
            </p>
            <p>
              Рубли рассчитаны по кодам успешных платежей. Для старых тарифов
              применяется текущая цена. При отсутствии даты оплаты используется
              дата создания счёта. Stars учитываются отдельно.
            </p>
            <p>
              Удаление пользователей и устройств может удалить часть их истории.
              CSV содержит все дни выбранного периода.
            </p>
          </div>
        </details>
      </TabsContent>
      <TabsContent value="onboarding" className="space-y-5">
        <Panel
          title="Результат изменений воронки"
          description="Сравнение пользователей за 28 дней до и за первые 28 дней после включения новой воронки. Для каждого показателя учитываются только пользователи с завершённым окном наблюдения."
        >
          {snapshot.error ? (
            <Failure message={snapshot.error} retry={snapshot.reload} />
          ) : !snapshot.data ? (
            <Loading />
          ) : (
            <>
              <p className="mb-4 text-sm text-muted-foreground">
                Начало измерений · МСК: {date(s.cohort_outcomes?.started_at)}
              </p>
              <DataTable
                rows={s.cohort_outcomes?.items || []}
                empty="Измерения ещё не начались"
                columns={[
                  {
                    key: "period",
                    label: "Когорта",
                    cell: (r) => (
                      <div>
                        <strong>
                          {r.period === "before"
                            ? "До изменений"
                            : "После изменений"}
                        </strong>
                        <p className="text-xs text-muted-foreground">
                          {date(r.starts)} — {date(r.ends)} (не включая конец)
                        </p>
                      </div>
                    ),
                  },
                  { key: "users", label: "Всего" },
                  {
                    key: "online_rate",
                    label: "Первый онлайн за 24 ч",
                    cell: (r) => (
                      <div className="space-y-1">
                        <strong>
                          {r.online_rate == null
                            ? "Ждём данные"
                            : `${r.online_rate}%`}
                        </strong>
                        <p className="text-xs text-muted-foreground">
                          {r.online_success} из {r.online_mature} · ещё
                          наблюдаем: {r.online_pending}
                        </p>
                      </div>
                    ),
                  },
                  {
                    key: "paid_rate",
                    label: "Первая оплата за 7 дней",
                    cell: (r) => (
                      <div className="space-y-1">
                        <strong>
                          {r.paid_rate == null
                            ? "Ждём данные"
                            : `${r.paid_rate}%`}
                        </strong>
                        <p className="text-xs text-muted-foreground">
                          {r.paid_success} из {r.paid_mature} · ещё наблюдаем:{" "}
                          {r.paid_pending}
                        </p>
                      </div>
                    ),
                  },
                ]}
              />
              <div className="grid gap-3 sm:grid-cols-2 mt-4">
                {[
                  ["online", "Изменение подключения"],
                  ["paid", "Изменение оплаты"],
                ].map(([key, label]) => {
                  const before = s.cohort_outcomes?.items?.find(
                      (r: Data) => r.period === "before",
                    ),
                    after = s.cohort_outcomes?.items?.find(
                      (r: Data) => r.period === "after",
                    );
                  const delta =
                    before?.[key + "_rate"] != null &&
                    after?.[key + "_rate"] != null
                      ? after[key + "_rate"] - before[key + "_rate"]
                      : null;
                  return (
                    <div key={key} className="rounded-lg bg-muted p-4">
                      <p className="text-sm">{label}</p>
                      <p className="font-semibold mt-1">
                        {delta == null
                          ? "Недостаточно завершённых наблюдений"
                          : `${delta > 0 ? "+" : ""}${delta.toFixed(1)} п. п.`}
                      </p>
                    </div>
                  );
                })}
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Даже уже оплатившие новые пользователи попадут в расчёт только
                через 7 дней после запуска бота. Текущая когорта
                предварительная, пока не завершатся все окна. Удалённые
                пользователи и старые платежи без даты оплаты не учитываются.
                Исторические даты первого онлайна могли быть восстановлены.
                Сравнение не доказывает причинность: учитывайте объём выборки и
                состав источников трафика.
              </p>
            </>
          )}
        </Panel>
        <Panel
          title="Шаги до первого подключения"
          description="Новые пользователи после включения измерений, за последние 30 дней. Каждый человек учитывается на шаге один раз. Процент — от запустивших бота; некоторые шаги можно пропустить."
        >
          {snapshot.error ? (
            <Failure message={snapshot.error} retry={snapshot.reload} />
          ) : !snapshot.data ? (
            <Loading />
          ) : (
            <>
              <p className="mb-4 text-sm">
                Медианное время до первого онлайна:{" "}
                <strong>
                  {s.onboarding_steps?.median_minutes == null
                    ? "пока нет данных"
                    : `${Math.round(s.onboarding_steps.median_minutes)} мин`}
                </strong>{" "}
                · среди подключившихся
              </p>
              <DataTable
                rows={[
                  ["started", "Запустили бота"],
                  ["welcome_continue", "Нажали «Я помогу»"],
                  ["channel_passed", "Прошли проверку канала"],
                  ["cabinet", "Открыли кабинет"],
                  ["gift_view", "Увидели подарок"],
                  ["gift_claimed", "Забрали подарок"],
                  ["wizard_1", "Открыли выбор устройства"],
                  ["wizard_2", "Открыли выбор приложения"],
                  ["wizard_3", "Дошли до создания устройства"],
                  ["wizard_4", "Получили инструкцию подключения"],
                  ["connected", "Впервые вышли онлайн"],
                ].map(([key, label]) => ({
                  label,
                  count:
                    s.onboarding_steps?.[key] ??
                    s.onboarding_steps?.stages?.[key] ??
                    0,
                }))}
                columns={[
                  { key: "label", label: "Шаг" },
                  { key: "count", label: "Пользователи" },
                  {
                    key: "share",
                    label: "Доля",
                    cell: (r) =>
                      s.onboarding_steps?.started
                        ? `${Math.round((r.count * 100) / s.onboarding_steps.started)}%`
                        : "—",
                  },
                ]}
              />
            </>
          )}
        </Panel>
      </TabsContent>
      <TabsContent value="funnel">
        <OverviewPage
          analyticsOnly
          analyticsView="conversion"
          statsResource={snapshot}
        />
      </TabsContent>
      <TabsContent value="retention" className="space-y-5">
        <OverviewPage
          analyticsOnly
          analyticsView="retention"
          statsResource={snapshot}
        />
      </TabsContent>
      <TabsContent value="current" className="space-y-5">
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
        {snapshot.data && (
          <Panel
            title="Скоро понадобится оплата"
            description="Уже пользовались VPN. Баланса хватит не больше чем на 3 суток по устройствам, либо есть незакрытый обещанный платёж. Один человек может попасть в оба списка."
          >
            <div className="grid gap-5 sm:grid-cols-3">
              {[
                ["Всего", s.pay_soon?.total],
                ["Баланс заканчивается", s.pay_soon?.low_balance],
                ["Обещанный платёж", s.pay_soon?.trust],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="text-sm text-muted-foreground">{label}</p>
                  <p className="text-2xl font-semibold mt-1">{number(value)}</p>
                </div>
              ))}
            </div>
            <details className="mt-5 rounded-lg border p-4">
              <summary className="cursor-pointer font-medium">
                Показать людей ({number(s.pay_soon?.total)})
              </summary>
              <div className="mt-4">
                <DataTable
                  rows={s.pay_soon?.people || []}
                  empty="Таких людей сейчас нет"
                  columns={[
                    {
                      key: "telegram_id",
                      label: "Человек",
                      cell: (r) => (
                        <Button
                          variant="link"
                          className="h-auto px-0"
                          onClick={() => navigate("users?q=" + r.telegram_id)}
                        >
                          {who(r)}
                        </Button>
                      ),
                    },
                    {
                      key: "balance_rub",
                      label: "Баланс",
                      cell: (r) => money(r.balance_rub),
                    },
                    {
                      key: "days_left",
                      label: "Хватит",
                      cell: (r) =>
                        r.days_left == null
                          ? "—"
                          : `${number(r.days_left)} сут.`,
                    },
                    {
                      key: "reason",
                      label: "Почему в списке",
                      cell: (r) => (
                        <span>
                          {r.reason}
                          {r.trust_open && r.trust_amount != null
                            ? `, ${money(r.trust_amount)}`
                            : ""}
                          {r.due_at ? `, до ${date(r.due_at)}` : ""}
                        </span>
                      ),
                    },
                  ]}
                />
              </div>
            </details>
          </Panel>
        )}
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
                    Number(history.data.snapshot?.traffic_bytes || 0) /
                    1073741824
                  ).toLocaleString("ru-RU", { maximumFractionDigits: 1 })}{" "}
                  ГБ
                </p>
              </div>
            </div>
          </Panel>
        )}
      </TabsContent>
    </Tabs>
  );
}
