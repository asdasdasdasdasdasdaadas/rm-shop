import { useEffect, useRef, useState } from "react";
import { api, useResource, type Data } from "@/lib/api";
import { saveSettingsPatchWith } from "@/lib/contracts.mjs";
import {
  ActionButton,
  Choice,
  Empty,
  Failure,
  Field,
  Loading,
  Panel,
  useConfirm,
  useDirty,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Save, Trash2, ArrowUp, ArrowDown } from "lucide-react";
type Setting = {
  key: string;
  label: string;
  type?: string;
  hint?: string;
  min?: number;
  max?: number;
};
const groups: {
  id: string;
  title: string;
  description: string;
  fields: Setting[];
}[] = [
  {
    id: "general",
    title: "Сервис и поддержка",
    description: "То, что клиент видит в боте и личном кабинете.",
    fields: [
      { key: "brand_name", label: "Название сервиса" },
      {
        key: "support_username",
        label: "Telegram поддержки",
        hint: "Username или ссылка на поддержку.",
      },
      { key: "legal_offer_url", label: "Ссылка на оферту", type: "url" },
      {
        key: "legal_privacy_url",
        label: "Политика конфиденциальности",
        type: "url",
      },
      {
        key: "admin_live_chat_id",
        label: "Канал обращений",
        hint: "ID приватного канала, в котором бот является администратором.",
      },
      {
        key: "welcome_sticker_file_id",
        label: "Стикер приветствия",
        hint: "Telegram file_id. Пустое поле отключает стикер.",
      },
    ],
  },
  {
    id: "pricing",
    title: "Тарифы и пополнение",
    description:
      "Стоимость доступа и суммы, доступные пользователям при оплате.",
    fields: [
      {
        key: "vpn_day_price_rub",
        label: "Цена суток за устройство, ₽",
        type: "number",
        min: 1,
        max: 10000,
      },
      {
        key: "balance_topup_min",
        label: "Минимальное пополнение, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "balance_topup_max",
        label: "Максимальное пополнение, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "balance_topup_step",
        label: "Шаг выбора суммы, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "plan_1m_rub",
        label: "Тариф на месяц, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "plan_3m_rub",
        label: "Тариф на 3 месяца, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "plan_6m_rub",
        label: "Тариф на 6 месяцев, ₽",
        type: "number",
        min: 1,
      },
      { key: "plan_12m_rub", label: "Тариф на год, ₽", type: "number", min: 1 },
    ],
  },
  {
    id: "access",
    title: "Доступ и устройства",
    description: "Ограничения подключений и отдельный тариф для роутера.",
    fields: [
      {
        key: "max_devices",
        label: "Максимум устройств",
        type: "number",
        min: 0,
        max: 50,
        hint: "0 — без ограничения.",
      },
      {
        key: "remnawave_hwid_limit",
        label: "Лимит HWID",
        type: "number",
        min: 0,
        max: 20,
        hint: "Количество аппаратных идентификаторов на подписку.",
      },
      { key: "router_enabled", label: "Доступ для роутеров", type: "switch" },
      { key: "router_rub", label: "Цена роутера, ₽", type: "number", min: 1 },
      {
        key: "router_days",
        label: "Срок роутера, дни",
        type: "number",
        min: 1,
        max: 365,
      },
    ],
  },
  {
    id: "gifts",
    title: "Пробный доступ и обещанный платёж",
    description: "Условия первого подключения и временного доступа без оплаты.",
    fields: [
      { key: "trial_enabled", label: "Пробный период", type: "switch" },
      {
        key: "trial_days",
        label: "Длительность пробного периода, дни",
        type: "number",
        min: 1,
        max: 90,
      },
      { key: "trust_enabled", label: "Обещанный платёж", type: "switch" },
      {
        key: "trust_days",
        label: "Срок обещанного платежа, дни",
        type: "number",
        min: 1,
        max: 30,
      },
      {
        key: "trust_fee_rub",
        label: "Комиссия обещанного платежа, ₽",
        type: "number",
        min: 0,
      },
    ],
  },
  {
    id: "referrals",
    title: "Реферальная программа",
    description:
      "50 ₽ за первую оплату друга и 5% от его последующих пополнений. Отдельная акция управляется в разделе «Акции».",
    fields: [
      {
        key: "referral_program_enabled",
        label: "Начислять реферальные награды",
        type: "switch",
      },
      {
        key: "referral_invitee_reward_rub",
        label: "Подарок приглашённому за оплату, ₽",
        type: "number",
        min: 0,
      },
      {
        key: "referral_payout_min",
        label: "Минимальная сумма вывода, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "referral_reward_days",
        label: "Дни пригласившему",
        type: "number",
        min: 0,
        max: 365,
      },
      {
        key: "referral_invitee_days",
        label: "Дни приглашённому",
        type: "number",
        min: 0,
        max: 365,
      },
    ],
  },
];
export const saveSettingsPatch = (patch: Data) =>
  saveSettingsPatchWith(api, patch);
export function SettingsPage({ initial = "general" }: { initial?: string }) {
  const resource = useResource("settings");
  const [section, setSection] = useState(initial),
    [patch, setPatch] = useState<Data>({}),
    [error, setError] = useState("");
  const confirm = useConfirm();
  const saving = useRef(false);
  const dirty = Object.keys(patch).length > 0;
  useDirty(dirty);
  const values = { ...resource.data?.values, ...patch };
  const update = (key: string, value: any) => {
    setPatch((p) => ({ ...p, [key]: value }));
    setError("");
  };
  const changeSection = (next: string) => {
    if (dirty)
      confirm({
        title: "Есть несохранённые изменения",
        description:
          "Сохраните изменения перед переходом или продолжите без сохранения.",
        label: "Перейти без сохранения",
        action: async () => {
          setPatch({});
          setSection(next);
        },
      });
    else setSection(next);
  };
  const save = async () => {
    if (saving.current) return;
    saving.current = true;
    const submitted = patch;
    setError("");
    try {
      const next = await saveSettingsPatch(submitted);
      resource.setData(next);
      setPatch((current) =>
        Object.fromEntries(
          Object.entries(current).filter(
            ([key, value]) => value !== submitted[key],
          ),
        ),
      );
      toast.success("Настройки сохранены");
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      saving.current = false;
    }
  };
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  const group = groups.find((g) => g.id === section);
  return (
    <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible">
        {[
          ...groups.map((g) => [g.id, g.title]),
          ["payments", "Способы оплаты"],
          ["apps", "VPN-приложения"],
          ["notices", "Тексты бота"],
          ["automation", "Автоматические сообщения"],
          ["system", "Работа системы"],
        ].map(([id, label]) => (
          <Button
            key={id}
            variant={section === id ? "secondary" : "ghost"}
            className="justify-start whitespace-normal text-left h-auto py-2.5 shrink-0"
            onClick={() => changeSection(id)}
          >
            {label}
          </Button>
        ))}
      </aside>
      <div className="min-w-0 space-y-5">
        {group && (
          <Panel title={group.title} description={group.description}>
            <form
              id="settings-section"
              onSubmit={(e) => {
                e.preventDefault();
                void save().catch(() => {});
              }}
            >
              <div className="grid gap-6 sm:grid-cols-2">
                {group.fields
                  .filter((f) => {
                    if (f.key.startsWith("plan_"))
                      return !resource.data?.balance_enabled;
                    if (
                      [
                        "referral_reward_days",
                        "referral_invitee_days",
                      ].includes(f.key)
                    )
                      return !resource.data?.balance_enabled;
                    return true;
                  })
                  .map((f) => (
                    <Field key={f.key} label={f.label} hint={f.hint}>
                      {f.type === "switch" ? (
                        <div className="flex gap-3 items-center">
                          <Switch
                            aria-label={f.label}
                            checked={!!values[f.key]}
                            onCheckedChange={(v) => update(f.key, v)}
                          />
                          <span className="text-sm text-muted-foreground">
                            {values[f.key] ? "Включено" : "Выключено"}
                          </span>
                        </div>
                      ) : (
                        <Input
                          aria-label={f.label}
                          type={f.type || "text"}
                          min={f.min}
                          max={f.max}
                          step={f.type === "number" ? "1" : undefined}
                          required={
                            f.type === "number" ||
                            f.type === "url" ||
                            f.key === "brand_name" ||
                            f.key === "support_username"
                          }
                          value={values[f.key] ?? ""}
                          onChange={(e) =>
                            update(
                              f.key,
                              f.type === "number"
                                ? e.target.value === ""
                                  ? ""
                                  : Number(e.target.value)
                                : e.target.value,
                            )
                          }
                        />
                      )}
                    </Field>
                  ))}
                {section === "referrals" && (
                  <Field label="Использование награды">
                    <Choice
                      label="Режим реферальной программы"
                      value={values.referral_mode || "classic"}
                      options={[
                        ["classic", "Только на баланс"],
                        ...(resource.data.balance_enabled
                          ? [
                              ["payout", "На баланс или вывод"] as [
                                string,
                                string,
                              ],
                            ]
                          : []),
                      ]}
                      onChange={(v) => {
                        update("referral_mode", v);
                        update("referral_payout_enabled", v === "payout");
                      }}
                    />
                  </Field>
                )}
              </div>
              <button type="submit" className="sr-only">
                Сохранить настройки
              </button>
            </form>
          </Panel>
        )}
        {section === "payments" && (
          <Panel
            title="Способы оплаты"
            description="Порядок здесь соответствует порядку в кабинете."
          >
            <ListEditor
              kind="payments"
              list={values.pay_methods || []}
              onChange={(v) => update("pay_methods", v)}
            />
          </Panel>
        )}
        {section === "apps" && (
          <Panel
            title="VPN-приложения"
            description="Приложения и ссылки установки для каждой платформы."
          >
            <ListEditor
              kind="apps"
              list={values.vpn_apps || []}
              onChange={(v) => update("vpn_apps", v)}
            />
          </Panel>
        )}
        {section === "notices" && (
          <NoticeEditor
            fields={resource.data.notice_fields || []}
            values={values.notices || {}}
            onChange={(v) => update("notices", v)}
          />
        )}
        {section === "automation" && <Automation />}
        {section === "system" && <SystemSettings />}
        {dirty && (
          <div className="sticky bottom-4 z-20 bg-background border rounded-xl shadow-lg p-4 flex flex-wrap gap-3 items-center justify-between">
            <span className="text-sm">Есть несохранённые изменения</span>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setPatch({})}>
                Отменить
              </Button>
              <ActionButton
                onAction={async () => {
                  const form = document.getElementById(
                    "settings-section",
                  ) as HTMLFormElement | null;
                  if (form && !form.reportValidity()) return;
                  await save();
                }}
              >
                <Save />
                Сохранить изменения
              </ActionButton>
            </div>
          </div>
        )}
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
function ListEditor({
  kind,
  list,
  onChange,
}: {
  kind: "payments" | "apps";
  list: Data[];
  onChange: (v: Data[]) => void;
}) {
  const set = (index: number, key: string, value: any) =>
    onChange(
      list.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
    );
  return (
    <div className="space-y-5">
      {list.map((item, i) => (
        <div key={i} className="border rounded-lg p-4 space-y-4">
          <div className="flex justify-between gap-3 items-center">
            <h3 className="font-medium">
              {item.title || item.name || "Новое приложение"}
            </h3>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Переместить выше"
                disabled={i === 0}
                onClick={() => {
                  const next = [...list];
                  [next[i - 1], next[i]] = [next[i], next[i - 1]];
                  onChange(next);
                }}
              >
                <ArrowUp />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Переместить ниже"
                disabled={i === list.length - 1}
                onClick={() => {
                  const next = [...list];
                  [next[i + 1], next[i]] = [next[i], next[i + 1]];
                  onChange(next);
                }}
              >
                <ArrowDown />
              </Button>
              {kind === "apps" && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Удалить приложение"
                  onClick={() => onChange(list.filter((_, j) => i !== j))}
                >
                  <Trash2 />
                </Button>
              )}
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            {(kind === "payments"
              ? [
                  ["title", "Название"],
                  ["note", "Подсказка"],
                ]
              : [
                  ["id", "Идентификатор"],
                  ["name", "Название"],
                  ["mark", "Короткая метка"],
                  ["icon", "URL иконки"],
                  ["deep_link", "Ссылка импорта подписки"],
                ]
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <Input
                  aria-label={`${label} ${i + 1}`}
                  value={item[key] || ""}
                  onChange={(e) => set(i, key, e.target.value)}
                />
              </Field>
            ))}
          </div>
          {kind === "payments" ? (
            <div className="flex items-center gap-3">
              <Switch
                aria-label={`Включить ${item.title}`}
                checked={!!item.enabled}
                onCheckedChange={(v) => set(i, "enabled", v)}
              />
              <span className="text-sm">
                {item.available === false
                  ? item.hint || "Не настроен на сервере"
                  : item.enabled
                    ? "Доступен клиентам"
                    : "Скрыт"}
              </span>
            </div>
          ) : (
            <div className="space-y-3">
              {[
                ["ios", "iOS"],
                ["macos", "macOS"],
                ["appletv", "Apple TV"],
                ["android", "Android"],
                ["androidtv", "Android TV"],
                ["windows", "Windows"],
              ].map(([p, label]) => (
                <div key={p} className="flex items-center gap-3">
                  <Checkbox
                    aria-label={`${label} ${i + 1}`}
                    checked={(item.platforms || []).includes(p)}
                    onCheckedChange={(v) =>
                      set(
                        i,
                        "platforms",
                        v
                          ? [...(item.platforms || []), p]
                          : (item.platforms || []).filter(
                              (x: string) => x !== p,
                            ),
                      )
                    }
                  />
                  <span className="w-24 text-sm">{label}</span>
                  <Input
                    aria-label={`Ссылка установки ${label} ${i + 1}`}
                    placeholder="Ссылка на установку"
                    value={item.stores?.[p] || ""}
                    onChange={(e) =>
                      set(i, "stores", { ...item.stores, [p]: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      {kind === "apps" && (
        <Button
          variant="outline"
          onClick={() =>
            onChange([
              ...list,
              {
                id: "",
                name: "",
                mark: "",
                icon: "",
                deep_link: "",
                platforms: ["ios"],
                stores: {},
              },
            ])
          }
        >
          <Plus />
          Добавить приложение
        </Button>
      )}
    </div>
  );
}
function NoticeEditor({
  fields,
  values,
  onChange,
}: {
  fields: Data[];
  values: Data;
  onChange: (v: Data) => void;
}) {
  const [search, setSearch] = useState(""),
    [selected, setSelected] = useState("");
  const options = fields.filter((f) =>
    `${f.title} ${values[f.key] || ""}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const field = fields.find((f) => f.key === selected) || options[0];
  return (
    <Panel
      title="Тексты бота"
      description="Выберите сообщение. Изменение текста не отправляет рассылку."
    >
      <Input
        aria-label="Найти текст бота"
        placeholder="Поиск по названию или тексту"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setSelected("");
        }}
      />
      <div className="grid xl:grid-cols-[230px_minmax(0,1fr)] gap-5 mt-5">
        <div className="max-h-96 overflow-y-auto space-y-1">
          {options.map((f) => (
            <Button
              className="w-full justify-start text-left whitespace-normal h-auto"
              key={f.key}
              variant={field?.key === f.key ? "secondary" : "ghost"}
              onClick={() => setSelected(f.key)}
            >
              {f.title || f.key}
            </Button>
          ))}
        </div>
        {field ? (
          <div className="space-y-4">
            <Field
              label={field.title || field.key}
              hint={
                field.hint ? "Доступные переменные: " + field.hint : undefined
              }
            >
              <Textarea
                aria-label="Текст сообщения бота"
                rows={12}
                value={values[field.key] || ""}
                onChange={(e) =>
                  onChange({ ...values, [field.key]: e.target.value })
                }
              />
            </Field>
            <p className="text-xs text-muted-foreground">
              Сохраняйте имена переменных в фигурных скобках: бот подставит
              данные пользователя.
            </p>
          </div>
        ) : (
          <Empty
            title="Сообщение не найдено"
            description="Попробуйте другой поисковый запрос."
          />
        )}
      </div>
    </Panel>
  );
}
function Automation() {
  const resource = useResource("flags");
  const confirm = useConfirm();
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  return (
    <Panel
      title="Автоматические сообщения"
      description="Каждый переключатель сохраняется сразу. Тексты редактируются отдельно."
    >
      <div className="divide-y">
        {[
          [
            "payment_nudge",
            "Неоплаченный счёт",
            "Напоминание через 10 минут после создания счёта.",
          ],
          [
            "trial_nudge",
            "Подключение и окончание баланса",
            "Помощь с первым подключением и предупреждения о балансе.",
          ],
          [
            "invite_nudge",
            "Приглашение друзей",
            "Предложение поделиться реферальной ссылкой.",
          ],
          [
            "info_nudge",
            "Возврат в кабинет",
            "Информационные сообщения о сервисе.",
          ],
          [
            "legal_nudge",
            "Правовые документы",
            "Автоматические сообщения, связанные с документами.",
          ],
        ].map(([key, label, hint]) => (
          <div
            key={key}
            className="py-5 flex items-center justify-between gap-4"
          >
            <div>
              <p className="font-medium text-sm">{label}</p>
              <p className="text-xs text-muted-foreground mt-1">{hint}</p>
            </div>
            <Switch
              aria-label={label}
              checked={!!resource.data?.[key]}
              onCheckedChange={(v) =>
                confirm({
                  title: `${v ? "Включить" : "Выключить"} «${label}»?`,
                  description: hint,
                  action: async () => {
                    await api("flags", { [key]: v });
                    await resource.reload();
                    toast.success("Сохранено");
                  },
                })
              }
            />
          </div>
        ))}
      </div>
    </Panel>
  );
}
function SystemSettings() {
  const flags = useResource("flags"),
    job = useResource("subscriptions/replace", 5000);
  const [message, setMessage] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [revoke, setRevoke] = useState(true),
    [squads, setSquads] = useState(false),
    [cleanup, setCleanup] = useState("");
  const confirm = useConfirm();
  useEffect(() => {
    if (flags.data) setMessage(flags.data.maintenance_notice || "");
  }, [flags.data]);
  if (flags.error)
    return <Failure message={flags.error} retry={flags.reload} />;
  if (!flags.data) return <Loading />;
  return (
    <div className="space-y-5">
      <Panel
        title="Технические работы"
        description="При включении бот покажет это сообщение вместо обычного пользовательского пути."
      >
        <div className="space-y-4">
          <Textarea
            aria-label="Текст технических работ"
            rows={5}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <Input
            type="file"
            aria-label="Изображение технических работ"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <ActionButton
            variant="outline"
            onAction={async () => {
              const body = new FormData();
              body.append("message", message);
              if (file) body.append("file", file);
              await api("maintenance", body);
              toast.success("Сообщение сохранено");
              await flags.reload();
            }}
          >
            Сохранить сообщение
          </ActionButton>
          {flags.data.maintenance_has_photo && (
            <ActionButton
              variant="outline"
              onAction={async () => {
                await api("maintenance/photo", undefined, "DELETE");
                await flags.reload();
              }}
            >
              Удалить изображение
            </ActionButton>
          )}
          <div className="flex items-center gap-3">
            <Switch
              aria-label="Технические работы"
              checked={!!flags.data.maintenance}
              onCheckedChange={(v) =>
                confirm({
                  title: v
                    ? "Включить технические работы?"
                    : "Завершить технические работы?",
                  description: "Изменение влияет на всех пользователей бота.",
                  danger: v,
                  action: async () => {
                    await api("flags", { maintenance: v, message });
                    await flags.reload();
                  },
                })
              }
            />
            <span>{flags.data.maintenance ? "Включены" : "Выключены"}</span>
          </div>
        </div>
      </Panel>
      <Panel
        title="Тарификация"
        description="Глобальная пауза останавливает списания со всех пользователей."
      >
        <Button
          variant="outline"
          onClick={() =>
            confirm({
              title: flags.data?.billing_paused
                ? "Возобновить тарификацию?"
                : "Остановить тарификацию?",
              description: "Действие распространяется на весь сервис.",
              danger: true,
              action: async () => {
                await api("flags", {
                  billing_paused: !flags.data?.billing_paused,
                });
                await flags.reload();
              },
            })
          }
        >
          {flags.data.billing_paused
            ? "Возобновить списания"
            : "Приостановить списания"}
        </Button>
      </Panel>
      <Panel
        title="Обновление подписок"
        description="Применение сквадов из конфигурации сервера и перевыпуск ссылок."
      >
        {job.error ? (
          <Failure message={job.error} retry={job.reload} />
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-4">
              {job.data?.running
                ? "Выполняется…"
                : job.data?.message || "Нет активной операции"}
            </p>
            <div className="space-y-3 mb-5">
              <label className="flex items-center gap-3 text-sm">
                <Checkbox
                  checked={revoke}
                  onCheckedChange={(v) => setRevoke(!!v)}
                />
                Перевыпустить ссылки подключения
              </label>
              <label className="flex items-center gap-3 text-sm">
                <Checkbox
                  checked={squads}
                  onCheckedChange={(v) => setSquads(!!v)}
                />
                Применить сквады из настроек сервера
              </label>
            </div>
            <Button
              variant="destructive"
              disabled={!job.data || !!job.data.running || (!revoke && !squads)}
              onClick={() =>
                confirm({
                  title: "Обновить все подписки?",
                  description: revoke
                    ? "У пользователей изменятся ссылки подключения. Старые ссылки перестанут работать."
                    : "Для всех подписок будут применены сквады из конфигурации сервера.",
                  danger: true,
                  phrase: "ПЕРЕВЫПУСТИТЬ",
                  action: async () => {
                    await api("subscriptions/replace", {
                      revoke,
                      apply_squads: squads,
                    });
                    await job.reload();
                  },
                })
              }
            >
              Применить изменения
            </Button>
          </>
        )}
      </Panel>
      <Panel
        title="Очистка неактивных клиентов"
        description="Удаление пользователей, которые заблокировали бота и не воспользовались сервисом. За запуск — до 200 записей. Ошибочно выданные реферальные награды могут быть возвращены."
      >
        <Button
          variant="outline"
          onClick={() =>
            confirm({
              title: "Удалить неактивных пользователей, заблокировавших бота?",
              description:
                "Будут удалены профили и связанные устройства. Сервер проверит условия для каждого пользователя; операция необратима.",
              danger: true,
              phrase: "ОЧИСТИТЬ",
              label: "Очистить",
              action: async () => {
                const r = await api("users/purge-bot-blockers", {});
                setCleanup(
                  `Удалено: ${r.deleted}. Возвратов наград: ${r.clawed}. Пропущено: ${r.skipped}. Осталось: ${r.remaining}.`,
                );
              },
            })
          }
        >
          Очистить неактивных клиентов
        </Button>
        {cleanup && (
          <p className="text-sm mt-4" role="status">
            {cleanup}
          </p>
        )}
      </Panel>
    </div>
  );
}
