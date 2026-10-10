import { useState } from "react";
import { api, date, money, useResource, type Data } from "@/lib/api";
import {
  ActionButton,
  Choice,
  DataTable,
  Failure,
  Field,
  Loading,
  Panel,
  Pager,
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
  ["ambassador", "Могут стать амбассадорами"],
];
const templates: [string, string][] = [
  ["", "Своё сообщение"],
  ["whitelist", "Белые списки включены"],
  ["invite", "Пригласить друзей"],
  ["unused", "Помощь с первым подключением"],
  ["ambassador", "Приглашение в амбассадоры"],
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
            ? ((Number(data.sent || 0) + Number(data.failed || 0) + Number(data.skipped || 0)) /
                data.total) *
              100
            : 0
        }
      />
      <p className="text-xs text-muted-foreground">
        Доставлено: {data.sent || 0} · ошибок: {data.failed || 0} · пропущено: {data.skipped || 0}
        {data.message ? " · " + data.message : ""}
      </p>
    </div>
  );
}
function BroadcastResults() {
  const [page, setPage] = useState(1),
    [selected, setSelected] = useState<number | null>(null);
  const resource = useResource(`broadcast-results?page=${page}`, 15000);
  const rows = resource.data?.items || [];
  const current = rows.find((r: Data) => r.id === selected);
  const percent = (a: number, b: number) =>
    b ? `${((100 * a) / b).toFixed(1)}%` : "—";
  return (
    <Panel
      title="Результаты ручных рассылок"
      description="Каждый запуск учитывается отдельно. Переходы — нажатия отслеживаемых кнопок, не прочтения сообщений."
    >
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <>
          <DataTable
            rows={rows}
            empty="Новых рассылок пока нет. Отслеживание начнётся со следующего запуска."
            columns={[
              {
                key: "title",
                label: "Рассылка",
                cell: (r) => (
                  <Button
                    variant="link"
                    className="h-auto p-0 text-left whitespace-normal"
                    onClick={() => setSelected(selected === r.id ? null : r.id)}
                  >
                    {r.title} #{r.id}
                  </Button>
                ),
              },
              {
                key: "created_at",
                label: "Дата · МСК",
                cell: (r) => date(r.created_at),
              },
              { key: "sent", label: "Доставлено" },
              { key: "failed", label: "Ошибки" },
              { key: "skipped", label: "Пропущено по условиям" },
              { key: "clicked", label: "Перешли" },
              {
                key: "ctr",
                label: "CTR",
                cell: (r) => percent(r.clicked, r.sent),
              },
              { key: "connected", label: "Пользовались VPN" },
              { key: "payers", label: "Оплатили" },
              { key: "rub", label: "Сумма, ₽", cell: (r) => money(r.rub) },
              { key: "stars", label: "Stars" },
            ]}
          />
          <Pager
            page={page}
            total={resource.data.total || 0}
            limit={20}
            onChange={(p) => {
              setPage(p);
              setSelected(null);
            }}
          />
          {current && (
            <div className="rounded-lg border p-4 space-y-3 mt-3">
              <h3 className="font-semibold">
                {current.title} #{current.id}
              </h3>
              <p className="text-sm text-muted-foreground">
                {current.finished_at
                  ? "Отправка завершена"
                  : "Отправка не завершена"}{" "}
                · Получателей: {current.total} · С отслеживанием:{" "}
                {current.tracked} · Оплат: {current.payments} · Оплатили после
                перехода: {percent(current.payers, current.clicked)}
              </p>
              {current.error && (
                <p className="text-sm text-destructive">
                  Ошибка отправки: {current.error}
                </p>
              )}
              <p className="whitespace-pre-wrap break-words rounded-lg bg-muted p-4 text-sm">
                {current.body}
              </p>
              <Button variant="outline" onClick={() => setSelected(null)}>
                Скрыть подробности
              </Button>
            </div>
          )}
        </>
      )}
      <p className="mt-4 text-xs text-muted-foreground">
        Подключения и оплаты учитываются в течение 7 дней после последнего
        отслеживаемого перехода, в том числе из автоматических сообщений. Это
        связь по времени, а не доказанный прирост продаж. Рубли рассчитаны по
        кодам платежей; для старых тарифов — по текущей цене. Stars отдельно.
        Старые рассылки без меток не восстановить; удаление пользователей
        удаляет их события.
      </p>
    </Panel>
  );
}
function FunnelTest() {
  const resource = useResource("funnel-test");
  const [recipient, setRecipient] = useState(""),
    [selection, setSelection] = useState("scenario:start"),
    [result, setResult] = useState<Data | null>(null);
  const confirm = useConfirm();
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  const data = resource.data,
    target = recipient || String(data.admins?.[0] || "");
  const [mode, id] = selection.split(":");
  const ids =
    mode === "scenario"
      ? data.scenarios?.find((r: Data) => r.id === id)?.steps || []
      : [id];
  const steps = ids
    .map((key: string) => data.messages?.find((r: Data) => r.id === key))
    .filter(Boolean);
  return (
    <Panel
      title="Тест воронки"
      description="Отправка только администраторам из ADMIN_IDS. Сценарии отправляются сразу, без ожидания дней. Тест проверяет тексты и порядок, а не условия автоматического запуска. Кнопки не меняют аккаунт, статистика не затрагивается."
    >
      <div className="space-y-4">
        <Field label="Получатель теста">
          <Choice
            label="Получатель теста"
            value={target}
            onChange={setRecipient}
            options={(data.admins || []).map((id: number) => [
              String(id),
              `Админ · ${id}`,
            ])}
          />
        </Field>
        {!target && (
          <p className="text-sm text-destructive">
            Добавьте Telegram ID администратора в ADMIN_IDS и запустите бота от
            его имени.
          </p>
        )}
        <Field label="Что проверить">
          <Choice
            label="Что проверить"
            value={selection}
            onChange={setSelection}
            options={[
              ...(data.scenarios || []).map((r: Data) => [
                `scenario:${r.id}`,
                `Сценарий: ${r.title}`,
              ]),
              ...(data.messages || []).map((r: Data) => [
                `message:${r.id}`,
                r.title,
              ]),
            ]}
          />
        </Field>
        <div className="space-y-2">
          {steps.map((r: Data, i: number) => (
            <details key={r.id} className="rounded-lg border p-3">
              <summary className="cursor-pointer text-sm font-medium">
                {i + 1}. {r.title}
              </summary>
              <p className="text-xs text-muted-foreground my-2">
                {r.condition}
              </p>
              <p className="whitespace-pre-wrap text-sm">
                {r.body.replace(/<[^>]*>/g, "")}
              </p>
              <p className="text-xs text-muted-foreground mt-2">{r.exclusions}</p>
              {r.kind && <p className="text-xs text-muted-foreground mt-2">
                Отправлено за 7 дней: {r.delivery?.sent || 0}. Ошибок: {r.delivery?.failed || 0}.
                Последняя отправка: {r.delivery?.last_sent ? date(r.delivery.last_sent) : "нет данных"}.
                {r.kind === "nudge_idle" ? " Статистика общая для всех веток возврата." : ""}
              </p>}
            </details>
          ))}
        </div>
        <Button
          disabled={!target || !steps.length}
          onClick={() =>
            confirm({
              title: "Отправить тест админу?",
              description: `Получатель: ${target}. Сообщений: ${steps.length}. Администратор должен предварительно запустить бота.`,
              label: "Отправить тест",
              action: async () => {
                const response = await api("funnel-test", {
                  telegram_id: Number(target),
                  ...(mode === "scenario"
                    ? { scenario: id }
                    : { message_id: id }),
                });
                setResult(response);
                if (response.error) toast.error(response.error);
                else toast.success("Тестовые сообщения отправлены");
              },
            })
          }
        >
          Отправить тест админу
        </Button>
        {result && (
          <p role="status" className="text-sm">
            Отправлено: {result.sent} из {result.total}.
            {result.error
              ? ` Остановлено: ${result.error}. Повторная отправка запустит выбранный сценарий сначала.`
              : ""}
          </p>
        )}
      </div>
    </Panel>
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
            : template === "ambassador"
              ? "ambassador"
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
      <FunnelTest />
      <BroadcastResults />
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
                  {
                    <div className="border rounded-lg mt-2 p-3 text-center text-sm text-muted-foreground">
                      {template === "invite"
                        ? "Поделиться реферальной ссылкой · Войти в кабинет"
                        : "Войти в кабинет"}
                    </div>
                  }
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
