import { useState, type ReactNode } from "react";
import { date, money, qs, useResource, type Data } from "@/lib/api";
import {
  DataTable,
  Empty,
  Failure,
  Loading,
  Panel,
  useNavigate,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { ArrowRight, ArrowUpRight, RefreshCw, CircleCheck } from "lucide-react";
import { messageKinds } from "@/lib/message-kinds";
import { funnelRoute } from "@/lib/contracts.mjs";
import { CountUp, DashboardWidgets } from "@/components/widgets";
import { JourneyFunnel, JourneySources } from "@/components/journey";
const main = [
  ["entered", "Запустили бота"],
  ["trial", "Забрали подарок"],
  ["device", "Добавили устройство"],
  ["connected", "Подключились"],
  ["checkout", "Начали оплату"],
  ["paid", "Оплатили"],
  ["repeat_paid", "Пополнили повторно"],
];
const leaks = [
  ["no_gift", "Без подарка и оплаты"],
  ["gift_no_online", "Подарок без подключения"],
  ["device_no_online", "Устройство без онлайна"],
  ["online_no_paid", "Подключались, но не оплатили"],
  ["checkout_drop", "Счёт без оплаты"],
  ["paid_no_repeat", "Не пополнили повторно"],
  ["paid_empty", "Платили, деньги кончились"],
];
const sources = [
  ["organic", "Без рекламной метки"],
  ["from_ref", "По реферальной ссылке"],
  ["from_ad", "По рекламе"],
  ["promo", "Активировали промокод"],
];
const invites = [
  ["inv_entered", "Пришли по ссылке"],
  ["inv_legal", "Приняли документы"],
  ["inv_trial", "Забрали подарок"],
  ["inv_device", "Добавили устройство"],
  ["inv_connected", "Подключились"],
  ["inv_checkout", "Начали оплату"],
  ["inv_paid", "Оплатили"],
];
export function OverviewPage({
  analyticsOnly = false,
  statsResource,
  analyticsView,
}: {
  analyticsOnly?: boolean;
  analyticsView?: "conversion" | "retention";
  statsResource?: ReturnType<typeof useResource>;
}) {
  // The overview stays open on a second screen: refresh it every 5 minutes (not while the tab is hidden).
  const fetched = useResource(statsResource ? null : "stats", 300000);
  const resource = statsResource || fetched,
    navigate = useNavigate();
  const [period, setPeriod] = useState("30d");
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  const s = resource.data,
    u = s.users || {},
    pack = s.funnel?.[period] || {},
    cur = pack.current || {};
  const Content = ({
    value,
    children,
    className,
  }: {
    value: string;
    children: ReactNode;
    className?: string;
  }) =>
    analyticsView ? (
      analyticsView === value ? (
        <div className={className}>{children}</div>
      ) : null
    ) : (
      <TabsContent value={value} className={className}>
        {children}
      </TabsContent>
    );
  const clients = (step: string) => navigate(funnelRoute(step, pack));
  const funnel = (steps: string[][], transitions = false) => (
    <div className="space-y-1">
      {steps.map(([key, label], i) => {
        const count = Number(cur[key] || 0),
          base = transitions
            ? i
              ? Number(cur[steps[i - 1][0]] || 0)
              : count
            : Number(cur[steps === invites ? "inv_entered" : "entered"] || 0),
          numerator =
            transitions && i
              ? Number(cur[key + "_transition"] ?? count)
              : count,
          pct = base ? Math.round((numerator / base) * 100) : 0;
        return (
          <button
            key={key}
            className="w-full rounded-lg hover:bg-muted p-3 text-left grid grid-cols-[minmax(0,1fr)_80px] gap-4 items-center"
            onClick={() => clients(key)}
          >
            <div className="space-y-2">
              <span className="text-sm">{label}</span>
              <Progress value={Math.min(100, pct)} className="h-1.5" />
            </div>
            <div className="text-right">
              <p className="font-semibold tabular-nums">
                {count.toLocaleString("ru-RU")}
              </p>
              <p className="text-xs text-muted-foreground">
                {base ? pct + "%" : "—"}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
  return (
    <div className="space-y-6">
      {/* Only in «Статистика» → «Воронка»: not on «Обзор», not again under retention. */}
      {s.journey_comparison && analyticsView === "conversion" && (
        <>
          <JourneyFunnel data={s.journey_comparison} />
          {s.journey_comparison.sources && <JourneySources data={s.journey_comparison} />}
        </>
      )}
      {!analyticsOnly && (
        <>
          <div className="adm-hero grid gap-1 p-2 sm:grid-cols-2 xl:grid-cols-4">
            {[
              [
                "Пользователи",
                u.users_total || 0,
                "Всего зарегистрировано",
                "users",
                Number(u.users_total || 0),
              ],
              [
                "Онлайн за сутки",
                s.online?.day || 0,
                "Пользовались VPN за 24 часа",
                "users?online=1d",
                Number(s.online?.day || 0),
              ],
              [
                "Сумма пополнений",
                money(s.topups?.amount_rub || s.revenue_rub),
                "За всё время",
                "orders?status=granted",
                Number(s.topups?.amount_rub || s.revenue_rub || 0),
              ],
              [
                "Платящие пользователи",
                s.paying_users?.total ?? s.topups?.payers ?? 0,
                "Хотя бы одно пополнение",
                "users?paid=yes",
                Number(s.paying_users?.total ?? s.topups?.payers ?? 0),
              ],
            ].map(([label, value, hint, path, raw]) => (
              <button
                key={String(label)}
                className="adm-kpi"
                onClick={() => navigate(String(path))}
              >
                <small className="flex justify-between">
                  {label}
                  <ArrowUpRight className="size-4" />
                </small>
                <b>
                  {typeof raw === "number" ? (
                    <CountUp value={raw} format={(n) => (path === "orders?status=granted" ? money(Math.round(n)) : Math.round(n).toLocaleString("ru-RU"))} />
                  ) : (
                    value
                  )}
                  {path === "users?paid=yes" && s.paying_users && (
                    <span
                      className="ml-3 inline-flex align-middle rounded-full bg-white/20 px-2.5 py-1 text-xs font-semibold tracking-normal text-white"
                      title="Впервые оплатили сегодня, с 00:00 по Москве"
                    >
                      +{s.paying_users.new_today ?? 0} за день
                    </span>
                  )}
                </b>
                <span>{hint}</span>
              </button>
            ))}
          </div>
          <DashboardWidgets s={s} />
        </>
      )}
      <Tabs
        defaultValue="conversion"
        value={analyticsView}
        className="space-y-5"
      >
        {!analyticsView && (
          <div className="flex flex-wrap justify-between items-center gap-3">
            <TabsList className="max-w-full overflow-x-auto justify-start">
              <TabsTrigger value="conversion">Конверсия</TabsTrigger>
              <TabsTrigger value="retention">Возврат клиентов</TabsTrigger>
              <TabsTrigger value="system">Состояние системы</TabsTrigger>
            </TabsList>
            <div className="flex items-center gap-2">
              {resource.updatedAt > 0 && (
                <span className="text-xs text-muted-foreground" title="Обзор обновляется сам каждые 5 минут">
                  Обновлено в{" "}
                  {new Date(resource.updatedAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
              <Button variant="ghost" disabled={resource.loading} onClick={() => void resource.reload()}>
                <RefreshCw className={resource.loading ? "animate-spin" : undefined} />
                Обновить
              </Button>
            </div>
          </div>
        )}
        <Content value="conversion" className="space-y-5">
          <div className="flex flex-wrap justify-between items-end gap-3">
            <div>
              <h2 className="font-semibold text-lg">Путь новых клиентов</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Все, кто впервые запустил бота за период. Нажмите на число — откроется список людей.
              </p>
            </div>
            <div className="adm-seg" role="group" aria-label="Период">
              {[
                ["1d", "Сутки"],
                ["7d", "7 дней"],
                ["30d", "30 дней"],
                ["90d", "90 дней"],
                ["all", "Всё время"],
              ].map(([k, l]) => (
                <Button key={k} variant="ghost" size="sm" aria-pressed={period === k} onClick={() => setPeriod(k)}>
                  {l}
                </Button>
              ))}
            </div>
          </div>
          {!pack.current ? (
            <Empty title="Нет данных воронки" />
          ) : (
            <>
              <FunnelTable cur={cur} open={clients} />
              <Panel title="Откуда пришли" description="Доля от всех новых за период.">
                {funnel(sources)}
              </Panel>
            </>
          )}
        </Content>
        <Content value="retention" className="space-y-5">
          <Panel
            title="Результаты автоматических сообщений"
            description="Результаты по сценариям за 30 дней. Действия и оплаты относятся к последнему нажатию за 7 дней. Сумма — начисления за оплаты; это связь по времени, а не доказанный эффект сообщений."
          >
            <DataTable
              rows={s.reminder_results?.groups || []}
              columns={[
                {
                  key: "kind",
                  label: "Сообщение",
                  cell: (r) => messageKinds[r.kind] || r.kind,
                },
                { key: "sent", label: "Отправлено" },
                { key: "failed", label: "Ошибок" },
                { key: "recipients", label: "Получатели" },
                { key: "clicked", label: "Нажали" },
                { key: "opened", label: "Открыли кабинет" },
                { key: "devices", label: "Добавили устройство" },
                { key: "connected", label: "Подключились" },
                { key: "first_paid", label: "Первая оплата" },
                { key: "paid", label: "Всего оплативших" },
                { key: "paid_rub", label: "Начислено за оплаты, ₽", cell: (r) => money(r.paid_rub || 0) },
              ]}
            />
          </Panel>
        </Content>
        <Content value="system">
          <Panel
            title="Фоновые задачи"
            description="Последние отчёты тарификации и синхронизации VPN."
          >
            <DataTable
              rows={Object.entries(s.jobs || {}).map(([name, v]) => ({
                name,
                ...(v as Data),
              }))}
              columns={[
                {
                  key: "name",
                  label: "Задача",
                  cell: (r) =>
                    r.name === "billing" ? "Тарификация" : "Синхронизация VPN",
                },
                {
                  key: "finished_at",
                  label: "Последний запуск",
                  cell: (r) => date(r.finished_at || r.updated_at || r.at),
                },
                {
                  key: "message",
                  label: "Результат",
                  cell: (r) => r.message || r.error || r.status || "—",
                },
              ]}
            />
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => navigate("settings?section=system")}
            >
              Управление системой
              <ArrowRight />
            </Button>
          </Panel>
        </Content>
      </Tabs>
    </div>
  );
}

/** Where people stall after each step: the leak group that ends at that step. */
const LOSS: Record<string, string> = {
  trial: "no_gift",
  device: "gift_no_online",
  connected: "device_no_online",
  checkout: "online_no_paid",
  paid: "checkout_drop",
  repeat_paid: "paid_no_repeat",
};
const LEAK_LABEL = Object.fromEntries(leaks);

/** One funnel instead of four panels: each step, its share of everyone who started, the step-to-step
 *  conversion and how many got stuck right before it. The biggest drop is called out on top. */
function FunnelTable({ cur, open }: { cur: Data; open: (step: string) => void }) {
  const start = Number(cur.entered || 0);
  const rows = main.map(([key, label], i) => {
    const count = Number(cur[key] || 0);
    const prev = i ? Number(cur[main[i - 1][0]] || 0) : count;
    const passed = i ? Number(cur[key + "_transition"] ?? count) : count;
    const conv = prev ? Math.min(100, Math.round((passed / prev) * 100)) : 0;
    const leak = LOSS[key];
    return {
      key, label, count, conv, first: !i,
      share: start ? Math.round((count / start) * 100) : 0,
      stuck: leak ? Number(cur[leak] || 0) : 0,
      waiting: leak ? Number(cur["progress_" + leak] || 0) : 0,
      leak,
    };
  });
  const paid = rows.find((r) => r.key === "paid")!;
  const worst = rows.filter((r) => !r.first && r.key !== "repeat_paid").sort((a, b) => a.conv - b.conv)[0];
  const num = (n: number) => n.toLocaleString("ru-RU");
  return (
    <div className="space-y-4">
      <div className="adm-funnel-sum">
        <div>
          <small>Новых</small>
          <b>{num(start)}</b>
        </div>
        <div>
          <small>Оплатили</small>
          <b>{num(paid.count)}</b>
          <span>{paid.share}% от новых</span>
        </div>
        {worst && (
          <div className="adm-funnel-worst">
            <small>Больше всего теряем</small>
            <b>{worst.label}</b>
            <span>
              доходят {worst.conv}% · не дошли {num(Math.max(0, rows[rows.indexOf(worst) - 1].count - worst.count))}
            </span>
          </div>
        )}
      </div>
      <div className="relative w-full overflow-auto">
        <table className="w-full text-sm adm-funnel">
          <thead>
            <tr>
              <th className="text-left px-3">Этап</th>
              <th className="text-right px-3">Людей</th>
              <th className="text-left px-3 w-[38%]">Доля от новых</th>
              <th className="text-right px-3">Перешли с прошлого шага</th>
              <th className="text-left px-3">Застряли перед этапом</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className={r === worst ? "worst" : undefined}>
                <td className="px-3">{r.label}</td>
                <td className="px-3 text-right">
                  <button type="button" className="adm-link" onClick={() => open(r.key)}>
                    {num(r.count)}
                  </button>
                </td>
                <td className="px-3">
                  <div className="flex items-center gap-3">
                    <div className="adm-funnel-bar"><i style={{ width: `${Math.max(r.share, r.count ? 1 : 0)}%` }} /></div>
                    <span className="w-10 text-right tabular-nums">{r.share}%</span>
                  </div>
                </td>
                <td className="px-3 text-right tabular-nums">{r.first ? "—" : `${r.conv}%`}</td>
                <td className="px-3">
                  {r.leak && r.stuck > 0 ? (
                    <button type="button" className="adm-link text-destructive" onClick={() => open(r.leak!)} title={LEAK_LABEL[r.leak]}>
                      {num(r.stuck)}
                    </button>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                  {r.waiting > 0 && (
                    <span className="text-muted-foreground"> · ещё в пути {num(r.waiting)}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {Number(cur.paid_empty || 0) > 0 && (
        <p className="text-sm text-muted-foreground px-3">
          Платили, но деньги кончились:{" "}
          <button type="button" className="adm-link text-destructive" onClick={() => open("paid_empty")}>
            {num(Number(cur.paid_empty))}
          </button>
        </p>
      )}
    </div>
  );
}
