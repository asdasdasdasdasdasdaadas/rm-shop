import { useMemo, useState } from "react";
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

export function Results({ item, windowDays }: { item: Data; windowDays: number }) {
  const arms: Data[] = item.arms || [];
  return (
    <div className="space-y-3">
      <DataTable
        rows={arms}
        columns={[
          { key: "label", label: "Группа" },
          { key: "users", label: "Людей" },
          {
            key: "delivered",
            label: "Получили",
            cell: (r) => (r.arm === "control" ? "—" : r.delivered),
          },
          {
            key: "clicked",
            label: "Нажали",
            cell: (r) => (r.arm === "control" ? "—" : r.clicked),
          },
          { key: "connected", label: "Подключились" },
          {
            key: "payers",
            label: (
              <span title={`Оплатили хоть раз за ${windowDays} дней после попадания в тест, нажимали кнопку или нет`}>
                Оплатили
              </span>
            ),
            cell: (r) => `${r.payers} · ${pct(r.conversion)}`,
          },
          { key: "rub", label: "Выручка", cell: (r) => money(r.rub) },
          {
            key: "rub_per_user",
            label: "₽ на человека",
            cell: (r) => money(r.rub_per_user),
          },
          {
            key: "gift_rub",
            label: "Подарено",
            cell: (r) => (r.gift_rub ? money(r.gift_rub) : "—"),
          },
        ]}
      />
      {(item.comparisons || []).map((c: Data, i: number) => (
        <div key={i} className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant={c.sure ? "default" : "secondary"}>
            {c.arm.toUpperCase()} против {c.against === "control" ? "контроля" : c.against.toUpperCase()}
          </Badge>
          <span>{c.verdict}</span>
          {c.rub_per_100 !== undefined && (
            <span className="text-muted-foreground">
              · {c.rub_per_100 >= 0 ? "+" : ""}
              {money(c.rub_per_100)} на каждые 100 человек
            </span>
          )}
        </div>
      ))}
    </div>
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
    [days, setDays] = useState("");
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
            hint="Пусто — текст как у A (если меняете только подарок). Можно {name}, {gift_days}, {price}, {min_topup}, HTML как в боте."
          >
            <Textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
          </Field>
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

export function ExperimentsPage() {
  const resource = useResource("experiments"),
    [open, setOpen] = useState(false);
  const confirm = useConfirm();
  const data = resource.data;
  const items: Data[] = data?.items || [];
  const running = items.filter((i) => i.running),
    done = items.filter((i) => !i.running);
  const busy = new Set(running.map((i) => i.step_id));
  const free = (data?.steps || []).filter((s: Data) => !busy.has(s.id));
  const card = (item: Data) => (
    <Panel
      key={item.id}
      title={stepName(item.step, item.step_id)}
      description={
        `${item.running ? "Идёт" : "Остановлен"} с ${date(item.started_at)}` +
        (item.stopped_at ? ` по ${date(item.stopped_at)}` : "") +
        ` · контроль ${item.holdout_pct}%` +
        (item.b_pct ? ` · B ${item.b_pct}% остальных` : "") +
        (item.b_gift_days ? ` · подарок B: ${item.b_gift_days} дн.` : "")
      }
      action={
        item.running ? (
          <Button
            variant="outline"
            onClick={() =>
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
          >
            Остановить
          </Button>
        ) : undefined
      }
    >
      <div className="space-y-3">
        {item.b_text && (
          <details className="text-sm">
            <summary className="cursor-pointer text-muted-foreground">Текст варианта B</summary>
            <div className="mt-2 rounded-md border bg-muted/40 p-3 whitespace-pre-wrap">{item.b_text}</div>
          </details>
        )}
        <Results item={item} windowDays={data?.window_days || 7} />
      </div>
    </Panel>
  );
  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground max-w-2xl">
          Тесты автоматических сообщений бота. Каждый, кому подошло сообщение, попадает в одну группу навсегда.
          Оплаты считаются за {data?.window_days || 7} дней после попадания в тест — все, а не только после нажатия
          кнопки. Предупреждения о балансе и неоплаченном счёте не тестируются: они про уже заплаченные деньги.
        </p>
        <Button onClick={() => setOpen(true)} disabled={!data}>
          <Plus />
          Новый тест
        </Button>
      </div>
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !data ? (
        <Loading />
      ) : !items.length ? (
        <Empty
          title="Тестов ещё не было"
          description="Начните с контрольной группы 10% для первого сообщения после окончания подарка: станет видно, сколько денег оно приносит."
          action={
            <Button variant="outline" onClick={() => setOpen(true)}>
              <FlaskConical />
              Запустить первый тест
            </Button>
          }
        />
      ) : (
        <>
          {running.map(card)}
          {done.length > 0 && <h2 className="text-sm font-medium text-muted-foreground pt-2">Завершённые</h2>}
          {done.map(card)}
        </>
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
                void resource.reload();
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
