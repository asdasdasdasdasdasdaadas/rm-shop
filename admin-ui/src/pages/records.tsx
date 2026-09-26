import { useEffect, useState } from "react";
import { api, date, money, qs, useResource, who, type Data } from "@/lib/api";
import {
  ActionButton,
  Choice,
  DataTable,
  Empty,
  Failure,
  Field,
  Loading,
  Pager,
  Panel,
  Status,
  useConfirm,
  useNavigate,
  type Column,
  useDirty,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { toast } from "sonner";
import { Download, Plus, RefreshCw } from "lucide-react";
export const billKinds: Data = {
  charge: "Списание",
  disable: "Отключение",
  pause: "Пауза",
  admin_pause: "Остановка списаний",
  admin_resume: "Возобновление списаний",
  revive: "Включение",
  trial: "Пробный период",
  admin_balance: "Изменение баланса",
  admin_grant: "Начисление",
  referral: "Реферальная награда",
  referral_payout: "Вывод награды",
  referral_revoke: "Возврат награды",
  trust: "Обещанный платёж",
  trust_collect: "Возврат обещанного платежа",
  device_delete: "Удаление устройства",
  error: "Ошибка",
};
export const messageKinds: Data = {
  broadcast: "Рассылка",
  admin_dm: "Сообщение администратора",
  nudge_trial: "Пробный доступ",
  nudge_invite: "Приглашение друзей",
  nudge_info: "Информация о сервисе",
  nudge_idle: "Возврат пользователя",
  nudge_device: "Подключение устройства",
  nudge_legal: "Документы",
  nudge_first_online: "После подключения",
  nudge_trial_end: "Мало баланса",
  nudge_payment: "Неоплаченный счёт",
  welcome_intro: "Приветствие",
  first_device_thanks: "Первое устройство",
  cabinet_link: "Вход в кабинет",
  low_balance: "Баланс закончился",
  maintenance_hit: "Обращение при техработах",
  maintenance_out: "Ответ при техработах",
};
const statuses: Record<string, [string, string][]> = {
  orders: [
    ["", "Все статусы"],
    ["granted", "Оплачено"],
    ["pending", "Ожидает оплаты"],
    ["created", "Создан"],
    ["expired", "Истёк"],
  ],
  tickets: [
    ["", "Все обращения"],
    ["open", "Ждут ответа"],
    ["pending", "Ответ отправлен"],
    ["closed", "Закрыты"],
  ],
  payouts: [
    ["", "Все заявки"],
    ["pending", "Ждут выплаты"],
    ["paid", "Выплачены"],
    ["rejected", "Отклонены"],
  ],
};
export function RecordsPage({
  kind,
}: {
  kind: "orders" | "billing" | "messages" | "tickets" | "referrals" | "payouts";
}) {
  const navigate = useNavigate(),
    confirm = useConfirm();
  const [f, setF] = useState<Data>(
      Object.fromEntries(
        new URLSearchParams(location.hash.split("?")[1] || ""),
      ),
    ),
    [page, setPage] = useState(1),
    [selected, setSelected] = useState<Data | null>(null),
    [ticketDirty, setTicketDirty] = useState(false),
    [query, setQuery] = useState(f.q || "");
  const resource = useResource(kind + "?" + qs({ ...f, page, limit: 25 }));
  const change = (key: string, value: string) => {
    setF({ ...f, [key]: value });
    setPage(1);
  };
  const client: Column = {
    key: "client",
    label: "Клиент",
    cell: (r) => (
      <Button
        variant="link"
        className="p-0 h-auto"
        onClick={() => navigate("users?q=" + r.telegram_id)}
      >
        {who(r)}
      </Button>
    ),
  };
  const resolve = (r: Data, action: string) =>
    confirm({
      title: action === "paid" ? "Подтвердить выплату?" : "Отклонить заявку?",
      description: `${who(r)} · ${money(r.amount)}\n${r.details || ""}\n${action === "paid" ? "Подтверждайте только после фактического перевода денег." : "Результат будет отправлен пользователю."}`,
      action: async () => {
        await api(`payouts/${r.id}`, { action });
        await resource.reload();
        toast.success("Заявка обработана");
      },
    });
  const columns: Record<string, Column[]> = {
    orders: [
      { key: "order_id", label: "Счёт" },
      client,
      { key: "amount_rub", label: "Сумма", cell: (r) => money(r.amount_rub) },
      { key: "plan_code", label: "Тариф" },
      {
        key: "status",
        label: "Статус",
        cell: (r) => <Status value={r.status} />,
      },
      {
        key: "created_at",
        label: "Создан · МСК",
        cell: (r) => date(r.created_at),
      },
    ],
    billing: [
      {
        key: "created_at",
        label: "Дата · МСК",
        cell: (r) => date(r.created_at),
      },
      client,
      {
        key: "kind",
        label: "Операция",
        cell: (r) => billKinds[r.kind] || r.kind,
      },
      { key: "amount", label: "Сумма", cell: (r) => money(r.amount) },
      {
        key: "balance_after",
        label: "Баланс после",
        cell: (r) => (r.balance_after == null ? "—" : money(r.balance_after)),
      },
      { key: "device_title", label: "Устройство" },
      {
        key: "note",
        label: "Подробности",
        cell: (r) => (
          <span className="text-xs max-w-64 block whitespace-normal">
            {r.note || "—"}
          </span>
        ),
      },
    ],
    messages: [
      {
        key: "created_at",
        label: "Дата · МСК",
        cell: (r) => date(r.created_at),
      },
      client,
      {
        key: "kind",
        label: "Сообщение",
        cell: (r) => messageKinds[r.kind] || r.title || r.kind,
      },
      {
        key: "status",
        label: "Доставка",
        cell: (r) => <Status value={r.status} />,
      },
      {
        key: "source",
        label: "Отправка",
        cell: (r) => (r.source === "auto" ? "Автоматически" : "Вручную"),
      },
      {
        key: "open",
        label: "",
        cell: (r) => (
          <Button variant="outline" size="sm" onClick={() => setSelected(r)}>
            Подробнее
          </Button>
        ),
      },
    ],
    tickets: [
      {
        key: "id",
        label: "Обращение",
        cell: (r) => (
          <Button variant="link" className="p-0" onClick={() => setSelected(r)}>
            №{r.id}
          </Button>
        ),
      },
      client,
      {
        key: "status",
        label: "Статус",
        cell: (r) => <Status value={r.status} />,
      },
      {
        key: "last_body",
        label: "Последнее сообщение",
        cell: (r) => (
          <span className="block max-w-72 truncate">
            {r.last_body || "Вложение"}
          </span>
        ),
      },
      {
        key: "updated",
        label: "Обновлено · МСК",
        cell: (r) => date(r.last_message_at || r.created_at),
      },
      {
        key: "open",
        label: "",
        cell: (r) => (
          <Button variant="outline" size="sm" onClick={() => setSelected(r)}>
            Открыть диалог
          </Button>
        ),
      },
    ],
    referrals: [
      {
        key: "invitee",
        label: "Приглашённый",
        cell: (r) => (
          <Button
            variant="link"
            onClick={() => navigate("users?q=" + r.invitee_id)}
          >
            {r.invitee_name || r.invitee_username || r.invitee_id}
          </Button>
        ),
      },
      {
        key: "referrer",
        label: "Пригласивший",
        cell: (r) => (
          <Button
            variant="link"
            onClick={() => navigate("users?q=" + r.referrer_id)}
          >
            {r.referrer_name || r.referrer_username || r.referrer_id}
          </Button>
        ),
      },
      {
        key: "invitee_at",
        label: "Пришёл · МСК",
        cell: (r) => date(r.invitee_at),
      },
      {
        key: "referral_rewarded",
        label: "Награда",
        cell: (r) => (
          <Status value={r.referral_rewarded ? "Выдана" : "Ещё не выдана"} />
        ),
      },
    ],
    payouts: [
      client,
      { key: "amount", label: "Сумма", cell: (r) => money(r.amount) },
      { key: "details", label: "Реквизиты" },
      {
        key: "status",
        label: "Статус",
        cell: (r) => <Status value={r.status} />,
      },
      {
        key: "created_at",
        label: "Дата · МСК",
        cell: (r) => date(r.created_at),
      },
      {
        key: "action",
        label: "",
        cell: (r) =>
          r.status === "pending" ? (
            <div className="flex gap-2">
              <Button size="sm" onClick={() => resolve(r, "paid")}>
                Выплачено
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => resolve(r, "rejected")}
              >
                Отклонить
              </Button>
            </div>
          ) : null,
      },
    ],
  };
  return (
    <div className="space-y-5">
      <form
        className="flex flex-wrap gap-3 items-end"
        onSubmit={(e) => {
          e.preventDefault();
          change("q", query);
        }}
      >
        <div className="flex-1 min-w-52">
          <Field label="Поиск">
            <Input
              aria-label="Поиск записей"
              placeholder="Telegram ID, имя или username"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </Field>
        </div>
        {statuses[kind] && (
          <div className="w-48">
            <Field label="Статус">
              <Choice
                label="Статус записей"
                value={f.status || ""}
                options={statuses[kind]}
                onChange={(v) => change("status", v)}
              />
            </Field>
          </div>
        )}
        {kind === "billing" && (
          <div className="w-52">
            <Field label="Операция">
              <Choice
                label="Тип операции"
                value={f.kind || ""}
                options={[
                  ["", "Все операции"],
                  ...(Object.entries(billKinds) as [string, string][]),
                ]}
                onChange={(v) => change("kind", v)}
              />
            </Field>
          </div>
        )}
        {kind === "messages" && (
          <div className="w-52">
            <Field label="Тип сообщения">
              <Choice
                label="Тип сообщения"
                value={f.kind || ""}
                options={[
                  ["", "Все сообщения"],
                  ...(Object.entries(messageKinds) as [string, string][]),
                ]}
                onChange={(v) => change("kind", v)}
              />
            </Field>
          </div>
        )}
        {(kind === "billing" || kind === "messages") && (
          <div className="w-48">
            <Field label="Источник">
              <Choice
                label="Источник записи"
                value={f.source || ""}
                onChange={(v) => change("source", v)}
                options={
                  kind === "billing"
                    ? [
                        ["", "Все источники"],
                        ["cron", "Тарификация"],
                        ["admin", "Администратор"],
                        ["user", "Кабинет"],
                        ["signup", "Регистрация"],
                      ]
                    : [
                        ["", "Все отправки"],
                        ["auto", "Автоматически"],
                        ["manual", "Вручную"],
                      ]
                }
              />
            </Field>
          </div>
        )}
        {kind === "messages" && (
          <div className="w-48">
            <Field label="Канал">
              <Choice
                label="Канал сообщений"
                value={f.channel || ""}
                options={[
                  ["", "Все каналы"],
                  ["announce", "Объявления"],
                  ["maint", "Техработы"],
                ]}
                onChange={(v) => change("channel", v)}
              />
            </Field>
          </div>
        )}
        {kind === "referrals" && (
          <div className="w-48">
            <Field label="Награда">
              <Choice
                label="Награда за приглашение"
                value={f.reward || ""}
                options={[
                  ["", "Все приглашения"],
                  ["yes", "Награда выдана"],
                  ["no", "Награда не выдана"],
                ]}
                onChange={(v) => change("reward", v)}
              />
            </Field>
          </div>
        )}
        {kind !== "payouts" &&
          (["from", "to"] as const).map((key, i) => (
            <div key={key} className="w-40">
              <Field label={i ? "По дату" : "С даты"}>
                <Input
                  type="date"
                  aria-label={i ? "По дату" : "С даты"}
                  value={f[key] || ""}
                  onChange={(e) => change(key, e.target.value)}
                />
              </Field>
            </div>
          ))}
        <Button type="submit">Найти</Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setF({});
            setQuery("");
            setPage(1);
          }}
        >
          Сбросить
        </Button>
      </form>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <>
          <DataTable
            rows={resource.data.items || []}
            columns={columns[kind]}
            empty={
              <Empty
                title="Записей пока нет"
                description="Проверьте выбранный период и условия поиска."
              />
            }
          />
          <Pager
            page={page}
            total={resource.data.total || 0}
            onChange={setPage}
          />
        </>
      )}
      {kind === "messages" && (
        <Button
          variant="outline"
          onClick={() =>
            confirm({
              title: "Повторить ошибки по текущим фильтрам?",
              description:
                "Будут повторно отправлены до 80 неуспешных сообщений. Сервер исключит сообщения, для которых повтор запрещён.",
              label: "Повторить отправку",
              action: async () => {
                const r = await api("messages/retry-failed?" + qs(f), {});
                toast.info(
                  `Отправлено: ${r.sent}. Ошибок: ${r.failed}. Проверено: ${r.tried} из ${r.total}.`,
                );
                await resource.reload();
              },
            })
          }
        >
          Повторить ошибки доставки по фильтрам
        </Button>
      )}
      <Sheet
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) {
            if (ticketDirty)
              confirm({
                title: "Закрыть диалог без отправки?",
                description: "Черновик ответа будет потерян.",
                label: "Закрыть без отправки",
                action: async () => setSelected(null),
              });
            else setSelected(null);
          }
        }}
      >
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>
              {kind === "tickets"
                ? "Обращение №" + selected?.id
                : "Отправленное сообщение"}
            </SheetTitle>
            <SheetDescription>
              {selected ? who(selected) : ""} · {date(selected?.created_at)}
            </SheetDescription>
          </SheetHeader>
          {selected &&
            (kind === "tickets" ? (
              <Ticket
                key={selected.id}
                id={selected.id}
                onUpdate={resource.reload}
                onDirty={setTicketDirty}
              />
            ) : (
              <div className="space-y-5 pt-6">
                <Status value={selected.status} />
                <p className="whitespace-pre-wrap text-sm break-words rounded-lg border p-4">
                  {selected.body || selected.title || "Нет текста"}
                </p>
                {selected.extra?.error && (
                  <p className="text-destructive text-sm break-words">
                    {selected.extra.error}
                  </p>
                )}
                {selected.status === "failed" && (
                  <Button
                    variant="outline"
                    onClick={() =>
                      confirm({
                        title: "Повторить отправку?",
                        description:
                          "Сообщение снова отправится этому получателю. Возможность повтора проверит сервер.",
                        label: "Отправить повторно",
                        action: async () => {
                          await api(`messages/${selected.id}/retry`, {});
                          toast.success("Повторная отправка выполнена");
                          await resource.reload();
                          setSelected(null);
                        },
                      })
                    }
                  >
                    Повторить отправку
                  </Button>
                )}
              </div>
            ))}
        </SheetContent>
      </Sheet>
    </div>
  );
}
function Ticket({
  id,
  onUpdate,
  onDirty,
}: {
  id: number;
  onDirty: (dirty: boolean) => void;
  onUpdate: () => Promise<void>;
}) {
  const resource = useResource("tickets/" + id),
    [text, setText] = useState(""),
    [files, setFiles] = useState<File[]>([]);
  const confirm = useConfirm();
  useDirty(!!text.trim() || !!files.length);
  useEffect(() => {
    onDirty(!!text.trim() || !!files.length);
    return () => onDirty(false);
  }, [text, files, onDirty]);
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  return (
    <div className="space-y-4 pt-5">
      <div className="flex justify-between">
        <Status value={resource.data.ticket?.status} />
        <Button
          variant="outline"
          size="sm"
          disabled={resource.data.ticket?.status === "closed"}
          onClick={() =>
            confirm({
              title: "Закрыть обращение?",
              description: "Пользователь получит уведомление о закрытии.",
              label: "Закрыть обращение",
              action: async () => {
                await api("tickets/" + id, { action: "close" });
                await resource.reload();
                await onUpdate();
              },
            })
          }
        >
          Закрыть обращение
        </Button>
      </div>
      <div className="space-y-3">
        {(resource.data.messages || []).map((m: Data, i: number) => (
          <div
            key={m.id || i}
            className={`rounded-xl p-4 ${m.author === "admin" ? "bg-muted ml-5" : "border mr-5"}`}
          >
            <p className="text-xs text-muted-foreground mb-2">
              {m.author === "admin" ? "Поддержка" : "Клиент"} ·{" "}
              {date(m.created_at)}
            </p>
            <p className="text-sm whitespace-pre-wrap break-words">{m.body}</p>
            {(m.attachments || []).map((a: Data) => (
              <a
                key={a.id}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block underline text-sm mt-2"
              >
                {a.original_name || "Открыть вложение"}
              </a>
            ))}
          </div>
        ))}
      </div>
      <Field
        label="Ответ клиенту"
        hint="Ответ появится в Telegram и личном кабинете."
      >
        <Textarea
          aria-label="Ответ клиенту"
          rows={5}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </Field>
      <Input
        type="file"
        multiple
        aria-label="Вложения к ответу"
        onChange={(e) => setFiles(Array.from(e.target.files || []))}
      />
      <ActionButton
        disabled={!text.trim() && !files.length}
        onAction={async () => {
          const form = new FormData();
          form.append("text", text);
          files.forEach((f) => form.append("file", f));
          const r = await api("tickets/" + id, form);
          resource.setData(r);
          setText("");
          setFiles([]);
          await onUpdate();
          toast.success("Ответ отправлен");
        }}
      >
        Отправить ответ
      </ActionButton>
    </div>
  );
}
export function BackupsPage() {
  const resource = useResource("backups"),
    [file, setFile] = useState<File | null>(null);
  const confirm = useConfirm();
  const restore = (name: string, body: Data | FormData) =>
    confirm({
      title: "Восстановить базу данных?",
      description: `Источник: ${name}.\nТекущие данные будут заменены содержимым резервной копии. Изменения после даты копии будут потеряны.`,
      danger: true,
      phrase: "ВОССТАНОВИТЬ",
      label: "Восстановить базу",
      action: async () => {
        await api("backups/restore", body);
        toast.success("База восстановлена");
        await resource.reload();
      },
    });
  return (
    <div className="space-y-5">
      <Panel
        title="Резервные копии"
        description={
          resource.data
            ? `Автоматическое создание — ежедневно в 00:01 МСК. Срок хранения: ${resource.data.keep_days} дней.`
            : undefined
        }
        action={
          <ActionButton
            onAction={async () => {
              await api("backups", {});
              await resource.reload();
              toast.success("Копия создана");
            }}
          >
            <Plus />
            Создать копию
          </ActionButton>
        }
      >
        {resource.error ? (
          <Failure message={resource.error} retry={resource.reload} />
        ) : !resource.data ? (
          <Loading />
        ) : (
          <DataTable
            rows={resource.data.items || []}
            columns={[
              { key: "name", label: "Файл" },
              {
                key: "created_at",
                label: "Создан · МСК",
                cell: (r) => date(r.created_at),
              },
              {
                key: "size",
                label: "Размер",
                cell: (r) => (Number(r.size) / 1048576).toFixed(2) + " МБ",
              },
              {
                key: "actions",
                label: "",
                cell: (r) => (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={
                          "/admin/api/backups/" + encodeURIComponent(r.name)
                        }
                      >
                        <Download />
                        Скачать
                      </a>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => restore(r.name, { name: r.name })}
                    >
                      Восстановить
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        )}
      </Panel>
      <Panel
        title="Восстановление из файла"
        description="Используйте SQL или SQL.GZ, не больше 80 МБ."
      >
        <div className="flex flex-wrap gap-3">
          <Input
            className="max-w-md"
            type="file"
            aria-label="Файл резервной копии"
            accept=".sql,.gz"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <Button
            variant="outline"
            disabled={!file || file.size > 80 * 1024 * 1024}
            onClick={() => {
              if (file) {
                const body = new FormData();
                body.append("file", file);
                restore(file.name, body);
              }
            }}
          >
            Восстановить из файла
          </Button>
        </div>
        {file && file.size > 80 * 1024 * 1024 && (
          <p role="alert" className="text-destructive">
            Файл превышает 80 МБ
          </p>
        )}
      </Panel>
    </div>
  );
}
