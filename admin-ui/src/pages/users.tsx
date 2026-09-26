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
  useDirty,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Search,
  SlidersHorizontal,
  MoreHorizontal,
  X,
  Copy,
  ArrowDownUp,
} from "lucide-react";
import { toast } from "sonner";
import { billKinds } from "./records";
import { paymentSummary } from "@/lib/contracts.mjs";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
const filters: {
  key: string;
  label: string;
  options?: [string, string][];
  type?: string;
}[] = [
  {
    key: "status",
    label: "Статус",
    options: [
      ["", "Любой статус"],
      ["ok", "Активен"],
      ["block", "Заблокирован в магазине"],
      ["bot_block", "Заблокировал бота"],
    ],
  },
  {
    key: "paid",
    label: "Оплаты",
    options: [
      ["", "Любые оплаты"],
      ["yes", "Пополняли баланс"],
      ["no", "Ещё не оплачивали"],
    ],
  },
  {
    key: "devices",
    label: "Устройства",
    options: [
      ["", "Любое количество"],
      ["yes", "Есть устройства"],
      ["no", "Нет устройств"],
    ],
  },
  {
    key: "trial",
    label: "Пробный период",
    options: [
      ["", "Любой"],
      ["yes", "Использован"],
      ["no", "Не использован"],
    ],
  },
  {
    key: "online",
    label: "Последний онлайн",
    options: [
      ["", "Любой"],
      ["now", "За 15 минут"],
      ["1h", "За час"],
      ["1d", "За сутки"],
      ["7d", "За неделю"],
      ["30d", "За месяц"],
      ["inactive_1d", "Не заходили сутки"],
      ["inactive_7d", "Не заходили неделю"],
      ["inactive_30d", "Не заходили месяц"],
      ["never", "Ещё не подключались"],
    ],
  },
  {
    key: "bal_sign",
    label: "Баланс",
    options: [
      ["", "Любой баланс"],
      ["pos", "Положительный"],
      ["zero", "Нулевой"],
      ["neg", "Отрицательный"],
    ],
  },
  { key: "bal_min", label: "Баланс от, ₽", type: "number" },
  { key: "bal_max", label: "Баланс до, ₽", type: "number" },
  { key: "traffic_min", label: "Трафик от, ГБ", type: "number" },
  { key: "traffic_max", label: "Трафик до, ГБ", type: "number" },
  { key: "from", label: "Зарегистрировались с", type: "date" },
  { key: "to", label: "Зарегистрировались по", type: "date" },
];
const sort: [string, string][] = [
  ["", "Сначала новые"],
  ["traffic_desc", "Больше трафика"],
  ["traffic_asc", "Меньше трафика"],
  ["online_desc", "Недавно в сети"],
  ["online_asc", "Давно не заходили"],
];
const traffic = (u: Data) =>
  `${(Math.max(Number(u.used_traffic_bytes) || 0, Number(u.lifetime_traffic_bytes) || 0) / 1073741824).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ГБ`;
const identity = (u: Data) => (
  <div>
    <div className="font-medium">{who(u)}</div>
    <div className="text-xs text-muted-foreground">
      {u.username ? "@" + u.username + " · " : ""}
      {u.telegram_id}
    </div>
  </div>
);
export function UsersPage() {
  const navigate = useNavigate(),
    confirm = useConfirm();
  const initial = Object.fromEntries(
    new URLSearchParams(location.hash.split("?")[1] || ""),
  );
  const [values, setValues] = useState<Data>(initial),
    [search, setSearch] = useState(initial.q || ""),
    [page, setPage] = useState(1),
    [drawer, setDrawer] = useState(false),
    [draft, setDraft] = useState<Data>({}),
    [user, setUser] = useState<Data | null>(null),
    [selected, setSelected] = useState<number[]>([]),
    [result, setResult] = useState(""),
    [userDirty, setUserDirty] = useState(false),
    [compose, setCompose] = useState(false),
    [bulkText, setBulkText] = useState("");
  useDirty(compose && !!bulkText);
  const resource = useResource("users?" + qs({ ...values, page, limit: 25 })),
    rows = resource.data?.items || [];
  useEffect(() => {
    if (search === (values.q || "")) return;
    const timer = setTimeout(() => {
      setValues((v) => ({ ...v, q: search }));
      setPage(1);
      setSelected([]);
    }, 350);
    return () => clearTimeout(timer);
  }, [search, values.q]);
  useEffect(() => {
    history.replaceState(
      null,
      "",
      "#users" + (qs(values) ? "?" + qs(values) : ""),
    );
  }, [values]);
  const closeUser = () => {
    if (userDirty)
      confirm({
        title: "Закрыть карточку без сохранения?",
        description:
          "Введённое сообщение или изменение баланса будет потеряно.",
        label: "Закрыть без сохранения",
        action: async () => setUser(null),
      });
    else setUser(null);
  };
  const apply = (next: Data) => {
    setValues(next);
    setSearch(next.q || "");
    setPage(1);
    setSelected([]);
  };
  const bulk = (action: string, label: string) =>
    confirm({
      title: label,
      description: `Действие будет применено к ${selected.length} выбранным пользователям.`,
      danger: ["delete", "block"].includes(action),
      phrase: action === "delete" ? "УДАЛИТЬ" : undefined,
      action: async () => {
        const r = await api("users/bulk", { action, ids: selected });
        setResult(
          `Обработано ${r.done || 0} из ${r.total || selected.length}. Ошибок: ${r.failed || 0}, пропущено: ${r.skipped || 0}.`,
        );
        setSelected([]);
        await resource.reload();
      },
    });
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {[
          ["Все", {}],
          ["Без первой оплаты", { paid: "no" }],
          ["Без устройств", { devices: "no" }],
          ["Не заходили неделю", { online: "inactive_7d" }],
          ["Баланс закончился", { bal_max: "0" }],
        ].map(([label, value]) => (
          <Button
            key={String(label)}
            variant={
              JSON.stringify(values) === JSON.stringify(value)
                ? "secondary"
                : "outline"
            }
            size="sm"
            onClick={() => apply(value as Data)}
          >
            {String(label)}
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-56">
          <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
          <Input
            className="pl-9"
            aria-label="Найти пользователя"
            placeholder="Имя, @username или Telegram ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="w-52">
          <Choice
            value={values.sort || ""}
            options={sort}
            label="Сортировка"
            onChange={(v) => apply({ ...values, sort: v })}
          />
        </div>
        <Button
          variant="outline"
          onClick={() => {
            setDraft(values);
            setDrawer(true);
          }}
        >
          <SlidersHorizontal />
          Фильтры
          {Object.keys(values).filter(
            (k) => values[k] && k !== "q" && k !== "sort",
          ).length > 0 && (
            <Badge variant="secondary">
              {
                Object.keys(values).filter(
                  (k) => values[k] && k !== "q" && k !== "sort",
                ).length
              }
            </Badge>
          )}
        </Button>
      </div>
      <div className="flex justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              Дополнительные действия
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-destructive"
              disabled={
                !resource.data?.total ||
                resource.data.total > 500 ||
                !!values.funnel_step ||
                resource.loading ||
                !!resource.error
              }
              onSelect={() =>
                confirm({
                  title: "Удалить всех по текущим фильтрам?",
                  description: `Будут удалены ${resource.data?.total} пользователей, включая записи на других страницах. Профили и устройства восстановить нельзя.`,
                  danger: true,
                  phrase: "УДАЛИТЬ",
                  label: "Удалить пользователей",
                  action: async () => {
                    const r = await api("users/bulk", {
                      ...values,
                      action: "delete",
                      all_matching: true,
                    });
                    setResult(
                      `Удалено ${r.done} из ${r.total}. Ошибок: ${r.failed || 0}.`,
                    );
                    setSelected([]);
                    await resource.reload();
                  },
                })
              }
            >
              Удалить по фильтрам (до 500)
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="flex flex-wrap gap-2">
        {Object.entries(values)
          .filter(([, v]) => v)
          .map(([k, v]) => {
            const f = filters.find((f) => f.key === k);
            return (
              <Button
                key={k}
                variant="secondary"
                size="sm"
                onClick={() => {
                  const next = { ...values };
                  delete next[k];
                  apply(next);
                }}
              >
                {f?.label ||
                  (
                    {
                      q: "Поиск",
                      sort: "Сортировка",
                      funnel_step: "Этап воронки",
                    } as Data
                  )[k] ||
                  k}
                :{" "}
                {f?.options?.find(([key]) => key === v)?.[1] ||
                  sort.find(([key]) => k === "sort" && key === v)?.[1] ||
                  String(v)}
                <X className="size-3" />
              </Button>
            );
          })}
        {Object.values(values).some(Boolean) && (
          <Button variant="ghost" size="sm" onClick={() => apply({})}>
            Сбросить всё
          </Button>
        )}
      </div>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <>
          <div className="md:hidden space-y-3">
            {rows.map((u: Data) => (
              <div
                key={u.telegram_id}
                className="border rounded-xl bg-card p-4 space-y-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Checkbox
                      aria-label={`Выбрать ${who(u)}`}
                      checked={selected.includes(u.telegram_id)}
                      onCheckedChange={(v) =>
                        setSelected((s) =>
                          v
                            ? [...s, u.telegram_id]
                            : s.filter((id) => id !== u.telegram_id),
                        )
                      }
                    />
                    {identity(u)}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setUser(u)}
                  >
                    Открыть
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Баланс</p>
                    <p className="font-medium mt-1">{money(u.balance_rub)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Устройства / трафик
                    </p>
                    <p className="mt-1">
                      {u.device_count || 0} / {traffic(u)}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">
                      Последний онлайн · МСК
                    </p>
                    <p className="mt-1">{date(u.last_online_at)}</p>
                  </div>
                </div>
              </div>
            ))}
            {!rows.length && (
              <Empty
                title="Пользователи не найдены"
                description="Измените условия поиска."
              />
            )}
          </div>
          <div className="hidden md:block">
            <DataTable
              loading={resource.loading}
              rows={rows}
              empty={
                <Empty
                  title="Пользователи не найдены"
                  description="Попробуйте другое имя или измените фильтры."
                  action={
                    <Button variant="outline" onClick={() => apply({})}>
                      Сбросить фильтры
                    </Button>
                  }
                />
              }
              columns={[
                {
                  key: "select",
                  label: (
                    <Checkbox
                      aria-label="Выбрать пользователей на странице"
                      checked={
                        rows.length > 0 &&
                        rows.every((r: Data) =>
                          selected.includes(r.telegram_id),
                        )
                          ? true
                          : rows.some((r: Data) =>
                                selected.includes(r.telegram_id),
                              )
                            ? "indeterminate"
                            : false
                      }
                      onCheckedChange={(v) =>
                        setSelected(
                          v ? rows.map((r: Data) => r.telegram_id) : [],
                        )
                      }
                    />
                  ),
                  cell: (u) => (
                    <Checkbox
                      aria-label={`Выбрать ${who(u)}`}
                      checked={selected.includes(u.telegram_id)}
                      onCheckedChange={(v) =>
                        setSelected((s) =>
                          v
                            ? [...s, u.telegram_id]
                            : s.filter((id) => id !== u.telegram_id),
                        )
                      }
                    />
                  ),
                },
                {
                  key: "name",
                  label: "Клиент",
                  cell: (u) => (
                    <button
                      className="text-left hover:underline"
                      onClick={() => setUser(u)}
                    >
                      {identity(u)}
                    </button>
                  ),
                },
                {
                  key: "balance",
                  label: "Баланс",
                  cell: (u) => (
                    <span
                      className={
                        Number(u.balance_rub) <= 0
                          ? "text-destructive font-medium"
                          : ""
                      }
                    >
                      {money(u.balance_rub)}
                    </span>
                  ),
                },
                {
                  key: "devices",
                  label: "Устройства",
                  cell: (u) => u.devices_count ?? u.device_count ?? 0,
                },
                {
                  key: "online",
                  label: "Последний онлайн · МСК",
                  cell: (u) => (
                    <span className="whitespace-nowrap">
                      {date(u.last_online_at)}
                    </span>
                  ),
                },
                {
                  key: "traffic",
                  label: (
                    <span className="inline-flex gap-1 items-center">
                      Трафик
                      <ArrowDownUp className="size-3" />
                    </span>
                  ),
                  cell: traffic,
                },
                {
                  key: "status",
                  label: "Доступ",
                  cell: (u) => (
                    <Status
                      value={
                        u.blocked_at
                          ? "DISABLED"
                          : u.bot_blocked_at
                            ? "Бот заблокирован"
                            : u.billing_paused_at
                              ? "Без списаний"
                              : u.panel_status || "—"
                      }
                    />
                  ),
                },
                {
                  key: "open",
                  label: "",
                  cell: (u) => (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setUser(u)}
                    >
                      Открыть
                    </Button>
                  ),
                },
              ]}
            />
          </div>
          <Pager
            page={page}
            total={resource.data.total || 0}
            onChange={(p) => {
              setPage(p);
              setSelected([]);
            }}
          />
        </>
      )}
      {result && (
        <p role="status" className="rounded-lg border p-4 text-sm">
          {result}
        </p>
      )}
      {!!selected.length && (
        <div className="sticky bottom-4 flex items-center justify-between gap-3 rounded-xl border bg-background p-4 shadow-lg z-20">
          <span className="text-sm">Выбрано: {selected.length}</span>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setSelected([])}>
              Снять выбор
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button>
                  Действия
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => setCompose(true)}>
                  Написать выбранным
                </DropdownMenuItem>
                {[
                  ["cabinet_link", "Отправить ссылку в кабинет"],
                  ["trial_reset", "Сбросить пробный период"],
                  ["pause_billing", "Отключить списания"],
                  ["resume_billing", "Включить списания"],
                  ["unblock", "Разблокировать"],
                  ["reissue", "Перевыпустить подписки"],
                  ["block", "Заблокировать"],
                  ["delete", "Удалить пользователей"],
                ].map(([a, l]) => (
                  <DropdownMenuItem
                    key={a}
                    onSelect={() => bulk(a, l)}
                    className={a === "delete" ? "text-destructive" : ""}
                  >
                    {l}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      )}
      <Dialog open={compose} onOpenChange={setCompose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Сообщение выбранным клиентам</DialogTitle>
            <DialogDescription>
              Получателей: {selected.length}. Отправка начнётся после
              подтверждения.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            aria-label="Текст выбранным клиентам"
            rows={7}
            maxLength={3500}
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
          />
          <Button
            disabled={!bulkText.trim() || !selected.length}
            onClick={() =>
              confirm({
                title: "Отправить выбранным пользователям?",
                description: `Получателей: ${selected.length}\n\n${bulkText}`,
                label: "Отправить",
                action: async () => {
                  const r = await api("users/bulk", {
                    action: "message",
                    ids: selected,
                    text: bulkText,
                  });
                  setResult(
                    r.queued || r.running
                      ? "Рассылка запущена. Статус — в разделе «Рассылки»."
                      : `Обработано ${r.done || 0} из ${r.total || selected.length}. Ошибок: ${r.failed || 0}.`,
                  );
                  setBulkText("");
                  setCompose(false);
                  setSelected([]);
                },
              })
            }
          >
            Проверить отправку
          </Button>
        </DialogContent>
      </Dialog>
      <Sheet open={drawer} onOpenChange={setDrawer}>
        <SheetContent className="overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Фильтры пользователей</SheetTitle>
            <SheetDescription>
              Условия применяются вместе. Даты указаны по Москве.
            </SheetDescription>
          </SheetHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 py-6">
            {filters.map((f) => (
              <Field key={f.key} label={f.label}>
                {f.options ? (
                  <Choice
                    value={draft[f.key] || ""}
                    label={f.label}
                    options={f.options}
                    onChange={(v) => setDraft({ ...draft, [f.key]: v })}
                  />
                ) : (
                  <Input
                    aria-label={f.label}
                    type={f.type}
                    value={draft[f.key] || ""}
                    onChange={(e) =>
                      setDraft({ ...draft, [f.key]: e.target.value })
                    }
                  />
                )}
              </Field>
            ))}
          </div>
          <Button
            className="w-full"
            onClick={() => {
              apply(draft);
              setDrawer(false);
            }}
          >
            Показать пользователей
          </Button>
        </SheetContent>
      </Sheet>
      <Sheet
        open={!!user}
        onOpenChange={(open) => {
          if (!open) closeUser();
        }}
      >
        <SheetContent className="overflow-y-auto w-full sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>{user ? who(user) : "Клиент"}</SheetTitle>
            <SheetDescription>
              {user?.username ? "@" + user.username + " · " : ""}Telegram ID{" "}
              {user?.telegram_id}
            </SheetDescription>
          </SheetHeader>
          {user && (
            <UserDetail
              key={user.telegram_id}
              user={user}
              onChange={async () => {
                await resource.reload();
              }}
              onClose={() => setUser(null)}
              navigate={navigate}
              onDirty={setUserDirty}
            />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
function UserDetail({
  user,
  onChange,
  onClose,
  navigate,
  onDirty,
}: {
  user: Data;
  onDirty: (dirty: boolean) => void;
  onChange: () => Promise<void>;
  onClose: () => void;
  navigate: (p: string) => void;
}) {
  const [u, setUser] = useState(user),
    [tab, setTab] = useState("summary"),
    [amount, setAmount] = useState(""),
    [text, setText] = useState("");
  const confirm = useConfirm();
  useDirty(!!amount || !!text);
  useEffect(() => {
    onDirty(!!amount || !!text);
    return () => onDirty(false);
  }, [amount, text, onDirty]);
  const devices = useResource(
      tab === "devices" ? `users/${u.telegram_id}/devices` : null,
    ),
    billing = useResource(
      tab === "history" ? `billing?q=${u.telegram_id}&limit=25` : null,
    );
  const act = async (path: string, body: Data) => {
    const r = await api(`users/${u.telegram_id}/${path}`, body);
    if (r.balance_rub !== undefined)
      setUser({ ...u, balance_rub: r.balance_rub });
    if (r.blocked !== undefined)
      setUser({ ...u, blocked_at: r.blocked ? "yes" : null });
    if (r.paused !== undefined)
      setUser({ ...u, billing_paused_at: r.paused ? "yes" : null });
    await onChange();
    toast.success("Изменения сохранены");
  };
  return (
    <div className="pt-6 space-y-5">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-muted p-3">
          <p className="text-xs text-muted-foreground">Баланс</p>
          <p className="text-xl font-semibold mt-1">{money(u.balance_rub)}</p>
        </div>
        <div className="rounded-lg bg-muted p-3">
          <p className="text-xs text-muted-foreground">Пригласил</p>
          <p className="text-xl font-semibold mt-1">{u.invited_count || 0}</p>
        </div>
        <div className="rounded-lg bg-muted p-3">
          <p className="text-xs text-muted-foreground">Трафик</p>
          <p className="text-xl font-semibold mt-1">{traffic(u)}</p>
        </div>
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="w-full">
          <TabsTrigger value="summary">Профиль</TabsTrigger>
          <TabsTrigger value="devices">Устройства</TabsTrigger>
          <TabsTrigger value="history">Операции</TabsTrigger>
          <TabsTrigger value="message">Написать</TabsTrigger>
        </TabsList>
        <TabsContent value="summary" className="space-y-5 pt-4">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {[
              ["Зарегистрировался", date(u.created_at)],
              ["Был в сети", date(u.last_online_at)],
              [
                "Пробный период",
                u.trial_used ? "Использован" : "Не использован",
              ],
              ["Пригласивший", u.referred_by || "—"],
              ["Оплаты", paymentSummary(u)],
              ["Последняя оплата", date(u.last_paid_at)],
              ["Срок подписки", date(u.expire_at)],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <dt className="text-muted-foreground text-xs">{k}</dt>
                <dd className="mt-1">{v}</dd>
              </div>
            ))}
          </dl>
          <Panel
            title="Изменить баланс"
            description="Положительная сумма — начисление, отрицательная — списание."
          >
            <div className="flex gap-3">
              <Input
                aria-label="Сумма изменения баланса"
                type="number"
                placeholder="Например, 100 или −100"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <Button
                disabled={
                  !Number(amount) ||
                  !Number.isInteger(Number(amount)) ||
                  Math.abs(Number(amount)) > 1000000
                }
                onClick={() =>
                  confirm({
                    title: "Изменить баланс",
                    description: `${who(u)} · ${u.telegram_id}\nСейчас: ${money(u.balance_rub)}\nИзменение: ${money(amount)}\nПосле операции: ${money(Number(u.balance_rub || 0) + Number(amount))}`,
                    label: "Применить",
                    action: async () => {
                      await act("balance", { amount: Number(amount) });
                      setAmount("");
                    },
                  })
                }
              >
                Применить
              </Button>
            </div>
          </Panel>
          <div className="flex flex-wrap gap-2">
            <ActionButton
              variant="outline"
              onAction={async () => {
                await navigator.clipboard.writeText(String(u.telegram_id));
                toast.success("ID скопирован");
              }}
            >
              <Copy />
              ID
            </ActionButton>
            <Button
              variant="outline"
              onClick={() => {
                navigate("orders?q=" + u.telegram_id);
              }}
            >
              Все платежи
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  Управление
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onSelect={() =>
                    confirm({
                      title: "Сбросить пробный период?",
                      description:
                        "Пользователь сможет получить пробный доступ повторно.",
                      action: () => act("trial-reset", {}),
                    })
                  }
                >
                  Сбросить пробный период
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() =>
                    confirm({
                      title: u.billing_paused_at
                        ? "Включить списания?"
                        : "Отключить списания?",
                      description:
                        "Изменение относится только к этому пользователю.",
                      action: () =>
                        act("billing-pause", { paused: !u.billing_paused_at }),
                    })
                  }
                >
                  {u.billing_paused_at ? "Включить" : "Отключить"} списания
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() =>
                    confirm({
                      title: u.blocked_at
                        ? "Разблокировать клиента?"
                        : "Заблокировать клиента?",
                      description: "Изменится доступ пользователя к сервису.",
                      danger: !u.blocked_at,
                      action: () => act("block", { blocked: !u.blocked_at }),
                    })
                  }
                >
                  {u.blocked_at ? "Разблокировать" : "Заблокировать"}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive"
                  onSelect={() =>
                    confirm({
                      title: "Удалить пользователя?",
                      description: `Будут удалены профиль, устройства и связанные данные клиента ${u.telegram_id}. Это действие нельзя отменить.`,
                      danger: true,
                      phrase: String(u.telegram_id),
                      label: "Удалить",
                      action: async () => {
                        await act("delete", {});
                        onClose();
                      },
                    })
                  }
                >
                  Удалить пользователя
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </TabsContent>
        <TabsContent value="devices" className="pt-4">
          {devices.error ? (
            <Failure message={devices.error} retry={devices.reload} />
          ) : !devices.data ? (
            <Loading />
          ) : (
            <DataTable
              rows={devices.data.items || []}
              columns={[
                { key: "title", label: "Устройство" },
                { key: "platform", label: "Платформа" },
                {
                  key: "status",
                  label: "Доступ",
                  cell: (r) => <Status value={r.status} />,
                },
                {
                  key: "last_online_at",
                  label: "Онлайн",
                  cell: (r) => date(r.last_online_at),
                },
                { key: "traffic", label: "Трафик", cell: traffic },
              ]}
            />
          )}
        </TabsContent>
        {tab === "devices" && !!devices.data?.items?.length && (
          <Accordion type="multiple" className="mt-4">
            {devices.data.items.map((d: Data, i: number) => (
              <AccordionItem key={d.id || i} value={String(d.id || i)}>
                <AccordionTrigger>
                  Диагностика: {d.title || "Устройство"}
                </AccordionTrigger>
                <AccordionContent>
                  <dl className="grid grid-cols-2 gap-4 text-sm">
                    {[
                      ["Первое подключение", date(d.first_connected_at)],
                      ["Открытие подписки", date(d.sub_last_opened_at)],
                      [
                        "Нода",
                        d.node?.name || d.node?.hostname || "Нет данных",
                      ],
                      ["Приложение", d.user_agent || "Нет данных"],
                      ["Сохранённый трафик", traffic(d)],
                    ].map(([label, value]) => (
                      <div key={String(label)} className="min-w-0">
                        <dt className="text-xs text-muted-foreground">
                          {label}
                        </dt>
                        <dd className="mt-1 break-words">{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <h4 className="font-medium mt-5 mb-2">HWID-сессии</h4>
                  {(d.sessions || []).length ? (
                    (d.sessions || []).map((v: Data, j: number) => (
                      <p
                        className="text-xs py-2 border-t break-words"
                        key={v.hwid || j}
                      >
                        {[v.platform, v.model, v.hwid]
                          .filter(Boolean)
                          .join(" · ")}
                        {v.updatedAt ? " · " + date(v.updatedAt) : ""}
                      </p>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Панель не вернула сессии.
                    </p>
                  )}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
        <TabsContent value="history" className="pt-4">
          {billing.error ? (
            <Failure message={billing.error} retry={billing.reload} />
          ) : !billing.data ? (
            <Loading />
          ) : (
            <DataTable
              rows={billing.data.items || []}
              columns={[
                {
                  key: "created_at",
                  label: "Дата",
                  cell: (r) => date(r.created_at),
                },
                {
                  key: "kind",
                  label: "Операция",
                  cell: (r) => billKinds[r.kind] || r.kind,
                },
                { key: "amount", label: "Сумма", cell: (r) => money(r.amount) },
                {
                  key: "balance_after",
                  label: "После",
                  cell: (r) => money(r.balance_after),
                },
              ]}
            />
          )}
        </TabsContent>
        <TabsContent value="message" className="space-y-4 pt-4">
          <Field
            label="Сообщение в Telegram"
            hint="Будет отправлено только этому пользователю."
          >
            <Textarea
              aria-label="Сообщение клиенту"
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={3500}
              rows={6}
            />
          </Field>
          <Button
            disabled={!text.trim()}
            onClick={() =>
              confirm({
                title: "Отправить сообщение?",
                description: `Получатель: ${who(u)} (${u.telegram_id})\n\n${text}`,
                label: "Отправить",
                action: async () => {
                  await api(`users/${u.telegram_id}/message`, { text });
                  setText("");
                  toast.success("Сообщение отправлено");
                },
              })
            }
          >
            Отправить сообщение
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              confirm({
                title: "Отправить ссылку в кабинет?",
                description: `Ссылка придёт в Telegram пользователю ${who(u)}.`,
                label: "Отправить",
                action: async () => {
                  await api(`users/${u.telegram_id}/cabinet-link`, {});
                  toast.success("Ссылка отправлена");
                },
              })
            }
          >
            Отправить вход в кабинет
          </Button>
        </TabsContent>
      </Tabs>
    </div>
  );
}
