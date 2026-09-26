import { useState } from "react";
import { api, date, money, useResource, type Data } from "@/lib/api";
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
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Plus,
  Copy,
  ArrowRight,
  CalendarClock,
  Gift,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import { RecordsPage } from "./records";
export function PromoPage() {
  const [archived, setArchived] = useState(false),
    [edit, setEdit] = useState<Data | null>(null),
    [error, setError] = useState("");
  const resource = useResource("promos" + (archived ? "?archived=1" : "")),
    confirm = useConfirm(),
    navigate = useNavigate();
  const update = (key: string, value: any) => {
    setEdit((e) => ({ ...e, [key]: value }));
    setError("");
  };
  const save = async () => {
    if (!edit) return;
    setError("");
    try {
      const payload = {
        ...edit,
        days: Number(edit.days),
        max_uses: edit.max_uses ? Number(edit.max_uses) : null,
        expires_at: edit.expiry ? edit.expiry + ":00+03:00" : null,
      };
      await api("promos" + (edit.id ? "/" + edit.id : ""), payload);
      setEdit(null);
      await resource.reload();
      toast.success("Промокод сохранён");
    } catch (e) {
      setError((e as Error).message);
      throw e;
    }
  };
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Switch
            checked={archived}
            onCheckedChange={setArchived}
            aria-label="Показать архивные промокоды"
          />
          <span className="text-sm">Показать архивные</span>
        </div>
        <Button
          onClick={() => {
            setError("");
            setEdit({
              code: "",
              days: 3,
              max_uses: "",
              expiry: "",
              enabled: true,
            });
          }}
        >
          <Plus />
          Создать промокод
        </Button>
      </div>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <DataTable
          rows={resource.data.items || []}
          empty={
            <Empty
              title="Создайте первый промокод"
              description="Клиент введёт код в кабинете и получит подарок на баланс."
              action={
                <Button
                  onClick={() =>
                    setEdit({
                      code: "",
                      days: 3,
                      max_uses: "",
                      expiry: "",
                      enabled: true,
                    })
                  }
                >
                  <Plus />
                  Создать промокод
                </Button>
              }
            />
          }
          columns={[
            {
              key: "code",
              label: "Код",
              cell: (r) => (
                <div className="flex gap-2 items-center">
                  <span className="font-mono font-medium">{r.code}</span>
                  <ActionButton
                    variant="ghost"
                    onAction={async () => {
                      await navigator.clipboard.writeText(r.code);
                      toast.success("Код скопирован");
                    }}
                  >
                    <Copy />
                    <span className="sr-only">Скопировать код</span>
                  </ActionButton>
                </div>
              ),
            },
            { key: "days", label: "Дней" },
            {
              key: "used",
              label: "Активации",
              cell: (r) => `${r.used_count} / ${r.max_uses ?? "без лимита"}`,
            },
            {
              key: "expires_at",
              label: "Действует до · МСК",
              cell: (r) => (r.expires_at ? date(r.expires_at) : "Без срока"),
            },
            {
              key: "enabled",
              label: "Статус",
              cell: (r) => (
                <Status
                  value={
                    r.archived
                      ? "В архиве"
                      : !r.enabled
                        ? "Выключен"
                        : r.expires_at && Date.parse(r.expires_at) < Date.now()
                          ? "Истёк"
                          : r.max_uses != null && r.used_count >= r.max_uses
                            ? "Лимит исчерпан"
                            : "Активен"
                  }
                />
              ),
            },
            {
              key: "edit",
              label: "",
              cell: (r) => (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setError("");
                      setEdit({
                        ...r,
                        expiry: r.expires_at
                          ? new Date(Date.parse(r.expires_at) + 10800000)
                              .toISOString()
                              .slice(0, 16)
                          : "",
                      });
                    }}
                  >
                    Изменить
                  </Button>
                  {!r.archived && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        confirm({
                          title: "Скрыть промокод?",
                          description: `Код ${r.code} перестанет приниматься и перейдёт в архив.`,
                          action: async () => {
                            await api(`promos/${r.id}/archive`, {});
                            await resource.reload();
                          },
                        })
                      }
                    >
                      В архив
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}
      <Button variant="link" onClick={() => navigate("settings?section=gifts")}>
        Настроить пробный доступ и подарки
        <ArrowRight />
      </Button>
      <Dialog
        open={!!edit}
        onOpenChange={(open) => {
          if (!open) setEdit(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {edit?.id ? "Изменить промокод" : "Новый промокод"}
            </DialogTitle>
            <DialogDescription>
              Дни конвертируются в подарок на баланс по текущей цене суток. Один
              код можно активировать один раз на пользователя.
            </DialogDescription>
          </DialogHeader>
          {edit && (
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                void save().catch(() => {});
              }}
            >
              <Field
                label="Промокод"
                hint="Оставьте пустым — сервер создаст код XXXX-XXXX-XXXX."
              >
                <Input
                  aria-label="Промокод"
                  disabled={!!edit.id}
                  value={edit.code || ""}
                  onChange={(e) => update("code", e.target.value.toUpperCase())}
                  placeholder="XXXX-XXXX-XXXX"
                />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Дни подарка">
                  <Input
                    aria-label="Дни подарка"
                    type="number"
                    required
                    min={1}
                    value={edit.days}
                    onChange={(e) => update("days", e.target.value)}
                  />
                </Field>
                <Field label="Лимит активаций" hint="Пусто — без лимита.">
                  <Input
                    aria-label="Лимит активаций"
                    type="number"
                    min={1}
                    value={edit.max_uses ?? ""}
                    onChange={(e) => update("max_uses", e.target.value)}
                  />
                </Field>
              </div>
              <Field label="Срок действия · МСК">
                <Input
                  aria-label="Срок действия промокода"
                  type="datetime-local"
                  value={edit.expiry || ""}
                  onChange={(e) => update("expiry", e.target.value)}
                />
              </Field>
              <div className="flex gap-3 items-center">
                <Switch
                  aria-label="Промокод активен"
                  checked={!!edit.enabled}
                  onCheckedChange={(v) => update("enabled", v)}
                />
                <span className="text-sm">Принимать этот промокод</span>
              </div>
              {error && (
                <p role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              )}
              <ActionButton
                onAction={async () => {
                  const form = document.querySelector(
                    "[role=dialog] form",
                  ) as HTMLFormElement;
                  if (form.reportValidity()) await save();
                }}
              >
                Сохранить промокод
              </ActionButton>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
export function AdsPage() {
  const resource = useResource("ads"),
    [open, setOpen] = useState(false),
    [title, setTitle] = useState(""),
    [slug, setSlug] = useState("");
  const confirm = useConfirm();
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Button onClick={() => setOpen(true)}>
          <Plus />
          Создать рекламную ссылку
        </Button>
      </div>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <DataTable
          rows={resource.data.items || []}
          columns={[
            { key: "title", label: "Источник" },
            { key: "clicks", label: "Переходы" },
            { key: "users", label: "Пользователи" },
            { key: "trial", label: "Пробный доступ" },
            { key: "paid", label: "Оплатили" },
            {
              key: "actions",
              label: "",
              cell: (r) => (
                <div className="flex gap-2">
                  <ActionButton
                    variant="outline"
                    onAction={async () => {
                      await navigator.clipboard.writeText(r.url);
                      toast.success("Ссылка скопирована");
                    }}
                  >
                    <Copy />
                    Ссылка
                  </ActionButton>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      confirm({
                        title: "Скрыть источник?",
                        description:
                          "Он исчезнет из списка. Сама ссылка продолжит работать.",
                        action: async () => {
                          await api(`ads/${r.id}/archive`, {});
                          await resource.reload();
                        },
                      })
                    }
                  >
                    Скрыть
                  </Button>
                </div>
              ),
            },
          ]}
        />
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Новая рекламная ссылка</DialogTitle>
            <DialogDescription>
              Название поможет отличать источники в статистике.
            </DialogDescription>
          </DialogHeader>
          <Field label="Название источника">
            <Input
              aria-label="Название источника"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например, Telegram-канал о технологиях"
            />
          </Field>
          <Field
            label="Код ссылки"
            hint="Необязательно. Пустое поле — автоматическая генерация."
          >
            <Input
              aria-label="Код рекламной ссылки"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
          </Field>
          <ActionButton
            disabled={!title.trim()}
            onAction={async () => {
              await api("ads", { title, slug });
              setOpen(false);
              setTitle("");
              setSlug("");
              await resource.reload();
              toast.success("Ссылка создана");
            }}
          >
            Создать ссылку
          </ActionButton>
        </DialogContent>
      </Dialog>
    </div>
  );
}
export function ReferralsPage() {
  const navigate = useNavigate();
  return (
    <Tabs
      defaultValue={
        new URLSearchParams(location.hash.split("?")[1] || "").get("view") ===
        "payouts"
          ? "payouts"
          : "friends"
      }
      className="space-y-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <TabsList>
          <TabsTrigger value="friends">Приглашения</TabsTrigger>
          <TabsTrigger value="payouts">Вывод наград</TabsTrigger>
        </TabsList>
        <Button
          variant="outline"
          onClick={() => navigate("settings?section=referrals")}
        >
          Настроить программу
        </Button>
      </div>
      <TabsContent value="friends">
        <RecordsPage kind="referrals" />
      </TabsContent>
      <TabsContent value="payouts">
        <RecordsPage kind="payouts" />
      </TabsContent>
    </Tabs>
  );
}
export function CampaignsPage() {
  const resource = useResource("referral-campaigns"),
    [launch, setLaunch] = useState(false),
    [mode, setMode] = useState("now"),
    [time, setTime] = useState(""),
    [selection, setSelection] = useState(""),
    [page, setPage] = useState(1);
  const confirm = useConfirm();
  const items: Data[] = resource.data?.items || [],
    active = items.find((i) => !i.stopped_at),
    id = selection || String(items[0]?.id || "");
  const stats = useResource(
    id ? `referral-campaigns?campaign_id=${id}&page=${page}` : null,
  );
  const update = async (action: string) => {
    await api("referral-campaigns", {
      action,
      campaign_id: active?.id,
      scheduled_at: time,
    });
    await resource.reload();
    await stats.reload();
    setLaunch(false);
    toast.success("Акция обновлена");
  };
  return (
    <div className="space-y-6">
      <Panel
        title="Месяц VPN за трёх друзей"
        description="30 дней на 3 устройства за первые успешные оплаты трёх приглашённых друзей. Акция работает отдельно от постоянной реферальной программы."
        action={<Gift className="size-5 text-muted-foreground" />}
      >
        {resource.error ? (
          <Failure message={resource.error} retry={resource.reload} />
        ) : !resource.data ? (
          <Loading />
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={active ? "default" : "secondary"}>
                {active
                  ? "Акция идёт"
                  : resource.data.scheduled_at
                    ? "Запланирована"
                    : "Не запущена"}
              </Badge>
              <span className="text-sm">
                Подарок:{" "}
                {money(active?.reward_rub ?? resource.data.next_reward_rub)} на
                баланс
              </span>
              {resource.data.scheduled_at && (
                <span className="text-sm">
                  Старт: {date(resource.data.scheduled_at)} МСК
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              При запуске бот отправит всем доступным пользователям условия
              акции и персональную реферальную ссылку. Каждый участник получает
              один подарок за запуск.
            </p>
            <div className="flex flex-wrap gap-3">
              {active ? (
                <Button
                  variant="outline"
                  onClick={() =>
                    confirm({
                      title: "Завершить акцию?",
                      description:
                        "Новые оплаты перестанут учитываться. Следующий запуск начнёт новый счётчик.",
                      action: () => update("stop"),
                    })
                  }
                >
                  Завершить акцию
                </Button>
              ) : (
                <Button
                  onClick={() => {
                    setMode(resource.data?.scheduled_at ? "schedule" : "now");
                    setTime(
                      resource.data?.scheduled_at
                        ? new Date(
                            Date.parse(resource.data.scheduled_at) + 10800000,
                          )
                            .toISOString()
                            .slice(0, 16)
                        : "",
                    );
                    setLaunch(true);
                  }}
                >
                  <Play />
                  {resource.data.scheduled_at
                    ? "Изменить расписание"
                    : "Запустить акцию"}
                </Button>
              )}
              {resource.data.scheduled_at && (
                <Button
                  variant="outline"
                  onClick={() =>
                    confirm({
                      title: "Отменить запланированный запуск?",
                      description: "Акция не запустится в назначенное время.",
                      action: () => update("cancel_schedule"),
                    })
                  }
                >
                  Отменить расписание
                </Button>
              )}
              <Button
                variant="ghost"
                onClick={() => {
                  void resource.reload();
                  void stats.reload();
                }}
              >
                Обновить статистику
              </Button>
            </div>
          </div>
        )}
      </Panel>
      <Panel
        title="Результаты запусков"
        description="Платежи, прогресс участников, подарки и доставка уведомлений."
        action={
          items.length ? (
            <div className="w-56">
              <Choice
                label="Запуск акции"
                value={id}
                options={items.map((i) => [
                  String(i.id),
                  `№${i.id} · ${i.stopped_at ? "Завершена" : "Идёт"} · ${date(i.started_at)}`,
                ])}
                onChange={(v) => {
                  setSelection(v);
                  setPage(1);
                }}
              />
            </div>
          ) : undefined
        }
      >
        {!id ? (
          <Empty
            title="Статистика появится после запуска"
            description="Здесь будет видно, сколько друзей оплатили и сколько пользователей получили подарок."
          />
        ) : stats.error ? (
          <Failure message={stats.error} retry={stats.reload} />
        ) : !stats.data ? (
          <Loading />
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
              {[
                ["Участники", stats.data.summary?.participants || 0],
                ["Оплатившие друзья", stats.data.summary?.friends || 0],
                ["Первые оплаты", money(stats.data.summary?.paid_rub)],
                ["Выдано подарков", stats.data.awards?.awards || 0],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-muted p-4">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-2xl font-semibold mt-2">{value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
              <Badge variant="outline">
                1 из 3: {stats.data.summary?.one_friend || 0}
              </Badge>
              <Badge variant="outline">
                2 из 3: {stats.data.summary?.two_friends || 0}
              </Badge>
              <Badge variant="outline">
                3 и больше: {stats.data.summary?.completed || 0}
              </Badge>
              <span>Подарки на {money(stats.data.awards?.awarded_rub)}</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Доставка: {stats.data.delivery?.sent || 0} отправлено ·{" "}
              {stats.data.delivery?.pending || 0} в очереди ·{" "}
              {stats.data.delivery?.failed || 0} ошибок ·{" "}
              {stats.data.delivery?.cancelled || 0} отменено
            </p>
            {(stats.data.failures || []).map((f: Data, i: number) => (
              <p key={i} className="text-xs text-destructive">
                {f.count}: {f.error}
              </p>
            ))}
            {!!stats.data.retryable_count &&
              !stats.data.campaign?.stopped_at && (
                <Button
                  variant="outline"
                  onClick={() =>
                    confirm({
                      title: "Повторить временные ошибки?",
                      description: `В очередь попадёт ${stats.data?.retryable_count} уведомлений.`,
                      action: async () => {
                        await api("referral-campaigns", {
                          action: "retry_failed",
                          campaign_id: Number(id),
                        });
                        await stats.reload();
                      },
                    })
                  }
                >
                  Повторить временные ошибки
                </Button>
              )}
            <DataTable
              rows={stats.data.items || []}
              columns={[
                {
                  key: "name",
                  label: "Участник",
                  cell: (r) => r.first_name || r.username || r.referrer_id,
                },
                {
                  key: "friends",
                  label: "Прогресс",
                  cell: (r) => `${r.friends} / 3`,
                },
                {
                  key: "paid_rub",
                  label: "Оплаты друзей",
                  cell: (r) => money(r.paid_rub),
                },
                {
                  key: "award_rub",
                  label: "Подарок",
                  cell: (r) =>
                    r.award_rub ? money(r.award_rub) : "Ещё не выдан",
                },
                {
                  key: "last_payment_at",
                  label: "Последняя оплата · МСК",
                  cell: (r) => date(r.last_payment_at),
                },
              ]}
            />
            <Pager
              page={page}
              total={stats.data.summary?.participants || 0}
              limit={stats.data.limit || 50}
              onChange={setPage}
            />
          </div>
        )}
      </Panel>
      <Dialog open={launch} onOpenChange={setLaunch}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Запуск акции</DialogTitle>
            <DialogDescription>
              Запуск включает массовое уведомление пользователей. Стоимость
              подарка фиксируется на момент старта.
            </DialogDescription>
          </DialogHeader>
          <Choice
            label="Время запуска"
            value={mode}
            options={
              resource.data?.scheduled_at
                ? [["schedule", "По расписанию"]]
                : [
                    ["now", "Сейчас"],
                    ["schedule", "По расписанию"],
                  ]
            }
            onChange={setMode}
          />
          {mode === "schedule" && (
            <Field label="Дата и время · Москва (UTC+3)">
              <Input
                type="datetime-local"
                aria-label="Время запуска акции МСК"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
            </Field>
          )}
          <p className="text-sm rounded-lg bg-muted p-4">
            Подарок по текущему тарифу:{" "}
            <strong>{money(resource.data?.next_reward_rub)}</strong>.
            Учитываются только первые оплаты друзей во время акции, включая
            ранее приглашённых. Старые зачтённые друзья повторно не участвуют.
          </p>
          <Button
            disabled={
              mode === "schedule" &&
              (!time || Date.parse(time + ":00+03:00") <= Date.now())
            }
            onClick={() =>
              confirm({
                title:
                  mode === "now"
                    ? "Запустить акцию и рассылку?"
                    : "Запланировать акцию и рассылку?",
                description:
                  mode === "now"
                    ? "Уведомления начнут отправляться всем доступным пользователям сразу."
                    : `Уведомления начнут отправляться ${time.replace("T", " ")} МСК.`,
                label:
                  mode === "now" ? "Запустить и уведомить" : "Запланировать",
                action: () => update(mode === "now" ? "start" : "schedule"),
              })
            }
          >
            {mode === "now" ? "Проверить запуск" : "Проверить расписание"}
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
