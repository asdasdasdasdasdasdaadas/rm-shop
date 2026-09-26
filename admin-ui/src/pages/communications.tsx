import { useState } from "react";
import { api, date, useResource, type Data } from "@/lib/api";
import {
  ActionButton,
  Choice,
  DataTable,
  Failure,
  Field,
  Loading,
  Panel,
  useConfirm,
  useDirty,
  useNavigate,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Send,
  ArrowLeft,
  ArrowRight,
  Check,
  MessageSquare,
} from "lucide-react";
import { toast } from "sonner";
const audiences: [string, string][] = [
  ["all", "Все доступные пользователи"],
  ["using", "Пользовались VPN"],
  ["unused", "Ещё не пользовались VPN"],
];
const templates: [string, string][] = [
  ["", "Своё сообщение"],
  ["whitelist", "Белые списки включены"],
  ["invite", "Пригласить друзей"],
  ["unused", "Помощь с первым подключением"],
];
function Delivery({ data }: { data: Data }) {
  return (
    <div className="rounded-lg border p-4 space-y-3" role="status">
      <div className="flex justify-between gap-3 text-sm">
        <span className="font-medium">
          {data.running ? "Рассылка выполняется" : "Последняя рассылка"}
        </span>
        <span>
          {data.sent || 0} / {data.total || 0}
        </span>
      </div>
      <Progress
        value={
          data.total
            ? ((Number(data.sent || 0) + Number(data.failed || 0)) /
                data.total) *
              100
            : 0
        }
      />
      <p className="text-xs text-muted-foreground">
        Доставлено: {data.sent || 0} · ошибок: {data.failed || 0}
        {data.message ? " · " + data.message : ""}
      </p>
    </div>
  );
}
export function BroadcastPage() {
  const resource = useResource("broadcast", 5000),
    [step, setStep] = useState(0),
    [audience, setAudience] = useState("all"),
    [template, setTemplate] = useState(""),
    [text, setText] = useState(""),
    [sent, setSent] = useState(false);
  const confirm = useConfirm(),
    navigate = useNavigate();
  useDirty(!sent && (!!text.trim() || !!template));
  const data = resource.data,
    effectiveAudience =
      template === "invite"
        ? "using"
        : template === "unused"
          ? "unused"
          : template === "whitelist"
            ? "all"
            : audience,
    count = data?.audiences?.[effectiveAudience] ?? 0,
    body = template ? data?.previews?.[template] || "" : text;
  const selectTemplate = (v: string) => {
    setTemplate(v);
    setSent(false);
  };
  const send = () =>
    confirm({
      title: "Отправить рассылку?",
      description: `Аудитория: ${audiences.find(([id]) => id === effectiveAudience)?.[1]}.\nПолучателей сейчас: ${count}. Фактическое число может измениться к началу отправки.\nСообщение отправится в Telegram. Отменить отправленное нельзя.`,
      label: "Отправить рассылку",
      action: async () => {
        await api("broadcast", template ? { template } : { text, audience });
        setSent(true);
        setText("");
        setTemplate("");
        setStep(0);
        await resource.reload();
        toast.success("Рассылка запущена");
      },
    });
  return (
    <div className="space-y-6">
      {resource.error && (
        <Failure message={resource.error} retry={resource.reload} />
      )}{" "}
      {!data && !resource.error ? (
        <Loading />
      ) : (
        data && (
          <>
            {(data.running || data.total > 0) && <Delivery data={data} />}
            <div className="flex gap-3 flex-wrap" aria-label="Шаги подготовки">
              {["Аудитория", "Сообщение", "Проверка"].map((label, i) => (
                <Button
                  key={label}
                  variant={i === step ? "secondary" : "ghost"}
                  disabled={i > step || data.running}
                  onClick={() => setStep(i)}
                >
                  <span className="flex items-center justify-center rounded-full border size-6 text-xs">
                    {i < step ? <Check className="size-3" /> : i + 1}
                  </span>
                  {label}
                </Button>
              ))}
            </div>
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
              <Panel
                title={
                  [
                    "Кому отправить",
                    "Что отправить",
                    "Проверьте перед отправкой",
                  ][step]
                }
                description={
                  [
                    "Выберите готовый сценарий или подготовьте своё сообщение.",
                    "Получатель увидит сообщение и кнопки выбранного сценария.",
                    "Убедитесь, что аудитория и содержание подходят друг другу.",
                  ][step]
                }
              >
                <div className="space-y-5">
                  {step === 0 && (
                    <>
                      <Field label="Сценарий">
                        <Choice
                          value={template}
                          label="Сценарий рассылки"
                          options={templates}
                          onChange={selectTemplate}
                        />
                      </Field>
                      <Field label="Получатели">
                        <Choice
                          label="Получатели рассылки"
                          value={effectiveAudience}
                          options={audiences}
                          onChange={setAudience}
                          disabled={!!template}
                        />
                      </Field>
                      <p className="rounded-lg bg-muted p-4 text-sm">
                        <strong>{count.toLocaleString("ru-RU")}</strong>{" "}
                        доступных получателей. Заблокировавшие бота не
                        включаются в аудиторию.
                      </p>
                      {template && (
                        <p className="text-sm text-muted-foreground">
                          У готового сценария аудитория определяется
                          автоматически. Для собственного выбора используйте
                          «Своё сообщение».
                        </p>
                      )}
                    </>
                  )}
                  {step === 1 && (
                    <>
                      {template ? (
                        <>
                          <div className="rounded-lg border p-4 whitespace-pre-wrap text-sm">
                            {body}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Это шаблон: имена и реферальные ссылки бот
                            подставляет индивидуально.
                          </p>
                          <Button
                            variant="outline"
                            onClick={() => navigate("settings?section=notices")}
                          >
                            Изменить шаблон в текстах бота
                          </Button>
                        </>
                      ) : (
                        <Field
                          label="Текст сообщения"
                          hint={`${text.length} / 3500 символов. Поддерживается Telegram HTML.`}
                        >
                          <Textarea
                            aria-label="Текст рассылки"
                            value={text}
                            maxLength={3500}
                            onChange={(e) => {
                              setText(e.target.value);
                              setSent(false);
                            }}
                            rows={12}
                            placeholder="Что нового и что пользователю нужно сделать?"
                          />
                        </Field>
                      )}
                    </>
                  )}
                  {step === 2 && (
                    <div className="space-y-4">
                      <dl className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">Получатели</dt>
                          <dd>{count}</dd>
                        </div>
                        <div className="flex justify-between gap-3">
                          <dt className="text-muted-foreground">Аудитория</dt>
                          <dd>
                            {
                              audiences.find(
                                ([id]) => id === effectiveAudience,
                              )?.[1]
                            }
                          </dd>
                        </div>
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">Сценарий</dt>
                          <dd>
                            {templates.find(([id]) => id === template)?.[1]}
                          </dd>
                        </div>
                      </dl>
                      <p className="text-sm text-muted-foreground">
                        После отправки проверьте доставку. Неуспешные сообщения
                        доступны в журнале.
                      </p>
                    </div>
                  )}
                  <div className="flex justify-between pt-3 border-t">
                    <Button
                      variant="ghost"
                      disabled={step === 0 || data.running}
                      onClick={() => setStep(step - 1)}
                    >
                      <ArrowLeft />
                      Назад
                    </Button>
                    {step < 2 ? (
                      <Button
                        disabled={
                          data.running || !count || (step === 1 && !body.trim())
                        }
                        onClick={() => setStep(step + 1)}
                      >
                        Продолжить
                        <ArrowRight />
                      </Button>
                    ) : (
                      <Button
                        disabled={data.running || !count || !body.trim()}
                        onClick={send}
                      >
                        <Send />
                        Отправить {count} пользователям
                      </Button>
                    )}
                  </div>
                </div>
              </Panel>
              <Panel
                title="Предпросмотр"
                description="Текст и структура сообщения. Telegram-разметка показана исходным текстом."
              >
                <div className="rounded-xl bg-muted/50 p-4">
                  <div className="rounded-xl bg-background border p-4 text-sm whitespace-pre-wrap break-words min-h-40">
                    {body || "Здесь появится текст сообщения."}
                  </div>
                  {template && (
                    <div className="border rounded-lg mt-2 p-3 text-center text-sm text-muted-foreground">
                      {template === "invite"
                        ? "Поделиться реферальной ссылкой"
                        : "Войти в кабинет"}
                    </div>
                  )}
                </div>
              </Panel>
            </div>
            <Button variant="link" onClick={() => navigate("messages")}>
              Открыть журнал доставки
              <ArrowRight />
            </Button>
          </>
        )
      )}
    </div>
  );
}
export function AnnouncementsPage() {
  const resource = useResource("announcements"),
    [form, setForm] = useState<Data>({
      kicker: "",
      title: "",
      lead: "",
      items: "",
      closing: "",
    }),
    [file, setFile] = useState<File | null>(null),
    [creating, setCreating] = useState(false);
  const confirm = useConfirm();
  useDirty(creating && Object.values(form).some(Boolean));
  const update = (key: string, value: string) =>
    setForm({ ...form, [key]: value });
  const submit = () => {
    const element = document.getElementById(
      "announcement-form",
    ) as HTMLFormElement;
    if (!element.reportValidity()) return;
    confirm({
      title: "Опубликовать анонс и отправить всем?",
      description: `Анонс появится в личном кабинете, а бот начнёт рассылку ${resource.data?.recipients || 0} пользователям.\n\n${form.title}`,
      label: "Опубликовать и отправить",
      action: async () => {
        const body = new FormData();
        Object.entries(form).forEach(([k, v]) =>
          body.append(
            k,
            k === "items"
              ? JSON.stringify(String(v).split("\n").filter(Boolean))
              : String(v),
          ),
        );
        if (file) body.append("file", file);
        await api("announcements", body);
        setCreating(false);
        setForm({ kicker: "", title: "", lead: "", items: "", closing: "" });
        setFile(null);
        await resource.reload();
        toast.success("Анонс опубликован, рассылка запущена");
      },
    });
  };
  return (
    <div className="space-y-5">
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <>
          {resource.data.broadcast?.running && (
            <Delivery data={resource.data.broadcast} />
          )}
          <div className="flex justify-end">
            <Button
              disabled={resource.data.broadcast?.running}
              onClick={() => {
                setForm({ ...resource.data?.defaults, items: "" });
                setCreating(true);
              }}
            >
              <PlusIcon />
              Создать анонс
            </Button>
          </div>
          {creating && (
            <div className="grid xl:grid-cols-2 gap-5">
              <Panel
                title="Новый анонс"
                description="Анонс публикуется в кабинете и отправляется пользователям в Telegram."
              >
                <form
                  id="announcement-form"
                  className="space-y-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    submit();
                  }}
                >
                  {[
                    ["kicker", "Надзаголовок", 80],
                    ["title", "Заголовок", 80],
                    ["lead", "Вступление", 800],
                    [
                      "items",
                      "Что изменилось — каждый пункт с новой строки",
                      1932,
                    ],
                    ["closing", "Завершение", 400],
                  ].map(([key, label, max]) => (
                    <Field key={String(key)} label={String(label)}>
                      {["lead", "items", "closing"].includes(String(key)) ? (
                        <Textarea
                          aria-label={String(label)}
                          maxLength={Number(max)}
                          value={form[String(key)] || ""}
                          onChange={(e) => update(String(key), e.target.value)}
                        />
                      ) : (
                        <Input
                          aria-label={String(label)}
                          required={key === "title"}
                          minLength={key === "title" ? 2 : undefined}
                          maxLength={Number(max)}
                          value={form[String(key)] || ""}
                          onChange={(e) => update(String(key), e.target.value)}
                        />
                      )}
                    </Field>
                  ))}
                  <Field label="Изображение (необязательно)">
                    <Input
                      type="file"
                      accept="image/*"
                      aria-label="Изображение анонса"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </Field>
                  <div className="flex gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() =>
                        confirm({
                          title: "Отменить создание?",
                          description: "Введённый текст будет удалён.",
                          label: "Отменить создание",
                          action: async () => {
                            setCreating(false);
                            setForm({});
                            setFile(null);
                          },
                        })
                      }
                    >
                      Отмена
                    </Button>
                    <Button
                      type="submit"
                      disabled={
                        !form.title?.trim() ||
                        (!form.lead?.trim() && !form.items?.trim()) ||
                        resource.data.broadcast?.running
                      }
                    >
                      Проверить публикацию
                    </Button>
                  </div>
                </form>
              </Panel>
              <Panel title="Предпросмотр анонса">
                <div className="space-y-4 rounded-xl bg-muted/50 p-5">
                  <p className="text-xs text-muted-foreground">{form.kicker}</p>
                  <h3 className="text-xl font-semibold">
                    {form.title || "Заголовок"}
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">{form.lead}</p>
                  <ul className="list-disc pl-5 text-sm space-y-2">
                    {String(form.items || "")
                      .split("\n")
                      .filter(Boolean)
                      .map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                  </ul>
                  <p className="text-sm whitespace-pre-wrap">{form.closing}</p>
                  {file && (
                    <Badge variant="secondary">Изображение: {file.name}</Badge>
                  )}
                </div>
              </Panel>
            </div>
          )}
          <DataTable
            rows={resource.data.items || []}
            columns={[
              { key: "title", label: "Анонс" },
              {
                key: "created_at",
                label: "Опубликован · МСК",
                cell: (r) => date(r.created_at),
              },
              {
                key: "items",
                label: "Изменения",
                cell: (r) => (
                  <span className="whitespace-normal text-sm">
                    {Array.isArray(r.items) ? r.items.join(" · ") : "—"}
                  </span>
                ),
              },
            ]}
          />
        </>
      )}
    </div>
  );
}
function PlusIcon() {
  return <MessageSquare className="size-4" />;
}
