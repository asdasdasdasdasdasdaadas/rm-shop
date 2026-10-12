import { buttonError, textError } from "@/lib/funnel-validation";
import { useRef, useState, useId } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { ArrowUp, ArrowDown, Trash2, Plus } from "lucide-react";
export type FunnelButton =
  string | { action: string; text: string; url?: string };
type Action = { id: string; label: string; button?: string };
export function ButtonEditor({
  value,
  actions,
  onChange,
}: {
  value: FunnelButton[];
  actions: Action[];
  onChange: (v: FunnelButton[]) => void;
}) {
  const errorPrefix = useId();
  const update = (i: number, patch: Partial<Exclude<FunnelButton, string>>) =>
    onChange(
      value.map((b, n) =>
        n === i
          ? {
              ...(typeof b === "string"
                ? {
                    action: b,
                    text: actions.find((a) => a.id === b)?.button || b,
                  }
                : b),
              ...patch,
            }
          : b,
      ),
    );
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        До 6 кнопок. Порядок здесь совпадает с порядком в сообщении.
      </p>
      {value.map((b, i) => {
        const item =
          typeof b === "string"
            ? { action: b, text: actions.find((a) => a.id === b)?.button || b }
            : b;
        const issue = buttonError(
          b,
          actions.map((a) => a.id),
        );
        const errorId = errorPrefix + "-" + i;
        return (
          <div key={i} className="rounded-xl border p-4 space-y-3">
            <p className="text-xs font-medium text-muted-foreground">
              Кнопка {i + 1}
            </p>
            <label className="block space-y-1">
              <span className="text-xs">Что написано на кнопке *</span>
              <Input
                aria-label={`Название кнопки ${i + 1}`}
                required
                aria-invalid={issue?.field === "text"}
                aria-describedby={issue?.field === "text" ? errorId : undefined}
                maxLength={64}
                value={item.text}
                onChange={(e) => update(i, { text: e.target.value })}
              />
            </label>
            <label className="block space-y-1">
              <span className="text-xs">Что произойдёт при нажатии *</span>
              <select
                aria-label={`Действие кнопки ${i + 1}`}
                required
                aria-invalid={issue?.field === "action"}
                aria-describedby={
                  issue?.field === "action" ? errorId : undefined
                }
                className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                value={item.action}
                onChange={(e) =>
                  update(i, {
                    action: e.target.value,
                    text:
                      item.text ===
                      (actions.find((a) => a.id === item.action)?.button || "")
                        ? actions.find((a) => a.id === e.target.value)
                            ?.button || "Открыть ссылку"
                        : item.text,
                  })
                }
              >
                {actions.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.label}
                  </option>
                ))}
                <option value="url">Открыть ссылку</option>
              </select>
            </label>
            {item.action === "url" && (
              <Input
                aria-label={`Ссылка кнопки ${i + 1}`}
                required
                type="url"
                aria-invalid={issue?.field === "url"}
                aria-describedby={issue?.field === "url" ? errorId : undefined}
                placeholder="Адрес ссылки * · https://…"
                value={item.url || ""}
                onChange={(e) => update(i, { url: e.target.value })}
              />
            )}
            {issue && (
              <p id={errorId} className="text-xs text-destructive">
                {issue.message}
              </p>
            )}
            <div className="flex gap-1">
              {[-1, 1].map((d) => (
                <Button
                  key={d}
                  size="icon"
                  variant="ghost"
                  aria-label={`${d < 0 ? "Поднять" : "Опустить"} кнопку ${i + 1}`}
                  disabled={i + d < 0 || i + d >= value.length}
                  onClick={() => {
                    const next = [...value];
                    [next[i], next[i + d]] = [next[i + d], next[i]];
                    onChange(next);
                  }}
                >
                  {d < 0 ? <ArrowUp /> : <ArrowDown />}
                </Button>
              ))}
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Удалить кнопку ${i + 1}`}
                onClick={() => onChange(value.filter((_, n) => n !== i))}
              >
                <Trash2 />
              </Button>
            </div>
          </div>
        );
      })}
      <Button
        variant="outline"
        disabled={value.length >= 6}
        onClick={() =>
          onChange([...value, { action: "cabinet", text: "Личный кабинет" }])
        }
      >
        <Plus />
        Добавить кнопку
      </Button>
    </div>
  );
}
export function MessageEditor({
  value,
  onChange,
  label = "Текст сообщения",
}: {
  value: string;
  onChange: (s: string) => void;
  label?: string;
}) {
  const textErrorId = useId();
  const issue = textError(value);
  const ref = useRef<HTMLTextAreaElement>(null),
    [pack, setPack] = useState(""),
    [items, setItems] = useState<
      { id: string; emoji: string; thumbnail: boolean }[]
    >([]),
    [busy, setBusy] = useState(false),
    [title, setTitle] = useState("");
  const selection = useRef({ start: value.length, end: value.length });
  const insert = (item: { id: string; emoji: string }) => {
    const { start, end } = selection.current;
    const tag = `<tg-emoji emoji-id="${item.id}">${item.emoji}</tg-emoji>`;
    onChange(value.slice(0, start) + tag + value.slice(end));
    selection.current = { start: start + tag.length, end: start + tag.length };
    requestAnimationFrame(() => {
      ref.current?.focus();
      ref.current?.setSelectionRange(
        selection.current.start,
        selection.current.end,
      );
    });
  };
  return (
    <div className="space-y-2">
      <Textarea
        ref={ref}
        aria-label={label}
        required
        aria-invalid={!!issue}
        aria-describedby={issue ? textErrorId : undefined}
        className="min-h-40"
        value={value}
        maxLength={3500}
        onChange={(e) => onChange(e.target.value)}
        onSelect={(e) => {
          selection.current = {
            start: e.currentTarget.selectionStart,
            end: e.currentTarget.selectionEnd,
          };
        }}
      />
      {issue && (
        <p id={textErrorId} className="text-xs text-destructive">
          {issue}
        </p>
      )}
      <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm">
          Анимированные эмодзи Telegram
        </summary>
        <div className="space-y-3 pt-3">
          <p className="text-xs text-muted-foreground">
            Вставьте ссылку на набор t.me/addemoji/… Выберите эмодзи: он
            появится на месте курсора. Анимацию проверьте тестом в Telegram. Для
            отправки нужен Premium у владельца бота или дополнительное имя бота
            с Fragment.
          </p>
          <Input
            aria-label="Набор эмодзи"
            placeholder="https://t.me/addemoji/…"
            value={pack}
            onChange={(e) => setPack(e.target.value)}
          />
          <Button
            variant="outline"
            disabled={busy || !pack.trim()}
            onClick={async () => {
              setBusy(true);
              try {
                const r = await api(
                  "funnel-emojis?set=" + encodeURIComponent(pack.trim()),
                );
                setItems(r.items);
                setTitle(r.title);
              } catch (e) {
                toast.error((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Загрузка…" : "Загрузить набор"}
          </Button>
          <p className="text-sm">{title}</p>
          <div className="grid grid-cols-6 gap-2 max-h-52 overflow-auto">
            {items.map((item) => (
              <button
                type="button"
                key={item.id}
                title={`${item.emoji} · ${item.id}`}
                aria-label={`Вставить ${item.emoji} ${item.id}`}
                className="rounded border p-2 hover:bg-muted"
                onClick={() => insert(item)}
              >
                {item.thumbnail ? (
                  <img
                    loading="lazy"
                    className="size-8"
                    alt={item.emoji}
                    src={"/admin/api/funnel-emojis?id=" + item.id}
                  />
                ) : (
                  item.emoji
                )}
              </button>
            ))}
          </div>
        </div>
      </details>
    </div>
  );
}
