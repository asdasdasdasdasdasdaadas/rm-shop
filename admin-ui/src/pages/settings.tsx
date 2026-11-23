import { useEffect, useRef, useState, type ReactNode } from "react";
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
import { Plus, Save, Trash2, ChevronDown, GripVertical, Search as SearchIcon } from "lucide-react";
type Setting = {
  key: string;
  label: string;
  type?: string;
  hint?: string;
  min?: number;
  max?: number;
  /** Shown inside the field after the value: ₽, дней, %. */
  unit?: string;
  /** A switch this field belongs to: the field shows only while it is on. */
  parent?: string;
  /** A live example under the field, built from the current values. */
  example?: (v: Data) => string;
};
type Group = {
  id: string;
  title: string;
  description: string;
  nav: string;
  fields: Setting[];
};
const rub = (n: unknown) => `${Math.round(Number(n) || 0).toLocaleString("ru-RU")} ₽`;
const bonusExample = (min: unknown, pct: unknown) =>
  Number(min) && Number(pct) ? `Пополнит ${rub(min)} — получит ${rub(Number(min) * (1 + Number(pct) / 100))}` : "";
const NAV = ["Деньги", "Клиенты и доступ", "Бот и кабинет", "Интеграции", "Система"];
const groups: Group[] = [
  {
    id: "pricing",
    nav: "Деньги",
    title: "Тарифы и пополнение",
    description: "Сколько стоит VPN и какие суммы можно пополнить.",
    fields: [
      {
        key: "vpn_day_price_rub",
        label: "Цена суток за устройство",
        unit: "₽",
        type: "number",
        min: 1,
        max: 10000,
        example: (v) => (Number(v.vpn_day_price_rub) ? `Месяц на одно устройство ≈ ${rub(Number(v.vpn_day_price_rub) * 30)}` : ""),
      },
      { key: "balance_topup_min", label: "Минимальное пополнение", unit: "₽", type: "number", min: 1 },
      { key: "balance_topup_step", label: "Шаг выбора суммы", unit: "₽", type: "number", min: 1 },
      {
        key: "autopay_enabled",
        label: "Автопополнение через СБП",
        type: "switch",
        hint: "«Подписка» в кабинете: раз в 30 дней CISPay сам кладёт сумму на баланс через СБП. Пока выключено, её видят только админы — для проверки.",
      },
      {
        key: "autopay_grace_days",
        label: "Подписка: VPN не выключается",
        unit: "дней",
        type: "number",
        min: 0,
        max: 14,
        parent: "autopay_enabled",
        hint: "Сколько дней у подписчика VPN работает в минус, если баланс кончился или банк не провёл списание. У подписчиков нет напоминаний «баланс на исходе» и обещанного платежа.",
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
    id: "gifts",
    nav: "Деньги",
    title: "Бонусы и подарки",
    description: "Пробный доступ, обещанный платёж и бонусы к пополнению.",
    fields: [
      { key: "trial_enabled", label: "Пробный период", type: "switch", hint: "Новый человек получает бесплатные дни, чтобы попробовать VPN." },
      { key: "trial_days", label: "Длительность", unit: "дней", type: "number", min: 1, max: 90, parent: "trial_enabled" },
      { key: "trust_enabled", label: "Обещанный платёж", type: "switch", hint: "Доступ в долг на несколько дней, когда деньги кончились." },
      { key: "trust_days", label: "Срок", unit: "дней", type: "number", min: 1, max: 30, parent: "trust_enabled" },
      { key: "trust_fee_rub", label: "Комиссия", unit: "₽", type: "number", min: 0, parent: "trust_enabled" },
      {
        key: "first_bonus_enabled",
        label: "Бонус за первую оплату",
        type: "switch",
        hint: "Первое пополнение до конца подарка — плюс процент на баланс. Кабинет показывает отсчёт и открывающийся подарок.",
      },
      { key: "first_bonus_min_rub", label: "Пополнение от", unit: "₽", type: "number", min: 1, parent: "first_bonus_enabled" },
      {
        key: "first_bonus_percent",
        label: "Бонус к пополнению",
        unit: "%",
        type: "number",
        min: 1,
        max: 100,
        parent: "first_bonus_enabled",
        example: (v) => bonusExample(v.first_bonus_min_rub, v.first_bonus_percent),
      },
      {
        key: "return_bonus_enabled",
        label: "Бонус за возвращение",
        type: "switch",
        hint: "Через 10 дней после того, как у платившего клиента кончились деньги, бот предлагает процент к пополнению. Начисляется сам, один раз.",
      },
      { key: "return_bonus_min_rub", label: "Пополнение от", unit: "₽", type: "number", min: 1, parent: "return_bonus_enabled" },
      {
        key: "return_bonus_percent",
        label: "Бонус к пополнению",
        unit: "%",
        type: "number",
        min: 1,
        max: 100,
        parent: "return_bonus_enabled",
        example: (v) => bonusExample(v.return_bonus_min_rub, v.return_bonus_percent),
      },
      { key: "return_bonus_days", label: "Действует", unit: "дней", type: "number", min: 1, max: 60, parent: "return_bonus_enabled" },
    ],
  },
  {
    id: "referrals",
    nav: "Деньги",
    title: "Реферальная программа",
    description: "Другу 50 ₽ сразу, как он откроет меню бота; пригласившему 50 ₽, когда друг впервые подключит VPN. Один раз за каждого нового друга.",
    fields: [{ key: "referral_program_enabled", label: "Начислять реферальные награды", type: "switch" }],
  },
  {
    id: "ton",
    nav: "Деньги",
    title: "Оплата в TON",
    description: "Пополнение из кошелька Telegram прямо в чате с ботом. Деньги приходят на ваш кошелёк, ключи на сервере не хранятся.",
    fields: [
      {
        key: "ton_enabled",
        label: "Оплата в TON для всех",
        type: "switch",
        hint: "Выключено — оплату видят только админы (команда /ton), чтобы проверить перед запуском.",
      },
      { key: "ton_wallet", label: "Кошелёк для приёма", hint: "Адрес TON (UQ… или EQ…). Сюда приходят все платежи." },
      { key: "ton_rate_margin_pct", label: "Запас к курсу", unit: "%", type: "number", min: 0, max: 20, hint: "Защита от скачков курса за 10 минут, пока действует счёт." },
      {
        key: "toncenter_api_key",
        label: "Ключ Toncenter",
        hint: "Необязательно. Без ключа проверка медленнее (1 запрос в секунду). Ключ выдаёт бот @tonapibot.",
      },
    ],
  },
  {
    id: "access",
    nav: "Клиенты и доступ",
    title: "Доступ и устройства",
    description: "Сколько устройств можно подключить, проверка трафика и чистка панели.",
    fields: [
      { key: "max_devices", label: "Максимум устройств", unit: "шт.", type: "number", min: 5, max: 5, hint: "5 устройств на пользователя." },
      { key: "remnawave_hwid_limit", label: "Лимит HWID", unit: "шт.", type: "number", min: 0, max: 20, hint: "Аппаратных идентификаторов на подписку." },
      {
        key: "no_traffic_alert_enabled",
        label: "«Подключился, но трафика нет»",
        type: "switch",
        hint: "У нового устройства VPN включился, но трафика почти нет — обычно блокировка у провайдера или не то приложение. Одно уведомление на устройство.",
      },
      { key: "no_traffic_alert_min_mb", label: "Трафика меньше", unit: "МБ", type: "number", min: 1, max: 1000, parent: "no_traffic_alert_enabled" },
      {
        key: "no_traffic_alert_after_minutes",
        label: "Проверять через",
        unit: "мин",
        type: "number",
        min: 10,
        max: 1440,
        parent: "no_traffic_alert_enabled",
        hint: "После первого включения VPN на устройстве.",
      },
      {
        key: "connect_digest_enabled",
        label: "Сводка «Подключения за сутки»",
        type: "switch",
        hint: "Каждый день в 10:00 по Москве: новые устройства по системам и приложениям — сколько заработало, сколько без трафика.",
      },
      {
        key: "panel_cleanup_enabled",
        label: "Удалять устройства без подключения",
        type: "switch",
        hint: "Раз в день удаляет из панели и кабинета устройства, через которые ни разу не прошёл трафик. Людей с открытым обращением не трогает.",
      },
      { key: "panel_cleanup_days", label: "Через", unit: "дней", type: "number", min: 7, max: 365, parent: "panel_cleanup_enabled", hint: "После добавления устройства." },
    ],
  },
  {
    id: "sharing",
    nav: "Клиенты и доступ",
    title: "Шеринг подписки",
    description: "Раз в 10 минут бот берёт из панели IP каждого устройства: много IP — предупреждение, ещё больше — наказание.",
    fields: [
      {
        key: "sharing_alert_enabled",
        label: "Предупреждать о шеринге",
        type: "switch",
        hint: "Уведомление в живой канал или админам: кто, IP, трафик и кнопка «Сбросить подключения». По одному устройству не чаще раза в 3 дня.",
      },
      {
        key: "sharing_alert_simultaneous",
        label: "Если IP одновременно от",
        type: "number",
        min: 2,
        max: 50,
        parent: "sharing_alert_enabled",
        hint: "За последние 10 минут. Wi-Fi и мобильный вместе — это 2.",
      },
      {
        key: "sharing_alert_daily",
        label: "Или IP за сутки от",
        type: "number",
        min: 2,
        max: 500,
        parent: "sharing_alert_enabled",
        hint: "Мобильный интернет сам часто меняет IP, поэтому порог выше.",
      },
      {
        key: "sharing_block_enabled",
        label: "Блокировать за шеринг",
        type: "switch",
        hint: "Бот сам выключает ключи человека, ставит пометку «Шеринг» и блокирует в боте. Админам — кнопка «Разблокировать и вернуть баланс».",
      },
      {
        key: "sharing_block_simultaneous",
        label: "Если IP одновременно от",
        type: "number",
        min: 3,
        max: 50,
        parent: "sharing_block_enabled",
        hint: "Выше порога предупреждения, чтобы не задеть телефон с Wi-Fi и LTE.",
      },
      {
        key: "sharing_block_daily",
        label: "Или IP за сутки от",
        type: "number",
        min: 5,
        max: 500,
        parent: "sharing_block_enabled",
        hint: "Мобильный интернет за день даёт 5–10 адресов.",
      },
      {
        key: "sharing_delete_device",
        label: "Удалять устройство",
        type: "switch",
        parent: "sharing_block_enabled",
        hint: "Устройство, с которого раздавали ключ, удаляется. Остальные только выключаются.",
      },
      {
        key: "sharing_notify_user",
        label: "Сообщать человеку",
        type: "switch",
        parent: "sharing_block_enabled",
        hint: "Бот сразу пишет «Доступ ограничен». Выключено — узнает при следующем сообщении боту.",
      },
      {
        key: "sharing_penalty_enabled",
        label: "Штраф на баланс",
        type: "switch",
        parent: "sharing_block_enabled",
        hint: "Сколько списали, запоминается: при разблокировке вернётся ровно это.",
      },
      {
        key: "sharing_penalty_balance_rub",
        label: "Баланс после штрафа",
        unit: "₽",
        type: "number",
        min: -1000000,
        max: 0,
        parent: "sharing_penalty_enabled",
        hint: "Например −100000. Если баланс уже ниже — не трогаем.",
      },
    ],
  },
  {
    id: "general",
    nav: "Бот и кабинет",
    title: "Сервис и поддержка",
    description: "Что клиент видит в боте и личном кабинете.",
    fields: [
      { key: "brand_name", label: "Название сервиса" },
      { key: "support_username", label: "Telegram поддержки", hint: "Username или ссылка на поддержку." },
      { key: "legal_offer_url", label: "Ссылка на оферту", type: "url" },
      { key: "legal_privacy_url", label: "Политика конфиденциальности", type: "url" },
      { key: "admin_live_chat_id", label: "Канал обращений", hint: "ID приватного канала, в котором бот — администратор." },
      { key: "welcome_sticker_file_id", label: "Стикер приветствия", hint: "Telegram file_id. Пусто — без стикера." },
      {
        key: "welcome_tariff_enabled",
        label: "Тариф и условия в приветствии",
        type: "switch",
        hint: "Цена за день, баланс вместо подписки и минимальное пополнение во втором сообщении после /start.",
      },
      {
        key: "widgets_enabled",
        label: "Карточки-виджеты в чате",
        type: "switch",
        hint: "Баланс, чеки, подарки, рефералка и обращения приходят живыми карточками. Выключите, если Telegram ограничивает виджеты.",
      },
      {
        key: "frog_user_ids",
        label: "Лягушка: кому показывать всегда",
        hint: "Telegram ID или @username через запятую. Живую лягушку видят все; эти люди видят её и во время A/B-теста и в него не попадают.",
      },
      {
        key: "cases_enabled",
        label: "Кейсы с лягушкой",
        type: "switch",
        hint: "Рулетка в кабинете: в кейсе одна из 48 лягушек разной редкости, выбранная живёт на главной. Кейсы можно выдавать вручную в карточке клиента.",
      },
      { key: "case_topup_min_rub", label: "Кейс за пополнение от", unit: "₽", type: "number", min: 0, parent: "cases_enabled", hint: "0 — за пополнения кейсы не даём." },
      { key: "case_subscription_count", label: "Кейсов за месяц подписки", type: "number", min: 0, max: 20, parent: "cases_enabled" },
      { key: "case_dup_bonus_rub", label: "Повторная лягушка", unit: "₽ на баланс", type: "number", min: 0, max: 1000, parent: "cases_enabled" },
    ],
  },
  {
    id: "tg_ads",
    nav: "Интеграции",
    title: "Telegram Ads",
    description: "Показы, клики и расход по каждой рекламной ссылке в «Росте». Обновляется раз в 30 минут.",
    fields: [
      {
        key: "tg_ads_token",
        label: "API-токен кабинета",
        hint: "ads.telegram.org → настройки аккаунта → API. Пусто — статистика не загружается.",
      },
      {
        key: "tg_ads_rub_rate",
        label: "Курс валюты кабинета",
        unit: "₽",
        type: "number",
        min: 0,
        max: 100000,
        hint: "Рублей за 1 единицу. 0 — для TON берётся рыночный курс; для EUR и Stars укажите вручную.",
      },
    ],
  },
];
/** Sections that are not a list of fields: their own editors. */
const SPECIAL: { id: string; title: string; nav: string; keys: string[] }[] = [
  { id: "payments", title: "Способы оплаты", nav: "Деньги", keys: ["pay_methods"] },
  { id: "notices", title: "Тексты бота", nav: "Бот и кабинет", keys: ["notices"] },
  { id: "faq", title: "Частые вопросы", nav: "Бот и кабинет", keys: ["faq_items"] },
  { id: "apps", title: "VPN-приложения", nav: "Бот и кабинет", keys: ["vpn_apps"] },
  { id: "system", title: "Работа системы", nav: "Система", keys: [] },
];
const SECTIONS = [
  ...groups.map((g) => ({ id: g.id, title: g.title, nav: g.nav, keys: g.fields.map((f) => f.key) })),
  ...SPECIAL,
];
export const saveSettingsPatch = (patch: Data) =>
  saveSettingsPatchWith(api, patch);
export function SettingsPage({ initial = "general" }: { initial?: string }) {
  const resource = useResource("settings");
  const [section, setSection] = useState(
      initial === "automation" || initial === "welcome" ? "general" : SECTIONS.some((x) => x.id === initial) ? initial : "pricing",
    ),
    [patch, setPatch] = useState<Data>({}),
    [query, setQuery] = useState(""),
    [error, setError] = useState("");
  const saving = useRef(false);
  const dirty = Object.keys(patch).length > 0;
  useDirty(dirty);
  const values = { ...resource.data?.values, ...patch };
  const update = (key: string, value: any) => {
    setPatch((p) => ({ ...p, [key]: value }));
    setError("");
  };
  // Unsaved changes travel between sections: one save for everything.
  const changeSection = (next: string) => {
    setQuery("");
    setSection(next);
    window.scrollTo({ top: 0 });
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
  const changed = Object.keys(patch);
  const q = query.trim().toLowerCase();
  const view = q ? "" : section;
  // A field matches by its own name or explanation, or by the switch it belongs to; it shows where it lives.
  const owner = (g: Group, f: Setting) => g.fields.find((x) => x.key === f.parent);
  const found = q
    ? groups.flatMap((g) =>
        g.fields
          .filter((f) => (f.label + " " + (f.hint || "") + " " + (owner(g, f)?.label || "")).toLowerCase().includes(q))
          .map((f) => ({ group: g, field: f, context: [g.title, owner(g, f)?.label].filter(Boolean).join(" → ") })),
      )
    : [];
  const foundSpecial = q ? SECTIONS.filter((x) => x.title.toLowerCase().includes(q)) : [];
  return (
    <div className="adm-set">
      <aside className="adm-set-nav">
        <label className="adm-set-search">
          <SearchIcon aria-hidden="true" />
          <input
            type="search"
            aria-label="Поиск по настройкам"
            placeholder="Поиск по настройкам"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        {NAV.map((nav) => (
          <div key={nav} className="adm-set-navgroup">
            <h3>{nav}</h3>
            {SECTIONS.filter((x) => x.nav === nav).map((x) => (
              <button
                key={x.id}
                type="button"
                aria-current={section === x.id && !q ? "page" : undefined}
                onClick={() => changeSection(x.id)}
              >
                {x.title}
                {x.keys.some((k) => k in patch) && <i aria-label="есть изменения" />}
              </button>
            ))}
          </div>
        ))}
      </aside>
      <form
        id="settings-section"
        className="min-w-0 space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          void save().catch(() => {});
        }}
      >
        {q ? (
          <>
            <header className="adm-set-head">
              <h2>Поиск: «{query.trim()}»</h2>
              <p>{found.length || foundSpecial.length ? "Можно менять прямо здесь." : "Ничего не нашлось."}</p>
            </header>
            {foundSpecial.length > 0 && (
              <div className="adm-set-card">
                {foundSpecial.map((x) => (
                  <button key={x.id} type="button" className="adm-set-row adm-set-jump" onClick={() => changeSection(x.id)}>
                    <span>{x.title}</span>
                    <span className="adm-set-muted">{x.nav} →</span>
                  </button>
                ))}
              </div>
            )}
            {found.length > 0 && (
              <div className="adm-set-card">
                {found.map(({ field: f, context }) => (
                  <SettingRow key={f.key} f={f} values={values} patch={patch} update={update} context={context} />
                ))}
              </div>
            )}
          </>
        ) : (
          group && (
            <>
              <header className="adm-set-head">
                <h2>{group.title}</h2>
                <p>{group.description}</p>
              </header>
              <SettingCards fields={group.fields} values={values} patch={patch} update={update} />
            </>
          )
        )}
        <button type="submit" className="sr-only">
          Сохранить настройки
        </button>
      </form>
      <div className="adm-set-rest min-w-0 space-y-5">
        {view === "sharing" && <SharingCheck />}
        {view === "payments" && (
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
        {view === "apps" && (
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
        {view === "notices" && (
          <NoticeEditor
            fields={resource.data.notice_fields || []}
            values={values.notices || {}}
            onChange={(v) => update("notices", v)}
          />
        )}
        {view === "faq" && (
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
        {view === "system" && <SystemSettings />}
        {dirty && (
          <div className="adm-set-bar">
            <span className="text-sm">
              Есть несохранённые изменения
              <span className="adm-set-muted"> · {changed.length} {changed.length === 1 ? "настройка" : changed.length < 5 ? "настройки" : "настроек"}</span>
            </span>
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
type RowProps = {
  values: Data;
  patch: Data;
  update: (key: string, value: any) => void;
};
/** One setting as a row: name and explanation on the left, the control on the right. */
function SettingRow({ f, values, patch, update, context }: RowProps & { f: Setting; context?: string }) {
  const id = "set-" + f.key;
  const example = f.example?.(values);
  return (
    <div className={"adm-set-row" + (f.key in patch ? " changed" : "")}>
      <div className="adm-set-label">
        <label htmlFor={id}>{f.label}</label>
        {context && <span className="adm-set-muted"> · {context}</span>}
        {f.hint && <p id={id + "-hint"}>{f.hint}</p>}
        {example && <p className="adm-set-example">{example}</p>}
      </div>
      {f.type === "switch" ? (
        <Switch
          id={id}
          aria-label={f.label}
          aria-describedby={f.hint ? id + "-hint" : undefined}
          checked={!!values[f.key]}
          onCheckedChange={(v) => update(f.key, v)}
        />
      ) : (
        <span className={"adm-set-input" + (f.type === "number" ? " num" : "")}>
          <input
            id={id}
            aria-label={f.label}
            aria-describedby={f.hint ? id + "-hint" : undefined}
            type={f.type || "text"}
            min={f.min}
            max={f.max}
            step={f.type === "number" ? "1" : undefined}
            required={f.type === "number" || f.type === "url" || f.key === "brand_name" || f.key === "support_username"}
            value={values[f.key] ?? ""}
            onChange={(e) =>
              update(f.key, f.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value)
            }
          />
          {f.unit && <em>{f.unit}</em>}
        </span>
      )}
    </div>
  );
}
/**
 * A section as cards: plain fields together in one card; a switch that has settings of its own becomes a card
 * with the switch in its header and its settings below, shown only while it is on.
 */
function SettingCards({ fields, ...row }: RowProps & { fields: Setting[] }) {
  const parents = new Set(fields.map((f) => f.parent).filter(Boolean));
  const childrenOf = (key: string): Setting[] => fields.filter((f) => f.parent === key);
  const renderChildren = (key: string): ReactNode =>
    childrenOf(key).map((c) =>
      parents.has(c.key) ? (
        <div key={c.key} className="adm-set-sub">
          <SettingRow f={c} {...row} />
          {row.values[c.key] && <div className="adm-set-nested">{renderChildren(c.key)}</div>}
        </div>
      ) : (
        <SettingRow key={c.key} f={c} {...row} />
      ),
    );
  const out: ReactNode[] = [];
  let plain: Setting[] = [];
  const flush = () => {
    if (plain.length)
      out.push(
        <div key={"plain-" + plain[0].key} className="adm-set-card">
          {plain.map((f) => (
            <SettingRow key={f.key} f={f} {...row} />
          ))}
        </div>,
      );
    plain = [];
  };
  for (const f of fields) {
    if (f.parent) continue;
    if (parents.has(f.key)) {
      flush();
      const on = !!row.values[f.key];
      out.push(
        <div key={f.key} className={"adm-set-card adm-set-feature" + (on ? " on" : "")}>
          <SettingRow f={f} {...row} />
          {on && <div className="adm-set-children">{renderChildren(f.key)}</div>}
        </div>,
      );
    } else plain.push(f);
  }
  flush();
  return <>{out}</>;
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
function RegionFilterPanel() {
  const res = useResource("region-filter");
  const confirm = useConfirm();
  const [all, setAll] = useState(false);
  const d: Data = res.data || {};
  const cands: Data[] = d.candidates || [];
  const recent: Data[] = d.recent || [];
  const when = (v: string) => (v ? new Date(v).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "");
  const purge = () =>
    confirm({
      title: `Удалить ${cands.length} пользователей из Ирана?`,
      description:
        "Удалятся профили и устройства, в том числе в панели. Платившие сюда не попадают. Из статистики они пропадут, а бот больше не будет им отвечать.",
      danger: true,
      phrase: "УДАЛИТЬ",
      label: "Удалить",
      action: async () => {
        const r = await api("region-filter", { action: "purge", ids: cands.map((c) => c.telegram_id) });
        toast.success(`Удалено: ${r.deleted}`);
        await res.reload();
      },
    });
  const allow = async (id: number) => {
    await api("region-filter", { action: "allow", telegram_id: id });
    toast.success("Пропустили: бот снова отвечает этому человеку");
    await res.reload();
  };
  return (
    <Panel
      title="Пользователи из Ирана"
      description="В Иране заблокирован Telegram: оттуда приходят через поиск, берут подарок и создают устройства, но оплатить не могут, и VPN у них не работает. Новых бот узнаёт по персидскому языку Telegram или персидским буквам в имени: отвечает один раз «сервис недоступен в вашем регионе» и больше ничего — в базу и статистику они не попадают."
    >
      {res.error && <p className="text-sm text-destructive">{res.error}</p>}
      {res.data && (
        <>
          <dl className="adm-rows mb-4">
            {[
              ["Фильтр", d.enabled ? "включён" : "выключен (REGION_FILTER_ENABLED=false)"],
              ["Не пустили всего", d.rejected],
              ["Не пустили за сутки", d.day],
              ["Уже в базе, похожи на Иран, не платили", cands.length],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between gap-4 py-1 text-sm">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="font-medium">{v}</dd>
              </div>
            ))}
          </dl>
          {!!cands.length && (
            <>
              <div className="text-sm border rounded-lg divide-y mb-3">
                {(all ? cands : cands.slice(0, 8)).map((c) => (
                  <div key={c.telegram_id} className="flex justify-between gap-3 px-3 py-2">
                    <span className="truncate">
                      {c.first_name || "—"}
                      {c.username ? <span className="text-muted-foreground"> @{c.username}</span> : null}
                    </span>
                    <span className="text-muted-foreground shrink-0">
                      {c.device_count ? `устройств: ${c.device_count} · ` : ""}
                      {when(c.created_at)}
                    </span>
                  </div>
                ))}
              </div>
              {cands.length > 8 && !all && (
                <button type="button" className="text-sm underline text-muted-foreground mb-3" onClick={() => setAll(true)}>
                  Показать всех {cands.length}
                </button>
              )}
              <div>
                <Button variant="outline" onClick={purge}>
                  Удалить {cands.length} из базы
                </Button>
              </div>
            </>
          )}
          {!!recent.length && (
            <details className="mt-4 text-sm">
              <summary className="cursor-pointer font-medium">Кого не пустили недавно</summary>
              <div className="border rounded-lg divide-y mt-2">
                {recent.map((r) => (
                  <div key={r.telegram_id} className="flex justify-between gap-3 px-3 py-2">
                    <span className="truncate">
                      {r.first_name || "—"}
                      {r.username ? <span className="text-muted-foreground"> @{r.username}</span> : null}
                      <span className="text-muted-foreground"> · {r.reason}{r.hits > 1 ? ` · писал ${r.hits} раз` : ""}</span>
                    </span>
                    {r.allowed_at ? (
                      <span className="text-muted-foreground shrink-0">пропущен</span>
                    ) : (
                      <button type="button" className="underline text-muted-foreground shrink-0" onClick={() => allow(r.telegram_id)}>
                        Пропустить
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </details>
          )}
        </>
      )}
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
      <div className="adm-set-danger">
      <h3>Осторожно: действует сразу на весь сервис</h3>
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
      </div>
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
        description="Удаление пользователей, которые заблокировали бота и не воспользовались сервисом. За запуск — до 200 записей."
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
                  `Удалено: ${r.deleted}. Пропущено: ${r.skipped}. Осталось: ${r.remaining}.`,
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
      <RegionFilterPanel />
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

// «Проверить сейчас»: one full sharing pass right away, then who has the most IPs.
function SharingCheck() {
  const resource = useResource("sharing-check");
  const [last, setLast] = useState<Data | null>(null);
  const top: Data[] = (last || resource.data)?.top || [];
  const who = (u: Data) =>
    u.username ? `@${u.username}` : u.first_name || String(u.telegram_id);
  return (
    <Panel
      title="Проверить сейчас"
      description="Забрать IP из панели и применить настройки выше прямо сейчас, не дожидаясь 10 минут. Сохраните настройки перед проверкой."
    >
      <div className="space-y-4">
        <ActionButton
          onAction={async () => {
            const r = (await api("sharing-check", {})) as Data;
            setLast(r);
            const n = (r.caught || []).length;
            toast.success(
              n
                ? `Поймано: ${n}`
                : `Шеринга нет · IP записано: ${r.ips ?? 0}${r.warned ? ` · предупреждений: ${r.warned}` : ""}`,
            );
          }}
        >
          Проверить сейчас
        </ActionButton>
        {last && (last.caught || []).length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Поймано и наказано</div>
            {(last.caught as Data[]).map((c) => (
              <div key={c.telegram_id} className="rounded-md border p-3 text-sm">
                <div className="font-medium">
                  {who(c)} · {c.title || "устройство"} · {c.now_ips} IP сейчас · {c.day_ips} за сутки
                </div>
                <ul className="mt-1 text-muted-foreground">
                  {(c.actions as string[]).map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
        {last && (
          <div className="text-sm text-muted-foreground">
            IP записано: {last.ips ?? 0} · предупреждений отправлено: {last.warned ?? 0}
          </div>
        )}
        <div className="space-y-2">
          <div className="text-sm font-medium">Больше всего IP сейчас</div>
          {resource.error ? (
            <Failure message={resource.error} retry={resource.reload} />
          ) : top.length === 0 ? (
            <Empty title="Данных пока нет" description="Появятся после первой проверки." />
          ) : (
            <div className="rounded-md border divide-y text-sm">
              {top.map((t) => (
                <div key={t.device_id} className="flex flex-wrap gap-x-3 gap-y-1 px-3 py-2">
                  <span className="font-medium">{who(t)}</span>
                  <span className="text-muted-foreground">{t.title || "устройство"}</span>
                  <span className="ml-auto tabular-nums">
                    {t.now_ips} сейчас · {t.day_ips} за сутки
                  </span>
                  {t.blocked && <Badge variant="destructive">заблокирован</Badge>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
