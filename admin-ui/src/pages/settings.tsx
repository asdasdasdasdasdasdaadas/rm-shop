import { useEffect, useRef, useState } from "react";
import { api, useResource, type Data } from "@/lib/api";
import { saveSettingsPatchWith } from "@/lib/contracts.mjs";
import {
  ActionButton,
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
import { Plus, Save, Trash2, ChevronDown, GripVertical } from "lucide-react";
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
      {
        key: "widgets_enabled",
        label: "Карточки-виджеты в чате",
        type: "switch",
        hint: "Баланс, чеки, подарки, рефералка и обращения приходят живыми карточками. Выключите, если Telegram ограничивает виджеты: всё придёт обычными сообщениями с кнопками.",
      },
    ],
  },
  {
    id: "welcome",
    title: "Приветствие",
    description: "Что новый пользователь видит после /start.",
    fields: [
      {
        key: "welcome_tariff_enabled",
        label: "Тариф и условия в приветствии",
        type: "switch",
        hint: "Цена за день, баланс вместо подписки и минимальное пополнение во втором сообщении после /start.",
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
        key: "balance_topup_step",
        label: "Шаг выбора суммы, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "cabinet_price_enabled",
        label: "Цена под балансом в кабинете",
        type: "switch",
        hint: "Плашка «6 ₽ в день за устройство» на главном экране кабинета.",
      },
    ],
  },
  {
    id: "ton",
    title: "Оплата в TON",
    description:
      "Пополнение из кошелька Telegram прямо в чате с ботом. Деньги приходят на ваш кошелёк, ключи на сервере не хранятся.",
    fields: [
      {
        key: "ton_enabled",
        label: "Оплата в TON для всех",
        type: "switch",
        hint: "Выключено — оплату видят только админы (команда /ton), чтобы проверить перед запуском.",
      },
      {
        key: "ton_wallet",
        label: "Кошелёк для приёма",
        hint: "Адрес TON (UQ… или EQ…). Сюда приходят все платежи.",
      },
      {
        key: "ton_rate_margin_pct",
        label: "Запас к курсу, %",
        type: "number",
        min: 0,
        max: 20,
        hint: "Защита от скачков курса за 10 минут, пока действует счёт.",
      },
      {
        key: "toncenter_api_key",
        label: "Ключ Toncenter",
        hint: "Необязательно. Без ключа проверка работает медленнее (1 запрос в секунду). Ключ выдаёт бот @tonapibot.",
      },
    ],
  },
  {
    id: "access",
    title: "Доступ и устройства",
    description: "Ограничения подключений устройств.",
    fields: [
      {
        key: "max_devices",
        label: "Максимум устройств",
        type: "number",
        min: 5,
        max: 5,
        hint: "5 устройств на пользователя.",
      },
      {
        key: "remnawave_hwid_limit",
        label: "Лимит HWID",
        type: "number",
        min: 0,
        max: 20,
        hint: "Количество аппаратных идентификаторов на подписку.",
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
      {
        key: "first_bonus_enabled",
        label: "Бонус за первую оплату",
        type: "switch",
        hint: "Первое пополнение до конца подарка от суммы ниже — плюс процент от суммы на баланс. Кабинет показывает отсчёт и открывающийся подарок.",
      },
      {
        key: "first_bonus_min_rub",
        label: "Бонус: пополнение от, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "first_bonus_percent",
        label: "Бонус: процент к пополнению",
        type: "number",
        min: 1,
        max: 100,
      },
      {
        key: "return_bonus_enabled",
        label: "Бонус за возвращение",
        type: "switch",
        hint: "Через 10 дней после того, как у платившего клиента кончились деньги, бот предлагает процент к пополнению. Бонус начисляется сам вместе с пополнением, один раз.",
      },
      {
        key: "return_bonus_min_rub",
        label: "Возвращение: пополнение от, ₽",
        type: "number",
        min: 1,
      },
      {
        key: "return_bonus_percent",
        label: "Возвращение: процент к пополнению",
        type: "number",
        min: 1,
        max: 100,
      },
      {
        key: "return_bonus_days",
        label: "Возвращение: сколько дней действует",
        type: "number",
        min: 1,
        max: 60,
      },
    ],
  },
  {
    id: "referrals",
    title: "Реферальная программа",
    description:
      "Другу 50 ₽ сразу, как он откроет меню бота; пригласившему 50 ₽, когда друг впервые подключит VPN. Один раз за каждого нового друга.",
    fields: [
      {
        key: "referral_program_enabled",
        label: "Начислять реферальные награды",
        type: "switch",
      },
    ],
  },
];
export const saveSettingsPatch = (patch: Data) =>
  saveSettingsPatchWith(api, patch);
export function SettingsPage({ initial = "general" }: { initial?: string }) {
  const resource = useResource("settings");
  const [section, setSection] = useState(
      initial === "automation" ? "general" : initial,
    ),
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
          ["faq", "Частые вопросы"],
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
                {group.fields.map((f) => (
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
              defaults={resource.data.vpn_app_defaults || []}
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
        {section === "faq" && (
          <Panel
            title="Частые вопросы"
            description="Вопросы и ответы для бота и личного кабинета. Обычный текст без HTML. Изменения применятся после сохранения; свои ответы нужно обновлять вручную при изменении тарифов."
          >
            <div className="space-y-4">
              {(values.faq_items ?? resource.data?.faq_defaults ?? []).map(
                (item: Data, index: number) => {
                  const list =
                    values.faq_items ?? resource.data?.faq_defaults ?? [];
                  const change = (key: string, value: string) =>
                    update(
                      "faq_items",
                      list.map((r: Data, i: number) =>
                        i === index ? { ...r, [key]: value } : r,
                      ),
                    );
                  return (
                    <div
                      key={index}
                      className="rounded-lg border p-4 space-y-3"
                    >
                      <Field label={`Вопрос ${index + 1}`}>
                        <Input
                          maxLength={150}
                          value={item.q}
                          onChange={(e) => change("q", e.target.value)}
                        />
                      </Field>
                      <Field label="Ответ">
                        <Textarea
                          maxLength={1200}
                          value={item.a}
                          onChange={(e) => change("a", e.target.value)}
                        />
                      </Field>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          disabled={index === 0}
                          onClick={() => {
                            const next = [...list];
                            [next[index - 1], next[index]] = [
                              next[index],
                              next[index - 1],
                            ];
                            update("faq_items", next);
                          }}
                        >
                          Выше
                        </Button>
                        <Button
                          variant="outline"
                          disabled={index === list.length - 1}
                          onClick={() => {
                            const next = [...list];
                            [next[index + 1], next[index]] = [
                              next[index],
                              next[index + 1],
                            ];
                            update("faq_items", next);
                          }}
                        >
                          Ниже
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() =>
                            update(
                              "faq_items",
                              list.filter((_: Data, i: number) => i !== index),
                            )
                          }
                        >
                          Удалить
                        </Button>
                      </div>
                    </div>
                  );
                },
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  disabled={
                    (values.faq_items ?? resource.data?.faq_defaults ?? [])
                      .length >= 25
                  }
                  onClick={() =>
                    update("faq_items", [
                      ...(values.faq_items ??
                        resource.data?.faq_defaults ??
                        []),
                      { q: "", a: "" },
                    ])
                  }
                >
                  Добавить вопрос
                </Button>
                <Button
                  variant="outline"
                  onClick={() => update("faq_items", null)}
                >
                  Вернуть стандартные вопросы
                </Button>
              </div>
            </div>
          </Panel>
        )}
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
const PLATFORM_NAMES: [string, string][] = [
  ["ios", "iOS"],
  ["macos", "macOS"],
  ["appletv", "Apple TV"],
  ["android", "Android"],
  ["androidtv", "Android TV"],
  ["windows", "Windows"],
];
function AppIcon({ item }: { item: Data }) {
  const [broken, setBroken] = useState(false);
  const label = (item.mark || item.name || item.title || "?").slice(0, 2);
  return item.icon && !broken ? (
    <img
      src={item.icon}
      alt=""
      className="size-9 shrink-0 rounded-[10px] border object-cover"
      onError={() => setBroken(true)}
    />
  ) : (
    <span className="grid size-9 shrink-0 place-items-center rounded-[10px] border bg-muted text-xs font-semibold text-muted-foreground">
      {label}
    </span>
  );
}
function ListEditor({
  kind,
  list,
  defaults = [],
  onChange,
}: {
  kind: "payments" | "apps";
  list: Data[];
  defaults?: Data[];
  onChange: (v: Data[]) => void;
}) {
  // Built-in apps stay in the list for good: the admin hides one instead of deleting it.
  const builtIn = (item: Data) => defaults.some((d) => d.id === item.id);
  // Rows carry a stable key so an open form and focus follow the item while the list is reordered.
  const keys = useRef<number[]>([]),
    seq = useRef(0);
  while (keys.current.length < list.length) keys.current.push(++seq.current);
  keys.current.length = list.length;
  const [open, setOpen] = useState<number | null>(null),
    [dragging, setDragging] = useState<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const set = (index: number, key: string, value: any) =>
    onChange(
      list.map((item, i) => (i === index ? { ...item, [key]: value } : item)),
    );
  const move = (from: number, to: number) => {
    if (to < 0 || to >= list.length || from === to) return;
    const next = [...list],
      k = [...keys.current];
    next.splice(to, 0, ...next.splice(from, 1));
    k.splice(to, 0, ...k.splice(from, 1));
    keys.current = k;
    onChange(next);
  };
  const focusHandle = (key: number) =>
    requestAnimationFrame(() =>
      listRef.current
        ?.querySelector<HTMLElement>(`[data-handle="${key}"]`)
        ?.focus(),
    );
  // Set when a press turned into a drag, so the click that ends it does not open the row.
  const dragged = useRef(false);
  const startDrag = (e: React.PointerEvent, index: number) => {
    if (e.button !== 0) return;
    const onHandle = !!(e.target as HTMLElement).closest("[data-handle]");
    // Touch drags only by the handle: elsewhere a finger scrolls the page.
    if (!onHandle && e.pointerType !== "mouse") return;
    if ((e.target as HTMLElement).closest("[data-nodrag]")) return;
    if (onHandle) e.preventDefault();
    const key = keys.current[index],
      startY = e.clientY;
    let at = index,
      active = false;
    dragged.current = false;
    const onMove = (ev: PointerEvent) => {
      if (!active) {
        if (Math.abs(ev.clientY - startY) < 4) return;
        active = true;
        dragged.current = true;
        setDragging(key);
        document.body.style.userSelect = "none";
      }
      // The new place is how many other rows have their middle above the pointer.
      const others = Array.from(
        listRef.current?.querySelectorAll<HTMLElement>("[data-row]") || [],
      ).filter((r) => r.dataset.row !== String(key));
      const target = others.filter((r) => {
        const b = r.getBoundingClientRect();
        return b.top + b.height / 2 < ev.clientY;
      }).length;
      if (target !== at) {
        moveRef.current(at, target);
        at = target;
      }
    };
    const onUp = () => {
      setDragging(null);
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  };
  // The drag handler outlives renders; it always calls the latest move().
  const moveRef = useRef(move);
  moveRef.current = move;
  const name = (item: Data) =>
    item.title ||
    item.name ||
    (kind === "apps" ? "Новое приложение" : "Способ оплаты");
  const subtitle = (item: Data) =>
    kind === "apps"
      ? item.hidden
        ? "Скрыто в кабинете"
        : PLATFORM_NAMES.filter(([p]) => (item.platforms || []).includes(p))
            .map(([, l]) => l)
            .join(", ") || "Нет платформ"
      : item.available === false
        ? item.hint || "Не настроен на сервере"
        : item.enabled
          ? "Доступен клиентам"
          : "Скрыт";
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {kind === "apps"
          ? "Порядок такой же, как в кабинете: на каждой платформе первым предлагается верхнее подходящее приложение. Перетащите строку, чтобы поменять порядок. Переключатель скрывает приложение в кабинете."
          : "Порядок такой же, как у клиента при оплате. Перетащите строку, чтобы поменять порядок."}
      </p>
      <div ref={listRef} className="divide-y rounded-lg border">
        {list.map((item, i) => {
          const key = keys.current[i],
            isOpen = open === key,
            isDragged = dragging === key;
          return (
            <div
              key={key}
              data-row={key}
              className={
                "bg-background transition-shadow first:rounded-t-lg last:rounded-b-lg " +
                (isDragged
                  ? "relative z-10 shadow-lg ring-2 ring-primary/40"
                  : "")
              }
            >
              <div
                className="flex cursor-grab items-center gap-2 p-2 pr-3 active:cursor-grabbing sm:gap-3"
                onPointerDown={(e) => startDrag(e, i)}
              >
                <button
                  type="button"
                  data-handle={key}
                  aria-label={`Переместить «${name(item)}». Стрелки вверх и вниз меняют место`}
                  title="Перетащите, чтобы поменять порядок"
                  className="grid h-9 w-7 shrink-0 cursor-grab touch-none place-items-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing"
                  onKeyDown={(e) => {
                    const to =
                      e.key === "ArrowUp"
                        ? i - 1
                        : e.key === "ArrowDown"
                          ? i + 1
                          : null;
                    if (to === null) return;
                    e.preventDefault();
                    move(i, to);
                    focusHandle(key);
                  }}
                >
                  <GripVertical className="size-4" />
                </button>
                <span className="w-5 shrink-0 text-center text-sm tabular-nums text-muted-foreground">
                  {i + 1}
                </span>
                {kind === "apps" && <AppIcon item={item} />}
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  aria-expanded={isOpen}
                  onClick={() => {
                    if (dragged.current) dragged.current = false;
                    else setOpen(isOpen ? null : key);
                  }}
                >
                  <div className="truncate font-medium">{name(item)}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {subtitle(item)}
                  </div>
                </button>
                <div
                  data-nodrag
                  className="flex shrink-0 cursor-default items-center"
                >
                  {kind === "payments" && (
                    <Switch
                      className="mr-2"
                      aria-label={`Включить ${item.title}`}
                      checked={!!item.enabled}
                      onCheckedChange={(v) => set(i, "enabled", v)}
                    />
                  )}
                  {kind === "apps" && builtIn(item) && (
                    <Switch
                      className="mr-2"
                      aria-label={`Показывать ${item.name} в кабинете`}
                      title="Показывать в кабинете"
                      checked={!item.hidden}
                      onCheckedChange={(v) => set(i, "hidden", !v)}
                    />
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={isOpen ? "Свернуть" : "Изменить"}
                    onClick={() => setOpen(isOpen ? null : key)}
                  >
                    <ChevronDown
                      className={
                        "transition-transform " + (isOpen ? "rotate-180" : "")
                      }
                    />
                  </Button>
                </div>
              </div>
              {isOpen && (
                <div className="space-y-4 border-t bg-muted/20 p-4">
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
                          [
                            "guide",
                            "Ссылка «Как установить» (статья или видео)",
                          ],
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
                  {kind === "apps" && (
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
                              set(i, "stores", {
                                ...item.stores,
                                [p]: e.target.value,
                              })
                            }
                          />
                        </div>
                      ))}
                    </div>
                  )}
                  {kind === "apps" && !builtIn(item) && (
                    <div className="flex justify-end">
                      <Button
                        variant="outline"
                        className="text-destructive"
                        onClick={() => {
                          keys.current = keys.current.filter((_, j) => j !== i);
                          setOpen(null);
                          onChange(list.filter((_, j) => i !== j));
                        }}
                      >
                        <Trash2 />
                        Удалить приложение
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {kind === "apps" && (
        <Button
          variant="outline"
          onClick={() => {
            keys.current = [...keys.current, ++seq.current];
            setOpen(seq.current);
            onChange([
              ...list,
              {
                id: "",
                name: "",
                mark: "",
                icon: "",
                deep_link: "",
                guide: "",
                platforms: ["ios"],
                stores: {},
              },
            ]);
          }}
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
function SystemSettings() {
  const flags = useResource("flags"),
    job = useResource("subscriptions/replace", 5000),
    gone = useResource("users/deleted-accounts");
  const [goneResult, setGoneResult] = useState("");
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
      <Panel
        title="Удалённые аккаунты Telegram"
        description="Люди, которые удалили свой аккаунт в Telegram: сообщения им больше не доходят. Бот замечает их сам, когда сообщение не доставлено, а очистка ещё и проверяет тех, кто перестал получать сообщения. Кто ни разу не платил — удаляется. Кто платил — отключается: VPN и списания останавливаются, оплаты остаются в отчётах."
      >
        {gone.data && (
          <dl className="adm-rows mb-4">
            {[
              ["Удалённые, без оплат — удалим", gone.data.unpaid],
              ["Удалённые, платили — отключим", gone.data.paid],
              ["Не получают сообщения, ещё не проверены", gone.data.unchecked],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <dt>{k}</dt>
                <dd>{Number(v || 0).toLocaleString("ru-RU")}</dd>
              </div>
            ))}
          </dl>
        )}
        <Button
          variant="outline"
          onClick={() =>
            confirm({
              title: "Почистить удалённые аккаунты Telegram?",
              description:
                "Сначала бот проверит до 300 человек, которые не получают сообщения. Потом удалит до 200 профилей удалённых аккаунтов без оплат и отключит удалённые аккаунты с оплатами. Удаление необратимо.",
              danger: true,
              phrase: "ОЧИСТИТЬ",
              label: "Очистить",
              action: async () => {
                const r = await api("users/purge-deleted-accounts", {});
                setGoneResult(
                  `Проверено: ${r.checked}, нашлось удалённых: ${r.found}. Удалено: ${r.deleted}. Отключено: ${r.switched_off}. Пропущено: ${r.skipped}. Осталось: без оплат ${r.unpaid}, с оплатами ${r.paid}, не проверено ${r.unchecked}.`,
                );
                await gone.reload();
              },
            })
          }
        >
          Очистить удалённые аккаунты
        </Button>
        {goneResult && (
          <p className="text-sm mt-4" role="status">
            {goneResult}
          </p>
        )}
      </Panel>
    </div>
  );
}
