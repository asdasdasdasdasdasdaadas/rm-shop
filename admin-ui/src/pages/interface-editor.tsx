import { useEffect, useRef, useState } from "react";
import { api, type Data } from "@/lib/api";
import {
  Panel,
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  ArrowUp,
  ArrowDown,
  Plus,
  Trash2,
  RotateCcw,
  Save,
  Send,
} from "lucide-react";
import { toast } from "sonner";

const colors: [string, string, string][] = [
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
    [screen, setScreen] = useState("home"),
    [step, setStep] = useState("1"),
    [width, setWidth] = useState("390");
  const frame = useRef<HTMLIFrameElement>(null),
    confirm = useConfirm();
  const dirty = !!data && JSON.stringify(draft) !== JSON.stringify(data.draft);
  const unpublished =
    !!data && JSON.stringify(draft) !== JSON.stringify(data.published);
  useDirty(dirty);
  const load = () => {
    setError("");
    api("interface")
      .then((d) => {
        setData(d);
        setDraft(d.draft);
      })
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);
  const preview = () =>
    frame.current?.contentWindow?.postMessage(
      {
        type: "interface-preview",
        config: draft,
        catalog: data?.catalog,
        screen,
        step: Number(step),
      },
      location.origin,
    );
  useEffect(() => {
    preview();
  }, [draft, screen, step, data]);
  useEffect(() => {
    const listener = (e: MessageEvent) => {
      if (
        e.origin === location.origin &&
        e.source === frame.current?.contentWindow &&
        e.data?.type === "interface-preview-ready"
      )
        preview();
    };
    window.addEventListener("message", listener);
    return () => window.removeEventListener("message", listener);
  }, [draft, screen, step, data]);
  async function save(action: string) {
    if (busy || !data) return;
    setBusy(true);
    setError("");
    try {
      const next = await api("interface", {
        action,
        revision: data.revision,
        config: draft,
      });
      setData(next);
      setDraft(next.draft);
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
  const catalog = data.catalog;
  const patch = (key: string, value: unknown) =>
    setDraft({ ...draft, [key]: value });
  const changeCustom = (id: string, key: string, value: unknown) =>
    patch(
      "custom",
      draft.custom.map((b: Data) => (b.id === id ? { ...b, [key]: value } : b)),
    );
  const move = (key: string, index: number, delta: number) => {
    const items = [...draft[key]];
    [items[index], items[index + delta]] = [items[index + delta], items[index]];
    patch(key, items);
  };
  const reset = () =>
    confirm({
      title: "Вернуть стандартное оформление?",
      description:
        "Это изменит только черновик. Для применения пользователям нужна публикация.",
      label: "Сбросить черновик",
      action: async () => {
        setDraft({
          theme: {},
          texts: {},
          blocks: catalog.blocks.map((b: Data) => ({
            id: b.id,
            visible: true,
          })),
          custom: [],
        });
      },
    });
  return (
    <div className="space-y-5">
      <Panel
        title="Редактор веб-приложения"
        description="Меняйте оформление без кода. Сначала проверьте черновик, затем опубликуйте его для пользователей."
      >
        <div className="flex flex-wrap gap-2 items-center">
          <Badge variant={unpublished ? "secondary" : "outline"}>
            {dirty
              ? "Есть несохранённые изменения"
              : unpublished
                ? "Черновик отличается от сайта"
                : "Опубликованная версия"}
          </Badge>
          <Button
            disabled={busy || !dirty}
            onClick={() => save("save")}
            variant="outline"
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
                  "Пользователи увидят изменения после следующего открытия или перезагрузки кабинета.",
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
                  "Текущий черновик будет заменён предыдущим интерфейсом. Изменение применится пользователям.",
                label: "Откатить",
                action: () => save("rollback"),
              })
            }
          >
            <RotateCcw />
            Откат
          </Button>
        </div>
        {error && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {error}
          </p>
        )}
      </Panel>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_440px] items-start">
        <fieldset disabled={busy} className="min-w-0 space-y-5">
          <Field label="Экран">
            <Choice
              label="Экран"
              value={screen}
              onChange={setScreen}
              options={catalog.screens.map((s: Data) => [s.id, s.label])}
            />
          </Field>
          <Tabs defaultValue="content">
            <TabsList className="w-full">
              <TabsTrigger value="content">Тексты и кнопки</TabsTrigger>
              <TabsTrigger value="blocks">Блоки</TabsTrigger>
              <TabsTrigger value="theme">Оформление</TabsTrigger>
            </TabsList>
            <TabsContent value="content" className="space-y-4">
              <Panel
                title="Тексты экрана"
                description="Пустое поле возвращает стандартный текст. Баланс, цены и статусы по-прежнему подставляются автоматически."
              >
                <div className="space-y-5">
                  {catalog.fields
                    .filter((f: Data) => f.screen === screen)
                    .map((f: Data) => (
                      <Field
                        key={f.key}
                        label={f.label}
                        hint={
                          f.kind === "button"
                            ? "Меняется подпись. Действие кнопки сохраняется."
                            : undefined
                        }
                      >
                        {f.kind === "button" ? (
                          <Input
                            maxLength={60}
                            placeholder={f.default}
                            value={draft.texts[f.key] ?? ""}
                            onChange={(e) => {
                              const texts = { ...draft.texts };
                              if (e.target.value) texts[f.key] = e.target.value;
                              else delete texts[f.key];
                              patch("texts", texts);
                            }}
                          />
                        ) : (
                          <Textarea
                            rows={2}
                            maxLength={600}
                            placeholder={f.default}
                            value={draft.texts[f.key] ?? ""}
                            onChange={(e) => {
                              const texts = { ...draft.texts };
                              if (e.target.value) texts[f.key] = e.target.value;
                              else delete texts[f.key];
                              patch("texts", texts);
                            }}
                          />
                        )}
                      </Field>
                    ))}
                </div>
              </Panel>
            </TabsContent>
            <TabsContent value="blocks" className="space-y-4">
              {screen === "home" && (
                <Panel
                  title="Стандартные блоки"
                  description="Стрелки меняют порядок. Выключенный блок скрывается, но его функция остаётся доступной из других экранов. Условные блоки показываются только подходящим пользователям."
                >
                  <div className="space-y-2">
                    {draft.blocks.map((b: Data, i: number) => (
                      <div
                        key={b.id}
                        className="flex items-center gap-2 border rounded-xl p-3"
                      >
                        <span className="flex-1 text-sm">
                          {
                            catalog.blocks.find((x: Data) => x.id === b.id)
                              ?.label
                          }
                        </span>
                        <Switch
                          aria-label={
                            "Показывать " +
                            catalog.blocks.find((x: Data) => x.id === b.id)
                              ?.label
                          }
                          checked={b.visible}
                          disabled={b.id === "devicesBlock"}
                          onCheckedChange={(visible) =>
                            patch(
                              "blocks",
                              draft.blocks.map((x: Data) =>
                                x.id === b.id ? { ...x, visible } : x,
                              ),
                            )
                          }
                        />
                        <Button
                          size="icon"
                          variant="ghost"
                          aria-label={"Выше " + b.id}
                          disabled={i === 0}
                          onClick={() => move("blocks", i, -1)}
                        >
                          <ArrowUp />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          aria-label={"Ниже " + b.id}
                          disabled={i === draft.blocks.length - 1}
                          onClick={() => move("blocks", i, 1)}
                        >
                          <ArrowDown />
                        </Button>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
              <Panel
                title="Дополнительные блоки"
                description="Карточки, тексты и кнопки появятся после основного содержимого выбранного экрана."
                action={
                  <Button
                    variant="outline"
                    disabled={draft.custom.length >= 30}
                    onClick={() =>
                      patch("custom", [
                        ...draft.custom,
                        {
                          id: crypto
                            .getRandomValues(new Uint32Array(4))
                            .join("-"),
                          screen,
                          type: "card",
                          title: "Новый блок",
                          text: "",
                          label: "",
                          action: "topup",
                          url: "",
                          visible: true,
                        },
                      ])
                    }
                  >
                    <Plus />
                    Добавить блок
                  </Button>
                }
              >
                <div className="space-y-4">
                  {!draft.custom.some((b: Data) => b.screen === screen) && (
                    <p className="text-sm text-muted-foreground">
                      Здесь можно разместить подсказку, предложение или
                      дополнительную кнопку.
                    </p>
                  )}
                  {draft.custom.map((b: Data, i: number) =>
                    b.screen !== screen ? null : (
                      <div
                        key={b.id}
                        className="border rounded-xl p-4 space-y-4"
                      >
                        <div className="flex gap-1 items-center">
                          <span className="flex-1 font-medium text-sm">
                            {b.title || b.label || "Блок"}
                          </span>
                          <Switch
                            aria-label="Показывать блок"
                            checked={b.visible}
                            onCheckedChange={(v) =>
                              changeCustom(b.id, "visible", v)
                            }
                          />
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label="Поднять блок"
                            disabled={i === 0}
                            onClick={() => move("custom", i, -1)}
                          >
                            <ArrowUp />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label="Опустить блок"
                            disabled={i === draft.custom.length - 1}
                            onClick={() => move("custom", i, 1)}
                          >
                            <ArrowDown />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label="Удалить блок"
                            onClick={() =>
                              patch(
                                "custom",
                                draft.custom.filter((x: Data) => x.id !== b.id),
                              )
                            }
                          >
                            <Trash2 />
                          </Button>
                        </div>
                        <Field label="Тип блока">
                          <Choice
                            label="Тип блока"
                            value={b.type}
                            onChange={(v) => changeCustom(b.id, "type", v)}
                            options={[
                              ["card", "Карточка"],
                              ["text", "Текст"],
                              ["button", "Кнопка"],
                            ]}
                          />
                        </Field>
                        {b.type !== "button" && (
                          <>
                            <Field label="Заголовок блока">
                              <Input
                                value={b.title}
                                maxLength={120}
                                onChange={(e) =>
                                  changeCustom(b.id, "title", e.target.value)
                                }
                              />
                            </Field>
                            <Field label="Текст блока">
                              <Textarea
                                value={b.text}
                                maxLength={1200}
                                onChange={(e) =>
                                  changeCustom(b.id, "text", e.target.value)
                                }
                              />
                            </Field>
                          </>
                        )}
                        <Field
                          label="Подпись кнопки"
                          hint={
                            b.type === "button"
                              ? "Обязательное поле"
                              : "Оставьте пустой, если кнопка не нужна"
                          }
                        >
                          <Input
                            value={b.label}
                            maxLength={60}
                            onChange={(e) =>
                              changeCustom(b.id, "label", e.target.value)
                            }
                          />
                        </Field>
                        {(b.type === "button" || b.label) && (
                          <Field label="Действие кнопки">
                            <Choice
                              label="Действие кнопки"
                              value={b.action}
                              onChange={(v) => changeCustom(b.id, "action", v)}
                              options={catalog.actions.map((a: Data) => [
                                a.id,
                                a.label,
                              ])}
                            />
                          </Field>
                        )}
                        {b.action === "url" && b.label && (
                          <Field label="Ссылка HTTPS">
                            <Input
                              type="url"
                              value={b.url}
                              placeholder="https://…"
                              onChange={(e) =>
                                changeCustom(b.id, "url", e.target.value)
                              }
                            />
                          </Field>
                        )}
                      </div>
                    ),
                  )}
                </div>
              </Panel>
            </TabsContent>
            <TabsContent value="theme">
              <Panel
                title="Цвета и форма"
                description="Общие настройки для всех экранов веб-приложения. Проверяйте читаемость текста на выбранном фоне."
              >
                <div className="space-y-4">
                  {colors.map(([key, label, fallback]) => (
                    <div key={key} className="flex items-end gap-3">
                      <div className="flex-1">
                        <Field label={label}>
                          <Input
                            type="color"
                            className="h-11 p-1 cursor-pointer"
                            value={draft.theme[key] || fallback}
                            onChange={(e) =>
                              patch("theme", {
                                ...draft.theme,
                                [key]: e.target.value,
                              })
                            }
                          />
                        </Field>
                      </div>
                      <code className="text-xs pb-3">
                        {draft.theme[key] || "По умолчанию"}
                      </code>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={"Сбросить " + label}
                        onClick={() => {
                          const theme = { ...draft.theme };
                          delete theme[key];
                          patch("theme", theme);
                        }}
                      >
                        <RotateCcw />
                      </Button>
                    </div>
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
                  <Button variant="outline" onClick={reset}>
                    Вернуть стандартный интерфейс
                  </Button>
                </div>
              </Panel>
            </TabsContent>
          </Tabs>
        </fieldset>
        <div className="xl:sticky xl:top-6 space-y-3 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-semibold">Предпросмотр</h2>
            <Choice
              label="Ширина предпросмотра"
              value={width}
              onChange={setWidth}
              options={[
                ["320", "320 px"],
                ["390", "390 px"],
                ["430", "430 px"],
              ]}
            />
          </div>
          {screen === "wizard" && (
            <Choice
              label="Шаг подключения"
              value={step}
              onChange={setStep}
              options={[
                ["1", "Выбор устройства"],
                ["2", "Установка приложения"],
                ["4", "Подключение"],
              ]}
            />
          )}
          <div className="rounded-3xl border bg-muted p-2 overflow-auto">
            <iframe
              ref={frame}
              title="Предпросмотр веб-приложения"
              src="/admin/interface-preview"
              onLoad={preview}
              style={{ width: Number(width), maxWidth: "100%", height: 720 }}
              className="block mx-auto rounded-2xl border-0 bg-black"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Реальная разметка и стили, демонстрационные данные. Оплаты и
            отправка сообщений в предпросмотре отключены.
          </p>
        </div>
      </div>
    </div>
  );
}
