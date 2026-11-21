import { useMemo, useState, type ReactNode } from "react";
import { api, date, money, useResource, type Data } from "@/lib/api";
import {
  ActionButton,
  Choice,
  DataTable,
  Empty,
  Failure,
  Field,
  Loading,
  Panel,
  useConfirm,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FlaskConical, Plus } from "lucide-react";
import { toast } from "sonner";

const pct = (v: unknown) =>
  Number(v || 0).toLocaleString("ru-RU", { maximumFractionDigits: 1 }) + "%";

function stepName(step: Data | null | undefined, fallback: string) {
  return step ? `${step.branch} · шаг ${step.n}` : fallback;
}

type Metric = { label: string; value: (r: Data) => string; share?: (r: Data) => number; hint?: string };
type Verdict = { title: string; text: string; sure: boolean; extra?: string };

/**
 * Groups of a test side by side: the main metric big with a bar, the rest as rows; the leader is marked.
 * Verdicts go on top, because they answer «what do I do with this test».
 */
function Compare({ arms, main, metrics, verdicts }: { arms: Data[]; main: Metric; metrics: Metric[]; verdicts: Verdict[] }) {
  const best = Math.max(...arms.map((a) => main.share?.(a) ?? 0));
  const leader = arms.length > 1 && best > 0 ? arms.find((a) => (main.share?.(a) ?? 0) === best) : undefined;
  return (
    <div className="space-y-4">
      {verdicts.map((v, i) => (
        <div key={i} className={"adm-ab-verdict" + (v.sure ? " sure" : "")}>
          <b>{v.title}</b>
          <span>
            {v.text}
            {v.extra && <span className="adm-ab-muted"> · {v.extra}</span>}
          </span>
          <em>{v.sure ? "результат надёжный" : "пока не уверены"}</em>
        </div>
      ))}
      <div className="adm-ab-arms" style={{ gridTemplateColumns: `repeat(${Math.max(1, arms.length)}, minmax(0, 1fr))` }}>
        {arms.map((a) => (
          <section key={a.arm || a.label} className={"adm-ab-arm" + (a === leader ? " lead" : "")}>
            <header>
              <span>{a.label}</span>
              {a === leader && <i>впереди</i>}
            </header>
            <small title={main.hint}>{main.label}</small>
            <b>{main.value(a)}</b>
            <div className="adm-ab-bar"><i style={{ width: `${best ? ((main.share?.(a) ?? 0) / best) * 100 : 0}%` }} /></div>
            <dl>
              {metrics.map((m) => (
                <div key={m.label} title={m.hint}>
                  <dt>{m.label}</dt>
                  <dd>{m.value(a)}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
    </div>
  );
}

export function Results({ item, windowDays }: { item: Data; windowDays: number }) {
  const control = (r: Data, v: unknown) => (r.arm === "control" ? "не получали" : String(v ?? 0));
  return (
    <Compare
      arms={item.arms || []}
      main={{
        label: "Оплатили",
        hint: `Оплатили хоть раз за ${windowDays} дней после попадания в тест, нажимали кнопку или нет`,
        value: (r) => pct(r.conversion),
        share: (r) => Number(r.conversion || 0),
      }}
      metrics={[
        { label: "Людей", value: (r) => num(r.users) },
        { label: "Получили", value: (r) => control(r, r.delivered) },
        { label: "Нажали", value: (r) => control(r, r.clicked) },
        { label: "Подключились", value: (r) => num(r.connected) },
        { label: "Оплатили, человек", value: (r) => num(r.payers) },
        { label: "Выручка", value: (r) => money(r.rub) },
        { label: "₽ на человека", value: (r) => money(r.rub_per_user) },
        ...((item.arms || []).some((r: Data) => r.gift_rub) ? [{ label: "Подарено", value: (r: Data) => (r.gift_rub ? money(r.gift_rub) : "—") }] : []),
      ]}
      verdicts={(item.comparisons || []).map((c: Data) => ({
        title: `${String(c.arm).toUpperCase()} против ${c.against === "control" ? "контроля" : String(c.against).toUpperCase()}`,
        text: c.verdict,
        sure: !!c.sure,
        extra: c.rub_per_100 !== undefined ? `${c.rub_per_100 >= 0 ? "+" : ""}${money(c.rub_per_100)} на каждые 100 человек` : undefined,
      }))}
    />
  );
}

const num = (v: unknown) => Number(v || 0).toLocaleString("ru-RU");
const toVerdicts = (list: Data[] | undefined): Verdict[] =>
  (list || []).map((v) => ({ title: v.what, text: v.verdict, sure: !!v.sure }));

/** One test, whatever its kind: status, what is compared, verdict and the groups. */
function TestCard({
  title,
  item,
  facts,
  onStop,
  children,
  extra,
}: {
  title: string;
  item: Data;
  facts: string[];
  onStop?: () => void;
  children: ReactNode;
  extra?: ReactNode;
}) {
  return (
    <article className="adm-ab-card">
      <header>
        <div className="min-w-0">
          <span className={"adm-ab-status" + (item.running ? " on" : "")}>
            <i />
            {item.running ? "Идёт" : "Остановлен"}
          </span>
          <h3>{title}</h3>
          <p>
            {date(item.started_at)}
            {item.stopped_at ? ` — ${date(item.stopped_at)}` : " — сейчас"}
          </p>
          {facts.length > 0 && (
            <div className="adm-ab-facts">
              {facts.map((f) => (
                <span key={f}>{f}</span>
              ))}
            </div>
          )}
        </div>
        {onStop && item.running && (
          <Button variant="outline" onClick={onStop}>
            Остановить
          </Button>
        )}
      </header>
      {extra}
      {children}
    </article>
  );
}

function NewTest({
  steps,
  maxHoldout,
  onDone,
  onClose,
}: {
  steps: Data[];
  maxHoldout: number;
  onDone: () => void;
  onClose: () => void;
}) {
  const [stepId, setStepId] = useState(""),
    [holdout, setHoldout] = useState("10"),
    [bPct, setBPct] = useState("50"),
    [text, setText] = useState(""),
    [days, setDays] = useState(""),
    [bonus, setBonus] = useState("");
  const step = useMemo(() => steps.find((s) => s.id === stepId), [steps, stepId]);
  const hasB = Number(bPct) > 0;
  return (
    <div className="space-y-4">
      <Field label="Сообщение" hint={step ? `Условие: ${step.condition}. Через ${step.wait_hours} ч.` : undefined}>
        <Choice
          label="Выберите сообщение"
          value={stepId}
          onChange={setStepId}
          options={[["", "Выберите сообщение"], ...steps.map((s): [string, string] => [s.id, stepName(s, s.id)])]}
        />
      </Field>
      {step && (
        <div className="rounded-md border bg-muted/40 p-3 text-sm whitespace-pre-wrap">
          <div className="text-xs text-muted-foreground mb-1">Вариант A — текст сейчас</div>
          {step.text}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Контрольная группа, %"
          hint={`Им сообщение не отправится. Так видно, приносит ли оно деньги вообще. До ${maxHoldout}%.`}
        >
          <Input inputMode="numeric" value={holdout} onChange={(e) => setHoldout(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label="Вариант B, % от остальных" hint="0 — проверить только сообщение против тишины. 100 — заменить A на B.">
          <Input inputMode="numeric" value={bPct} onChange={(e) => setBPct(e.target.value.replace(/\D/g, ""))} />
        </Field>
      </div>
      {hasB && (
        <>
          <Field
            label="Текст варианта B"
            hint={`Пусто — текст как у A (если меняете только подарок или бонус). Можно {name}, {gift_days}, {price}, {min_topup}${step?.bonus ? ", {bonus_min}, {bonus_pct}, {bonus_until}" : ""}, HTML как в боте.`}
          >
            <Textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
          </Field>
          {step?.bonus && (
            <Field
              label="Процент бонуса для B"
              hint="Пусто — как в настройках. Например 10, чтобы проверить, хватит ли меньшего бонуса. Начисляется при пополнении тем, кто попал в B."
            >
              <Input inputMode="numeric" value={bonus} onChange={(e) => setBonus(e.target.value.replace(/\D/g, ""))} />
            </Field>
          )}
          {step?.gift && (
            <Field label="Дней в подарке для B" hint="Пусто — как у A (3 дня). От 1 до 14.">
              <Input inputMode="numeric" value={days} onChange={(e) => setDays(e.target.value.replace(/\D/g, ""))} />
            </Field>
          )}
        </>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>
          Отмена
        </Button>
        <ActionButton
          disabled={!stepId}
          onAction={async () => {
            await api("experiments", {
              step_id: stepId,
              holdout_pct: holdout,
              b_pct: bPct,
              b_text: hasB ? text : "",
              b_gift_days: hasB && step?.gift ? days : "",
              b_bonus_pct: hasB && step?.bonus ? bonus : "",
            });
            toast.success("Тест запущен");
            onDone();
          }}
        >
          Запустить тест
        </ActionButton>
      </div>
    </div>
  );
}

/** A built-in test that is switched on and off as a whole (the gift and the install step). */
function useBuiltinTest(path: string, texts: { start: string; stop: string; title: string }) {
  const resource = useResource(path);
  const confirm = useConfirm();
  const items: Data[] = resource.data?.items || [];
  const current = items.find((i) => i.running);
  const run = (action: "start" | "stop") =>
    confirm({
      title: action === "start" ? `Запустить тест «${texts.title}»?` : `Остановить тест «${texts.title}»?`,
      description: action === "start" ? texts.start : texts.stop,
      label: action === "start" ? "Запустить" : "Остановить",
      action: async () => {
        await api(path, { action });
        toast.success(action === "start" ? "Тест запущен" : "Тест остановлен");
        await resource.reload();
      },
    });
  return { resource, items, current, run };
}

export function ExperimentsPage() {
  const resource = useResource("experiments"),
    [open, setOpen] = useState(false),
    [view, setView] = useState<"running" | "done">("running");
  const confirm = useConfirm();
  const data = resource.data;
  const windowDays = data?.window_days || 7;
  const gift = useBuiltinTest("auto-gift", {
    title: "Стартовый подарок",
    start:
      "Половина новых пользователей получит стартовый подарок на баланс сразу, без кнопки «Забрать подарок». Дни начнут тратиться только после первого подключения.",
    stop: "Все новые снова будут забирать подарок кнопкой. Результаты останутся здесь.",
  });
  const install = useBuiltinTest("install-test", {
    title: "Шаг установки",
    start:
      "Половина тех, кто подключает первое устройство, увидит «Скачать» и «Добавить в приложение» на одной карточке. Главное мерило — подключили VPN за сутки.",
    stop: "Все снова увидят шаг установки как сейчас. Результаты останутся здесь.",
  });
  const frog = useBuiltinTest("frog-test", {
    title: "Живая лягушка",
    start:
      "Половина тех, кто открывает кабинет, увидит живую лягушку на главной, остальные — как сейчас. Главное мерило — возвращаются ли в кабинет в другой день; деньги и нажатия «Пополнить» — чтобы игрушка не мешала платить.",
    stop: "Лягушку снова решает переключатель в Настройках. Результаты останутся здесь.",
  });
  const items: Data[] = data?.items || [];
  const busy = new Set(items.filter((i) => i.running).map((i) => i.step_id));
  const free = (data?.steps || []).filter((s: Data) => !busy.has(s.id));

  const messageCard = (item: Data) => (
    <TestCard
      key={"m" + item.id}
      title={stepName(item.step, item.step_id)}
      item={item}
      facts={[
        "Сообщение бота",
        `контроль ${item.holdout_pct}%`,
        ...(item.b_pct ? [`вариант B ${item.b_pct}% остальных`] : ["A против тишины"]),
        ...(item.b_gift_days ? [`подарок B: ${item.b_gift_days} дн.`] : []),
        ...(item.b_bonus_pct ? [`бонус B: +${item.b_bonus_pct}%`] : []),
        `оплаты за ${windowDays} дней`,
      ]}
      onStop={() =>
        confirm({
          title: "Остановить тест?",
          description: "Все снова будут получать вариант A. Результаты останутся здесь.",
          label: "Остановить",
          action: async () => {
            await api(`experiments/${item.id}/stop`, {});
            toast.success("Тест остановлен");
            await resource.reload();
          },
        })
      }
      extra={
        item.b_text ? (
          <details className="adm-ab-text">
            <summary>Текст варианта B</summary>
            <div>{item.b_text}</div>
          </details>
        ) : undefined
      }
    >
      <Results item={item} windowDays={windowDays} />
    </TestCard>
  );
  const giftCard = (item: Data) => (
    <TestCard
      key={"g" + item.started_at}
      title="Стартовый подарок: сразу на балансе или по кнопке"
      item={item}
      facts={["Кабинет", "50 / 50 новых пользователей", `за ${gift.resource.data?.window_days || 14} дней`]}
      onStop={() => gift.run("stop")}
    >
      <Compare
        arms={item.arms || []}
        main={{ label: "Оплатили", value: (r) => pct(r.conversion), share: (r) => Number(r.conversion || 0) }}
        metrics={[
          { label: "Людей", value: (r) => num(r.users) },
          { label: "С подарком", value: (r) => num(r.took_gift) },
          { label: "Добавили устройство", value: (r) => num(r.device) },
          { label: "Подключили VPN", value: (r) => `${num(r.connected)} · ${pct(r.connected_pct)}` },
          { label: "Выручка", value: (r) => money(r.rub) },
          { label: "₽ на человека", value: (r) => money(r.rub_per_user) },
        ]}
        verdicts={toVerdicts(item.verdicts)}
      />
    </TestCard>
  );
  const installCard = (item: Data) => (
    <TestCard
      key={"i" + item.started_at}
      title="Шаг «Установите приложение»: как сейчас или два шага на одной карточке"
      item={item}
      facts={["Кабинет", "50 / 50 без устройства", `за ${install.resource.data?.window_days || 7} дней`]}
      onStop={() => install.run("stop")}
    >
      <Compare
        arms={item.arms || []}
        main={{
          label: "Подключили за сутки",
          value: (r) => pct(r.connected_day_pct),
          share: (r) => Number(r.connected_day_pct || 0),
        }}
        metrics={[
          { label: "Людей", value: (r) => num(r.users) },
          { label: "Создали ключ", value: (r) => `${num(r.device)} · ${pct(r.device_pct)}` },
          { label: "За сутки, человек", value: (r) => `${num(r.connected_day)} из ${num(r.day_done)}` },
          { label: "Подключили за неделю", value: (r) => `${num(r.connected)} · ${pct(r.connected_pct)}` },
          { label: "Оплатили", value: (r) => `${num(r.payers)} · ${pct(r.conversion)}` },
          { label: "Выручка", value: (r) => money(r.rub) },
        ]}
        verdicts={toVerdicts(item.verdicts)}
      />
    </TestCard>
  );

  const frogCard = (item: Data) => (
    <TestCard
      key={"f" + item.started_at}
      title="Живая лягушка на главной: притягивает, пофиг или отталкивает"
      item={item}
      facts={["Кабинет", "50 / 50 открывших кабинет", `возвраты за ${frog.resource.data?.return_days || 3} дня`, `деньги за ${frog.resource.data?.window_days || 7} дней`]}
      onStop={() => frog.run("stop")}
    >
      <Compare
        arms={item.arms || []}
        main={{
          label: `Вернулись за ${frog.resource.data?.return_days || 3} дня`,
          value: (r) => pct(r.return_pct),
          share: (r) => Number(r.return_pct || 0),
        }}
        metrics={[
          { label: "Людей", value: (r) => num(r.users) },
          { label: "Вернулись, человек", value: (r) => `${num(r.returned)} из ${num(r.ret_done)}` },
          { label: "Дней в кабинете на человека", value: (r) => String(r.days_per_user ?? 0).replace(".", ",") },
          { label: "Играли с лягушкой", value: (r) => (r.arm === "frog" ? `${num(r.players)} · ${pct(r.play_pct)}` : "—") },
          { label: `Играли ${5}+ раз`, value: (r) => (r.arm === "frog" ? `${num(r.fans)} · ${pct(r.fan_pct)}` : "—") },
          { label: "Нажали «Пополнить»", value: (r) => `${num(r.topup_clickers)} · ${pct(r.topup_pct)}` },
          { label: "Оплатили", value: (r) => `${num(r.payers)} · ${pct(r.conversion)}` },
          { label: "₽ на человека", value: (r) => money(r.rub_per_user) },
        ]}
        verdicts={toVerdicts(item.verdicts)}
      />
    </TestCard>
  );

  const all = [
    ...frog.items.map((i) => ({ at: i.started_at, running: !!i.running, node: frogCard(i) })),
    ...install.items.map((i) => ({ at: i.started_at, running: !!i.running, node: installCard(i) })),
    ...gift.items.map((i) => ({ at: i.started_at, running: !!i.running, node: giftCard(i) })),
    ...items.map((i) => ({ at: i.started_at, running: !!i.running, node: messageCard(i) })),
  ].sort((a, b) => String(b.at).localeCompare(String(a.at)));
  const running = all.filter((t) => t.running), done = all.filter((t) => !t.running);
  const shown = view === "running" ? running : done;
  const loading = !data || !gift.resource.data || !install.resource.data || !frog.resource.data;
  const error = resource.error || gift.resource.error || install.resource.error || frog.resource.error;

  return (
    <div className="space-y-5">
      <div className="adm-ab-top">
        <div className="adm-seg" role="group" aria-label="Какие тесты показать">
          {([["running", "Идут", running.length], ["done", "Завершённые", done.length]] as const).map(([v, label, n]) => (
            <button key={v} type="button" aria-pressed={view === v} className="px-4 text-sm font-medium" onClick={() => setView(v)}>
              {label} <span className="adm-ab-muted">{n}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {!frog.current && frog.resource.data && (
            <Button variant="outline" onClick={() => frog.run("start")}>Тест живой лягушки</Button>
          )}
          {!install.current && install.resource.data && (
            <Button variant="outline" onClick={() => install.run("start")}>Тест шага установки</Button>
          )}
          {!gift.current && gift.resource.data && (
            <Button variant="outline" onClick={() => gift.run("start")}>Тест стартового подарка</Button>
          )}
          <Button onClick={() => setOpen(true)} disabled={!data}>
            <Plus />
            Тест сообщения
          </Button>
        </div>
      </div>
      <p className="text-sm text-muted-foreground max-w-3xl">
        Каждый, кто попал в тест, остаётся в своей группе навсегда. Оплаты считаются за {windowDays} дней после попадания
        — все, а не только после нажатия кнопки. Предупреждения о балансе и неоплаченном счёте не тестируются.
      </p>
      {error ? (
        <Failure message={error} retry={() => { void resource.reload(); void gift.resource.reload(); void install.resource.reload(); void frog.resource.reload(); }} />
      ) : loading ? (
        <Loading />
      ) : !shown.length ? (
        view === "running" ? (
          <Empty
            title="Сейчас тестов нет"
            description="Начните с контрольной группы 10% для первого сообщения после окончания подарка: станет видно, сколько денег оно приносит."
            action={
              <Button variant="outline" onClick={() => setOpen(true)}>
                <FlaskConical />
                Запустить тест сообщения
              </Button>
            }
          />
        ) : (
          <Empty title="Завершённых тестов нет" description="Остановленные тесты и их результаты появятся здесь." />
        )
      ) : (
        shown.map((t) => t.node)
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Новый тест сообщения</DialogTitle>
            <DialogDescription>
              Выберите сообщение и что с ним сравнить. На одно сообщение — один тест одновременно.
            </DialogDescription>
          </DialogHeader>
          {data && (
            <NewTest
              steps={free}
              maxHoldout={data.max_holdout || 50}
              onClose={() => setOpen(false)}
              onDone={() => {
                setOpen(false);
                setView("running");
                void resource.reload();
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
