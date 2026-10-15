import { useEffect, useRef, useState } from "react";
import { api, type Data } from "@/lib/api";
import {
  Field,
  Choice,
  Loading,
  Failure,
  useDirty,
  useConfirm,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  ArrowUp,
  ArrowDown,
  Plus,
  Trash2,
  Undo2,
  Redo2,
  Save,
  Send,
  Palette,
  MousePointer2,
  EyeOff,
} from "lucide-react";
import { toast } from "sonner";
type Selection = {
  kind: "field" | "block" | "custom" | "theme";
  id: string;
  property?: string;
} | null;
const colors = [
  ["background", "Фон", "#101114"],
  ["surface", "Карточки", "#20242b"],
  ["text", "Основной текст", "#f3f4f6"],
  ["muted", "Второстепенный текст", "#bdc3ce"],
  ["button", "Основные кнопки", "#e9ecf2"],
  ["buttonText", "Текст кнопок", "#16191f"],
];
export function InterfaceEditorPage() {
  const [data, setData] = useState<Data | null>(null),
    [draft, setDraft] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [inlineDirty, setInlineDirty] = useState(false),
    [screen, setScreen] = useState("home"),
    [step, setStep] = useState("1"),
    [width, setWidth] = useState("390"),
    [selection, setSelection] = useState<Selection>(null),
    [historyTick, setHistoryTick] = useState(0);
  const draftRef = useRef<Data | null>(null),
    flushRef = useRef<(() => void) | null>(null);
  const frame = useRef<HTMLIFrameElement>(null),
    history = useRef<{ past: Data[]; future: Data[] }>({
      past: [],
      future: [],
    }),
    confirm = useConfirm();
  const dirty =
      inlineDirty ||
      (!!data && JSON.stringify(draft) !== JSON.stringify(data.draft)),
    unpublished =
      inlineDirty ||
      (!!data && JSON.stringify(draft) !== JSON.stringify(data.published));
  useDirty(dirty);
  const load = () =>
    api("interface")
      .then((d) => {
        setData(d);
        setDraft(d.draft);
        draftRef.current = d.draft;
        history.current = { past: [], future: [] };
      })
      .catch((e) => setError(e.message));
  useEffect(() => {
    void load();
  }, []);
  const update = (next: Data) => {
    if (!draft || JSON.stringify(next) === JSON.stringify(draft)) return;
    history.current.past.push(draft);
    history.current.past = history.current.past.slice(-100);
    history.current.future = [];
    setDraft(next);
    draftRef.current = next;
    setHistoryTick((v) => v + 1);
  };
  const undo = (redo = false) => {
    if (!draft) return;
    const from = redo ? history.current.future : history.current.past,
      to = redo ? history.current.past : history.current.future;
    const next = from.pop();
    if (next) {
      to.push(draft);
      setDraft(next);
      draftRef.current = next;
      setHistoryTick((v) => v + 1);
    }
  };
  const patch = (key: string, value: unknown) => {
    if (draft) update({ ...draft, [key]: value });
  };
  const edit = (s: Selection, value: string) => {
    if (!draft || !s) return;
    if (s.kind === "field") {
      const texts = { ...draft.texts };
      if (value.trim()) texts[s.id] = value;
      else delete texts[s.id];
      patch("texts", texts);
    } else if (
      s.kind === "custom" &&
      ["title", "text", "label"].includes(s.property || "")
    )
      changeCustom(s.id, s.property!, value);
  };
  const changeCustom = (id: string, key: string, value: unknown) => {
    if (draft)
      patch(
        "custom",
        draft.custom.map((b: Data) =>
          b.id === id ? { ...b, [key]: value } : b,
        ),
      );
  };
  const moveTo = (source: Selection, target: Selection) => {
    if (
      !draft ||
      !source ||
      !target ||
      source.kind !== target.kind ||
      source.id === target.id
    )
      return;
    const key =
      source.kind === "block"
        ? "blocks"
        : source.kind === "custom"
          ? "custom"
          : null;
    if (!key) return;
    const items = [...draft[key]],
      from = items.findIndex((b) => b.id === source.id),
      to = items.findIndex((b) => b.id === target.id);
    if (from < 0 || to < 0) return;
    const [item] = items.splice(from, 1);
    items.splice(to, 0, item);
    patch(key, items);
  };
  const preview = () =>
    frame.current?.contentWindow?.postMessage(
      {
        type: "interface-preview",
        config: draft,
        catalog: data?.catalog,
        screen,
        step: Number(step),
        selection,
      },
      location.origin,
    );
  useEffect(() => {
    preview();
  }, [draft, data, screen, step, selection]);
  useEffect(() => {
    const listener = (e: MessageEvent) => {
      if (
        e.origin !== location.origin ||
        e.source !== frame.current?.contentWindow
      )
        return;
      const msg = e.data;
      if (msg?.type === "interface-preview-ready") preview();
      if (msg?.type === "interface-flushed") {
        flushRef.current?.();
        flushRef.current = null;
        return;
      }
      if (msg?.type === "interface-edit") {
        edit(msg.selection, msg.value);
        setInlineDirty(false);
        return;
      }
      if (busy) return;
      if (msg?.type === "interface-editing") setInlineDirty(true);
      if (msg?.type === "interface-select") setSelection(msg.selection);

      if (msg?.type === "interface-move") moveTo(msg.source, msg.target);
    };
    window.addEventListener("message", listener);
    return () => window.removeEventListener("message", listener);
  }, [draft, data, screen, step, selection, busy]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        busy ||
        !(e.ctrlKey || e.metaKey) ||
        e.key.toLowerCase() !== "z" ||
        (e.target as HTMLElement)?.closest(
          "input,textarea,[contenteditable=true]",
        )
      )
        return;
      e.preventDefault();
      undo(e.shiftKey);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [draft, busy, historyTick]);
  async function save(action: string) {
    if (busy || !data) return;
    setBusy(true);
    setError("");
    try {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          flushRef.current = null;
          reject(
            new Error(
              "Холст не ответил. Дождитесь загрузки и повторите сохранение.",
            ),
          );
        }, 3000);
        flushRef.current = () => {
          clearTimeout(timeout);
          resolve();
        };
        frame.current?.contentWindow?.postMessage(
          { type: "interface-flush" },
          location.origin,
        );
      });
      const next = await api("interface", {
        action,
        revision: data.revision,
        config: draftRef.current,
      });
      setData(next);
      setDraft(next.draft);
      draftRef.current = next.draft;
      if (action === "rollback") {
        history.current = { past: [], future: [] };
        setSelection(null);
      }
      toast.success(
        action === "save"
          ? "Черновик сохранён"
          : action === "publish"
            ? "Интерфейс опубликован"
            : "Предыдущий интерфейс восстановлен",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!data || !draft)
    return error ? <Failure message={error} retry={load} /> : <Loading />;
  const catalog = data.catalog,
    fields = catalog.fields.filter(
      (f: Data) => f.screen === screen && (!f.step || f.step === Number(step)),
    ),
    custom = draft.custom.filter((b: Data) => b.screen === screen);
  const field =
    selection?.kind === "field"
      ? catalog.fields.find((f: Data) => f.key === selection.id)
      : null;
  const block =
    selection?.kind === "block"
      ? draft.blocks.find((b: Data) => b.id === selection.id)
      : null;
  const item =
    selection?.kind === "custom"
      ? draft.custom.find((b: Data) => b.id === selection.id)
      : null;
  const add = (type: string) => {
    const id = crypto.getRandomValues(new Uint32Array(4)).join("-");
    patch("custom", [
      ...draft.custom,
      {
        id,
        screen,
        type,
        title: type === "button" ? "" : "Новый заголовок",
        text: type === "button" ? "" : "Нажмите дважды, чтобы изменить текст.",
        label: type === "text" ? "" : "Подробнее",
        action: "support",
        url: "",
        visible: true,
      },
    ]);
    setSelection({ kind: "custom", id });
  };
  const selectedName =
    field?.label ||
    item?.title ||
    item?.label ||
    (block && catalog.blocks.find((b: Data) => b.id === block.id)?.label) ||
    "Свойства";
  const movement = (s: NonNullable<Selection>) => {
    const list = s.kind === "block" ? draft.blocks : custom,
      index = list.findIndex((b: Data) => b.id === s.id);
    return (
      <div className="flex gap-2">
        <Button
          variant="outline"
          aria-label="Переместить выше"
          disabled={index <= 0}
          onClick={() => moveTo(s, { ...s, id: list[index - 1].id })}
        >
          <ArrowUp />
          Выше
        </Button>
        <Button
          variant="outline"
          aria-label="Переместить ниже"
          disabled={index < 0 || index === list.length - 1}
          onClick={() => moveTo(s, { ...s, id: list[index + 1].id })}
        >
          <ArrowDown />
          Ниже
        </Button>
      </div>
    );
  };
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-3">
        <span className="mr-auto text-sm font-medium">
          {dirty
            ? "Изменения не сохранены"
            : unpublished
              ? "Черновик"
              : "Опубликованная версия"}
        </span>
        <Button
          size="icon"
          variant="ghost"
          aria-label="Отменить изменение"
          disabled={busy || !history.current.past.length}
          onClick={() => undo()}
        >
          <Undo2 />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          aria-label="Повторить изменение"
          disabled={busy || !history.current.future.length}
          onClick={() => undo(true)}
        >
          <Redo2 />
        </Button>
        <Button
          variant="outline"
          disabled={busy || !dirty}
          onClick={() => save("save")}
        >
          <Save />
          Сохранить черновик
        </Button>
        <Button
          disabled={busy || !unpublished}
          onClick={() =>
            confirm({
              title: "Опубликовать интерфейс?",
              description:
                "Изменения появятся у пользователей при следующем открытии кабинета.",
              label: "Опубликовать",
              action: () => save("publish"),
            })
          }
        >
          <Send />
          Опубликовать
        </Button>
        <Button
          variant="ghost"
          disabled={busy || !data.can_rollback}
          onClick={() =>
            confirm({
              title: "Вернуть предыдущую публикацию?",
              description:
                "Текущий черновик будет заменён предыдущей опубликованной версией.",
              label: "Откатить",
              action: () => save("rollback"),
            })
          }
        >
          Откат
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}
      <fieldset disabled={busy} className="canvas-workspace">
        <aside className="canvas-panel canvas-layers">
          <Field label="Экран">
            <Choice
              label="Экран"
              value={screen}
              onChange={(v) => {
                setScreen(v);
                setSelection(null);
              }}
              options={catalog.screens.map((s: Data) => [s.id, s.label])}
            />
          </Field>
          {screen === "wizard" && (
            <Choice
              label="Шаг подключения"
              value={step}
              onChange={(v) => {
                setStep(v);
                setSelection(null);
              }}
              options={[
                ["1", "Выбор устройства"],
                ["2", "Установка приложения"],
                ["4", "Подключение"],
              ]}
            />
          )}
          <h3 className="text-xs font-semibold uppercase text-muted-foreground">
            Слои экрана
          </h3>
          {screen === "home" &&
            draft.blocks.map((b: Data) => (
              <button
                type="button"
                key={b.id}
                className="canvas-layer"
                data-selected={
                  selection?.kind === "block" && selection.id === b.id
                }
                onClick={() => setSelection({ kind: "block", id: b.id })}
              >
                <span>
                  {catalog.blocks.find((x: Data) => x.id === b.id)?.label}
                </span>
                {!b.visible && <EyeOff size={14} />}
              </button>
            ))}
          {custom.map((b: Data) => (
            <button
              type="button"
              key={b.id}
              className="canvas-layer"
              data-selected={
                selection?.kind === "custom" && selection.id === b.id
              }
              onClick={() => setSelection({ kind: "custom", id: b.id })}
            >
              <span>{b.title || b.label || "Блок"}</span>
              {!b.visible && <EyeOff size={14} />}
            </button>
          ))}
          <details>
            <summary className="text-sm cursor-pointer py-2">
              Тексты и кнопки
            </summary>
            {fields.map((f: Data) => (
              <button
                type="button"
                key={f.key}
                className="canvas-layer"
                data-selected={
                  selection?.kind === "field" && selection.id === f.key
                }
                onClick={() => setSelection({ kind: "field", id: f.key })}
              >
                {f.label}
              </button>
            ))}
          </details>
          <div className="border-t pt-3 space-y-2">
            <h3 className="text-xs font-semibold uppercase text-muted-foreground">
              Добавить на экран
            </h3>
            {[
              ["card", "Карточку"],
              ["text", "Текст"],
              ["button", "Кнопку"],
            ].map(([type, label]) => (
              <Button
                key={type}
                variant="outline"
                className="w-full justify-start"
                disabled={draft.custom.length >= 30}
                onClick={() => add(type)}
              >
                <Plus />
                {label}
              </Button>
            ))}
          </div>
          <Button
            variant="ghost"
            className="justify-start"
            onClick={() => setSelection({ kind: "theme", id: "theme" })}
          >
            <Palette />
            Цвета и форма
          </Button>
        </aside>
        <main className="canvas-stage">
          <div className="canvas-stage-toolbar">
            <span className="text-xs text-muted-foreground">
              Холст · двойной клик меняет текст
            </span>
            <Choice
              label="Ширина холста"
              value={width}
              onChange={setWidth}
              options={[
                ["320", "320 px"],
                ["390", "390 px"],
                ["430", "430 px"],
              ]}
            />
          </div>
          <div className="canvas-artboard">
            <iframe
              ref={frame}
              title="Холст веб-приложения"
              src="/admin/interface-preview"
              onLoad={preview}
              style={{
                width: Number(width),
                maxWidth: "100%",
                height: 760,
                pointerEvents: busy ? "none" : undefined,
              }}
            />
          </div>
          <p className="text-xs text-muted-foreground text-center">
            Перетаскивайте блоки за синюю ручку ⠿. Кнопки на холсте выбираются,
            а не выполняют действие.
          </p>
        </main>
        <aside className="canvas-panel canvas-inspector">
          {!selection ? (
            <div className="space-y-3 text-sm text-muted-foreground py-8">
              <MousePointer2 />
              <h2 className="font-semibold text-foreground">
                Выберите элемент на холсте
              </h2>
              <p>
                Один клик — свойства. Двойной — ввод текста прямо на экране.
              </p>
              <p>
                Баланс и другие данные пользователя рассчитываются
                автоматически.
              </p>
            </div>
          ) : (
            <>
              <h2 className="font-semibold break-words">
                {selection.kind === "theme" ? "Цвета и форма" : selectedName}
              </h2>
              {field && (
                <>
                  <Field
                    label={
                      field.kind === "button"
                        ? "Подпись кнопки"
                        : "Текст элемента"
                    }
                    hint="Пустое поле возвращает стандартный текст."
                  >
                    <Textarea
                      rows={field.kind === "button" ? 2 : 4}
                      maxLength={field.kind === "button" ? 60 : 600}
                      placeholder={field.default}
                      value={draft.texts[field.key] ?? ""}
                      onChange={(e) => edit(selection, e.target.value)}
                    />
                  </Field>
                  <p className="text-xs text-muted-foreground">
                    {field.kind === "button"
                      ? "Действие стандартной кнопки сохраняется."
                      : "Можно редактировать и двойным кликом на холсте."}
                  </p>
                  <Button variant="outline" onClick={() => edit(selection, "")}>
                    Стандартный текст
                  </Button>
                </>
              )}
              {block && (
                <>
                  <Field label="Показывать блок">
                    <Switch
                      checked={block.visible}
                      disabled={block.id === "devicesBlock"}
                      onCheckedChange={(visible) =>
                        patch(
                          "blocks",
                          draft.blocks.map((b: Data) =>
                            b.id === block.id ? { ...b, visible } : b,
                          ),
                        )
                      }
                    />
                  </Field>
                  {movement(selection!)}
                  <p className="text-xs text-muted-foreground">
                    Для редактирования содержимого нажмите на текст или кнопку
                    внутри блока. Условные блоки сохраняют условия показа.
                  </p>
                </>
              )}
              {item && (
                <>
                  <Field label="Показывать блок">
                    <Switch
                      checked={item.visible}
                      onCheckedChange={(v) =>
                        changeCustom(item.id, "visible", v)
                      }
                    />
                  </Field>
                  {item.type !== "button" && (
                    <>
                      <Field label="Заголовок блока">
                        <Input
                          maxLength={120}
                          value={item.title}
                          onChange={(e) =>
                            changeCustom(item.id, "title", e.target.value)
                          }
                        />
                      </Field>
                      <Field label="Текст блока">
                        <Textarea
                          rows={4}
                          maxLength={1200}
                          value={item.text}
                          onChange={(e) =>
                            changeCustom(item.id, "text", e.target.value)
                          }
                        />
                      </Field>
                    </>
                  )}
                  <Field
                    label="Подпись кнопки"
                    hint={
                      item.type === "button"
                        ? "Обязательное поле"
                        : "Пустая подпись убирает кнопку"
                    }
                  >
                    <Input
                      maxLength={60}
                      value={item.label}
                      onChange={(e) =>
                        changeCustom(item.id, "label", e.target.value)
                      }
                    />
                  </Field>
                  {(item.type === "button" || item.label) && (
                    <Field label="Действие кнопки">
                      <Choice
                        label="Действие кнопки"
                        value={item.action}
                        onChange={(v) => changeCustom(item.id, "action", v)}
                        options={catalog.actions.map((a: Data) => [
                          a.id,
                          a.label,
                        ])}
                      />
                    </Field>
                  )}
                  {item.action === "url" && item.label && (
                    <Field label="Ссылка HTTPS">
                      <Input
                        type="url"
                        value={item.url}
                        onChange={(e) =>
                          changeCustom(item.id, "url", e.target.value)
                        }
                      />
                    </Field>
                  )}
                  {movement(selection!)}
                  <Button
                    variant="outline"
                    onClick={() => {
                      patch(
                        "custom",
                        draft.custom.filter((b: Data) => b.id !== item.id),
                      );
                      setSelection(null);
                    }}
                  >
                    <Trash2 />
                    Удалить блок
                  </Button>
                </>
              )}
              {selection.kind === "theme" && (
                <>
                  {colors.map(([key, label, fallback]) => (
                    <Field key={key} label={label}>
                      <Input
                        type="color"
                        className="h-10 p-1"
                        value={draft.theme[key] || fallback}
                        onChange={(e) =>
                          patch("theme", {
                            ...draft.theme,
                            [key]: e.target.value,
                          })
                        }
                      />
                    </Field>
                  ))}
                  <Field label="Скругление карточек, px">
                    <Input
                      type="number"
                      min={8}
                      max={40}
                      value={draft.theme.radius ?? 28}
                      onChange={(e) =>
                        patch("theme", {
                          ...draft.theme,
                          radius: Number(e.target.value),
                        })
                      }
                    />
                  </Field>
                  <Button variant="outline" onClick={() => patch("theme", {})}>
                    Стандартные цвета и форма
                  </Button>
                </>
              )}
            </>
          )}
        </aside>
      </fieldset>
    </div>
  );
}
