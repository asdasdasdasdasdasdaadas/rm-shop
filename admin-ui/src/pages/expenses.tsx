// «Затраты»: the service's regular bills (app/expenses.py) — hosting, domains, servers — and reminders to pay them.
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, useResource, type Data } from "@/lib/api";
import { DataTable, Empty, Failure, Field, Loading, Panel, Choice, useConfirm } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Check, ExternalLink, Loader2, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";

const SIGN: Record<string, string> = { RUB: "₽", USD: "$", EUR: "€" };
const amount = (value: unknown, currency = "RUB") =>
  Number(value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 }) + " " + (SIGN[currency] || currency);
// Sums are kept per currency: «1 200 ₽ + 15 $». Rates are not guessed.
const totals = (map: Data | undefined) => {
  const parts = Object.entries(map || {}).filter(([, v]) => Number(v) > 0);
  return parts.length ? parts.map(([cur, v]) => amount(v, cur)).join(" + ") : "0 ₽";
};
const day = (iso: unknown) =>
  iso ? new Date(String(iso).slice(0, 10) + "T12:00:00Z").toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" }) : "—";
const plural = (n: number, one: string, few: string, many: string) => {
  const a = Math.abs(n) % 100, b = a % 10;
  return a > 10 && a < 15 ? many : b === 1 ? one : b >= 2 && b <= 4 ? few : many;
};
export const whenLeft = (left: number | null | undefined) => {
  if (left == null) return "";
  if (left < 0) return `просрочено на ${-left} ${plural(-left, "день", "дня", "дней")}`;
  if (left === 0) return "сегодня";
  if (left === 1) return "завтра";
  return `через ${left} ${plural(left, "день", "дня", "дней")}`;
};
function Due({ left }: { left: number | null | undefined }) {
  if (left == null) return null;
  const tone = left < 0 ? "destructive" : left <= 3 ? "default" : "secondary";
  return <Badge variant={tone}>{whenLeft(left)}</Badge>;
}

const BLANK = { title: "", amount: "", currency: "RUB", period: "month", next_date: "", url: "", description: "" };
type Form = typeof BLANK;

function ExpenseDialog({ item, periods, onClose, onSaved }: { item: Data | null | "new"; periods: Data; onClose: () => void; onSaved: (d: Data) => void }) {
  const [form, setForm] = useState<Form>(BLANK), [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => {
    setError("");
    if (item === "new") setForm({ ...BLANK, next_date: new Date().toISOString().slice(0, 10) });
    else if (item) setForm({ title: item.title, amount: String(item.amount), currency: item.currency, period: item.period, next_date: item.next_date || "", url: item.url, description: item.description });
  }, [item]);
  const set = (key: keyof Form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [key]: e.target.value });
  const editing = item && item !== "new";
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const data = await api(editing ? `expenses/${(item as Data).id}` : "expenses", form);
      toast.success(editing ? "Затрата сохранена" : "Затрата добавлена");
      onSaved(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return <Dialog open={!!item} onOpenChange={(o) => { if (!o && !busy) onClose(); }}>
    <DialogContent className="max-w-lg">
      <DialogHeader>
        <DialogTitle>{editing ? "Изменить затрату" : "Новая затрата"}</DialogTitle>
        <DialogDescription>Дата — ближайшая оплата. После «Оплачено» она переносится на следующий срок по периоду.</DialogDescription>
      </DialogHeader>
      <form className="space-y-4" onSubmit={save}>
        <Field label="Наименование"><Input required maxLength={120} placeholder="Хостинг, домен, сервер…" value={form.title} onChange={set("title")} autoFocus /></Field>
        <div className="grid gap-4 sm:grid-cols-[1fr_8rem]">
          <Field label="Сумма"><Input required inputMode="decimal" placeholder="1500" value={form.amount} onChange={set("amount")} /></Field>
          <Field label="Валюта"><Choice label="Валюта" value={form.currency} onChange={(v) => setForm({ ...form, currency: v || "RUB" })} options={[["RUB", "₽ рубли"], ["USD", "$ доллары"], ["EUR", "€ евро"]]} /></Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Дата оплаты"><Input required type="date" value={form.next_date} onChange={set("next_date")} /></Field>
          <Field label="Повторяется"><Choice label="Период" value={form.period} onChange={(v) => setForm({ ...form, period: v || "month" })} options={Object.entries(periods) as [string, string][]} /></Field>
        </div>
        <Field label="Ссылка" hint="Где платить: личный кабинет хостинга, регистратора."><Input inputMode="url" maxLength={500} placeholder="https://…" value={form.url} onChange={set("url")} /></Field>
        <Field label="Описание"><Textarea maxLength={2000} rows={3} placeholder="Что это, с какой карты, логин в кабинете…" value={form.description} onChange={set("description")} /></Field>
        {error && <p role="alert" className="text-destructive text-sm">{error}</p>}
        <DialogFooter>
          <Button type="button" variant="outline" disabled={busy} onClick={onClose}>Отмена</Button>
          <Button type="submit" disabled={busy}>{busy && <Loader2 className="animate-spin" />}{editing ? "Сохранить" : "Добавить"}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>;
}

function NotifyPanel({ notify, onSaved }: { notify: Data; onSaved: (d: Data) => void }) {
  const [days, setDays] = useState((notify.days || []).join(", ")), [busy, setBusy] = useState(false);
  useEffect(() => setDays((notify.days || []).join(", ")), [notify.days]);
  const save = async (body: Data, okText: string) => {
    setBusy(true);
    try {
      onSaved(await api("expenses/notify", body));
      toast.success(okText);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const shown = (notify.days || []).map((d: number) => (d === 0 ? "в день оплаты" : `за ${d} ${plural(d, "день", "дня", "дней")}`)).join(", ");
  return <Panel title="Напоминания в канал" description={`После ${notify.hour}:00 по Москве: ${shown || "—"}, и ещё раз на следующий день, если оплата не отмечена. Каждое напоминание приходит один раз.`}
    action={<label className="flex items-center gap-3 text-sm"><span>{notify.enabled ? "Включены" : "Выключены"}</span><Switch aria-label="Напоминания об оплате" checked={!!notify.enabled} disabled={busy} onCheckedChange={(on) => void save({ enabled: on }, on ? "Напоминания включены" : "Напоминания выключены")} /></label>}>
    <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); void save({ days }, "Дни напоминаний сохранены"); }}>
      <div className="w-56"><Field label="За сколько дней напоминать" hint="Через запятую; 0 — в день оплаты."><Input value={days} onChange={(e) => setDays(e.target.value)} placeholder="3, 0" /></Field></div>
      <Button type="submit" variant="outline" disabled={busy || days.trim() === (notify.days || []).join(", ")}>Сохранить</Button>
    </form>
    <p className="mt-3 text-xs text-muted-foreground">{notify.target ? `Куда: ${notify.target}. Канал задаётся в Настройках → живой канал.` : "Некуда отправлять: не задан ни живой канал, ни ID админов."}</p>
  </Panel>;
}

export function ExpensesPage() {
  const r = useResource("expenses");
  const [edit, setEdit] = useState<Data | null | "new">(null), [busy, setBusy] = useState(0);
  const confirm = useConfirm();
  const d = r.data;
  if (r.error) return <Failure message={r.error} retry={r.reload} />;
  if (!d) return <Loading />;
  const s = d.summary;
  const paid = async (x: Data) => {
    setBusy(x.id);
    try {
      r.setData(await api(`expenses/${x.id}/paid`, {}));
      toast.success(x.period === "once" ? `«${x.title}» оплачено` : `«${x.title}» оплачено, следующая оплата перенесена`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(0);
    }
  };
  const tiles: [string, React.ReactNode, string][] = [
    ["Ближайшая оплата", s.upcoming[0] ? amount(s.upcoming[0].amount, s.upcoming[0].currency) : "—", s.upcoming[0] ? `${s.upcoming[0].title} · ${day(s.upcoming[0].date)} · ${whenLeft(s.upcoming[0].days_left)}` : "открытых затрат нет"],
    [`К оплате в этом месяце · ${s.month_label}`, totals(s.month_due), Object.keys(s.month_paid).length ? `уже оплачено ${totals(s.month_paid)}` : "в этом месяце ещё ничего не отмечено"],
    ["За 30 дней", totals(s.next_30), s.overdue_count ? `в том числе просрочено ${s.overdue_count}: ${totals(s.overdue)}` : "просроченных нет"],
    ["В месяц в среднем", totals(s.per_month), `в год ${totals(s.per_year)} · без разовых`],
  ];
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground">Хостинги, домены, сервера и другие регулярные расходы сервиса · даты по Москве</p>
      <div className="flex gap-2"><Button variant="outline" aria-label="Обновить затраты" onClick={() => void r.reload()}><RefreshCw /></Button><Button onClick={() => setEdit("new")}><Plus />Добавить затрату</Button></div>
    </div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{tiles.map(([label, value, sub]) => <div key={label} className="rounded-xl border p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="text-2xl font-semibold mt-2 tabular-nums">{value}</p><p className="mt-2 text-xs text-muted-foreground">{sub}</p></div>)}</div>
    {s.upcoming.length > 0 && <Panel title="Ближайшие оплаты" description="По дате, с просроченными сверху.">
      <ul className="divide-y">{s.upcoming.map((u: Data) => <li key={u.id} className="flex flex-wrap items-center justify-between gap-3 py-2.5">
        <span className="min-w-0"><span className="font-medium">{u.title}</span><span className="ml-2 text-sm text-muted-foreground">{day(u.date)}</span></span>
        <span className="flex items-center gap-3"><Due left={u.days_left} /><span className="tabular-nums font-medium">{amount(u.amount, u.currency)}</span></span>
      </li>)}</ul>
    </Panel>}
    <Panel title="Все затраты" description="«Оплачено» записывает платёж и переносит дату на следующий срок; разовая затрата закрывается. Сама дата не переносится, пока оплата не отмечена.">
      <DataTable rows={d.items} empty={<Empty title="Затрат пока нет" />} columns={[
        { key: "next_date", label: "Дата оплаты", cell: (x) => <span className={x.done ? "text-muted-foreground" : ""}><span className="block whitespace-nowrap">{x.done ? "оплачено" : day(x.next_date)}</span>{!x.done && <span className="mt-1 block"><Due left={x.days_left} /></span>}</span> },
        { key: "title", label: "Наименование", cell: (x) => <span className="block min-w-40"><span className="font-medium">{x.title}</span>{x.description && <span className="mt-0.5 block text-xs text-muted-foreground whitespace-pre-line line-clamp-3">{x.description}</span>}</span> },
        { key: "amount", label: "Сумма", cell: (x) => <span className="whitespace-nowrap tabular-nums"><span className="block font-medium">{amount(x.amount, x.currency)}</span><span className="block text-xs text-muted-foreground">{x.period_label}{x.period !== "month" && x.monthly ? ` · ${amount(x.monthly, x.currency)}/мес` : ""}</span></span> },
        { key: "url", label: "Ссылка", cell: (x) => x.url ? <a href={x.url} target="_blank" rel="noopener noreferrer" className="inline-flex max-w-56 items-center gap-1 text-primary underline-offset-4 hover:underline"><span className="truncate">{x.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span><ExternalLink className="size-3.5 shrink-0" /></a> : <span className="text-muted-foreground">—</span> },
        { key: "actions", label: <span className="sr-only">Действия</span>, className: "text-right", cell: (x) => <span className="flex justify-end gap-1">
          {!x.done && <Button size="sm" variant="outline" disabled={busy === x.id} onClick={() => void paid(x)}>{busy === x.id ? <Loader2 className="animate-spin" /> : <Check />}Оплачено</Button>}
          <Button size="icon" variant="ghost" aria-label={`Изменить «${x.title}»`} onClick={() => setEdit(x)}><Pencil /></Button>
          <Button size="icon" variant="ghost" aria-label={`Удалить «${x.title}»`} onClick={() => confirm({ title: `Удалить «${x.title}»?`, description: "Затрата пропадёт из списка и сводки. Записи о прошлых оплатах останутся в истории.", label: "Удалить", danger: true, action: async () => { r.setData(await api(`expenses/${x.id}/delete`, {})); toast.success("Затрата удалена"); } })}><Trash2 /></Button>
        </span> },
      ]} />
    </Panel>
    <NotifyPanel notify={d.notify} onSaved={(data) => r.setData(data)} />
    {d.history.length > 0 && <Panel title="Последние оплаты" description="Что отмечено кнопкой «Оплачено».">
      <DataTable rows={d.history} columns={[
        { key: "paid_on", label: "Оплачено", cell: (h) => day(h.paid_on) },
        { key: "title", label: "Наименование" },
        { key: "amount", label: "Сумма", cell: (h) => amount(h.amount, h.currency) },
        { key: "due_date", label: "За срок", cell: (h) => day(h.due_date) },
      ]} />
    </Panel>}
    <ExpenseDialog item={edit} periods={d.periods} onClose={() => setEdit(null)} onSaved={(data) => { r.setData(data); setEdit(null); }} />
  </div>;
}
