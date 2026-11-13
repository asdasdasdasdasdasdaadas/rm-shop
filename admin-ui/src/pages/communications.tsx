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
  ["not_connected", "Добавили устройство, но не подключились"],
  ["zero_off", "VPN отключился — закончились деньги"],
  ["low_balance", "Баланса осталось меньше чем на 3 дня"],
  ["no_browser", "Пользуются VPN, но ни разу не входили в браузере"],
];
// What each segment is for: shown under the audience picker.
const audienceHint: Record<string, string> = {
  not_connected: "Им нужна помощь с подключением, а не скидка: короткая инструкция и кнопка в кабинет.",
  zero_off: "Пользовались VPN, он выключился из-за нулевого баланса. Лучше всего работает напоминание пополнить с одной кнопкой.",
  low_balance: "VPN работает, но скоро выключится. Предупредите заранее — так меньше людей теряют доступ.",
  no_browser: "VPN работал за последние 30 дней, а кабинет в браузере не открывали. Запасной вход пригодится, если Telegram не грузится.",
};
// Next 19:00 in Moscow (UTC+3, no daylight saving): people read messages in the evening.
const nextEveningMsk = () => {
  const now = new Date(),
    at = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 16, 0));
  if (at.getTime() < now.getTime() + 5 * 60_000) at.setUTCDate(at.getUTCDate() + 1);
  return at;
};
const audienceLabel = (id: string) => audiences.find(([a]) => a === id)?.[1] || id;
const templates: [string, string][] = [
  ["", "Своё сообщение"],
  ["gift3", "+3 дня всем с текстом"],
  ["referral_news", "Новая реферальная программа"],
  ["whitelist", "Белые списки включены"],
  ["invite", "Пригласить друзей"],
  ["unused", "Помощь с первым подключением"],
  ["browser", "Кабинет в браузере"],
];
// Stored templates with an audience of their own.
const templateAudience: Record<string, string> = { invite: "using", unused: "unused", browser: "no_browser" };
// A photo, GIF or video goes with one's own text or with «Кабинет в браузере» (a screen recording of the login).
const withMedia = (t: string) => !t || t === "browser";
// «Кабинет в браузере» ships its own looping clip (app/assets/browser-login.mp4); the admin may swap or drop it.
const BUILTIN_CLIP = { url: "/admin/api/broadcast/builtin/browser-login.mp4", kind: "animation", video: true };
const clipOptions: [string, string][] = [
  ["builtin", "Встроенное: вход по QR, 5 секунд"],
  ["own", "Своё фото, GIF или видео"],
  ["none", "Без видео"],
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
const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : "—");
// Each broadcast measured by money: delivered → tapped → paid within 7 days of the tap.
function Results() {
  const res = useResource("broadcast-results", 30000),
    confirm = useConfirm(),
    items: Data[] = res.data?.items || [];
  if (!items.length) return null;
  return (
    <Panel
      title="Результаты рассылок"
      description="Нажали — открыли кнопку из сообщения. Оплатили — пополнили в течение 7 дней после нажатия. Вошли в браузере — открыли кабинет на сайте в течение 3 дней (для «Кабинет в браузере»)."
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-muted-foreground text-left">
            <tr>
              <th className="py-2 pr-3 font-normal">Рассылка</th>
              <th className="py-2 pr-3 font-normal text-right">Доставлено</th>
              <th className="py-2 pr-3 font-normal text-right">Нажали</th>
              <th className="py-2 pr-3 font-normal text-right">Оплатили</th>
              <th className="py-2 pr-3 font-normal text-right">Вошли в браузере</th>
              <th className="py-2 font-normal text-right">Выручка</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => {
              const spec = r.spec || {},
                sent = Number(r.sent || 0);
              return (
                <tr key={r.id} className="border-t align-top">
                  <td className="py-3 pr-3">
                    <div className="font-medium">{r.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {whenLabel(r.created_at)}
                      {spec.audience && spec.audience !== "all" ? ` · ${audienceLabel(spec.audience)}` : ""}
                      {spec.sample ? ` · тест ${spec.sample}%` : ""}
                      {spec.parent ? " · остальным после теста" : ""}
                    </div>
                    {spec.sample && r.rest > 0 && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-2"
                        onClick={() =>
                          confirm({
                            title: `Отправить остальным ${r.rest}?`,
                            description: `Тот же текст уйдёт тем из аудитории, кто не получил тест. Тест: нажали ${pct(Number(r.clicked || 0), sent)}, оплатили ${pct(Number(r.payers || 0), sent)}.`,
                            label: "Отправить остальным",
                            action: async () => {
                              await api("broadcast", { rest_of: r.id });
                              await res.reload();
                              toast.success("Рассылка остальным запущена");
                            },
                          })
                        }
                      >
                        <Send />
                        Отправить остальным · {r.rest}
                      </Button>
                    )}
                    {r.rest_sent && <div className="text-xs text-muted-foreground mt-1">Остальным отправлено</div>}
                  </td>
                  <td className="py-3 pr-3 text-right tabular-nums">{sent}</td>
                  <td className="py-3 pr-3 text-right tabular-nums">
                    {r.clicked || 0} <span className="text-muted-foreground">· {pct(Number(r.clicked || 0), sent)}</span>
                  </td>
                  <td className="py-3 pr-3 text-right tabular-nums">
                    {r.payers || 0} <span className="text-muted-foreground">· {pct(Number(r.payers || 0), sent)}</span>
                  </td>
                  <td className="py-3 pr-3 text-right tabular-nums">
                    {spec.template === "browser" ? (
                      <>
                        {r.browser_logins || 0}{" "}
                        <span className="text-muted-foreground">· {pct(Number(r.browser_logins || 0), sent)}</span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="py-3 text-right tabular-nums">
                    {Number(r.rub || 0).toLocaleString("ru-RU")} ₽
                    {r.stars ? ` · ${r.stars} ⭐` : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
    [sent, setSent] = useState(false),
    [later, setLater] = useState(false),
    [evening, setEvening] = useState(false),
    [sample, setSample] = useState(0),
    [media, setMedia] = useState<Media | null>(null),
    [clip, setClip] = useState("builtin"),
    [when, setWhen] = useState(() => localInput(new Date(Date.now() + 3600_000)));
  const confirm = useConfirm(),
    navigate = useNavigate();
  useDirty(!sent && (!!text.trim() || !!template || !!media));
  // The preview keeps a local copy of the file; free it when the attachment changes or the page closes.
  useEffect(() => () => { if (media) URL.revokeObjectURL(media.url); }, [media]);
  const data = resource.data,
    effectiveAudience =
      templateAudience[template] ?? (template === "whitelist" || template in announce ? "all" : audience),
    count = data?.audiences?.[effectiveAudience] ?? 0,
    editable = !template || template in announce,
    body = editable ? text : data?.previews?.[template] || "",
    attached = withMedia(template) && (template !== "browser" || clip === "own") ? media : null,
    shown = attached || (template === "browser" && clip === "builtin" ? BUILTIN_CLIP : null),
    tooLong = !!attached && text.length > CAPTION_MAX,
    ready = (!!body.trim() || !!attached) && !tooLong;
  const selectTemplate = (v: string) => {
    if (v in announce) setText(data?.previews?.[v] || "");
    else if (template in announce) setText("");
    setTemplate(v);
    setSent(false);
  };
  const whenDate = evening ? nextEveningMsk() : new Date(when),
    whenValid = !later || (!Number.isNaN(whenDate.getTime()) && whenDate.getTime() > Date.now() + 60_000),
    testN = sample ? Math.max(1, Math.round((count * sample) / 100)) : count;
  const send = () =>
    confirm({
      title: later ? "Запланировать рассылку?" : "Отправить рассылку?",
      description: `Аудитория: ${audienceLabel(effectiveAudience)}.\n${sample ? `Тест: ${sample}% — примерно ${testN} из ${count}. Остальным отправите из «Результатов», когда увидите конверсию.` : `Получателей сейчас: ${count}.`} Фактическое число может измениться к началу отправки.\n${later ? `Отправка начнётся ${whenLabel(whenDate.toISOString())}. До этого рассылку можно отменить.` : "Сообщение отправится в Telegram. Отменить отправленное нельзя."}`,
      label: later ? "Запланировать" : "Отправить рассылку",
      action: async () => {
        const payload =
          template in announce
            ? { template, text }
            : template
              ? {
                  template,
                  ...(attached
                    ? { media: { id: attached.id, kind: attached.kind } }
                    : template === "browser" && clip === "none"
                      ? { media: "none" }
                      : {}),
                }
              : { text, audience, ...(attached ? { media: { id: attached.id, kind: attached.kind } } : {}) };
        const full = sample ? { ...payload, sample } : payload;
        await api(
          "broadcast",
          later ? { ...full, scheduled_at: whenDate.toISOString() } : full,
        );
        setSent(true);
        setText("");
        setTemplate("");
        setClip("builtin");
        setMedia(null);
        setStep(0);
        setLater(false);
        setEvening(false);
        setSample(0);
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
                      {!template && audienceHint[effectiveAudience] && (
                        <p className="text-sm text-muted-foreground">{audienceHint[effectiveAudience]}</p>
                      )}
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
                      {step === 1 && template === "browser" && (
                        <Field label="Видео">
                          <Choice value={clip} label="Видео в рассылке" options={clipOptions} onChange={(v) => { setClip(v); setSent(false); }} />
                        </Field>
                      )}
                      {step === 1 && withMedia(template) && (template !== "browser" || clip === "own") && (
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
                            {audienceLabel(effectiveAudience)}
                          </dd>
                        </div>
                        {shown && (
                          <div className="flex justify-between gap-3">
                            <dt className="text-muted-foreground">Вложение</dt>
                            <dd>{shown === BUILTIN_CLIP ? "Встроенное видео: вход по QR" : kindLabel[shown.kind]}</dd>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">Сценарий</dt>
                          <dd>
                            {templates.find(([id]) => id === template)?.[1]}
                          </dd>
                        </div>
                      </dl>
                      <Field
                        label="Сначала тест"
                        hint={
                          sample
                            ? `Уйдёт ~${testN} случайным получателям. Через день-два сравните в «Результатах» нажатия и оплаты и отправьте остальным одной кнопкой.`
                            : "Тест на части аудитории помогает не тратить всю базу на слабый текст."
                        }
                      >
                        <Choice
                          label="Сначала тест"
                          value={String(sample)}
                          options={[
                            ["0", "Без теста — всем сразу"],
                            ["10", "Тест на 10%, потом остальным"],
                            ["20", "Тест на 20%, потом остальным"],
                          ]}
                          onChange={(v) => setSample(Number(v) || 0)}
                        />
                      </Field>
                      <Field label="Когда отправить">
                        <Choice
                          label="Когда отправить"
                          value={!later ? "now" : evening ? "evening" : "later"}
                          options={[
                            ["now", "Сразу"],
                            ["evening", `Вечером, ${whenLabel(nextEveningMsk().toISOString())} (19:00 МСК)`],
                            ["later", "Запланировать на дату и время"],
                          ]}
                          onChange={(v) => {
                            setLater(v !== "now");
                            setEvening(v === "evening");
                          }}
                        />
                      </Field>
                      {later && !evening && (
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
                          : `Отправить ${testN} пользователям`}
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
                    {shown &&
                      (shown.video ? (
                        <video
                          src={shown.url}
                          className="w-full max-h-80 object-cover bg-black"
                          autoPlay
                          loop
                          muted
                          playsInline
                          controls={shown.kind === "video"}
                        />
                      ) : (
                        <img src={shown.url} alt="" className="w-full max-h-80 object-cover" />
                      ))}
                    <div className="p-4 text-sm whitespace-pre-wrap break-words min-h-20">
                      {body || (shown ? "" : "Здесь появится текст сообщения.")}
                    </div>
                  </div>
                  {
                    <div className="border rounded-lg mt-2 p-3 text-center text-sm text-muted-foreground">
                      {template in announce
                        ? announce[template]
                        : template === "invite"
                          ? "Поделиться реферальной ссылкой · Войти в кабинет"
                          : template === "browser"
                            ? "🌐 Открыть в браузере · Как войти"
                            : "Войти в кабинет"}
                    </div>
                  }
                </div>
              </Panel>
            </div>
            <Results />
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
