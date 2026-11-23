// Telegram Ads cabinet inside «Рост», in the look of ads.telegram.org: pill tabs, a flat zebra table, blue
// diamond prices. Data: /admin/api/tg-ads/* (app/tg_cabinet.py). The autobid itself runs on the server.
import { Fragment, useMemo, useState, type ReactNode } from "react";
import { api, useResource, type Data } from "@/lib/api";
import { ActionButton, Failure, Loading, useConfirm } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bot, ChevronDown, MoreVertical, Plus, RefreshCw, Search, User } from "lucide-react";
import { toast } from "sonner";

const num = (v: unknown, d = 0) =>
  Number(v || 0).toLocaleString("ru-RU", { maximumFractionDigits: d, minimumFractionDigits: 0 });
const price = (v: unknown) => Number(v || 0).toFixed(2);
const time = (v: unknown) =>
  v ? new Date(String(v)).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
const ago = (v: unknown) => {
  if (!v) return "давно";
  const m = Math.max(0, Math.round((Date.now() - new Date(String(v)).getTime()) / 60000));
  return m < 1 ? "только что" : m < 60 ? `${m} мин назад` : m < 48 * 60 ? `${Math.round(m / 60)} ч назад` : `${Math.round(m / 1440)} дн назад`;
};

/** The blue diamond Telegram Ads puts before every amount. */
export function Gem({ className = "" }: { className?: string }) {
  return (
    <svg className={"tga-gem " + className} viewBox="0 0 16 16" aria-hidden>
      <path d="M8 14.5 1.2 6.3 3.6 2.5h8.8l2.4 3.8L8 14.5Z" fill="currentColor" />
      <path d="M1.2 6.3h13.6M5.3 2.5 4.4 6.3 8 14.5l3.6-8.2-.9-3.8" stroke="var(--tga-gem-line)" strokeWidth=".9" fill="none" />
    </svg>
  );
}
const Amount = ({ v, cur }: { v: unknown; cur?: string }) => (
  <span className="tga-amount">
    {cur && cur !== "TON" ? null : <Gem />}
    {price(v)}
    {cur && cur !== "TON" ? ` ${cur}` : ""}
  </span>
);

function Spark({ values, height = 34, className = "" }: { values: number[]; height?: number; className?: string }) {
  const max = Math.max(1, ...values);
  const w = Math.max(1, values.length);
  return (
    <svg className={"tga-spark " + className} viewBox={`0 0 ${w * 4} ${height}`} preserveAspectRatio="none" aria-hidden>
      {values.map((v, i) => {
        const h = v ? Math.max(2, (v / max) * (height - 2)) : 1;
        return <rect key={i} x={i * 4 + 0.5} y={height - h} width={3} height={h} rx={1} className={v ? "on" : "off"} />;
      })}
    </svg>
  );
}

function Delta({ now, before }: { now: number; before: number }) {
  if (!before && !now) return <span className="tga-delta">—</span>;
  if (!before) return <span className="tga-delta up">новое</span>;
  const pct = Math.round(((now - before) / before) * 100);
  return <span className={"tga-delta " + (pct > 0 ? "up" : pct < 0 ? "down" : "")}>{pct > 0 ? "+" : ""}{pct}%</span>;
}

const STATUS: Record<string, [string, string]> = {
  active: ["Active", "ok"],
  in_review: ["In Review", "wait"],
  ready_for_review: ["Не отправлено", "wait"],
  on_hold: ["On Hold", "muted"],
  stopped: ["Stopped", "muted"],
  declined: ["Declined", "bad"],
};
const AB: Record<string, string> = {
  idle: "muted", watching: "wait", searching: "wait", probing: "wait", holding: "ok", ceiling: "warn",
  dead: "bad", review: "bad", paused: "muted", empty: "muted", expensive: "warn",
};
const HARD = { max: 5 };   // the autobid's hard ceiling, from the cabinet response
const autoTop = (cpm: unknown) => price(Math.min(Number(cpm || 0) * 1.3, HARD.max));
/** What the server said after turning the autobid on: the ceiling it took and the daily limit it set. */
const autobidToast = (got: Data, ok: string) => {
  if (got.review) toast.warning("Telegram отправил объявление на модерацию после этой правки");
  else toast.success(`${ok}${got.max_cpm ? `: потолок ${price(got.max_cpm)}` : ""}${got.daily_limit ? `, лимит в день ${price(got.daily_limit)}` : ""}`);
  if (got.limit_error) toast.error(got.limit_error);
};
const VERDICT_AD: Record<string, [string, string]> = {
  scale: ["масштабировать", "ok"], hold: ["держать", "wait"], stop: ["выключить", "bad"], early: ["рано", "muted"],
};
const days = (v: number | null | undefined) =>
  v == null ? null : v < 1 ? `~${Math.max(1, Math.round(v * 24))} ч` : `~${String(Math.round(v * 10) / 10).replace(".", ",")} дн`;

const BRAND = { name: "VPN" };   // the bot's name, from the cabinet response

type Tab = "overview" | "ads" | "results" | "hours" | "places" | "log";
const TABS: Record<Tab, string> = { overview: "Обзор", ads: "Объявления", results: "Итог", hours: "Часы", places: "Площадки", log: "Журнал" };

export function TgCabinet({ onChange }: { onChange: () => void }) {
  const [tab, setTab] = useState<Tab>("overview"),
    [period, setPeriod] = useState("7d"),
    [creating, setCreating] = useState<false | { kind: string; places: string }>(false),
    [scheduleFor, setScheduleFor] = useState<number | null>(null);
  const head = useResource("tg-ads");
  const cab = useResource(`tg-ads/cabinet?period=${period}`, 60_000);
  const report: Data = head.data?.report || {};
  const d = cab.data;
  if (d?.brand) BRAND.name = d.brand;
  if (d?.hard_max_cpm) HARD.max = d.hard_max_cpm;
  if (head.data && !head.data.configured)
    return (
      <section className="tga">
        <div className="tga-head"><b>Telegram Ads</b></div>
        <p className="tga-hint">
          Чтобы бот вёл рекламу, вставьте API-токен кабинета в Настройки → Telegram Ads. Токен — на ads.telegram.org,
          вкладка API в настройках аккаунта.
        </p>
      </section>
    );
  const reload = async () => {
    await Promise.all([cab.reload(), head.reload()]);
    onChange();
  };
  return (
    <section className="tga">
      <div className="tga-head">
        <div className="tga-crumbs">
          <span className="tga-logo">📣</span>
          <b>Telegram Ads</b>
          <span className="tga-sep">/</span>
          <span>{TABS[tab]}</span>
        </div>
        <div className="tga-head-right">
          <span className="tga-balance">
            Баланс: <Amount v={report.remaining} cur={report.currency} />
          </span>
          <span className="tga-muted">{report.at ? `обновлено ${ago(report.at)}` : report.error ? `ошибка: ${report.error}` : ""}</span>
          <ActionButton
            variant="ghost"
            className="tga-icon-btn"
            aria-label="Обновить из Telegram Ads"
            onAction={async () => {
              const got = await api("tg-ads", {});
              toast.success(`Обновлено: объявлений ${got.ads ?? 0}`);
              await reload();
            }}
          >
            <RefreshCw />
          </ActionButton>
          <Button className="tga-pill-btn" onClick={() => setCreating({ kind: "bots", places: "" })}>
            <Plus /> Создать объявление
          </Button>
        </div>
      </div>
      <nav className="tga-tabs">
        {(Object.keys(TABS) as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
            {TABS[t]}
          </button>
        ))}
        {(tab === "overview" || tab === "ads") && (
          <div className="tga-period">
            {[["today", "Сегодня"], ["7d", "7 дней"], ["30d", "30 дней"]].map(([k, l]) => (
              <button key={k} className={period === k ? "on" : ""} onClick={() => setPeriod(k)}>{l}</button>
            ))}
          </div>
        )}
      </nav>
      {cab.error ? (
        <Failure message={cab.error} retry={cab.reload} />
      ) : !d ? (
        <Loading />
      ) : tab === "overview" ? (
        <Overview d={d} unmatched={head.data?.unmatched || []} onAds={() => setTab("ads")} reload={reload} />
      ) : tab === "ads" ? (
        <AdsTable d={d} reload={reload} onSchedule={(id) => { setScheduleFor(id); setTab("hours"); }} />
      ) : tab === "results" ? (
        <Results onLaunch={(kind, places) => setCreating({ kind, places })} />
      ) : tab === "hours" ? (
        <Hours ads={d.ads || []} initial={scheduleFor} reload={reload} />
      ) : tab === "places" ? (
        <Places onLaunch={(kind, places) => setCreating({ kind, places })} />
      ) : (
        <Log items={d.log || []} />
      )}
      <CreateAd open={!!creating} preset={creating || undefined} onClose={() => setCreating(false)} balance={report.remaining} currency={report.currency} bot={d?.bot} reload={reload} />
    </section>
  );
}

// ------------------------------------------------------------------------------------------------ overview

function Overview({ d, unmatched, onAds, reload }: { d: Data; unmatched: Data[]; onAds: () => void; reload: () => Promise<void> }) {
  const t = d.tiles || {}, x = d.extra || {}, cur = d.currency;
  const tiles: [string, string, Data, ReactNode][] = [
    ["views", "Просмотры", t.views || {}, x.ctr != null ? `CTR ${String(x.ctr).replace(".", ",")}%` : "по данным Telegram"],
    ["clicks", "Клики", t.clicks || {}, x.spent ? <>потрачено <Amount v={x.spent} cur={cur} /></> : "по данным Telegram"],
    ["users", "Реальные пользователи", t.users || {}, `подключились ${num(x.connected)} · оплатили ${num(x.paid)}`],
  ];
  const ads: Data[] = d.ads || [];
  const live = ads.filter((a) => a.status === "active");
  const silent = live.filter((a) => !a.views_hour);
  const best = [...ads].filter((a) => a.link?.per_1000 != null).sort((a, b) => b.link.per_1000 - a.link.per_1000).slice(0, 3);
  return (
    <div className="tga-body">
      <div className="tga-tiles">
        {tiles.map(([k, label, v, sub]) => (
          <div key={k} className={"tga-tile " + k}>
            <div className="tga-tile-top">
              <small>{label}</small>
              <Delta now={Number(v.value || 0)} before={Number(v.prev || 0)} />
            </div>
            <b>{num(v.value)}</b>
            <Spark values={v.series || []} />
            <span>{sub}</span>
          </div>
        ))}
      </div>
      <div className="tga-facts">
        <Fact label="Цена человека" value={x.per_user != null ? <Amount v={x.per_user} cur={cur} /> : "—"} />
        <Fact label="Цена платящего" value={x.per_paid != null ? <Amount v={x.per_paid} cur={cur} /> : "—"} />
        <Fact label="В рублях" value={x.spent_rub != null ? `${num(x.spent_rub)} ₽` : "—"} />
        <Fact label="Человек за всё время" value={d.person_rub != null ? `${num(d.person_rub, d.person_rub < 10 ? 1 : 0)} ₽` : "—"} />
        <Fact label="Крутятся сейчас" value={`${live.length - silent.length} из ${live.length}`} warn={silent.length > 0} />
      </div>
      {silent.length > 0 && (
        <button className="tga-note warn" onClick={onAds}>
          Без показов за последний час: {silent.map((a) => a.title).join(", ")} — откройте «Объявления», там видно, что делает автоставка.
        </button>
      )}
      <TargetCard t={d.target || {}} reload={reload} />
      <Verdicts ads={ads} onAds={onAds} />
      {(d.ltv || []).some((v: Data) => v.users) && (
        <div className="tga-card">
          <div className="tga-card-title">Сколько платит человек с рекламы</div>
          <LtvRow ltv={d.ltv} cost={d.person_rub} />
          <p className="tga-hint">Зелёным — человек за этот срок уже заплатил больше, чем стоил. Считаются только те, кто пришёл не меньше N дней назад.</p>
        </div>
      )}
      {best.length > 0 && (
        <div className="tga-card">
          <div className="tga-card-title">Тексты, которые приводят людей</div>
          {best.map((a) => (
            <div key={a.ad_id} className="tga-best">
              <AdBubble text={a.text} />
              <div>
                <b>{String(a.link.per_1000).replace(".", ",")}</b>
                <span>человек на 1000 показов</span>
                <small>{a.title}</small>
              </div>
            </div>
          ))}
        </div>
      )}
      {unmatched.length > 0 && (
        <div className="tga-card">
          <div className="tga-card-title">Объявления без нашей ссылки — оплаты по ним не посчитать</div>
          {unmatched.map((a) => (
            <div key={a.ad_id} className="tga-row-line">
              <span>{a.title || `Объявление ${a.ad_id}`}</span>
              <span className="tga-muted">{a.promote_url}</span>
              <span className="ml-auto">{num(a.views)} показов</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** The cabinet-wide «человек не дороже»: automatic (a third of what a person pays) or fixed. */
function TargetCard({ t, reload }: { t: Data; reload: () => Promise<void> }) {
  const [edit, setEdit] = useState(false), [rub, setRub] = useState("");
  const save = async (auto: boolean) => {
    await api("tg-ads/target", { auto, rub: auto ? null : rub });
    toast.success(auto ? "Цель считается сама" : `Цель: человек не дороже ${rub} ₽`);
    setEdit(false);
    await reload();
  };
  return (
    <div className="tga-card tga-target">
      <div>
        <div className="tga-card-title">Цель: человек не дороже {t.effective != null ? <b>{num(t.effective)} ₽</b> : "—"}</div>
        <p className="tga-hint">
          {t.auto ? `Сама: ${t.basis}.` : `Задана вручную. Сама было бы ${t.auto_rub != null ? `${num(t.auto_rub)} ₽` : "— мало данных"}.`}{" "}
          Автоставка держит её у каждого объявления, где своя цель не указана.
        </p>
      </div>
      {edit ? (
        <div className="tga-inline">
          <Input value={rub} onChange={(e) => setRub(e.target.value.replace(/\D/g, ""))} placeholder="₽" inputMode="numeric" className="w-24" />
          <ActionButton disabled={!rub} onAction={() => save(false)}>Сохранить</ActionButton>
          {!t.auto && <ActionButton variant="ghost" onAction={() => save(true)}>Считать саму</ActionButton>}
        </div>
      ) : (
        <Button variant="outline" onClick={() => { setRub(String(t.rub ?? t.effective ?? "")); setEdit(true); }}>Изменить</Button>
      )}
    </div>
  );
}

/** Which ads to give more money, keep, or switch off — by what people from them paid. */
function Verdicts({ ads, onAds }: { ads: Data[]; onAds: () => void }) {
  const live = ads.filter((a) => a.status === "active" || a.status === "on_hold");
  // A silent ad paid off on places that stopped showing it: money added there would only sit.
  const by = (code: string) => live.filter((a) => a.link?.verdict?.code === code && (code === "stop" || !a.silence));
  const silentGood = live.filter((a) => a.silence && ["scale", "hold"].includes(a.link?.verdict?.code));
  const groups: [string, string, Data[]][] = [
    ["scale", "Можно добавлять бюджет", by("scale")],
    ["hold", "Окупаются без запаса — держать", by("hold")],
    ["stop", "Не окупаются — на паузу и вернуть остаток", by("stop")],
  ];
  const early = by("early");
  if (!groups.some((g) => g[2].length) && !early.length && !silentGood.length) return null;
  const empty = live.filter((a) => a.link && !a.link.shared && (!a.link.greeting || !a.link.followup));
  return (
    <div className="tga-card">
      <div className="tga-card-title">Что делать с деньгами</div>
      {groups.filter((g) => g[2].length).map(([code, label, list]) => (
        <div key={code} className="tga-verdict-line">
          <span className={"tga-chip " + VERDICT_AD[code][1]}>{VERDICT_AD[code][0]}</span>
          <span>{label}: {list.map((a) => a.title).join(", ")}</span>
        </div>
      ))}
      {silentGood.length > 0 && (
        <div className="tga-verdict-line">
          <span className="tga-chip bad">молчит</span>
          <span>Окупались, но площадки перестали показывать — бюджет не добавлять: {silentGood.map((a) => a.title).join(", ")}</span>
        </div>
      )}
      {early.length > 0 && (
        <div className="tga-verdict-line">
          <span className="tga-chip muted">рано</span>
          <span>Пока не судить, держите на 1 TON: {early.map((a) => a.title).join(", ")}</span>
        </div>
      )}
      {empty.length > 0 && (
        <button className="tga-note warn" onClick={onAds}>
          Без приветствия или дожима: {empty.map((a) => a.title).join(", ")} — это бесплатно поднимает долю подключившихся.
          Откройте объявление → «Приветствие и дожим».
        </button>
      )}
      <p className="tga-hint">
        Решаем по деньгам, а не по кликам: только когда 5+ человек прожили 14 дней. Новую площадку пробуйте на 1 TON и
        добавляйте бюджет, только когда она окупилась в полтора раза.
      </p>
    </div>
  );
}

/** What one person from the ads paid within 7 / 14 / 30 days, next to what one person cost. */
function LtvRow({ ltv, cost }: { ltv?: Data[]; cost: number | null }) {
  if (!ltv?.length) return null;
  return (
    <div className="tga-ltv" title="Только люди, пришедшие не меньше N дней назад: свежие ещё не успели заплатить">
      {ltv.map((x) => (
        <div key={x.days} className={x.ok === true ? "ok" : x.ok === false ? "bad" : ""}>
          <small>за {x.days} дн</small>
          <b>{x.per_user != null ? `${num(x.per_user)} ₽` : "рано"}</b>
          <span>{x.users ? `${num(x.users)} чел.` : "никто ещё не дожил"}</span>
        </div>
      ))}
      <div className="tga-ltv-cost">
        <small>стоил</small>
        <b>{cost != null ? `${num(cost, cost < 10 ? 1 : 0)} ₽` : "—"}</b>
        <span>расход ÷ люди</span>
      </div>
    </div>
  );
}

const Fact = ({ label, value, warn }: { label: string; value: ReactNode; warn?: boolean }) => (
  <div className={"tga-fact" + (warn ? " warn" : "")}>
    <small>{label}</small>
    <b>{value}</b>
  </div>
);

/** The ad as people see it: a bubble with «Реклама», the bot name and the text (custom emoji markup dropped). */
function AdBubble({ text, title = BRAND.name }: { text: string; title?: string }) {
  const plain = String(text || "").replace(/!\[([^\]]*)\]\(tg:\/\/emoji\?id=\d+\)/g, "$1");
  return (
    <div className="tga-bubble">
      <div>
        <span className="tga-bubble-ad">Реклама</span> <b>{title}</b>
      </div>
      <p>{plain}</p>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ ads

function AdsTable({ d, reload, onSchedule }: { d: Data; reload: () => Promise<void>; onSchedule: (id: number) => void }) {
  const [open, setOpen] = useState<number | null>(null),
    [cpmOf, setCpmOf] = useState<Data | null>(null),
    [limitOf, setLimitOf] = useState<Data | null>(null),
    [greetOf, setGreetOf] = useState<Data | null>(null),
    [showGone, setShowGone] = useState(false);
  const confirm = useConfirm();
  const ads: Data[] = d.ads || [];
  const visible = showGone ? ads : ads.filter((a) => a.status !== "declined" || a.remaining > 0);
  const act = async (body: Data, ok: string) => {
    const got = await api("tg-ads/ad", body);
    if (body.action === "autobid" && body.enabled) autobidToast(got, ok);
    else if (got.review) toast.warning("Telegram отправил объявление на модерацию после этой правки");
    else toast.success(ok);
    await reload();
  };
  return (
    <div className="tga-body">
      <div className="tga-table-wrap">
        <table className="tga-table tga-cards">
          <thead>
            <tr>
              <th>Объявление</th>
              <th>Показы</th>
              <th>Клики</th>
              <th title="Пришли в бота по ссылке объявления">Люди</th>
              <th title="Ставка за 1000 показов. Ниже — остаток бюджета">CPM</th>
              <th>Автоставка</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visible.map((a) => {
              const st = STATUS[a.status] || [a.status, "muted"];
              const ab = a.autobid || {};
              const isOpen = open === a.ad_id;
              return (
                <Fragment key={a.ad_id}>
                  <tr className={isOpen ? "open" : ""} onClick={() => setOpen(isOpen ? null : a.ad_id)}>
                    <td className="tga-title-cell">
                      <span className="tga-kind">{a.placement === "channel_post" ? "📢" : "🤖"}</span>
                      <div>
                        <b>{a.title}</b>
                        <small>{a.link ? `t.me/${d.bot}?start=ad_${a.link.slug}` : a.promote_url}</small>
                        <span className={"tga-status " + st[1]}>
                          {a.is_paused && a.status === "active" ? "Paused" : st[0]}
                          {a.silence && <em className="tga-silent" title={a.silence.text}> · молчит {a.silence.hours} ч</em>}
                        </span>
                        {VERDICT_AD[a.link?.verdict?.code] && !(a.silence && a.link.verdict.code !== "stop") && (
                          <span className={"tga-chip tga-verdict " + VERDICT_AD[a.link.verdict.code][1]} title={a.link.verdict.text}>
                            {VERDICT_AD[a.link.verdict.code][0]}
                          </span>
                        )}
                      </div>
                    </td>
                    <td data-label="Показы">
                      {num(a.views)}
                      <small className={a.views_hour ? "tga-live" : "tga-muted"}>{a.views_hour ? `+${a.views_hour} за час` : "0 за час"}</small>
                    </td>
                    <td data-label="Клики">
                      {num(a.clicks)}
                      <small className="tga-muted">CTR {a.views ? `${String(Math.round((a.clicks / a.views) * 1000) / 10).replace(".", ",")}%` : "–"}</small>
                    </td>
                    <td data-label="Люди">
                      {a.link ? num(a.link.users) : "—"}
                      {a.person_rub != null ? (
                        <small className="tga-muted" title="Сколько стоил один пришедший: расход ÷ люди">{num(a.person_rub, a.person_rub < 10 ? 1 : 0)} ₽ за человека</small>
                      ) : a.link?.per_1000 != null ? (
                        <small className="tga-muted">{String(a.link.per_1000).replace(".", ",")} / 1000</small>
                      ) : null}
                    </td>
                    <td data-label="CPM">
                      <button
                        className="tga-link"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCpmOf(a);
                        }}
                      >
                        <Amount v={a.cpm} cur={a.currency} />
                      </button>
                      <small className={"tga-muted" + (a.days_left != null && a.days_left < 1 ? " tga-low" : "")} title="Остаток бюджета и на сколько его хватит при расходе последних суток">
                        осталось <Amount v={a.remaining} cur={a.currency} />
                        {a.days_left != null && ` · ${days(a.days_left)}`}
                      </small>
                    </td>
                    <td data-label="Автоставка" onClick={(e) => e.stopPropagation()}>
                      <div className="tga-ab">
                        <Switch
                          checked={!!ab.enabled}
                          aria-label="Автоставка"
                          disabled={a.status !== "active" && !ab.enabled}
                          onCheckedChange={(on) => void act({ ad_id: a.ad_id, action: "autobid", enabled: on }, on ? "Автоставка включена" : "Автоставка выключена").catch((e) => toast.error(e.message))}
                        />
                        <span className={"tga-chip " + (AB[ab.state] || "muted")} title={ab.note}>{ab.state_text}</span>
                      </div>
                    </td>
                    <td className="tga-menu-cell" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="tga-dots" aria-label="Действия"><MoreVertical /></button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onSelect={() => setCpmOf(a)}>Изменить CPM</DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => void act({ ad_id: a.ad_id, action: "pause", paused: !a.is_paused }, a.is_paused ? "Возобновлено" : "На паузе").catch((e) => toast.error(e.message))}>
                            {a.is_paused ? "Возобновить" : "Поставить на паузу"}
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => setLimitOf(a)}>Дневной лимит</DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => onSchedule(a.ad_id)}>Расписание по часам</DropdownMenuItem>
                          {a.link && <DropdownMenuItem onSelect={() => setGreetOf(a)}>Приветствие и дожим</DropdownMenuItem>}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            disabled={!a.remaining}
                            onSelect={() =>
                              confirm({
                                title: `Вернуть остаток «${a.title}»?`,
                                description: `Объявление встанет на паузу, через 10 минут ${price(a.remaining)} ${a.currency} вернутся на баланс кабинета. Снова запустить его можно, только добавив бюджет вручную в Telegram Ads.`,
                                label: "Вернуть остаток",
                                danger: true,
                                action: async () => {
                                  await api("tg-ads/ad", { ad_id: a.ad_id, action: "refund" });
                                  toast.success("На паузе. Остаток вернётся через 10 минут");
                                  await reload();
                                },
                              })
                            }
                          >
                            Вернуть остаток на баланс
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="tga-detail-row">
                      <td colSpan={7}>
                        <AdDetail a={a} cur={a.currency} reload={reload} onGreeting={() => setGreetOf(a)} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {ads.length !== visible.length && (
        <button className="tga-link small" onClick={() => setShowGone(true)}>Показать отклонённые без бюджета ({ads.length - visible.length})</button>
      )}
      <CpmDialog ad={cpmOf} onClose={() => setCpmOf(null)} onSave={async (v) => act({ ad_id: cpmOf!.ad_id, action: "cpm", cpm: v }, "Ставка сохранена")} />
      <NumberDialog
        ad={limitOf}
        title="Дневной лимит"
        hint="Сколько объявление может тратить в сутки. 0 — без лимита. Telegram может отправить объявление на модерацию после этой правки."
        value={limitOf?.daily_limit}
        onClose={() => setLimitOf(null)}
        onSave={async (v) => act({ ad_id: limitOf!.ad_id, action: "limit", limit: v }, "Лимит сохранён")}
      />
      <GreetingDialog ad={greetOf} onClose={() => setGreetOf(null)} reload={reload} />
    </div>
  );
}

function AdDetail({ a, cur, reload, onGreeting }: { a: Data; cur: string; reload: () => Promise<void>; onGreeting: () => void }) {
  const ab = a.autobid || {}, l = a.link;
  const [max, setMax] = useState(String(ab.max_cpm ?? ""));
  const [person, setPerson] = useState(String(ab.max_user_rub ?? ""));
  const funnel: [string, number][] = [
    ["Показы", a.views],
    ["Клики", a.clicks],
    ["Пришли в бота", l?.users || 0],
    ["Подключились", l?.connected || 0],
    ["Оплатили", l?.paid || 0],
  ];
  const top = Math.max(1, funnel[0][1]);
  const payback = l && l.spent_rub ? Math.round((l.revenue / l.spent_rub) * 100) : null;
  return (
    <div className="tga-detail">
      {a.silence && (
        <div className="tga-silence">
          <div>
            <b>Молчит {a.silence.hours} ч</b>
            <p>{a.silence.text}</p>
          </div>
          {a.silence.back_cpm != null && (
            <ActionButton
              variant="outline"
              onAction={async () => {
                const got = await api("tg-ads/ad", { ad_id: a.ad_id, action: "cpm", cpm: a.silence.back_cpm });
                if (got.review) toast.warning("Telegram отправил объявление на модерацию после этой правки");
                else toast.success(`Ставка снова ${price(a.silence.back_cpm)}`);
                await reload();
              }}
            >
              Вернуть ставку {price(a.silence.back_cpm)}
            </ActionButton>
          )}
        </div>
      )}
      <div className="tga-detail-col">
        <AdBubble text={a.text} />
        <dl className="tga-dl">
          <dt>Где</dt>
          <dd>{a.target?.text || "—"}</dd>
          <dt>Создано</dt>
          <dd>{time(a.created_at)}</dd>
          <dt>Последний показ</dt>
          <dd>{a.last_view_at ? ago(a.last_view_at) : "не было"}</dd>
          <dt>Потрачено</dt>
          <dd><Amount v={a.spent} cur={cur} />{a.spent_rub != null ? ` · ${num(a.spent_rub)} ₽` : ""}</dd>
          {a.daily_limit > 0 && (<><dt>Лимит в день</dt><dd><Amount v={a.daily_limit} cur={cur} /></dd></>)}
          {a.schedule && (<><dt>Расписание</dt><dd>{(a.schedule.week_hours_mask || []).reduce((s: number, m: number) => s + m.toString(2).split("1").length - 1, 0)} ч в неделю</dd></>)}
          {a.decline_reason && (<><dt>Отклонено</dt><dd className="text-destructive">{a.decline_reason}</dd></>)}
        </dl>
        <div className="tga-spark-box">
          <small>Показы за 24 часа</small>
          <Spark values={a.spark || []} height={40} />
        </div>
      </div>
      <div className="tga-detail-col">
        <div className="tga-card-title">Воронка</div>
        <div className="tga-funnel">
          {funnel.map(([label, v], i) => (
            <div key={label}>
              <span>{label}</span>
              <i style={{ width: `${Math.max(2, (v / top) * 100)}%` }} />
              <b>{num(v)}</b>
              <small>{i ? (funnel[i - 1][1] ? `${Math.round((v / funnel[i - 1][1]) * 1000) / 10}%` : "—") : ""}</small>
            </div>
          ))}
        </div>
        {l?.shared && <p className="tga-hint">Эта ссылка стоит в нескольких объявлениях — люди и оплаты общие для них.</p>}
        <div className="tga-card-title">Окупаемость</div>
        {l ? (
          <div className="tga-payback">
            <div className="tga-payback-bar">
              <i style={{ width: `${Math.min(100, payback ?? 0)}%` }} className={payback != null && payback >= 100 ? "ok" : ""} />
            </div>
            <div className="tga-payback-nums">
              <span>Принесли <b>{num(l.revenue)} ₽</b></span>
              <span>Потрачено <b>{l.spent_rub ? `${num(l.spent_rub)} ₽` : "—"}</b></span>
              <span>
                {payback == null ? "нет курса или расхода" : payback >= 100 ? `окупилось${l.payback_days != null ? ` за ${l.payback_days} дн` : ""} · ${payback}%` : `${payback}% — ещё не окупилось`}
              </span>
            </div>
          </div>
        ) : (
          <p className="tga-hint">У объявления нет нашей ссылки ad_… — оплаты не посчитать.</p>
        )}
        {l && <LtvRow ltv={l.ltv} cost={l.users && l.spent_rub ? l.spent_rub / l.users : null} />}
        {l?.verdict && VERDICT_AD[l.verdict.code] && (
          <p className="tga-ab-note">
            <span className={"tga-chip " + VERDICT_AD[l.verdict.code][1]}>{VERDICT_AD[l.verdict.code][0]}</span> {l.verdict.text}
            {a.silence && l.verdict.code !== "stop" && " — но сейчас объявление молчит, бюджет не добавлять"}
          </p>
        )}
        {l && (
          <button className="tga-link small" onClick={onGreeting}>
            {l.greeting || l.followup
              ? [l.greeting && "приветствие", l.followup && "дожим через час"].filter(Boolean).join(" и ").replace(/^./, (c: string) => c.toUpperCase()) + ": изменить"
              : "+ Приветствие и дожим для пришедших с этого объявления"}
          </button>
        )}
      </div>
      <div className="tga-detail-col">
        <div className="tga-card-title">Автоставка</div>
        <p className="tga-ab-note">
          <span className={"tga-chip " + (AB[ab.state] || "muted")}>{ab.state_text}</span> {ab.note}
        </p>
        <dl className="tga-dl">
          <dt>Ставка сейчас</dt>
          <dd><Amount v={a.cpm} cur={cur} /></dd>
          {ab.good_cpm && (<><dt>Последняя рабочая</dt><dd><Amount v={ab.good_cpm} cur={cur} /></dd></>)}
          {ab.floor_cpm && (<><dt>Ниже не опускать</dt><dd><Amount v={ab.floor_cpm} cur={cur} /></dd></>)}
          {ab.refund_at && (<><dt>Возврат остатка</dt><dd>{time(ab.refund_at)}</dd></>)}
        </dl>
        <div className="tga-ab-form">
          <label className="tga-field">
            <span>Потолок ставки</span>
            <div className="tga-input-gem"><Gem /><Input value={max} onChange={(e) => setMax(e.target.value.replace(",", "."))} placeholder={autoTop(a.cpm)} inputMode="decimal" /></div>
          </label>
          <label className="tga-field">
            <span>Человек не дороже, ₽</span>
            <Input value={person} onChange={(e) => setPerson(e.target.value.replace(/\D/g, ""))} placeholder="без цели" inputMode="numeric" />
          </label>
          <ActionButton
            variant="outline"
            onAction={async () => {
              const got = await api("tg-ads/ad", { ad_id: a.ad_id, action: "autobid", enabled: true, max_cpm: max || null, max_user_rub: person || null });
              autobidToast(got, ab.enabled ? "Автоставка сохранена" : "Автоставка включена");
              await reload();
            }}
          >
            {ab.enabled ? "Сохранить" : "Включить"}
          </ActionButton>
        </div>
        <p className="tga-hint">
          Потолок по умолчанию — ставка при включении +30%, и никогда не выше {price(HARD.max)}, что бы ни было указано.
          Если у объявления нет дневного лимита, при включении ставится половина остатка — бюджета хватит минимум на 2 дня.
          Каждые 10 минут: нет показов 40 минут — ставка +15%, не выше потолка; показы идут 2 часа — пробует на 7% дешевле.
          На потолке 3 часа без показов — возвращает последнюю рабочую ставку и больше не поднимает: дело не в цене.
          С целью по цене человека держит ставку так, чтобы пришедший стоил не дороже — считает по людям на 1000 показов за 14
          дней, когда пришли хотя бы трое. Бюджет не пополняет никогда.
        </p>
      </div>
    </div>
  );
}

function CpmDialog({ ad, onClose, onSave }: { ad: Data | null; onClose: () => void; onSave: (v: string) => Promise<void> }) {
  return (
    <NumberDialog
      ad={ad}
      title="Edit CPM"
      hint="Цена за 1000 показов. Если включена автоставка, она продолжит подбирать ставку от этой."
      value={ad?.cpm}
      onClose={onClose}
      onSave={onSave}
    />
  );
}

function NumberDialog({ ad, title, hint, value, onClose, onSave }: { ad: Data | null; title: string; hint: string; value: unknown; onClose: () => void; onSave: (v: string) => Promise<void> }) {
  const [v, setV] = useState("");
  return (
    <Dialog open={!!ad} onOpenChange={(o) => { if (!o) onClose(); else setV(price(value)); }}>
      <DialogContent className="tga-modal" onOpenAutoFocus={() => setV(price(value))}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>для «{ad?.title}»</DialogDescription>
        </DialogHeader>
        <div className="tga-input-gem">
          <Gem />
          <Input autoFocus value={v} onChange={(e) => setV(e.target.value.replace(",", "."))} inputMode="decimal" />
        </div>
        <p className="tga-hint">{hint}</p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <ActionButton onAction={async () => { await onSave(v); onClose(); }}>Сохранить</ActionButton>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function GreetingDialog({ ad, onClose, reload }: { ad: Data | null; onClose: () => void; reload: () => Promise<void> }) {
  const [text, setText] = useState(""),
    [later, setLater] = useState("");
  return (
    <Dialog open={!!ad} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="tga-modal" onOpenAutoFocus={() => { setText(ad?.link?.greeting || ""); setLater(ad?.link?.followup || ""); }}>
        <DialogHeader>
          <DialogTitle>Приветствие и дожим</DialogTitle>
          <DialogDescription>
            Для новичков по ссылке ad_{ad?.link?.slug}. Оба продолжают мысль объявления: пришёл с «соцсети не грузятся» —
            сразу про соцсети.
          </DialogDescription>
        </DialogHeader>
        <label className="tga-field">
          <span>Приветствие — первым сообщением, перед обычным</span>
          <Textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} placeholder="Соцсети заработают через минуту 🐸 Нажмите «Подключить» — первые 3 дня бесплатно." />
          <em className="tga-muted text-xs not-italic">{text.length} / 700 · пусто — без приветствия</em>
        </label>
        <label className="tga-field">
          <span>Дожим — через час, если человек так и не подключился</span>
          <Textarea rows={4} value={later} onChange={(e) => setLater(e.target.value)} placeholder="{name}, соцсети всё ещё не грузятся? Подключение — одна кнопка, первые 3 дня бесплатно 🐸" />
          <em className="tga-muted text-xs not-italic">
            {later.length} / 700 · один раз, с кнопкой «Подключить VPN» · {"{name}"} — имя · не чаще общего лимита напоминаний · пусто — без дожима
          </em>
        </label>
        <div className="flex justify-between gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              const s = draftFromAd(ad?.text);
              if (!text.trim()) setText(s.greeting);
              if (!later.trim()) setLater(s.followup);
            }}
            disabled={!!text.trim() && !!later.trim()}
          >
            Подставить по тексту объявления
          </Button>
          <div className="flex gap-2">
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <ActionButton
            onAction={async () => {
              await api("tg-ads/greeting", { link_id: ad!.link.id, text, followup: later });
              toast.success("Сохранено");
              onClose();
              await reload();
            }}
          >
            Сохранить
          </ActionButton>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** A first draft of the greeting and the follow-up from the ad's own first sentence — to edit, not to send as is. */
export function draftFromAd(text?: string) {
  const plain = String(text || "").replace(/!\[([^\]]*)\]\(tg:\/\/emoji\?id=\d+\)/g, "").replace(/^[^\p{L}\d]+/u, "");
  const hook = (plain.match(/^[^.!?]*[.!?]?/)?.[0] || "").trim();
  return {
    greeting: `${hook ? hook + " " : ""}🐸 Нажмите «Подключить VPN» — займёт минуту.`,
    followup: "{name}, VPN ещё не подключён — это одна кнопка ниже, займёт минуту 🐸",
  };
}

// ------------------------------------------------------------------------------------------------ hours

const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

function Hours({ ads, initial, reload }: { ads: Data[]; initial: number | null; reload: () => Promise<void> }) {
  const res = useResource("tg-ads/hours");
  const [metric, setMetric] = useState<"views" | "users" | "paid">("users");
  const live = ads.filter((a) => ["active", "on_hold"].includes(a.status));
  const [adId, setAdId] = useState<number | null>(initial ?? live[0]?.ad_id ?? null);
  const ad = ads.find((a) => a.ad_id === adId);
  const fromAd = (a?: Data) => {
    const m: number[] = a?.schedule?.week_hours_mask;
    return Array.from({ length: 7 }, (_, d) => Array.from({ length: 24 }, (_, h) => (m ? !!(m[d] & (1 << h)) : true)));
  };
  const [mask, setMask] = useState<boolean[][]>(() => fromAd(ad));
  const [drag, setDrag] = useState<boolean | null>(null);
  const g: number[][] | undefined = res.data?.[metric];
  const max = useMemo(() => Math.max(1, ...(g || []).flat()), [g]);
  if (res.error) return <Failure message={res.error} retry={res.reload} />;
  if (!res.data) return <Loading />;
  const toggle = (d: number, h: number, v: boolean) => setMask((m) => m.map((row, i) => (i === d ? row.map((c, j) => (j === h ? v : c)) : row)));
  const best = () => {
    const users: number[][] = res.data!.users, paid: number[][] = res.data!.paid;
    const byHour = Array.from({ length: 24 }, (_, h) => DAYS.reduce((s, _, d) => s + users[d][h] + 3 * paid[d][h], 0));
    const keep = byHour.map((v) => v > 0);
    if (!keep.some(Boolean)) return toast.error("Пока мало данных: никто не пришёл с рекламы за 30 дней");
    setMask(Array.from({ length: 7 }, () => keep.slice()));
    toast.success(`Оставлены часы, когда приходят люди: ${keep.filter(Boolean).length} из 24`);
  };
  const toMask = () => mask.map((row) => row.reduce((acc, on, h) => (on ? acc | (1 << h) : acc), 0));
  const on = mask.flat().filter(Boolean).length;
  return (
    <div className="tga-body">
      <div className="tga-toolbar">
        <div className="tga-seg">
          {[["users", "Пришли"], ["paid", "Оплатили"], ["views", "Показы"]].map(([k, l]) => (
            <button key={k} className={metric === k ? "on" : ""} onClick={() => setMetric(k as typeof metric)}>{l}</button>
          ))}
        </div>
        <span className="tga-muted">за 30 дней, время московское · клик и протяжка — отметить часы показа</span>
      </div>
      <div className="tga-heat" onMouseLeave={() => setDrag(null)} onMouseUp={() => setDrag(null)}>
        <div />
        {Array.from({ length: 24 }, (_, h) => <small key={h}>{h % 3 === 0 ? h : ""}</small>)}
        {DAYS.map((day, d) => (
          <Fragment key={day}>
            <small>{day}</small>
            {Array.from({ length: 24 }, (_, h) => {
              const v = g?.[d]?.[h] || 0;
              return (
                <button
                  key={h}
                  className={"tga-cell" + (mask[d][h] ? "" : " off")}
                  style={{ ["--a" as string]: v ? 0.15 + 0.85 * (v / max) : 0 }}
                  title={`${day} ${h}:00–${h + 1}:00 · ${v}`}
                  onMouseDown={() => { setDrag(!mask[d][h]); toggle(d, h, !mask[d][h]); }}
                  onMouseEnter={() => { if (drag !== null) toggle(d, h, drag); }}
                >
                  {v ? <span>{v}</span> : null}
                </button>
              );
            })}
          </Fragment>
        ))}
      </div>
      <div className="tga-toolbar">
        <select className="tga-select" value={adId ?? ""} onChange={(e) => { const id = Number(e.target.value); setAdId(id); setMask(fromAd(ads.find((a) => a.ad_id === id))); }}>
          {live.map((a) => <option key={a.ad_id} value={a.ad_id}>{a.title}</option>)}
        </select>
        <span className="tga-muted">{on} ч в неделю</span>
        <Button variant="outline" onClick={best}>Отметить лучшие часы</Button>
        <Button variant="ghost" onClick={() => setMask(fromAd())}>Все часы</Button>
        <ActionButton
          disabled={!ad}
          onAction={async () => {
            const got = await api("tg-ads/ad", { ad_id: adId, action: "schedule", mask: on === 168 ? null : toMask() });
            toast[got.review ? "warning" : "success"](got.review ? "Расписание сохранено, но Telegram отправил объявление на модерацию" : on === 168 ? "Расписание снято" : "Расписание сохранено");
            await reload();
          }}
        >
          {on === 168 ? "Показывать круглосуточно" : "Применить расписание"}
        </ActionButton>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ places

const VERDICT: Record<string, string> = {
  "стоит попробовать": "ok", крутится: "ok", молчит: "bad", "нет людей": "bad", "мало людей": "warn", было: "muted", "не проверено": "muted",
};

function Places({ onLaunch }: { onLaunch: (kind: string, places: string) => void }) {
  const res = useResource("tg-ads/places");
  const [names, setNames] = useState("");
  const items: Data[] = res.data?.items || [];
  const list = names.split(/[\s,]+/).filter(Boolean);
  const fresh = items.filter((p) => p.verdict === "стоит попробовать");
  return (
    <div className="tga-body">
      <div className="tga-places-check">
        <Textarea
          rows={2}
          value={names}
          onChange={(e) => setNames(e.target.value)}
          placeholder="@боты и @каналы через пробел или с новой строки — до 30 за раз: сколько там людей и стоит ли пробовать"
        />
        <ActionButton
          disabled={!list.length}
          onAction={async () => {
            const got = await api("tg-ads/places", { usernames: list });
            if (got.failed?.length) toast.warning(`Проверено ${got.checked}, не вышло: ${got.failed.join("; ")}`);
            else toast.success(`Проверено: ${got.checked}`);
            setNames("");
            await res.reload();
          }}
        >
          <Search /> Проверить{list.length > 1 ? ` ${list.length}` : ""}
        </ActionButton>
      </div>
      {res.error ? (
        <Failure message={res.error} retry={res.reload} />
      ) : !res.data ? (
        <Loading />
      ) : (
        <>
          {fresh.length > 0 && (
            <div className="tga-note ok">
              Стоит попробовать: {fresh.map((p) => "@" + p.username).join(", ")}
              {res.data.bar ? ` — людей не меньше, чем на самой маленькой площадке, где наша реклама крутится (${num(res.data.bar)})` : ""}.
              <button
                className="tga-link"
                onClick={() => onLaunch(fresh[0].kind === "channel" ? "channels" : "bots", fresh.filter((p) => p.kind === fresh[0].kind).map((p) => "@" + p.username).join("\n"))}
              >
                Запустить на них
              </button>
            </div>
          )}
          <div className="tga-table-wrap">
            <table className="tga-table tga-cards">
              <thead>
                <tr>
                  <th>Площадка</th>
                  <th title="Активные за месяц, как их считает Telegram Ads">Аудитория</th>
                  <th>Наши объявления</th>
                  <th>Показы</th>
                  <th>Итог</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((p) => {
                  const dropped = p.prev_audience && p.audience != null && p.prev_audience >= 2 * Math.max(1, p.audience);
                  return (
                    <tr key={p.username || p.title} className="static">
                      <td className="tga-title-cell">
                        <span className="tga-kind">{p.kind === "channel" ? "📢" : "🤖"}</span>
                        <div>
                          <b>{p.title || "@" + p.username}</b>
                          {p.username && <small>@{p.username}</small>}
                        </div>
                      </td>
                      <td data-label="Аудитория">
                        {p.audience != null ? num(p.audience) : "—"}
                        {dropped && <small className="tga-low">было {num(p.prev_audience)}</small>}
                        {p.checked_at && <small className="tga-muted">{ago(p.checked_at)}</small>}
                      </td>
                      <td data-label="Объявления" className="tga-wrap">{p.ads.length ? p.ads.map((a: Data) => a.title).join(", ") : "—"}</td>
                      <td data-label="Показы">
                        {num(p.views)}
                        <small className="tga-muted">{num(p.views_day)} за сутки</small>
                      </td>
                      <td data-label="Итог">
                        <span className={"tga-chip " + (VERDICT[p.verdict] || "muted")}>{p.verdict}</span>
                      </td>
                      <td className="tga-menu-cell">
                        {p.username && !["крутится", "молчит"].includes(p.verdict) && (
                          <button className="tga-link small" onClick={() => onLaunch(p.kind === "channel" ? "channels" : "bots", "@" + p.username)}>
                            Запустить
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!items.length && <p className="tga-hint">Площадки появятся из таргетинга объявлений или после проверки.</p>}
          </div>
        </>
      )}
      <p className="tga-hint">
        «Молчит» — объявление там активно, но за сутки ни одного показа. «Стоит попробовать» — людей не меньше, чем на самой
        маленькой площадке, где наша реклама уже крутится. Площадки работающих объявлений бот перепроверяет дважды в сутки — если
        аудитория упала, увидите «было …».
      </p>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ results

const rub = (v: unknown) => `${num(v)} ₽`;
const Profit = ({ v }: { v: number }) => <b className={v > 0 ? "tga-plus" : v < 0 ? "tga-minus" : ""}>{v > 0 ? "+" : ""}{rub(v)}</b>;

function Results({ onLaunch }: { onLaunch: (kind: string, places: string) => void }) {
  const res = useResource("tg-ads/results");
  if (res.error) return <Failure message={res.error} retry={res.reload} />;
  if (!res.data) return <Loading />;
  const t = res.data.total || {}, places: Data[] = res.data.places || [], links: Data[] = res.data.links || [];
  const mixed: Data[] = res.data.mixed || [];
  return (
    <div className="tga-body">
      <div className="tga-facts">
        <Fact label="Потрачено" value={rub(t.spent_rub)} />
        <Fact label="Принесли люди с рекламы" value={rub(t.revenue)} />
        <Fact label="Итог" value={<Profit v={t.profit || 0} />} />
        <Fact label="Окупаемость" value={t.roi != null ? `${t.roi}%` : "—"} />
      </div>
      <p className="tga-hint">
        Все пополнения людей, пришедших по рекламным ссылкам, минус расход в рублях по курсу синхронизации. Свежие объявления
        выглядят хуже — их люди ещё не успели заплатить; решение — по отметке «масштабировать / держать / выключить».
      </p>
      <div className="tga-card-title">По площадкам</div>
      {places.length ? (
        <div className="tga-table-wrap">
          <table className="tga-table tga-cards">
            <thead><tr><th>Площадка</th><th>Пришли</th><th>Оплатили</th><th>Потрачено</th><th>Принесли</th><th>Итог</th></tr></thead>
            <tbody>
              {places.map((p) => (
                <tr key={p.username || p.title} className="static">
                  <td className="tga-title-cell">
                    <span className="tga-kind">{p.kind === "channel" ? "📢" : "🤖"}</span>
                    <div><b>{p.title || "@" + p.username}</b>{p.username && <small>@{p.username}</small>}</div>
                  </td>
                  <td data-label="Пришли">{num(p.users)}</td>
                  <td data-label="Оплатили">{num(p.paid)}</td>
                  <td data-label="Потрачено">{rub(p.spent_rub)}</td>
                  <td data-label="Принесли">{rub(p.revenue)}</td>
                  <td data-label="Итог"><Profit v={p.profit} />{p.roi != null && <small className="tga-muted">{p.roi}%</small>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="tga-hint">Здесь будут площадки, у которых своё объявление: только так деньги можно приписать площадке.</p>
      )}
      {mixed.length > 0 && (
        <div className="tga-card">
          <div className="tga-card-title">Объявления на несколько площадок — какая из них приносит, не видно</div>
          {mixed.map((e) => (
            <div key={e.link_id} className="tga-mixed">
              <div>
                <b>{e.ads.map((a: Data) => a.title).join(", ")}</b>
                <span className="tga-muted"> · {rub(e.spent_rub)} → {rub(e.revenue)} · </span>
                <Profit v={e.profit} />
              </div>
              <div className="tga-mixed-places">
                {e.places.map((p: Data) =>
                  p.username ? (
                    <button key={p.username} className="tga-link small" onClick={() => onLaunch(p.kind === "channel" ? "channels" : "bots", "@" + p.username)}>
                      + отдельно @{p.username}
                    </button>
                  ) : (
                    <span key={p.title} className="tga-muted text-xs">{p.title}</span>
                  ),
                )}
              </div>
            </div>
          ))}
          <p className="tga-hint">
            Запустите по объявлению на каждую площадку (по 1 TON на пробу) — у каждого будет своя ссылка, и через 14 дней
            станет видно, какая площадка окупается. Старое объявление можно поставить на паузу и вернуть остаток.
          </p>
        </div>
      )}
      <div className="tga-card-title">По объявлениям</div>
      <div className="tga-table-wrap">
        <table className="tga-table tga-cards">
          <thead><tr><th>Ссылка</th><th>Пришли</th><th>Потрачено</th><th>Принесли</th><th>Итог</th><th>Что делать</th></tr></thead>
          <tbody>
            {links.map((e) => (
              <tr key={e.link_id} className="static">
                <td className="tga-title-cell">
                  <div><b>{e.ads.map((a: Data) => a.title).join(", ")}</b><small>ad_{e.slug}</small></div>
                </td>
                <td data-label="Пришли">{num(e.users)}<small className="tga-muted">оплатили {num(e.paid)}</small></td>
                <td data-label="Потрачено">{rub(e.spent_rub)}</td>
                <td data-label="Принесли">{rub(e.revenue)}</td>
                <td data-label="Итог"><Profit v={e.profit} />{e.roi != null && <small className="tga-muted">{e.roi}%</small>}</td>
                <td data-label="Что делать">
                  {VERDICT_AD[e.verdict?.code] ? (
                    <span className={"tga-chip " + VERDICT_AD[e.verdict.code][1]} title={e.verdict.text}>{VERDICT_AD[e.verdict.code][0]}</span>
                  ) : (
                    <span className="tga-muted">{e.verdict?.text}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ log

const ACTION: Record<string, string> = {
  cpm: "ставка",
  autobid_on: "автоставка включена",
  autobid_off: "автоставка выключена",
  daily_limit: "дневной лимит",
  pause: "пауза",
  resume: "возобновлено",
  refund_asked: "возврат остатка",
  refund: "остаток вернулся",
  schedule: "расписание",
  created: "создано",
};

function Log({ items }: { items: Data[] }) {
  if (!items.length) return <p className="tga-hint tga-body">Здесь будет каждое изменение ставок и настроек — кто, когда и почему.</p>;
  return (
    <div className="tga-body">
      <div className="tga-log">
        {items.map((r) => (
          <div key={r.id}>
            <span className="tga-who" title={r.who === "bot" ? "Автоставка" : "Админ"}>{r.who === "bot" ? <Bot /> : <User />}</span>
            <time>{time(r.at)}</time>
            <b>{r.title || `Объявление ${r.ad_id}`}</b>
            <span>
              {ACTION[r.action] || r.action}
              {r.old_value != null && r.new_value != null ? <> <Amount v={r.old_value} /> → <Amount v={r.new_value} /></> : r.new_value != null && r.action === "created" ? <> по <Amount v={r.new_value} /></> : null}
            </span>
            <small>{r.note}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ create

function CreateAd({ open, preset, onClose, balance, currency, bot, reload }: { open: boolean; preset?: { kind: string; places: string }; onClose: () => void; balance: unknown; currency?: string; bot?: string; reload: () => Promise<void> }) {
  const empty = { title: "", text: "", kind: "bots", places: "", language: "ru", topics: [] as number[], cpm: "3", budget: "1", daily_limit: "", slug: "", greeting: "", followup: "", autobid: true, max_cpm: "", paused: false };
  const [f, setF] = useState(empty);
  const [topicsOpen, setTopicsOpen] = useState(false);
  const [seen, setSeen] = useState<typeof preset>(undefined);
  if (open && preset && preset !== seen) {
    setSeen(preset);
    if (preset.places) setF((x) => ({ ...x, kind: preset.kind, places: preset.places }));
  }
  const targets = useResource(open && f.kind === "channels" ? "tg-ads/targets" : null);
  const confirm = useConfirm();
  const set = (k: keyof typeof empty, v: unknown) => setF((x) => ({ ...x, [k]: v }));
  const slug = (f.slug || f.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "")).slice(0, 32);
  const submit = () =>
    confirm({
      title: "Создать объявление?",
      description: `${Number(f.budget) > 1 ? "Бюджет больше 1 TON: если эти площадки ещё не окупались, лучше начать с 1 TON и добавить, когда объявление получит «масштабировать». " : ""}С баланса кабинета на объявление уйдёт ${price(f.budget)} ${currency || "TON"} (сейчас на балансе ${price(balance)}). Ставка ${price(f.cpm)}${f.autobid ? `, автоставка до ${f.max_cpm ? price(f.max_cpm) : autoTop(f.cpm)}${!Number(f.daily_limit) && Number(f.budget) > 0 ? `, лимит в день ${price(Math.min(Number(f.budget), Math.max(0.5, Number(f.budget) / 2)))}` : ""}` : ""}. После создания — модерация Telegram.`,
      label: "Создать",
      action: async () => {
        const got = await api("tg-ads/create", {
          ...f,
          slug: f.slug,
          places: f.places.split(/[\s,]+/).filter(Boolean),
          link_title: `TG Ads · ${f.title}`,
        });
        toast.success(`Создано, ссылка ad_${got.slug} заведена. Объявление на модерации`);
        setF(empty);
        onClose();
        await reload();
      },
    });
  const topics: Data[] = targets.data?.topics || [];
  const langs: Data[] = targets.data?.languages || [];
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="tga-modal tga-create">
        <DialogHeader>
          <DialogTitle>Новое объявление</DialogTitle>
          <DialogDescription>Ссылка ad_… для статистики заводится сама — каждый пришедший будет посчитан.</DialogDescription>
        </DialogHeader>
        <div className="tga-create-grid">
          <div className="space-y-3">
            <label className="tga-field">
              <span>Название (видно только вам)</span>
              <Input value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="Боты: hitvpn · CPM 3" />
            </label>
            <label className="tga-field">
              <span>Текст <em className={f.text.length > 160 ? "text-destructive" : ""}>{f.text.length}/160</em></span>
              <Textarea rows={4} value={f.text} onChange={(e) => set("text", e.target.value)} placeholder="Соцсети и видео не грузятся? Лягушка VPN включается за минуту прямо в Telegram." />
            </label>
            <div className="tga-seg">
              {[["bots", "В ботах"], ["channels", "В каналах"]].map(([k, l]) => (
                <button key={k} type="button" className={f.kind === k ? "on" : ""} onClick={() => set("kind", k)}>{l}</button>
              ))}
            </div>
            {f.kind === "bots" ? (
              <label className="tga-field">
                <span>Боты — @username через пробел или с новой строки</span>
                <Textarea rows={3} value={f.places} onChange={(e) => set("places", e.target.value)} placeholder={"@hitvpnbot\n@AtlantaVPN_bot"} />
              </label>
            ) : (
              <>
                <label className="tga-field">
                  <span>Каналы (пусто — по языку и темам)</span>
                  <Textarea rows={2} value={f.places} onChange={(e) => set("places", e.target.value)} placeholder="@channel1 @channel2" />
                </label>
                {!f.places.trim() && (
                  <div className="grid grid-cols-2 gap-2">
                    <label className="tga-field">
                      <span>Язык каналов</span>
                      <select className="tga-select" value={f.language} onChange={(e) => set("language", e.target.value)}>
                        {(langs.length ? langs : [{ code: "ru", name: "Russian" }]).map((l) => (
                          <option key={l.code ?? l.language_code} value={l.code ?? l.language_code}>{l.name}</option>
                        ))}
                      </select>
                    </label>
                    <div className="tga-field">
                      <span>Темы</span>
                      <button type="button" className="tga-select text-left" onClick={() => setTopicsOpen((x) => !x)}>
                        {f.topics.length ? `${f.topics.length} выбрано` : "любые"} <ChevronDown className="inline size-3" />
                      </button>
                    </div>
                    {topicsOpen && (
                      <div className="tga-topics col-span-2">
                        {topics.map((t) => {
                          const id = Number(t.id ?? t.topic_id);
                          const on = f.topics.includes(id);
                          return (
                            <button key={id} type="button" className={on ? "on" : ""} onClick={() => set("topics", on ? f.topics.filter((x) => x !== id) : [...f.topics, id])}>
                              {t.name}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          <div className="space-y-3">
            <AdBubble text={f.text || "Текст объявления"} />
            <div className="grid grid-cols-2 gap-2">
              <label className="tga-field">
                <span>CPM</span>
                <div className="tga-input-gem"><Gem /><Input value={f.cpm} onChange={(e) => set("cpm", e.target.value.replace(",", "."))} inputMode="decimal" /></div>
              </label>
              <label className="tga-field">
                <span title="Новую площадку — на 1 TON, добавлять, когда окупится">Бюджет · на пробу 1</span>
                <div className="tga-input-gem"><Gem /><Input value={f.budget} onChange={(e) => set("budget", e.target.value.replace(",", "."))} inputMode="decimal" /></div>
              </label>
              <label className="tga-field">
                <span>Лимит в день</span>
                <div className="tga-input-gem"><Gem /><Input value={f.daily_limit} onChange={(e) => set("daily_limit", e.target.value.replace(",", "."))} placeholder={f.autobid ? "½ бюджета" : "без лимита"} inputMode="decimal" /></div>
              </label>
              <label className="tga-field">
                <span>Код ссылки</span>
                <Input value={f.slug} onChange={(e) => set("slug", e.target.value.toLowerCase())} placeholder={slug || "bots_new"} />
              </label>
            </div>
            <p className="tga-muted text-xs break-all">t.me/{bot}?start=ad_{f.slug || slug || "…"}</p>
            <label className="tga-switch-row">
              <Switch checked={f.autobid} onCheckedChange={(v) => set("autobid", v)} />
              <span>Автоставка, потолок</span>
              <div className="tga-input-gem small"><Gem /><Input value={f.max_cpm} onChange={(e) => set("max_cpm", e.target.value.replace(",", "."))} placeholder={autoTop(f.cpm)} disabled={!f.autobid} /></div>
            </label>
            <label className="tga-switch-row">
              <Switch checked={f.paused} onCheckedChange={(v) => set("paused", v)} />
              <span>Создать на паузе</span>
            </label>
            <label className="tga-field">
              <span>Приветствие в боте для пришедших (необязательно)</span>
              <Textarea rows={2} value={f.greeting} onChange={(e) => set("greeting", e.target.value)} />
            </label>
            <label className="tga-field">
              <span>Дожим через час, если не подключился (необязательно)</span>
              <Textarea rows={2} value={f.followup} onChange={(e) => set("followup", e.target.value)} placeholder="{name}, соцсети всё ещё не грузятся? Подключение — одна кнопка 🐸" />
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button disabled={!f.title.trim() || !f.text.trim() || f.text.length > 160} onClick={submit}>Создать объявление</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
