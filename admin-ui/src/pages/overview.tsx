import { useState } from "react";
import { date, money, qs, useResource, type Data } from "@/lib/api";
import {
  Choice,
  DataTable,
  Empty,
  Failure,
  Loading,
  Panel,
  useNavigate,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { ArrowRight, ArrowUpRight, RefreshCw, CircleCheck } from "lucide-react";
import { messageKinds } from "./records";
import { funnelRoute } from "@/lib/contracts.mjs";
const main = [
  ["entered", "Запустили бота"],
  ["trial", "Забрали подарок"],
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
export function OverviewPage() {
  const resource = useResource("stats"),
    navigate = useNavigate();
  const [period, setPeriod] = useState("30d");
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  const s = resource.data,
    u = s.users || {},
    pack = s.funnel?.[period] || {},
    cur = pack.current || {};
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
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          [
            "Пользователи",
            u.users_total || 0,
            "Всего зарегистрировано",
            "users",
          ],
          [
            "Онлайн за сутки",
            s.online?.day || 0,
            "Пользовались VPN за 24 часа",
            "users?online=1d",
          ],
          [
            "Сумма пополнений",
            money(s.topups?.amount_rub || s.revenue_rub),
            "За всё время",
            "orders?status=granted",
          ],
          [
            "Оплатившие клиенты",
            s.topups?.payers || 0,
            "Хотя бы одно пополнение",
            "users?paid=yes",
          ],
        ].map(([label, value, hint, path]) => (
          <Card key={String(label)}>
            <CardContent className="pt-5">
              <button
                className="w-full text-left"
                onClick={() => navigate(String(path))}
              >
                <div className="flex justify-between text-muted-foreground">
                  <span className="text-sm">{label}</span>
                  <ArrowUpRight className="size-4" />
                </div>
                <p className="text-3xl font-semibold tracking-tight my-3">
                  {value}
                </p>
                <p className="text-xs text-muted-foreground">{hint}</p>
              </button>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(300px,1fr)]">
        <Panel
          title="Требуют внимания"
          description="Рабочая очередь администратора."
        >
          <div className="divide-y">
            {[
              [
                "Обращения без ответа",
                s.tickets_open || 0,
                "tickets?status=open",
              ],
              [
                "Заявки на вывод наград",
                u.payouts_pending || 0,
                "referrals?view=payouts",
              ],
              [
                "Заблокировали бота",
                u.bot_blocked || 0,
                "users?status=bot_block",
              ],
            ].map(([label, count, path]) => (
              <button
                key={String(label)}
                className="w-full py-4 flex items-center justify-between gap-3 text-sm hover:text-primary"
                onClick={() => navigate(String(path))}
              >
                <span>{label}</span>
                <span className="flex items-center gap-4 font-medium">
                  {count}
                  <ArrowRight className="size-4" />
                </span>
              </button>
            ))}
          </div>
        </Panel>
        <Panel
          title="Быстрые действия"
          description="Частые задачи без поиска по настройкам."
        >
          <div className="grid gap-3">
            {[
              ["Найти клиента", "users"],
              ["Создать промокод", "promo"],
              ["Подготовить рассылку", "broadcast"],
              ["Запустить акцию", "campaigns"],
            ].map(([label, path]) => (
              <Button
                key={path}
                variant="outline"
                className="justify-between"
                onClick={() => navigate(path)}
              >
                {label}
                <ArrowRight />
              </Button>
            ))}
          </div>
        </Panel>
      </div>
      <Tabs defaultValue="conversion" className="space-y-5">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <TabsList className="max-w-full overflow-x-auto justify-start">
            <TabsTrigger value="conversion">Конверсия</TabsTrigger>
            <TabsTrigger value="retention">Возврат клиентов</TabsTrigger>
            <TabsTrigger value="system">Состояние системы</TabsTrigger>
          </TabsList>
          <Button variant="ghost" onClick={() => void resource.reload()}>
            <RefreshCw />
            Обновить
          </Button>
        </div>
        <TabsContent value="conversion" className="space-y-5">
          <div className="flex flex-wrap justify-between items-center gap-3">
            <div>
              <h2 className="font-semibold">
                Путь от первого запуска до оплаты
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Клиенты, впервые запустившие бота за выбранный период. Нажмите
                на этап, чтобы открыть список.
              </p>
            </div>
            <div className="w-48">
              <Choice
                label="Период когорты"
                value={period}
                options={[
                  ["1d", "За сутки"],
                  ["7d", "За 7 дней"],
                  ["30d", "За 30 дней"],
                  ["90d", "За 90 дней"],
                  ["all", "За всё время"],
                ]}
                onChange={setPeriod}
              />
            </div>
          </div>
          {!pack.current ? (
            <Empty title="Нет данных воронки" />
          ) : (
            <>
              <div className="grid gap-5 xl:grid-cols-2">
                <Panel
                  title="Основная воронка"
                  description="Процент — доля перешедших с предыдущего этапа. Подарок можно пропустить."
                >
                  {funnel(main, true)}
                </Panel>
                <Panel
                  title="Где теряем клиентов"
                  description="Процент от всей когорты. Эти группы могут пересекаться."
                >
                  {funnel(leaks)}
                </Panel>
                <Panel
                  title="Источники клиентов"
                  description="Доля от всей когорты; активация промокода может пересекаться с источниками."
                >
                  {funnel(sources)}
                </Panel>
                <Panel
                  title="Приглашённые друзья"
                  description="Результаты друзей, которых привели пользователи выбранной когорты."
                >
                  {funnel(invites)}
                </Panel>
              </div>
            </>
          )}
        </TabsContent>
        <TabsContent value="retention" className="space-y-5">
          <Panel
            title="Результаты автоматических сообщений"
            description="Клики, подключения и оплаты после сообщений. Оплата в течение 7 дней — связь по времени, а не доказанный эффект рассылки."
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
                { key: "connected", label: "Подключились" },
                { key: "paid", label: "Оплатили" },
              ]}
            />
          </Panel>
          <Panel
            title="Почему уходят"
            description={`Ответили ${s.exit_feedback?.answered || 0} из ${s.exit_feedback?.total || 0} пользователей.`}
          >
            <div className="flex flex-wrap gap-3 mb-5">
              {(s.exit_feedback?.reasons || []).map((r: Data) => (
                <span key={r.key} className="rounded-lg bg-muted p-3 text-sm">
                  {r.label}: <strong>{r.count}</strong>
                </span>
              ))}
            </div>
            <DataTable
              rows={s.exit_feedback?.recent || []}
              columns={[
                {
                  key: "telegram_id",
                  label: "Клиент",
                  cell: (r) => (
                    <Button
                      variant="link"
                      onClick={() => navigate("users?q=" + r.telegram_id)}
                    >
                      {r.username || r.telegram_id}
                    </Button>
                  ),
                },
                {
                  key: "reason",
                  label: "Причина",
                  cell: (r) =>
                    (s.exit_feedback?.reasons || []).find(
                      (x: Data) => x.key === r.reason,
                    )?.label || r.reason,
                },
                {
                  key: "answered_at",
                  label: "Дата · МСК",
                  cell: (r) => date(r.answered_at),
                },
              ]}
            />
          </Panel>
        </TabsContent>
        <TabsContent value="system">
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
        </TabsContent>
      </Tabs>
    </div>
  );
}
