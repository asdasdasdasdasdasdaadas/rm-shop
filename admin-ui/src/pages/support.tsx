import { useEffect, useRef, useState, type ClipboardEvent } from "react";
import { api, date, money, qs, useResource, who, type Data } from "@/lib/api";
import { ActionButton, Failure, Loading, useConfirm, useDirty, useNavigate } from "@/components/workspace";
import { Avatar, ago } from "@/components/widgets";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { ArrowLeft, Paperclip, RotateCw, Search, SendHorizontal, Star as StarIcon, X as XIcon } from "lucide-react";

// Support desk: dialogs on the left, the conversation in the middle, the client on the right.
const TABS: [string, string][] = [
  ["open", "Ждут ответа"],
  ["", "Все"],
  ["closed", "Закрытые"],
];
const DEFAULT_REPLIES = [
  "👋 Здравствуйте! Сейчас посмотрю.",
  "🔄 Обновите подписку в приложении: потяните список серверов вниз или нажмите «Обновить».",
  "📲 Удалите профиль в приложении и добавьте заново по кнопке «Подключить» в кабинете.",
  "💳 Проверим платёж. Пришлите, пожалуйста, скриншот чека.",
  "✅ Готово, проверьте ещё раз 🙂",
];
const REPLIES_KEY = "adm_quick_replies";
const loadReplies = (): string[] => {
  try {
    const v = JSON.parse(localStorage.getItem(REPLIES_KEY) || "null");
    return Array.isArray(v) && v.length ? v.map(String) : DEFAULT_REPLIES;
  } catch {
    return DEFAULT_REPLIES;
  }
};
const saveReplies = (v: string[]) => {
  try {
    localStorage.setItem(REPLIES_KEY, JSON.stringify(v));
  } catch {
    /* private mode: the list lives until reload */
  }
};
const isImage = (a: Data) => a.kind === "photo" || String(a.mime || "").startsWith("image/");
const fileUrl = (id: unknown) => `/admin/api/tickets/files/${id}`;
const stLabel = (s: unknown) => (s === "open" ? "Ждёт ответа" : s === "pending" ? "Отвечено" : s === "closed" ? "Закрыто" : String(s || ""));
const short = (s: string) => (s.length > 34 ? s.slice(0, 32) + "…" : s);
const dayLabel = (v: unknown) => {
  const d = new Date(String(v || ""));
  if (isNaN(+d)) return "";
  const today = new Date();
  const y = new Date(today);
  y.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Сегодня";
  if (d.toDateString() === y.toDateString()) return "Вчера";
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
};
const time = (v: unknown) => {
  const d = new Date(String(v || ""));
  return isNaN(+d) ? "" : d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
};

export function SupportPage() {
  const [tab, setTab] = useState("open"),
    [q, setQ] = useState(""),
    [query, setQuery] = useState(""),
    [selected, setSelected] = useState<Data | null>(null),
    [dirty, setDirty] = useState(false);
  const confirm = useConfirm();
  const list = useResource("tickets?" + qs({ status: tab, q: query, limit: 60 }), 20000);
  const rows: Data[] = list.data?.items || [];
  const counts: Data = list.data?.counts || {};
  // On a wide screen the first dialog opens by itself, so the desk is never half empty.
  useEffect(() => {
    if (!selected && rows.length && window.matchMedia("(min-width: 861px)").matches) setSelected(rows[0]);
  }, [rows, selected]);
  useEffect(() => {
    const t = setTimeout(() => setQuery(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);
  const open = (r: Data) => {
    if (selected?.id === r.id) return;
    if (dirty)
      confirm({
        title: "Перейти без отправки?",
        description: "Черновик ответа будет потерян.",
        label: "Перейти",
        action: async () => setSelected(r),
      });
    else setSelected(r);
  };
  return (
    <div className={"sd" + (selected ? " has-chat" : "")}>
      <section className="sd-list">
        <div className="sd-tabs" role="tablist">
          {TABS.map(([v, label]) => (
            <button key={v} type="button" role="tab" aria-selected={tab === v} className={tab === v ? "on" : ""} onClick={() => setTab(v)}>
              {label}
              {v === "open" && Number(counts.open) > 0 && <i>{counts.open}</i>}
            </button>
          ))}
        </div>
        <label className="sd-search">
          <Search />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Имя, @ник, текст или №" aria-label="Поиск обращений" />
        </label>
        <div className="sd-rows">
          {list.error ? (
            <Failure message={list.error} retry={list.reload} />
          ) : !list.data ? (
            <Loading />
          ) : !rows.length ? (
            <p className="sd-empty">{tab === "open" ? "Все ответили 🎉" : "Обращений нет"}</p>
          ) : (
            rows.map((r) => (
              <button key={r.id} type="button" className={"sd-row" + (selected?.id === r.id ? " sel" : "")} onClick={() => open(r)}>
                <Avatar row={r} size={44} />
                <span className="sd-row-main">
                  <span className="sd-row-top">
                    <b>{who(r)}</b>
                    <small>{ago(r.last_message_at || r.created_at)}</small>
                  </span>
                  <span className="sd-row-pv">
                    {r.last_photo_id ? <img src={fileUrl(r.last_photo_id)} alt="" loading="lazy" /> : null}
                    {r.last_author === "admin" && <b>Вы: </b>}
                    {r.last_body || "Вложение"}
                  </span>
                  <span className="sd-row-meta">
                    <span className={"sd-chip " + String(r.status || "")}>{r.status === "open" ? "Ждёт " + ago(r.last_message_at).replace(" назад", "") : stLabel(r.status)}</span>
                    {r.status === "open" && Number(r.unread) > 1 && <span className="sd-chip new">{r.unread} новых</span>}
                    {r.support_rating ? <span className="sd-chip">★ {r.support_rating}</span> : null}
                    <span className="sd-chip ghost">№{r.id}</span>
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
      </section>
      {selected ? (
        <Dialog key={selected.id} row={selected} onBack={() => setSelected(null)} onChange={list.reload} onDirty={setDirty} />
      ) : (
        <section className="sd-chat sd-none">
          <p>Выберите обращение слева</p>
        </section>
      )}
    </div>
  );
}

function Dialog({ row, onBack, onChange, onDirty }: { row: Data; onBack: () => void; onChange: () => Promise<void>; onDirty: (d: boolean) => void }) {
  const res = useResource("tickets/" + row.id, 10000),
    client = useResource(`tickets/${row.id}/client`);
  const [text, setText] = useState(""),
    [files, setFiles] = useState<File[]>([]),
    [replies, setReplies] = useState<string[]>(loadReplies),
    [zoom, setZoom] = useState<string | null>(null);
  const confirm = useConfirm();
  const log = useRef<HTMLDivElement>(null);
  const typedAt = useRef(0);
  const draft = !!text.trim() || !!files.length;
  useDirty(draft);
  useEffect(() => {
    onDirty(draft);
    return () => onDirty(false);
  }, [draft, onDirty]);
  const messages: Data[] = res.data?.messages || [];
  const t: Data = res.data?.ticket || row;
  // Stay at the latest message, also while screenshots load, unless the admin scrolled up to read.
  const stick = useRef(true);
  const toEnd = () => {
    if (stick.current) log.current?.scrollTo({ top: log.current.scrollHeight });
  };
  useEffect(toEnd, [messages.length]);
  const send = async () => {
    const form = new FormData();
    form.append("text", text);
    files.forEach((f) => form.append("file", f));
    const r = await api("tickets/" + row.id, form);
    res.setData(r);
    setText("");
    setFiles([]);
    await onChange();
    toast.success("Ответ отправлен");
  };
  const paste = (e: ClipboardEvent) => {
    const pics = Array.from(e.clipboardData.files || []).filter((f) => f.type.startsWith("image/"));
    if (!pics.length) return;
    e.preventDefault();
    setFiles((cur) => [...cur, ...pics.map((f, i) => new File([f], f.name && f.name !== "image.png" ? f.name : `скриншот-${Date.now()}-${i}.png`, { type: f.type }))]);
  };
  const addReply = () => {
    const v = text.trim();
    if (!v || replies.includes(v)) return;
    const next = [...replies, v];
    setReplies(next);
    saveReplies(next);
    toast.success("Шаблон сохранён");
  };
  const dropReply = (v: string) => {
    const next = replies.filter((x) => x !== v);
    setReplies(next);
    saveReplies(next);
  };
  let lastDay = "";
  return (
    <>
      <section className="sd-chat">
        <header className="sd-chat-hd">
          <button type="button" className="sd-back" onClick={onBack} aria-label="К списку">
            <ArrowLeft />
          </button>
          <Avatar row={row} size={40} />
          <div className="sd-chat-t">
            <b>{who(row)}</b>
            <span>
              №{row.id} · {stLabel(t.status)} · начато {date(t.created_at || row.created_at)}
            </span>
          </div>
          {t.support_rating ? (
            <span className="adm-chat-rate" title="Оценка поддержки">
              {[1, 2, 3, 4, 5].map((n) => (
                <StarIcon key={n} className={n <= Number(t.support_rating) ? "on" : ""} />
              ))}
            </span>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            disabled={t.status === "closed"}
            onClick={() =>
              confirm({
                title: "Закрыть обращение?",
                description: "Пользователь получит уведомление о закрытии.",
                label: "Закрыть обращение",
                action: async () => {
                  await api("tickets/" + row.id, { action: "close" });
                  await res.reload();
                  await onChange();
                },
              })
            }
          >
            Закрыть
          </Button>
        </header>
        <div
          className="sd-log"
          ref={log}
          onScroll={(e) => {
            const el = e.currentTarget;
            stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
          }}
        >
          {res.error ? (
            <Failure message={res.error} retry={res.reload} />
          ) : !res.data ? (
            <Loading />
          ) : (
            messages.map((m, i) => {
              const day = dayLabel(m.created_at);
              const showDay = day !== lastDay;
              lastDay = day;
              const atts: Data[] = m.attachments || [];
              return (
                <div key={m.id || i} className="sd-msg">
                  {showDay && <span className="sd-day">{day}</span>}
                  <div className={"adm-bubble " + (m.author === "admin" ? "me" : "them")}>
                    {atts.filter(isImage).map((a) => (
                      <button key={a.id} type="button" className="sd-img" onClick={() => setZoom(a.url)} aria-label="Открыть картинку">
                        <img src={a.url} alt={a.original_name || "Скриншот"} onLoad={toEnd} />
                      </button>
                    ))}
                    {m.body && <p className="adm-bubble-text">{m.body}</p>}
                    {atts
                      .filter((a) => !isImage(a))
                      .map((a) => (
                        <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer" className="adm-bubble-file">
                          <Paperclip className="size-3.5" />
                          {a.original_name || "Файл"}
                        </a>
                      ))}
                    <span className="adm-bubble-time">{time(m.created_at)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
        <div className="sd-comp">
          <div className="sd-quick">
            {replies.map((r) => (
              <span key={r} className="sd-q">
                <button type="button" title={r} onClick={() => setText((cur) => (cur.trim() ? cur.trimEnd() + "\n" + r : r))}>
                  {short(r)}
                </button>
                <button type="button" className="x" aria-label={"Удалить шаблон " + short(r)} onClick={() => dropReply(r)}>
                  <XIcon />
                </button>
              </span>
            ))}
            <button type="button" className="sd-q add" disabled={!text.trim()} onClick={addReply} title="Сохранить текст из поля как шаблон">
              + в шаблоны
            </button>
          </div>
          {files.length > 0 && (
            <div className="sd-files">
              {files.map((f, i) => (
                <span key={f.name + i}>
                  {f.type.startsWith("image/") ? <img src={URL.createObjectURL(f)} alt="" /> : <Paperclip className="size-3.5" />}
                  {short(f.name)}
                  <button type="button" aria-label={"Убрать " + f.name} onClick={() => setFiles(files.filter((_, j) => j !== i))}>
                    <XIcon className="size-3.5" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="adm-composer-row">
            <label className="adm-attach" title="Прикрепить файл">
              <Paperclip />
              <input
                type="file"
                multiple
                aria-label="Вложения к ответу"
                className="sr-only"
                onChange={(e) => setFiles([...files, ...Array.from(e.target.files || [])])}
              />
            </label>
            <Textarea
              aria-label="Ответ клиенту"
              placeholder={t.status === "closed" ? "Ответ откроет обращение снова" : "Сообщение… скриншот можно вставить через ⌘V"}
              rows={2}
              value={text}
              onPaste={paste}
              onChange={(e) => {
                setText(e.target.value);
                // The client sees «Поддержка печатает…» while the answer is being typed.
                if (e.target.value.trim() && Date.now() - typedAt.current > 3000) {
                  typedAt.current = Date.now();
                  api("tickets/" + row.id, { action: "typing" }).catch(() => {});
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && draft) {
                  e.preventDefault();
                  void send().catch((err) => toast.error((err as Error).message));
                }
              }}
            />
            <ActionButton className="adm-send" aria-label="Отправить ответ" disabled={!draft} onAction={send}>
              <SendHorizontal />
            </ActionButton>
          </div>
          <p className="adm-composer-hint">⌘ + Enter — отправить · ответ придёт в Telegram и в кабинет</p>
        </div>
      </section>
      <Client res={client} />
      {zoom && (
        <button type="button" className="sd-zoom" onClick={() => setZoom(null)} aria-label="Закрыть картинку">
          <img src={zoom} alt="" />
        </button>
      )}
    </>
  );
}

function Client({ res }: { res: ReturnType<typeof useResource> }) {
  const navigate = useNavigate(),
    confirm = useConfirm();
  if (res.error)
    return (
      <aside className="sd-side">
        <Failure message={res.error} retry={res.reload} />
      </aside>
    );
  if (!res.data)
    return (
      <aside className="sd-side">
        <Loading />
      </aside>
    );
  const u: Data = res.data.user || {},
    devices: Data[] = res.data.devices || [],
    pays: Data[] = res.data.payments || [],
    h: Data = res.data.history || {};
  const id = u.telegram_id;
  const online = (d: Data) => {
    const t = Date.parse(String(d.last_online_at || ""));
    return !isNaN(t) && Date.now() - t < 15 * 60000;
  };
  const credit = (rub: number) =>
    confirm({
      title: `Начислить ${money(rub)}?`,
      description: `${who(u)} · ${id}\nСейчас: ${money(u.balance_rub)}\nПосле: ${money(Number(u.balance_rub || 0) + rub)}\nКлиент получит уведомление.`,
      label: "Начислить",
      action: async () => {
        await api(`users/${id}/grant`, { days: rub });
        toast.success("Начислено");
        await res.reload();
      },
    });
  return (
    <aside className="sd-side">
      <div className="sd-card">
        <div className="sd-kv">
          <span>Баланс</span>
          <b className={Number(u.balance_rub) <= 0 ? "bad" : ""}>{money(u.balance_rub)}</b>
        </div>
        <div className="sd-kv">
          <span>Хватит на</span>
          <b>{Number(u.days_left) > 0 ? `${u.days_left} дн` : `${u.hours_left || 0} ч`}</b>
        </div>
        <div className="sd-kv">
          <span>Клиент с</span>
          <b>{dayLabel(u.created_at) || "—"}</b>
        </div>
        {u.blocked && <p className="sd-warn">Заблокирован в админке</p>}
      </div>
      <h3>Устройства</h3>
      <div className="sd-card">
        {devices.length ? (
          devices.map((d) => (
            <div key={d.id ?? d.title} className="sd-kv">
              <span>
                {d.title || "Устройство"}
                {d.platform ? ` · ${d.platform}` : ""}
              </span>
              <span className="sd-dev">
                <b className={online(d) ? "ok" : "mut"}>{online(d) ? "● в сети" : d.last_online_at ? ago(d.last_online_at) : "не подключалось"}</b>
                {d.id ? (
                  <button
                    type="button"
                    title="Перевыпустить ключ"
                    aria-label={"Перевыпустить ключ " + (d.title || "")}
                    onClick={() =>
                      confirm({
                        title: "Перевыпустить ключ?",
                        description: `${d.title || "Устройство"}: старая ссылка перестанет работать, клиенту нужно будет добавить новую.`,
                        label: "Перевыпустить",
                        action: async () => {
                          await api(`users/${id}/devices/${d.id}/reissue`, {});
                          toast.success("Ключ перевыпущен");
                          await res.reload();
                        },
                      })
                    }
                  >
                    <RotateCw />
                  </button>
                ) : null}
              </span>
            </div>
          ))
        ) : (
          <p className="sd-mut">Устройств нет</p>
        )}
      </div>
      <h3>Последние платежи</h3>
      <div className="sd-card">
        {pays.length ? (
          pays.map((p, i) => (
            <div key={i} className="sd-kv">
              <span>
                {dayLabel(p.created_at)}
                {p.provider ? ` · ${p.provider}` : ""}
              </span>
              <b>{money(p.amount_rub)}</b>
            </div>
          ))
        ) : (
          <p className="sd-mut">Оплат не было</p>
        )}
      </div>
      <h3>Действия</h3>
      <div className="sd-acts">
        <Button variant="outline" size="sm" onClick={() => credit(50)}>
          +50 ₽
        </Button>
        <Button variant="outline" size="sm" onClick={() => credit(100)}>
          +100 ₽
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            confirm({
              title: "Отправить ссылку на кабинет?",
              description: "Клиенту придёт сообщение со ссылкой для входа в кабинет в браузере.",
              label: "Отправить",
              action: async () => {
                await api(`users/${id}/cabinet-link`, {});
                toast.success("Ссылка отправлена");
              },
            })
          }
        >
          Ссылка в кабинет
        </Button>
        <Button variant="outline" size="sm" onClick={() => navigate("users?q=" + encodeURIComponent(String(id)))}>
          Карточка клиента
        </Button>
      </div>
      <p className="sd-mut sd-hist">
        Обращений всего: {h.total || 1}
        {h.rating ? ` · средняя оценка ${h.rating}★` : ""}
      </p>
    </aside>
  );
}
