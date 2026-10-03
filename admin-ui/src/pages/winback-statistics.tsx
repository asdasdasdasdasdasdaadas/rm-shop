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
import { Badge } from "@/components/ui/badge";
import {
  Choice,
  DataTable,
  Failure,
  Loading,
  Panel,
  Pager,
  useNavigate,
} from "@/components/workspace";
import { date, money, useResource, who } from "@/lib/api";

const stages = {
  sent: { label: "Отправлено", color: "#64748b" },
  activated: { label: "Активировано", color: "#3b82f6" },
  connected: { label: "Вышли онлайн", color: "#14b8a6" },
  paid: { label: "Оплатили", color: "#a855f7" },
};
const statuses: Record<string, [string, string]> = {
  activated: [
    "Активирован",
    "text-emerald-700 dark:text-emerald-400 bg-emerald-500/10",
  ],
  available: [
    "Ждёт активации",
    "text-blue-700 dark:text-blue-400 bg-blue-500/10",
  ],
  expired: ["Срок истёк", "text-amber-800 dark:text-amber-400 bg-amber-500/10"],
  pending: [
    "Ожидает отправки",
    "text-amber-800 dark:text-amber-400 bg-amber-500/10",
  ],
  cancelled: ["Отменён", "text-muted-foreground bg-muted"],
};
export function WinbackStatistics() {
  const [days, setDays] = useState("30"),
    [page, setPage] = useState(1);
  const resource = useResource(`statistics/winback?days=${days}&page=${page}`);
  const navigate = useNavigate(),
    s = resource.data?.summary;
  return (
    <Panel
      title="Возвращение с подарком на 5 дней"
      description="Личные промокоды: от отправки до подключения и оплаты. Период выбирает предложения по дате отправки, очередь — по дате создания. Даты по Москве."
    >
      <div className="flex gap-2 mb-5">
        <Choice
          label="Период подарков"
          value={days}
          onChange={(v) => {
            setDays(v);
            setPage(1);
          }}
          options={[
            ["7", "7 дней"],
            ["30", "30 дней"],
            ["90", "90 дней"],
            ["365", "Год"],
          ]}
        />
        <Button variant="outline" onClick={() => void resource.reload()}>
          Обновить
        </Button>
      </div>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !s ? (
        <Loading />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Object.entries(stages).map(([key, stage]) => (
              <div key={key} className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">{stage.label}</p>
                <p className="text-2xl font-semibold mt-1">{s[key]}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {key === "sent"
                    ? `${s.recipients} получателей`
                    : key === "activated"
                      ? `${s.sent ? Math.round((s.activated / s.sent) * 100) : 0}% от отправленных`
                      : `${s.activated ? Math.round((s[key] / s.activated) * 100) : 0}% от активаций · за 7 дней`}
                </p>
              </div>
            ))}
          </div>
          <p className="text-sm text-muted-foreground my-4">
            В очереди: {s.pending} · Ждут активации: {s.available} · Истекли без
            активации: {s.expired}. Наблюдение завершено для {s.mature}{" "}
            активаций, ещё наблюдаем {s.observing}. Конверсии предварительные,
            пока не завершились 7 дней.
          </p>
          <div className="grid gap-4 sm:grid-cols-3 my-5">
            {[
              ["Начислено подарками", money(s.gift_rub)],
              ["Погашено минуса", money(s.debt_rub)],
              ["Зачислено успешными оплатами", money(s.paid_credit_rub)],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="text-xl font-semibold">{value}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mb-5">
            Оплаты — успешные пополнения в течение 7 дней после активации; сумма
            показывает зачисленные рубли, включая эквивалент Stars, а не
            денежную выручку. Это события после подарка, а не доказанный эффект
            акции. Повторные предложения одному человеку считаются отдельно.
            Удалённые пользователи исключены. Исторический онлайн доступен
            только по сохранившимся данным.
            {s.unknown_debt > 0 &&
              ` Для ${s.unknown_debt} старых активаций сумма погашенного минуса неизвестна.`}
          </p>
          {resource.data?.series?.length ? (
            <ChartContainer
              config={stages}
              className="h-64 w-full aspect-auto mb-5"
            >
              <BarChart accessibilityLayer data={resource.data.series}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="day"
                  tickFormatter={(v) => String(v).slice(5)}
                />
                <YAxis allowDecimals={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                {Object.keys(stages).map((key) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    fill={`var(--color-${key})`}
                    radius={[3, 3, 0, 0]}
                  />
                ))}
              </BarChart>
            </ChartContainer>
          ) : (
            <p className="text-sm py-6 text-muted-foreground">
              В этом периоде предложения ещё не создавались.
            </p>
          )}
          <p className="text-xs text-muted-foreground mb-3">
            График группирует все результаты по дню отправки предложения.
          </p>
          <DataTable
            rows={resource.data?.items || []}
            empty="Предложений за выбранный период нет"
            columns={[
              {
                key: "telegram_id",
                label: "Получатель",
                cell: (r) => (
                  <Button
                    variant="link"
                    className="px-0"
                    onClick={() => navigate("users?q=" + r.telegram_id)}
                  >
                    {who(r)}
                  </Button>
                ),
              },
              { key: "code", label: "Промокод" },
              {
                key: "sent_at",
                label: "Отправлен · МСК",
                cell: (r) => date(r.sent_at),
              },
              {
                key: "state",
                label: "Статус",
                cell: (r) => (
                  <Badge variant="outline" className={statuses[r.state]?.[1]}>
                    {statuses[r.state]?.[0]}
                  </Badge>
                ),
              },
              {
                key: "activated_at",
                label: "Активирован",
                cell: (r) => date(r.activated_at),
              },
              {
                key: "connected_at",
                label: "Онлайн после подарка",
                cell: (r) => date(r.connected_at),
              },
              {
                key: "gift_rub",
                label: "Подарок",
                cell: (r) => (
                  <span>
                    {money(r.gift_rub)} · {r.device_count} устр.
                  </span>
                ),
              },
              {
                key: "debt_repaid_rub",
                label: "Погашен минус",
                cell: (r) =>
                  r.debt_repaid_rub == null ? "—" : money(r.debt_repaid_rub),
              },
              {
                key: "payments",
                label: "Оплаты за 7 дней",
                cell: (r) => (
                  <span>
                    {r.payments} · {money(r.paid_credit_rub)}
                  </span>
                ),
              },
            ]}
          />
          <Pager
            page={page}
            total={resource.data?.total || 0}
            limit={25}
            onChange={setPage}
          />
        </>
      )}
    </Panel>
  );
}
