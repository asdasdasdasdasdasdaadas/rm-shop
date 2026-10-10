import { useEffect, useState } from "react";
import { api, useResource, money, date, type Data } from "@/lib/api";
import {
  Panel,
  Field,
  DataTable,
  Pager,
  ActionButton,
  Loading,
  Failure,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";
const labels: Data = {
  pending: "На рассмотрении",
  approved: "Активен",
  rejected: "Отклонено",
  suspended: "Приостановлен",
  earned: "Начислено",
  skipped: "Без начисления",
  revoked: "Отменено",
  paid: "Выплачено",
};
const actions: Data = {
  approve: "Одобрить",
  reject: "Отклонить заявку",
  suspend: "Приостановить участие",
  risk_hold: "Приостановить выплаты",
  risk_release: "Снять проверку",
  pay: "Подтвердить перевод",
  reject_payout: "Отклонить выплату",
  revoke: "Учесть возврат",
  application: "Подана заявка",
  settings: "Изменены настройки",
  payout_requested: "Запрошена выплата",
};
const cash = (v: any) => money(Number(v || 0) / 100);
function Status({ value }: { value: string }) {
  return (
    <Badge
      variant="outline"
      className={
        ["approved", "earned", "paid"].includes(value)
          ? "text-emerald-600 border-emerald-500/30"
          : ["rejected", "revoked", "suspended"].includes(value)
            ? "text-red-500 border-red-500/30"
            : "text-amber-600 border-amber-500/30"
      }
    >
      {labels[value] || value}
    </Badge>
  );
}
export function AmbassadorsPage() {
  const [tab, setTab] = useState("members"),
    [page, setPage] = useState(1),
    [filter, setFilter] = useState(""),
    [uid, setUid] = useState(""),
    [statusFilter, setStatusFilter] = useState("");
  const { data, error, reload } = useResource(
    `ambassadors?page=${page}&section=${tab}&status=${statusFilter}${uid ? `&uid=${uid}` : ""}`,
  );
  const [draft, setDraft] = useState<Data>({}),
    [operation, setOperation] = useState<Data | null>(null),
    [note, setNote] = useState("");
  useEffect(() => {
    if (data) setDraft(data.settings);
  }, [data?.settings]);
  const choose = (action: string, row: Data) => {
    setOperation({
      action,
      telegram_id: row.telegram_id || row.ambassador_id,
      amount_cents: row.amount_cents,
      details: row.details,
      id: row.id,
      payment_key: row.payment_key,
    });
    setNote("");
  };
  if (error) return <Failure message={error} retry={reload} />;
  if (!data) return <Loading />;
  const s = data.summary;
  const memberColumns = [
    {
      key: "telegram_id",
      label: "Участник",
      cell: (r: Data) => (
        <Button
          variant="link"
          onClick={() => {
            setUid(String(r.telegram_id));
            setFilter(String(r.telegram_id));
            setPage(1);
          }}
        >
          {r.telegram_id}
        </Button>
      ),
    },
    {
      key: "application",
      label: "Где будет привлекать",
      className: "max-w-80 whitespace-normal",
    },
    {
      key: "status",
      label: "Статус",
      cell: (r: Data) => (
        <div className="space-y-1">
          <Status value={r.status} />
          {r.risk_hold && (
            <Badge variant="destructive">Выплаты на проверке</Badge>
          )}
        </div>
      ),
    },
    {
      key: "created_at",
      label: "Заявка",
      cell: (r: Data) => date(r.created_at),
    },
    {
      key: "actions",
      label: "Решение",
      cell: (r: Data) => (
        <div className="flex flex-wrap gap-2">
          {(["pending", "suspended"].includes(r.status) ? ["approve"] : [])
            .concat(
              r.status === "pending"
                ? ["reject"]
                : r.status === "approved"
                  ? ["suspend"]
                  : [],
              ["risk_" + (r.risk_hold ? "release" : "hold")],
            )
            .map((a) => (
              <Button
                key={a}
                variant="outline"
                size="sm"
                onClick={() => choose(a, r)}
              >
                {actions[a]}
              </Button>
            ))}
        </div>
      ),
    },
  ];
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          ["Заявок ждут решения", s.applications],
          ["Активных участников", s.active],
          ["Привели / оплатили", `${s.clients} / ${s.payers}`],
          [
            "Бюджет использован",
            `${cash(s.budget_used)} / ${money(data.settings.budget)}`,
          ],
          ["Уже выплачено", cash(s.paid)],
          ["Ожидают выплаты", cash(s.pending)],
        ].map(([label, value]) => (
          <Panel key={String(label)} title={String(label)}>
            <p className="text-2xl font-semibold">{value}</p>
          </Panel>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">
        Начисления {data.settings.accruing ? "включены" : "на паузе"} · Набор{" "}
        {data.settings.recruitment ? "открыт" : "закрыт"}. Вознаграждения
        отдельно от VPN-баланса. Возвраты учитываются вручную во вкладке
        «Начисления».
      </p>
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!filter || /^\d+$/.test(filter)) {
            setUid(filter);
            setPage(1);
          } else toast.error("Введите Telegram ID");
        }}
      >
        <Input
          className="max-w-xs"
          aria-label="Telegram ID амбассадора"
          placeholder="Telegram ID амбассадора"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <Button variant="outline">Показать участника</Button>
        {uid && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setUid("");
              setFilter("");
              setPage(1);
            }}
          >
            Все участники
          </Button>
        )}
        <Button type="button" variant="ghost" onClick={reload}>
          Обновить
        </Button>
      </form>
      {data.detail && (
        <Panel
          title={`Участник ${uid}`}
          description={
            data.detail.member?.review_note ||
            "История привлечения и баланс вознаграждений"
          }
        >
          <div className="flex flex-wrap gap-6 text-sm">
            <span>
              Доступно: <b>{cash(data.detail.wallet.available)}</b>
            </span>
            <span>
              Ожидают: <b>{cash(data.detail.wallet.holding)}</b>
            </span>
            <span>
              В резерве: <b>{cash(data.detail.wallet.pending)}</b>
            </span>
            <span>
              Пришли / подключились / оплатили / повторно:{" "}
              <b>{Object.values(data.detail.stats).join(" / ")}</b>
            </span>
          </div>
        </Panel>
      )}
      <Tabs
        value={tab}
        onValueChange={(v) => {
          setTab(v);
          setStatusFilter("");
          setPage(1);
        }}
      >
        <TabsList className="h-auto flex flex-wrap justify-start">
          {[
            ["members", "Участники"],
            ["awards", "Начисления"],
            ["payouts", "Выплаты"],
            ...(uid ? [["clients", "Клиенты участника"]] : []),
            ["settings", "Условия и запуск"],
            ["audit", "История действий"],
          ].map(([v, l]) => (
            <TabsTrigger value={v} key={v}>
              {l}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      {["members", "awards", "payouts"].includes(tab) && (
        <div className="max-w-xs">
          <Field label="Статус">
            <Select
              value={statusFilter || "all"}
              onValueChange={(value) => {
                setStatusFilter(value === "all" ? "" : value);
                setPage(1);
              }}
            >
              <SelectTrigger aria-label="Статус">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                {(tab === "members"
                  ? ["pending", "approved", "rejected", "suspended"]
                  : tab === "awards"
                    ? ["earned", "skipped", "revoked"]
                    : ["pending", "paid", "rejected"]
                ).map((value) => (
                  <SelectItem key={value} value={value}>
                    {labels[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>
      )}
      {data.settings.accruing &&
        Number(s.budget_used) >= Number(data.settings.budget) * 100 && (
          <p role="status" className="text-sm text-destructive">
            Бюджет исчерпан. Новые награды не начисляются — увеличьте бюджет или
            приостановите программу.
          </p>
        )}
      {tab === "settings" ? (
        <Panel
          title="Условия программы"
          description="Сначала задайте бюджет, затем включите набор и начисления. Изменения применяются только к новым платежам. Во время паузы бонусы не копятся задним числом."
        >
          <div className="grid sm:grid-cols-2 gap-5">
            {["recruitment", "accruing"].map((k) => (
              <Field
                key={k}
                label={
                  k === "recruitment"
                    ? "Принимать заявки"
                    : "Начислять вознаграждения"
                }
              >
                <Switch
                  checked={!!draft[k]}
                  onCheckedChange={(v) => setDraft({ ...draft, [k]: v })}
                />
              </Field>
            ))}
            {[
              ["first_percent", "Первая оплата, %"],
              ["first_cap", "Максимум за первую оплату, ₽"],
              ["recurring_percent", "Повторные оплаты, %"],
              ["hold_days", "Ожидание перед выводом, дней"],
              ["payout_min", "Минимальная выплата, ₽"],
              ["budget", "Общий бюджет, ₽"],
              ["member_cap", "Лимит на участника, ₽ (0 — без лимита)"],
              ["max_members", "Максимум активных участников"],
            ].map(([k, l]) => (
              <Field key={k} label={l}>
                <Input
                  type="number"
                  min="0"
                  step="1"
                  value={draft[k] ?? ""}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      [k]: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                />
              </Field>
            ))}
          </div>
          <p className="text-sm text-muted-foreground my-4">
            Учитываются пополнения в рублях. Stars не участвуют. Бюджет
            включает отменённые начисления и не
            восстанавливается после возврата. Если следующая награда превышает
            остаток бюджета или лимит участника, она целиком пропускается.
          </p>
          <ActionButton
            onAction={async () => {
              await api("ambassadors", { ...draft, action: "settings" });
              toast.success("Условия сохранены");
              await reload();
            }}
          >
            Сохранить условия
          </ActionButton>
        </Panel>
      ) : (
        <>
          <DataTable
            rows={data[tab] || []}
            columns={
              tab === "members"
                ? memberColumns
                : tab === "awards"
                  ? [
                      {
                        key: "created_at",
                        label: "Дата",
                        cell: (r) => date(r.created_at),
                      },
                      { key: "ambassador_id", label: "Амбассадор" },
                      { key: "client_id", label: "Клиент" },
                      { key: "payment_key", label: "Платёж" },
                      {
                        key: "payment_rub",
                        label: "Оплата",
                        cell: (r) => money(r.payment_rub),
                      },
                      {
                        key: "amount_cents",
                        label: "Вознаграждение",
                        cell: (r) => cash(r.amount_cents),
                      },
                      {
                        key: "status",
                        label: "Статус",
                        cell: (r) => <Status value={r.status} />,
                      },
                      {
                        key: "available_at",
                        label: "Доступно с · МСК",
                        cell: (r) =>
                          r.status === "earned" ? date(r.available_at) : "—",
                      },
                      {
                        key: "reason",
                        label: "Причина",
                        className: "max-w-64 whitespace-normal",
                      },
                      {
                        key: "actions",
                        label: "Действие",
                        cell: (r) =>
                          r.status === "earned" && (
                            <Button
                              variant="outline"
                              onClick={() => choose("revoke", r)}
                            >
                              Учесть возврат
                            </Button>
                          ),
                      },
                    ]
                  : tab === "payouts"
                    ? [
                        { key: "id", label: "№" },
                        { key: "ambassador_id", label: "Амбассадор" },
                        {
                          key: "amount_cents",
                          label: "Сумма",
                          cell: (r) => cash(r.amount_cents),
                        },
                        {
                          key: "details",
                          label: "Реквизиты",
                          className: "max-w-80 whitespace-normal",
                        },
                        {
                          key: "status",
                          label: "Статус",
                          cell: (r) => <Status value={r.status} />,
                        },
                        {
                          key: "created_at",
                          label: "Заявка · МСК",
                          cell: (r) => date(r.created_at),
                        },
                        {
                          key: "note",
                          label: "Комментарий",
                          className: "max-w-64 whitespace-normal",
                        },
                        {
                          key: "actions",
                          label: "Решение",
                          cell: (r) =>
                            r.status === "pending" && (
                              <div className="flex gap-2">
                                <Button onClick={() => choose("pay", r)}>
                                  Перевод выполнен
                                </Button>
                                <Button
                                  variant="outline"
                                  onClick={() => choose("reject_payout", r)}
                                >
                                  Отклонить
                                </Button>
                              </div>
                            ),
                        },
                      ]
                    : tab === "clients"
                      ? [
                          { key: "telegram_id", label: "Клиент" },
                          { key: "first_name", label: "Имя" },
                          {
                            key: "created_at",
                            label: "Пришёл · МСК",
                            cell: (r) => date(r.created_at),
                          },
                          {
                            key: "first_online_at",
                            label: "Первое подключение",
                            cell: (r) => date(r.first_online_at),
                          },
                          { key: "payments", label: "Оплат с начислением" },
                        ]
                      : [
                          {
                            key: "created_at",
                            label: "Дата · МСК",
                            cell: (r) => date(r.created_at),
                          },
                          {
                            key: "action",
                            label: "Действие",
                            cell: (r) => actions[r.action] || r.action,
                          },
                          { key: "target", label: "Объект" },
                          {
                            key: "details",
                            label: "Подробности",
                            className: "max-w-xl whitespace-normal break-words",
                            cell: (r) =>
                              typeof r.details === "string"
                                ? r.details
                                : JSON.stringify(r.details),
                          },
                        ]
            }
          />
          <Pager
            page={page}
            total={data[tab + "_total"] || 0}
            onChange={setPage}
          />
        </>
      )}
      <Dialog
        open={!!operation}
        onOpenChange={(v) => {
          if (!v) setOperation(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{actions[operation?.action || ""]}</DialogTitle>
            <DialogDescription>
              {operation?.action === "pay"
                ? "Сначала выполните перевод вручную по реквизитам. Эта кнопка только отмечает выплату и уведомляет участника."
                : operation?.action === "revoke"
                  ? "Отмените награду только после подтверждённого возврата. Платёж клиенту это действие не возвращает."
                  : "Результат будет сохранён в истории. Участник получит уведомление, комментарий увидит в кабинете."}
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm">
            Участник: <b>{operation?.telegram_id}</b>
            {operation?.amount_cents != null && (
              <>
                {" "}
                · Сумма: <b>{cash(operation.amount_cents)}</b>
              </>
            )}
          </p>
          {operation?.details && (
            <p className="text-sm break-words">{operation.details}</p>
          )}
          <Field label="Комментарий или подтверждение перевода">
            <Textarea
              maxLength={1000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
          <ActionButton
            onAction={async () => {
              await api("ambassadors", { ...operation, note });
              setOperation(null);
              toast.success("Сохранено");
              await reload();
            }}
          >
            Подтвердить
          </ActionButton>
        </DialogContent>
      </Dialog>
    </div>
  );
}
