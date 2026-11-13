// «Подарок → подключение → оплаты» and «Результаты по источникам» as tables you can read at a glance:
// one row per step, the last 30 days next to the previous 30, the change in points, the weak step marked.
import { useState } from "react";

type Transition = { label: string; converted: number; eligible: number; rate: number | null; median_hours: number | null };
type Period = { period: string; users: number; transitions: Transition[]; blocked: number; block_eligible: number; block_rate: number | null };
type Outcome = { key: string; label: string; users: number; eligible: number; rate: number | null };
type SourcePeriod = { period: string; users: number; outcomes: Outcome[]; transitions: Transition[] };
type Source = { source: string; label: string; items: SourcePeriod[] };
export type Journey = { note?: string; items: Period[]; sources?: Source[]; sources_note?: string };

// Below this many people a percentage says little: show it, but greyed and without a verdict.
const FEW = 5;
const pick = <T extends { period: string }>(items: T[], p: string) => items.find((i) => i.period === p);

function wait(h: number | null) {
  if (h == null) return "—";
  if (h < 0.05) return "сразу";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} мин`;
  if (h < 48) return `${Math.round(h)} ч`;
  return `${Math.round(h / 24)} дн`;
}

function Rate({ rate, n, of, big }: { rate: number | null; n: number; of: number; big?: boolean }) {
  const few = of < FEW;
  return (
    <div className={few ? "opacity-50" : ""} title={few ? "Мало людей — процент случайный" : undefined}>
      <div className={(big ? "text-lg " : "") + "font-semibold tabular-nums"}>{rate == null || !of ? "—" : `${Math.round(rate)}%`}</div>
      <div className="text-xs text-muted-foreground tabular-nums">{of ? `${n} из ${of}` : "нет данных"}</div>
    </div>
  );
}

function Change({ now, prev, worseUp, quiet }: { now?: { rate: number | null; eligible: number }; prev?: { rate: number | null; eligible: number }; worseUp?: boolean; quiet?: boolean }) {
  if (!now || !prev || now.rate == null || prev.rate == null || now.eligible < FEW || prev.eligible < FEW)
    return quiet ? null : <span className="text-xs text-muted-foreground">—</span>;
  const d = Math.round(now.rate - prev.rate);
  if (!d) return <span className="text-xs text-muted-foreground">без изменений</span>;
  const good = worseUp ? d < 0 : d > 0;
  return (
    <span className={"text-sm font-medium tabular-nums " + (good ? "text-emerald-500" : "text-red-500")} title="Разница в процентных пунктах">
      {d > 0 ? "↑" : "↓"} {Math.abs(d)} п.п.
    </span>
  );
}

function Bar({ rate, weak }: { rate: number | null; weak: boolean }) {
  return (
    <div className="h-1.5 rounded-full bg-muted overflow-hidden mt-1.5">
      <div className={"h-full rounded-full " + (weak ? "bg-red-500" : "bg-primary")} style={{ width: `${Math.max(0, Math.min(100, rate || 0))}%` }} />
    </div>
  );
}

function HowCounted({ text }: { text?: string }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  return (
    <div className="text-xs text-muted-foreground">
      <button type="button" className="underline decoration-dotted underline-offset-2" onClick={() => setOpen(!open)}>
        {open ? "Скрыть, как считается" : "Как считается"}
      </button>
      {open && <p className="mt-2 max-w-3xl leading-relaxed">{text}</p>}
    </div>
  );
}

const th = "py-2 px-3 font-normal text-muted-foreground text-xs whitespace-nowrap";
const td = "py-3 px-3 align-top";

export function JourneyFunnel({ data }: { data: Journey }) {
  const now = pick(data.items, "current"), prev = pick(data.items, "previous");
  if (!now) return null;
  const solid = now.transitions.filter((t) => t.rate != null && t.eligible >= FEW);
  const weakest = solid.length ? solid.reduce((a, b) => ((b.rate ?? 0) < (a.rate ?? 0) ? b : a)) : null;
  return (
    <section className="rounded-xl border p-5 space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">Путь нового пользователя</h2>
        <span className="text-sm text-muted-foreground">
          Пришли за 30 дней: <b className="text-foreground">{now.users}</b>
          {prev ? <> · за прошлые 30: {prev.users}</> : null}
        </span>
      </div>
      {weakest && (
        <p className="rounded-lg bg-red-500/10 px-4 py-3 text-sm">
          Узкое место: <b>{weakest.label}</b> — {Math.round(weakest.rate ?? 0)}% ({weakest.converted} из {weakest.eligible}).
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left">
            <tr>
              <th className={th + " pl-0"}>Шаг · за 7 дней</th>
              <th className={th + " w-40"}>Последние 30 дней</th>
              <th className={th}>Прошлые 30 дней</th>
              <th className={th}>Изменение</th>
              <th className={th}>Обычно за</th>
            </tr>
          </thead>
          <tbody>
            {now.transitions.map((t, i) => {
              const p = prev?.transitions[i], weak = t === weakest;
              return (
                <tr key={t.label} className={"border-t " + (weak ? "bg-red-500/5" : "")}>
                  <td className={td + " pl-0 font-medium"}>{t.label}</td>
                  <td className={td}>
                    <Rate rate={t.rate} n={t.converted} of={t.eligible} big />
                    <Bar rate={t.rate} weak={weak} />
                  </td>
                  <td className={td}>{p ? <Rate rate={p.rate} n={p.converted} of={p.eligible} /> : "—"}</td>
                  <td className={td}><Change now={t} prev={p} /></td>
                  <td className={td + " tabular-nums"}>{wait(t.median_hours)}</td>
                </tr>
              );
            })}
            <tr className="border-t">
              <td className={td + " pl-0 text-muted-foreground"}>Заблокировали бота</td>
              <td className={td}><Rate rate={now.block_rate} n={now.blocked} of={now.block_eligible} /></td>
              <td className={td}>{prev ? <Rate rate={prev.block_rate} n={prev.blocked} of={prev.block_eligible} /> : "—"}</td>
              <td className={td}>
                <Change worseUp now={{ rate: now.block_rate, eligible: now.block_eligible }}
                  prev={prev ? { rate: prev.block_rate, eligible: prev.block_eligible } : undefined} />
              </td>
              <td className={td} />
            </tr>
          </tbody>
        </table>
      </div>
      <HowCounted text={data.note} />
    </section>
  );
}

const OUTCOMES: [string, string][] = [["online", "Подключились"], ["paid", "Оплатили"], ["repeat_paid", "Оплатили повторно"]];

export function JourneySources({ data }: { data: Journey }) {
  const sources = data.sources || [];
  if (!sources.length) return null;
  // Outcome keys come from the server; fall back to their order if the names differ.
  const keys = (sources[0].items[0]?.outcomes || []).map((o) => o.key);
  const cols = keys.map((k, i) => [k, OUTCOMES.find(([key]) => key === k)?.[1] || sources[0].items[0].outcomes[i].label.replace(/^Первый |^Первая /, "")]);
  const best = (k: string) => {
    let top: string | null = null, rate = -1;
    for (const s of sources) {
      const o = pick(s.items, "current")?.outcomes.find((x) => x.key === k);
      if (o && o.rate != null && o.eligible >= FEW && o.rate > rate) { rate = o.rate; top = s.source; }
    }
    return rate > 0 ? top : null;
  };
  return (
    <section className="rounded-xl border p-5 space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">Откуда приходят и кто платит</h2>
        <span className="text-sm text-muted-foreground">Последние 30 дней, в скобках — прошлые 30 · итог за первые 7 дней</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left">
            <tr>
              <th className={th + " pl-0"}>Источник</th>
              <th className={th}>Пришли</th>
              {cols.map(([k, label]) => <th key={k} className={th}>{label}</th>)}
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => {
              const now = pick(s.items, "current"), prev = pick(s.items, "previous");
              return (
                <tr key={s.source} className="border-t">
                  <td className={td + " pl-0 font-medium"}>{s.label}</td>
                  <td className={td + " tabular-nums"}>
                    <div className="text-lg font-semibold">{now?.users ?? 0}</div>
                    <div className="text-xs text-muted-foreground">({prev?.users ?? 0})</div>
                  </td>
                  {cols.map(([k]) => {
                    const o = now?.outcomes.find((x) => x.key === k), po = prev?.outcomes.find((x) => x.key === k);
                    const top = best(k) === s.source;
                    return (
                      <td key={k} className={td + (top ? " bg-emerald-500/5" : "")}>
                        {o ? <Rate rate={o.rate} n={o.users} of={o.eligible} big /> : "—"}
                        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                          {po && po.eligible ? <span>({po.rate == null ? "—" : Math.round(po.rate) + "%"})</span> : null}
                          <Change now={o} prev={po} quiet />
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        Серым — меньше {FEW} человек, процент пока случайный. Зелёным — лучший источник по этому шагу.
      </p>
      <HowCounted text={data.sources_note} />
    </section>
  );
}
