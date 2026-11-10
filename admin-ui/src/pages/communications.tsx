import { useEffect, useRef, useState } from "react";
import { api, useResource, type Data } from "@/lib/api";
import {
  Choice,
  Failure,
  Field,
  Loading,
  Panel,
  useConfirm,
  useDirty,
  useNavigate,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Send,
  ArrowLeft,
  ArrowRight,
  Check,
  Clock,
  X,
  ImagePlus,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
const audiences: [string, string][] = [
  ["all", "Все доступные пользователи"],
  ["using", "Пользовались VPN"],
  ["unused", "Ещё не пользовались VPN"],
];
const templates: [string, string][] = [
  ["", "Своё сообщение"],
  ["gift3", "+3 дня всем с текстом"],
  ["referral_news", "Новая реферальная программа"],
  ["whitelist", "Белые списки включены"],
  ["invite", "Пригласить друзей"],
  ["unused", "Помощь с первым подключением"],
];
// Announcements to everyone: editable text plus a fixed button.
const announce: Record<string, string> = {
  gift3: "Забрать 3 дня бесплатно",
  referral_news: "Пригласить друзей",
};
// Telegram caption limit is 1024; the bot adds a short «Откройте личный кабинет 👇» line.
const CAPTION_MAX = 964;
const kindLabel: Record<string, string> = { photo: "Фото", animation: "GIF", video: "Видео" };
type Media = { id: string; kind: string; name: string; url: string; video: boolean };
function MediaPicker({
  media,
  onChange,
}: {
  media: Media | null;
  onChange: (m: Media | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null),
    file = useRef<File | null>(null),
    [busy, setBusy] = useState(false);
  const upload = async (f: File, asGif: boolean) => {
    const body = new FormData();
    body.append("file", f);
    if (asGif) body.append("as_gif", "1");
    setBusy(true);
    try {
      const r = await api("broadcast/media", body);
      file.current = f;
      onChange({
        ...r.media,
        name: f.name,
        url: URL.createObjectURL(f),
        video: f.type.startsWith("video/"),
      });
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };
  return (
    <div className="space-y-3">
      <input
        ref={input}
        type="file"
        hidden
        accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime,video/webm"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload(f, false);
        }}
      />
      {media ? (
        <div className="flex items-center justify-between gap-3 rounded-lg border p-3 text-sm">
          <span className="truncate">
            {kindLabel[media.kind]} · {media.name}
          </span>
          <Button variant="ghost" size="sm" onClick={() => onChange(null)}>
            <X />
            Убрать
          </Button>
        </div>
      ) : (
        <Button variant="outline" disabled={busy} onClick={() => input.current?.click()}>
          {busy ? <Loader2 className="animate-spin" /> : <ImagePlus />}
          {busy ? "Загружаем…" : "Прикрепить фото, GIF или видео"}
        </Button>
      )}
      {media?.video && (
        <Choice
          label="Как отправить видео"
          value={media.kind}
          options={[
            ["video", "Видео со звуком и плеером"],
            ["animation", "Как GIF: без звука, крутится по кругу"],
          ]}
          onChange={(v) => file.current && v !== media.kind && upload(file.current, v === "animation")}
          disabled={busy}
        />
      )}
      <p className="text-xs text-muted-foreground">
        JPG, PNG, WEBP — фото до 10 МБ; GIF, MP4, MOV, WEBM — до 50 МБ. Текст станет подписью.
      </p>
    </div>
  );
}
const pad = (n: number) => String(n).padStart(2, "0");
// Value for <input type="datetime-local"> in the admin's own time zone.
const localInput = (d: Date) =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
const whenLabel = (iso: string) =>
  new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
function Scheduled({ items, reload }: { items: Data[]; reload: () => Promise<unknown> }) {
  const confirm = useConfirm();
  if (!items?.length) return null;
  return (
    <div className="rounded-lg border p-4 space-y-3">
      <p className="font-medium text-sm">Запланированные рассылки</p>
      {items.map((item) => (
        <div key={item.id} className="flex items-center justify-between gap-3 text-sm">
          <span className="flex items-center gap-2 min-w-0">
            <Clock className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate">
              {whenLabel(item.at)} · {item.title}
            </span>
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              confirm({
                title: "Отменить запланированную рассылку?",
                description: `${item.title}, ${whenLabel(item.at)}.`,
                label: "Отменить рассылку",
                action: async () => {
                  await api("broadcast", { cancel_scheduled: item.id });
                  await reload();
                  toast.success("Рассылка отменена");
                },
              })
            }
          >
            <X />
            Отменить
          </Button>
        </div>
      ))}
    </div>
  );
}
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
export function BroadcastPage() {
  const resource = useResource("broadcast", 5000),
    [step, setStep] = useState(0),
    [audience, setAudience] = useState("all"),
    [template, setTemplate] = useState(""),
    [text, setText] = useState(""),
    [sent, setSent] = useState(false),
    [later, setLater] = useState(false),
    [media, setMedia] = useState<Media | null>(null),
    [when, setWhen] = useState(() => localInput(new Date(Date.now() + 3600_000)));
  const confirm = useConfirm(),
    navigate = useNavigate();
  useDirty(!sent && (!!text.trim() || !!template || !!media));
  // The preview keeps a local copy of the file; free it when the attachment changes or the page closes.
  useEffect(() => () => { if (media) URL.revokeObjectURL(media.url); }, [media]);
  const data = resource.data,
    effectiveAudience =
      template === "invite"
        ? "using"
        : template === "unused"
          ? "unused"
          : template === "whitelist" || template in announce
            ? "all"
            : audience,
    count = data?.audiences?.[effectiveAudience] ?? 0,
    editable = !template || template in announce,
    body = editable ? text : data?.previews?.[template] || "",
    attached = !template ? media : null,
    tooLong = !!attached && text.length > CAPTION_MAX,
    ready = (!!body.trim() || !!attached) && !tooLong;
  const selectTemplate = (v: string) => {
    if (v in announce) setText(data?.previews?.[v] || "");
    else if (template in announce) setText("");
    setTemplate(v);
    setSent(false);
  };
  const whenDate = new Date(when),
    whenValid = !later || (!Number.isNaN(whenDate.getTime()) && whenDate.getTime() > Date.now() + 60_000);
  const send = () =>
    confirm({
      title: later ? "Запланировать рассылку?" : "Отправить рассылку?",
      description: `Аудитория: ${audiences.find(([id]) => id === effectiveAudience)?.[1]}.\nПолучателей сейчас: ${count}. Фактическое число может измениться к началу отправки.\n${later ? `Отправка начнётся ${whenLabel(whenDate.toISOString())}. До этого рассылку можно отменить.` : "Сообщение отправится в Telegram. Отменить отправленное нельзя."}`,
      label: later ? "Запланировать" : "Отправить рассылку",
      action: async () => {
        const payload =
          template in announce
            ? { template, text }
            : template
              ? { template }
              : { text, audience, ...(attached ? { media: { id: attached.id, kind: attached.kind } } : {}) };
        await api(
          "broadcast",
          later ? { ...payload, scheduled_at: whenDate.toISOString() } : payload,
        );
        setSent(true);
        setText("");
        setTemplate("");
        setMedia(null);
        setStep(0);
        setLater(false);
        await resource.reload();
        toast.success(later ? "Рассылка запланирована" : "Рассылка запущена");
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
            <Scheduled items={data.scheduled || []} reload={resource.reload} />
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
                      {template && !editable ? (
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
                          hint={`${text.length} / ${attached ? CAPTION_MAX : 3500} символов${attached ? " (подпись к медиа)" : ""}. Поддерживается Telegram HTML.${template in announce ? ` Под текстом будет кнопка «${announce[template]}».` : ""}`}
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
                      {step === 1 && !template && (
                        <Field label="Фото, GIF или видео">
                          <MediaPicker media={media} onChange={(m) => { setMedia(m); setSent(false); }} />
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
                        {attached && (
                          <div className="flex justify-between gap-3">
                            <dt className="text-muted-foreground">Вложение</dt>
                            <dd>{kindLabel[attached.kind]}</dd>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">Сценарий</dt>
                          <dd>
                            {templates.find(([id]) => id === template)?.[1]}
                          </dd>
                        </div>
                      </dl>
                      <Field label="Когда отправить">
                        <Choice
                          label="Когда отправить"
                          value={later ? "later" : "now"}
                          options={[
                            ["now", "Сразу"],
                            ["later", "Запланировать на дату и время"],
                          ]}
                          onChange={(v) => setLater(v === "later")}
                        />
                      </Field>
                      {later && (
                        <Field
                          label="Дата и время"
                          hint={
                            whenValid
                              ? "Время вашего устройства. Рассылка начнётся в течение минуты после него."
                              : "Выберите время хотя бы на минуту позже текущего."
                          }
                        >
                          <Input
                            type="datetime-local"
                            aria-label="Дата и время рассылки"
                            value={when}
                            min={localInput(new Date())}
                            onChange={(e) => setWhen(e.target.value)}
                          />
                        </Field>
                      )}
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
                          data.running || !count || (step === 1 && !ready)
                        }
                        onClick={() => setStep(step + 1)}
                      >
                        Продолжить
                        <ArrowRight />
                      </Button>
                    ) : (
                      <Button
                        disabled={(data.running && !later) || !count || !ready || !whenValid}
                        onClick={send}
                      >
                        {later ? <Clock /> : <Send />}
                        {later
                          ? `Запланировать на ${whenValid ? whenLabel(whenDate.toISOString()) : "…"}`
                          : `Отправить ${count} пользователям`}
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
                  <div className="rounded-xl bg-background border overflow-hidden">
                    {attached &&
                      (attached.video ? (
                        <video
                          src={attached.url}
                          className="w-full max-h-80 object-cover bg-black"
                          autoPlay
                          loop
                          muted
                          playsInline
                          controls={attached.kind === "video"}
                        />
                      ) : (
                        <img src={attached.url} alt="" className="w-full max-h-80 object-cover" />
                      ))}
                    <div className="p-4 text-sm whitespace-pre-wrap break-words min-h-20">
                      {body || (attached ? "" : "Здесь появится текст сообщения.")}
                    </div>
                  </div>
                  {
                    <div className="border rounded-lg mt-2 p-3 text-center text-sm text-muted-foreground">
                      {template in announce
                        ? announce[template]
                        : template === "invite"
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
