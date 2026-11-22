import { useState } from "react";
import { FriendNftPanel } from "./friend-nft";
import { api, money, useResource, type Data } from "@/lib/api";
import {
  ActionButton,
  DataTable,
  Empty,
  Failure,
  Field,
  Loading,
  Panel,
  useConfirm,
  useNavigate,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Plus,
  Copy,
} from "lucide-react";
import { toast } from "sonner";
import { RecordsPage } from "./records";
/** The whole of «Рост» at a glance: what a person cost and what they brought so far. */
function GrowthSummary({ items }: { items: Data[] }) {
  const sum = (rows: Data[], k: string) => rows.reduce((a, r) => a + Number(r[k] || 0), 0);
  const paidFor = items.filter((r) => r.spend_rub);
  const spend = sum(paidFor, "spend_rub"), users = sum(items, "users");
  const paidUsers = sum(paidFor, "users"), paidRevenue = sum(paidFor, "revenue");
  const cost = paidUsers ? Math.round(spend / paidUsers) : null;
  const ltv = users ? Math.round(sum(items, "revenue") / users) : null;
  const paidLtv = paidUsers ? Math.round(paidRevenue / paidUsers) : null;
  if (!items.length) return null;
  return (
    <div className="adm-funnel-sum adm-growth-sum">
      <div>
        <small>Расход</small>
        <b>{money(spend)}</b>
        <span>{paidFor.length ? `по ${paidFor.length} из ${items.length} ссылок` : "укажите расход у ссылок"}</span>
      </div>
      <div title="Расход ÷ пользователи, пришедшие по ссылкам с расходом">
        <small>Цена пользователя</small>
        <b>{cost != null ? money(cost) : "—"}</b>
        <span>{paidUsers} чел. по платным ссылкам</span>
      </div>
      <div title="Выручка ÷ все пришедшие по рекламным ссылкам. Ниже — по ссылкам с расходом">
        <small>LTV</small>
        <b>{ltv != null ? money(ltv) : "—"}</b>
        <span>{paidLtv != null ? `по платным ссылкам ${money(paidLtv)}` : `${users} чел.`}</span>
      </div>
      <div title="Выручка платных ссылок ÷ их расход">
        <small>Окупаемость</small>
        <b className={spend && paidRevenue >= spend ? "text-emerald-600" : ""}>{spend ? `${Math.round((paidRevenue / spend) * 100)}%` : "—"}</b>
        <span>{spend ? (paidLtv != null && cost ? `LTV в ${String(Math.round((paidLtv / cost) * 10) / 10).replace(".", ",")} раза ${paidLtv >= cost ? "больше" : "меньше"} цены` : "") : "нет расходов"}</span>
      </div>
    </div>
  );
}

export function AdsPage() {
  const resource = useResource("ads"),
    [open, setOpen] = useState(false),
    [title, setTitle] = useState(""),
    [slug, setSlug] = useState(""),
    [spendOf, setSpendOf] = useState<Data | null>(null),
    [spend, setSpend] = useState("");
  const confirm = useConfirm();
  const dash = <span className="text-muted-foreground">—</span>;
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Button onClick={() => setOpen(true)}>
          <Plus />
          Создать рекламную ссылку
        </Button>
      </div>
      {resource.data && <GrowthSummary items={resource.data.items || []} />}
      <TgAdsPanel onChange={resource.reload} />
      <PartnersPanel onChange={resource.reload} />
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <>
        <DataTable
          rows={resource.data.items || []}
          columns={[
            { key: "title", label: "Источник", cell: (r) => <span className="block min-w-40 leading-snug">{r.title}</span> },
            {
              key: "partner",
              label: "Рекламодатель",
              cell: (r) => r.partner || <span className="text-muted-foreground">—</span>,
            },
            {
              key: "tg",
              label: (
                <span title="Из Telegram Ads по объявлениям с этой ссылкой: показы, клики и CTR">Telegram Ads</span>
              ),
              cell: (r) =>
                r.tg ? (
                  <span className="block whitespace-nowrap tabular-nums leading-tight">
                    {Number(r.tg.views).toLocaleString("ru-RU")} показов
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {Number(r.tg.clicks).toLocaleString("ru-RU")} кликов
                      {r.tg.ctr != null ? ` · CTR ${String(r.tg.ctr).replace(".", ",")}%` : ""}
                    </span>
                  </span>
                ) : (
                  dash
                ),
            },
            { key: "clicks", label: "Переходы" },
            { key: "users", label: "Пользователи" },
            { key: "trial", label: "Пробный доступ" },
            {
              key: "connected",
              label: (
                <span title="Хотя бы раз подключились к VPN. Ниже — сколько из них были онлайн за последние 7 дней">
                  Подключились
                </span>
              ),
              cell: (r) => (
                <span className="block whitespace-nowrap tabular-nums leading-tight">
                  {Number(r.connected || 0).toLocaleString("ru-RU")}
                  <span className="block text-xs text-muted-foreground mt-0.5">
                    пользуются {Number(r.active || 0).toLocaleString("ru-RU")}
                  </span>
                </span>
              ),
            },
            {
              key: "retained",
              label: (
                <span title="Из пришедших 14+ дней назад — доля тех, кто был онлайн за последние 7 дней. Свежие ссылки сюда не попадают, пока у людей идут пробные дни.">
                  Держатся
                </span>
              ),
              cell: (r) =>
                r.retained_pct != null ? (
                  <span className="block whitespace-nowrap tabular-nums leading-tight">
                    {r.retained_pct}%
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {Number(r.retained || 0).toLocaleString("ru-RU")} из {Number(r.matured || 0).toLocaleString("ru-RU")} · 14+ дней
                    </span>
                  </span>
                ) : (
                  <span className="text-muted-foreground" title="Ещё никто не пришёл 14+ дней назад">рано</span>
                ),
            },
            {
              key: "paid",
              label: <span title="Хотя бы раз пополнили баланс. Ниже — сколько из них пользуются VPN сейчас (онлайн за 7 дней).">Оплатили</span>,
              cell: (r) => (
                <span className="block whitespace-nowrap tabular-nums leading-tight">
                  {Number(r.paid || 0).toLocaleString("ru-RU")}
                  <span className="block text-xs text-muted-foreground mt-0.5">
                    пользуются {Number(r.paying_active || 0).toLocaleString("ru-RU")}
                  </span>
                </span>
              ),
            },
            {
              key: "spend_rub",
              label: <span title="Сколько стоило размещение. Нажмите, чтобы указать.">Расход</span>,
              cell: (r) => (
                <button
                  type="button"
                  className="block whitespace-nowrap text-left tabular-nums leading-tight"
                  title={
                    r.tg?.spent != null
                      ? r.spend_auto
                        ? "Посчитано по Telegram Ads. Нажмите, чтобы указать вручную."
                        : "Указано вручную; ниже — расход в Telegram Ads"
                      : undefined
                  }
                  onClick={() => {
                    setSpendOf(r);
                    setSpend(r.spend_manual != null ? String(r.spend_manual) : "");
                  }}
                >
                  <span className="underline decoration-dotted underline-offset-4">
                    {r.spend_rub != null ? money(r.spend_rub) : <span className="text-muted-foreground">указать</span>}
                  </span>
                  {r.tg?.spent != null && (
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {Number(r.tg.spent).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} {r.tg.currency}
                    </span>
                  )}
                </button>
              ),
            },
            {
              key: "user_cost",
              label: <span title="Расход ÷ все пришедшие по ссылке. Ниже — расход ÷ оплатившие и ÷ тех, кто платил и пользуется сейчас.">Цена пользователя</span>,
              cell: (r) =>
                r.user_cost != null ? (
                  <span className="block whitespace-nowrap tabular-nums leading-tight">
                    {money(r.user_cost)}
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {r.payer_cost != null ? `платящего ${money(r.payer_cost)}` : "платящих нет"}
                      {r.live_payer_cost != null && <span className="block">живого платящего {money(r.live_payer_cost)}</span>}
                    </span>
                  </span>
                ) : (
                  dash
                ),
            },
            {
              key: "ltv",
              label: (
                <span title="Сколько в среднем уже заплатил один пришедший по ссылке (выручка ÷ пользователи). Ниже — на одного оплатившего. Зелёным — больше цены пользователя.">
                  LTV
                </span>
              ),
              cell: (r) =>
                r.ltv != null && r.revenue ? (
                  <span className="block whitespace-nowrap tabular-nums leading-tight">
                    <span className={r.user_cost != null && r.ltv >= r.user_cost ? "text-emerald-600 font-medium" : ""}>
                      {money(r.ltv)}
                    </span>
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      платящего {money(r.payer_ltv || 0)}
                    </span>
                  </span>
                ) : (
                  dash
                ),
            },
            {
              key: "revenue",
              label: (
                <span title="Все пополнения людей, пришедших по ссылке, и сколько это от расхода. Зелёным — уже окупилась.">
                  Выручка
                </span>
              ),
              cell: (r) =>
                r.revenue ? (
                  <span className={r.spend_rub && r.revenue >= r.spend_rub ? "text-emerald-600 font-medium" : ""}>
                    {money(r.revenue)}
                    {r.spend_rub ? ` · ${Math.round((r.revenue / r.spend_rub) * 100)}%` : ""}
                  </span>
                ) : (
                  dash
                ),
            },
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
        </>
      )}
      <Dialog open={!!spendOf} onOpenChange={(v) => !v && setSpendOf(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Расход на «{spendOf?.title}»</DialogTitle>
            <DialogDescription>
              Сколько вы заплатили за размещение. По нему считаются цена одного платящего и окупаемость. Для ссылок из
              Telegram Ads расход подставляется сам — указывайте, только если хотите его заменить.
            </DialogDescription>
          </DialogHeader>
          <Field label="Расход, ₽" hint="Пусто — убрать расход.">
            <Input
              aria-label="Расход, ₽"
              inputMode="numeric"
              value={spend}
              onChange={(e) => setSpend(e.target.value.replace(/\D/g, ""))}
              placeholder="Например, 3000"
            />
          </Field>
          <ActionButton
            onAction={async () => {
              await api(`ads/${spendOf?.id}/spend`, { spend_rub: spend });
              setSpendOf(null);
              toast.success("Расход сохранён");
              await resource.reload();
            }}
          >
            Сохранить
          </ActionButton>
        </DialogContent>
      </Dialog>
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
// Telegram Ads: the account's ads, synced every 30 minutes; ads are tied to links by start=ad_<code>.
function TgAdsPanel({ onChange }: { onChange: () => void }) {
  const resource = useResource("tg-ads");
  const d = resource.data;
  if (!d) return null;
  const r: Data = d.report || {};
  const unmatched: Data[] = d.unmatched || [];
  const num = (v: unknown) => Number(v || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
  return (
    <Panel
      title="Telegram Ads"
      description={
        d.configured
          ? "Объявления кабинета подтягиваются раз в 30 минут и привязываются к ссылкам ниже по коду start=ad_… — расход, показы и клики видны рядом с оплатами."
          : "Чтобы подтянуть статистику, вставьте API-токен кабинета в Настройки → Telegram Ads. Токен выдаётся на ads.telegram.org в настройках аккаунта, раздел API."
      }
    >
      {d.configured && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            {r.ok ? (
              <>
                <span>
                  Объявлений: <b>{r.ads ?? 0}</b> · привязано к ссылкам: <b>{r.matched ?? 0}</b>
                </span>
                {r.remaining != null && (
                  <span>
                    Остаток: <b>{num(r.remaining)} {r.currency}</b>
                  </span>
                )}
                <span className="text-muted-foreground">
                  {r.rate ? `курс ${Math.round(r.rate)} ₽ за 1 ${r.currency}` : "без курса — расход только в валюте кабинета (курс задаётся в Настройках → Telegram Ads)"}
                </span>
              </>
            ) : r.error ? (
              <span className="text-destructive">Ошибка: {r.error}</span>
            ) : (
              <span className="text-muted-foreground">Ещё не обновлялось</span>
            )}
            {r.at && <span className="text-muted-foreground">обновлено {new Date(r.at).toLocaleString("ru-RU")}</span>}
            <ActionButton
              variant="outline"
              onAction={async () => {
                const got = (await api("tg-ads", {})) as Data;
                resource.setData(got);
                onChange();
                toast.success(`Telegram Ads: объявлений ${got.ads ?? 0}, привязано ${got.matched ?? 0}`);
              }}
            >
              Обновить
            </ActionButton>
          </div>
          {unmatched.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm font-medium">Объявления без нашей ссылки — оплаты по ним не посчитать</div>
              <div className="rounded-md border divide-y text-sm">
                {unmatched.map((a) => (
                  <div key={a.ad_id} className="flex flex-wrap gap-x-3 gap-y-1 px-3 py-2">
                    <span className="font-medium">{a.title || `Объявление ${a.ad_id}`}</span>
                    <span className="text-muted-foreground break-all">{a.promote_url}</span>
                    <span className="ml-auto tabular-nums whitespace-nowrap">
                      {num(a.views)} показов · {num(a.spent)} {a.currency}
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Создайте рекламную ссылку и поставьте её в объявление вместо этой — со следующего обновления оно привяжется.
              </p>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
export function ReferralsPage() {
  const navigate = useNavigate();
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Button
          variant="outline"
          onClick={() => navigate("settings?section=referrals")}
        >
          Настроить программу
        </Button>
      </div>
      <FriendNftPanel />
      <RecordsPage kind="referrals" />
    </div>
  );
}
// Advertisers: each gets a secret page where they create ad links and see their stats.
function PartnersPanel({ onChange }: { onChange: () => Promise<void> }) {
  const resource = useResource("partners"),
    [open, setOpen] = useState(false),
    [title, setTitle] = useState("");
  const confirm = useConfirm();
  const copyLink = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Ссылка для рекламодателя скопирована");
    } catch {
      toast.success("Ссылка для рекламодателя", { description: url, duration: 20000 });
    }
  };
  const items = (resource.data?.items || []) as Data[];
  return (
    <Panel
      title="Рекламодатели"
      description="У каждого своя страница по секретной ссылке: там он создаёт рекламные ссылки и видит по ним статистику. Удалять ссылки он не может."
      action={
        <Button variant="outline" onClick={() => setOpen(true)}>
          <Plus />
          Добавить
        </Button>
      }
    >
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : !items.length ? (
        <Empty
          title="Рекламодателей пока нет"
          description="Добавьте рекламодателя и отправьте ему ссылку на его страницу."
        />
      ) : (
        <DataTable
          rows={items}
          columns={[
            {
              key: "title",
              label: "Рекламодатель",
              cell: (r) => (
                <span className="flex items-center gap-2">
                  {r.title}
                  {r.revoked && <Badge variant="secondary">Отключён</Badge>}
                </span>
              ),
            },
            { key: "links", label: "Ссылок" },
            { key: "clicks", label: "Переходы" },
            { key: "users", label: "Пользователи" },
            {
              key: "actions",
              label: "",
              cell: (r) =>
                r.revoked ? null : (
                  <div className="flex gap-2">
                    <ActionButton variant="outline" onAction={() => copyLink(r.url)}>
                      <Copy />
                      Ссылка
                    </ActionButton>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        confirm({
                          title: `Отключить доступ «${r.title}»?`,
                          description:
                            "Его страница перестанет открываться. Созданные им ссылки продолжат работать и останутся в статистике.",
                          action: async () => {
                            await api(`partners/${r.id}/revoke`, {});
                            await resource.reload();
                          },
                        })
                      }
                    >
                      Отключить
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
            <DialogTitle>Новый рекламодатель</DialogTitle>
            <DialogDescription>
              Название увидит и сам рекламодатель — в заголовке своей страницы.
            </DialogDescription>
          </DialogHeader>
          <Field label="Название">
            <Input
              aria-label="Название рекламодателя"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например, блогер Анна"
            />
          </Field>
          <ActionButton
            disabled={title.trim().length < 2}
            onAction={async () => {
              const data = await api("partners", { title });
              setOpen(false);
              setTitle("");
              await Promise.all([resource.reload(), onChange()]);
              if (data?.item?.url) await copyLink(data.item.url);
            }}
          >
            Создать и скопировать ссылку
          </ActionButton>
        </DialogContent>
      </Dialog>
    </Panel>
  );
}
