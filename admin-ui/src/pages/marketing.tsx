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
  EyeOff,
} from "lucide-react";
import { toast } from "sonner";
import { RecordsPage } from "./records";
const num = (v: unknown) => Number(v || 0).toLocaleString("ru-RU");
import { TgCabinet } from "./tg-cabinet";
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
      <TgCabinet onChange={resource.reload} />
      <PartnersPanel onChange={resource.reload} />
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <>
        <DataTable
          tableClass="adm-cards"
          rows={resource.data.items || []}
          columns={[
            {
              key: "title",
              label: "Источник",
              className: "adm-card-title",
              cell: (r) => (
                <span className="block min-w-32 max-w-56 leading-snug">
                  {r.title}
                  {r.partner && <span className="block text-xs text-muted-foreground mt-0.5">{r.partner}</span>}
                </span>
              ),
            },
            {
              key: "clicks",
              name: "Переходы",
              label: (
                <span title="Переходы по ссылке. Ниже — показы и CTR из Telegram Ads, если ссылка стоит в объявлениях">Переходы</span>
              ),
              cell: (r) => (
                <span className="block tabular-nums leading-tight">
                  {num(r.clicks)}
                  {r.tg && (
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      <span className="block whitespace-nowrap">{num(r.tg.views)} показов</span>
                      {r.tg.ctr != null && <span className="block whitespace-nowrap">CTR {String(r.tg.ctr).replace(".", ",")}%</span>}
                    </span>
                  )}
                </span>
              ),
            },
            {
              key: "users",
              name: "Пришли",
              label: <span title="Пришли в бота по ссылке. Ниже — сколько взяли пробный доступ">Пришли</span>,
              cell: (r) => (
                <span className="block tabular-nums leading-tight">
                  {num(r.users)}
                  <span className="block whitespace-nowrap text-xs text-muted-foreground mt-0.5">пробный {num(r.trial)}</span>
                </span>
              ),
            },
            {
              key: "connected",
              name: "Подключились",
              label: (
                <span title="Хотя бы раз подключились к VPN. Ниже — сколько онлайн за 7 дней и доля державшихся из пришедших 14+ дней назад">
                  Подключились
                </span>
              ),
              cell: (r) => (
                <span className="block tabular-nums leading-tight">
                  {num(r.connected)}
                  <span className="block whitespace-nowrap text-xs text-muted-foreground mt-0.5">пользуются {num(r.active)}</span>
                  <span
                    className="block whitespace-nowrap text-xs text-muted-foreground"
                    title={r.retained_pct != null ? `${num(r.retained)} из ${num(r.matured)} пришедших 14+ дней назад были онлайн за 7 дней` : "Ещё никто не пришёл 14+ дней назад"}
                  >
                    {r.retained_pct != null ? `держатся ${r.retained_pct}%` : "держатся: рано"}
                  </span>
                </span>
              ),
            },
            {
              key: "paid",
              name: "Оплатили",
              label: <span title="Хотя бы раз пополнили баланс. Ниже — сколько из них пользуются VPN сейчас (онлайн за 7 дней).">Оплатили</span>,
              cell: (r) => (
                <span className="block tabular-nums leading-tight">
                  {num(r.paid)}
                  <span className="block whitespace-nowrap text-xs text-muted-foreground mt-0.5">пользуются {num(r.paying_active)}</span>
                </span>
              ),
            },
            {
              key: "spend_rub",
              name: "Расход",
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
              name: "Цена",
              label: <span title="Расход ÷ все пришедшие по ссылке. Ниже — расход ÷ оплатившие и ÷ тех, кто платил и пользуется сейчас.">Цена</span>,
              cell: (r) =>
                r.user_cost != null ? (
                  <span className="block whitespace-nowrap tabular-nums leading-tight">
                    {money(r.user_cost)}
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {r.payer_cost != null ? `платящего ${money(r.payer_cost)}` : "платящих нет"}
                      {r.live_payer_cost != null && <span className="block">живого {money(r.live_payer_cost)}</span>}
                    </span>
                  </span>
                ) : (
                  dash
                ),
            },
            {
              key: "revenue",
              name: "Выручка",
              label: (
                <span title="Все пополнения пришедших по ссылке и сколько это от расхода. Ниже — LTV: выручка на одного пришедшего и на одного оплатившего. Зелёным — уже окупилась.">
                  Выручка
                </span>
              ),
              cell: (r) =>
                r.revenue ? (
                  <span className="block whitespace-nowrap tabular-nums leading-tight">
                    <span className={r.spend_rub && r.revenue >= r.spend_rub ? "text-emerald-600 font-medium" : ""}>
                      {money(r.revenue)}
                      {r.spend_rub ? ` · ${Math.round((r.revenue / r.spend_rub) * 100)}%` : ""}
                    </span>
                    {r.ltv != null && (
                      <span className="block text-xs text-muted-foreground mt-0.5">
                        LTV{" "}
                        <span className={r.user_cost != null && r.ltv >= r.user_cost ? "text-emerald-600" : ""}>{money(r.ltv)}</span>
                        {r.payer_ltv ? <span className="block">платящего {money(r.payer_ltv)}</span> : null}
                      </span>
                    )}
                  </span>
                ) : (
                  dash
                ),
            },
            {
              key: "actions",
              label: "",
              className: "adm-card-menu",
              cell: (r) => (
                <div className="flex gap-1">
                  <ActionButton
                    variant="ghost"
                    className="size-8 p-0"
                    aria-label="Скопировать ссылку"
                    onAction={async () => {
                      await navigator.clipboard.writeText(r.url);
                      toast.success("Ссылка скопирована");
                    }}
                  >
                    <Copy />
                  </ActionButton>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="size-8 p-0"
                    aria-label="Скрыть источник"
                    title="Скрыть источник"
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
                    <EyeOff />
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
