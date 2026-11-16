// «NFT-подарки за друзей»: the switch, rules, gift sets by t.me/nft links, the issue queue and friend checks.
import { useEffect, useState } from "react";
import { api, date, useResource, type Data } from "@/lib/api";
import { ActionButton, DataTable, Failure, Field, Loading, Panel, useConfirm } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";

const F = "https://nft.fragment.com/gift/";
const thumb = (g: Data) => F + g.slug + ".webp";
const pl = (n: number, a: string, b: string, c: string) => {
  const m = n % 10, h = n % 100;
  return m === 1 && h !== 11 ? a : m >= 2 && m <= 4 && (h < 12 || h > 14) ? b : c;
};
const friends = (n: number) => `${n} ${pl(n, "друг", "друга", "друзей")}`;
const left = (iso: string) => {
  const ms = Math.max(0, new Date(iso).getTime() - Date.now());
  const d = Math.floor(ms / 864e5), h = Math.floor((ms % 864e5) / 36e5), m = Math.floor((ms % 36e5) / 6e4);
  return d ? `${d} д ${h} ч` : `${h} ч ${m} мин`;
};
const isBlack = (g: Data) => (g.a || []).some((x: string[]) => x[0] === "Фон" && /black/i.test(x[1] || ""));
const similar = (g: Data) =>
  `https://fragment.com/gifts/${String(g.slug || "").replace(/-\d+$/, "")}?sort=price_asc&filter=sale` +
  (isBlack(g) ? "&attr%5BBackdrop%5D=%5B%22Onyx+Black%22%5D" : "");
const BuyLinks = ({ g }: { g: Data }) => (
  <span className="flex gap-3 text-xs">
    {g.fragment && (
      <a className="text-primary hover:underline" href={g.fragment} target="_blank" rel="noreferrer">
        Купить на Fragment
      </a>
    )}
    <a className="text-primary hover:underline" href={similar(g)} target="_blank" rel="noreferrer">
      Похожие дешевле
    </a>
  </span>
);
const chat = (r: Data, id = "telegram_id", nick = "username") =>
  r[nick] ? `https://t.me/${String(r[nick]).replace(/^@/, "")}` : `tg://user?id=${r[id]}`;

function Gift({ g, small }: { g: Data; small?: boolean }) {
  return (
    <span className="flex items-center gap-2 min-w-0">
      <img src={thumb(g)} alt="" className={small ? "size-8 rounded-md" : "size-10 rounded-lg"} />
      <span className="min-w-0">
        <a href={g.link} target="_blank" rel="noreferrer" className="font-medium hover:underline">
          {g.name} #{g.no}
        </a>
        <span className="block text-xs text-muted-foreground">
          {(g.a || []).map((x: string[]) => x[1]).join(" · ")}
          {g.ton ? ` · ~${g.ton} TON` : ""}
        </span>
      </span>
    </span>
  );
}

function Rules({ cfg, reload }: { cfg: Data; reload: () => Promise<void> }) {
  const [form, setForm] = useState<Data>({});
  useEffect(
    () =>
      setForm({
        steps: (cfg.steps || []).join(", "),
        period_days: cfg.period_days,
        min_rub: cfg.min_rub,
        online_days: cfg.online_days,
        check_days: cfg.check_days,
      }),
    [cfg],
  );
  const save = async (patch: Data, done: string) => {
    await api("friend-nft", { action: "save", config: patch });
    toast.success(done);
    await reload();
  };
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <Panel
      title="NFT-подарки за друзей"
      description="Настоящие коллекционные подарки Telegram за друзей, которые сами оплатили VPN и пользуются им. Выключено — в кабинете обычное приглашение (+50 ₽); заработанные подарки остаются и их можно выдать."
      action={
        <label className="flex items-center gap-2 text-sm font-medium">
          <Switch
            checked={!!cfg.enabled}
            onCheckedChange={(on) =>
              void save({ enabled: on }, on ? "Акция включена" : "Акция выключена — в кабинете обычное приглашение").catch((e) =>
                toast.error((e as Error).message),
              )
            }
          />
          {cfg.enabled ? "Включено" : "Выключено"}
        </label>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Field label="Шаги, друзей" hint="Сколько друзей нужно для каждого подарка">
          <Input value={form.steps || ""} onChange={set("steps")} />
        </Field>
        <Field label="Витрина меняется, дней">
          <Input type="number" min={1} max={30} value={form.period_days || ""} onChange={set("period_days")} />
        </Field>
        <Field label="Оплата друга от, ₽" hint="Своими деньгами, не бонусами">
          <Input type="number" min={1} value={form.min_rub || ""} onChange={set("min_rub")} />
        </Field>
        <Field label="Проверка, дней" hint="Сколько ждём после оплаты">
          <Input type="number" min={1} max={30} value={form.check_days || ""} onChange={set("check_days")} />
        </Field>
        <Field label="Дней с VPN, минимум" hint="Из дней проверки">
          <Input type="number" min={0} value={form.online_days ?? ""} onChange={set("online_days")} />
        </Field>
      </div>
      <div className="mt-4">
        <ActionButton
          onAction={() =>
            save(
              {
                steps: String(form.steps || "")
                  .split(/[^0-9]+/)
                  .filter(Boolean)
                  .map(Number),
                period_days: Number(form.period_days),
                min_rub: Number(form.min_rub),
                check_days: Number(form.check_days),
                online_days: Number(form.online_days),
              },
              "Правила сохранены",
            )
          }
        >
          Сохранить правила
        </ActionButton>
      </div>
    </Panel>
  );
}

function Auto({ data, reload }: { data: Data; reload: () => Promise<void> }) {
  const cfg = data.config, rot = data.rotation, live = cfg.live || {};
  const [form, setForm] = useState<Data>({});
  const confirm = useConfirm();
  useEffect(() => setForm({ max_ton: cfg.max_ton, black_max_ton: cfg.black_max_ton }), [cfg]);
  const save = async (patch: Data, done: string) => {
    await api("friend-nft", { action: "save", config: patch });
    toast.success(done);
    await reload();
  };
  const search = async (action: string) => {
    await api("friend-nft", { action });
    toast.success("Ищу подарки на Fragment — витрина обновится примерно через минуту");
    setTimeout(() => void reload(), 45000);
  };
  const gifts: Data[] = data.showcase || [];
  const steps: number[] = cfg.steps || [];
  return (
    <Panel
      title="Подарки на витрине"
      description={`Каждые ${cfg.period_days} ${pl(cfg.period_days, "день", "дня", "дней")} шаги, которые человек ещё не прошёл, получают новые подарки. Заработанные не меняются. Последний шаг — «Главный подарок» на чёрном фоне.`}
      action={
        <label className="flex items-center gap-2 text-sm font-medium">
          <Switch
            checked={!!cfg.auto}
            onCheckedChange={(on) =>
              void save({ auto: on }, on ? "Бот сам подбирает подарки на продаже" : "Подарки из наборов ниже").catch((e) =>
                toast.error((e as Error).message),
              )
            }
          />
          Бот сам находит на Fragment
        </label>
      }
    >
      {cfg.auto ? (
        <p className="text-sm text-muted-foreground mb-4">
          При каждом обновлении бот берёт самые дешёвые подарки на продаже — по одному из разных коллекций, а для главного —
          самый дешёвый на Onyx Black. Покупаете вы, когда человек заработал подарок: ссылки будут в очереди выдачи.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground mb-4">Подарки берутся из наборов ниже по очереди.</p>
      )}
      {cfg.auto && (
        <div className="grid gap-4 sm:grid-cols-3 mb-4 items-end">
          <Field label="Обычный подарок до, TON">
            <Input type="number" min={1} value={form.max_ton ?? ""} onChange={(e) => setForm({ ...form, max_ton: e.target.value })} />
          </Field>
          <Field label="Главный (чёрный) до, TON">
            <Input type="number" min={1} value={form.black_max_ton ?? ""} onChange={(e) => setForm({ ...form, black_max_ton: e.target.value })} />
          </Field>
          <ActionButton
            variant="outline"
            onAction={() => save({ max_ton: Number(form.max_ton), black_max_ton: Number(form.black_max_ton) }, "Цены сохранены")}
          >
            Сохранить цены
          </ActionButton>
        </div>
      )}
      <div className="text-sm font-medium mb-2">
        Сейчас на витрине · следующие через {left(rot.next_at)}
        {cfg.auto && !rot.live && <Badge variant="secondary" className="ml-2">запасной набор</Badge>}
      </div>
      {cfg.auto && live.error && !rot.live && (
        <p className="text-sm text-destructive mb-2">Fragment: {live.error}. Бот попробует ещё раз через полчаса.</p>
      )}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {gifts.map((g, i) => (
          <div key={i} className="rounded-lg border p-3 space-y-2">
            <div className="text-xs text-muted-foreground">
              {i === steps.length - 1 ? "Главный · " : ""}за {friends(steps[i])}
            </div>
            <Gift g={g} small />
            {g.fragment && <BuyLinks g={g} />}
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {cfg.auto && (
          <ActionButton variant="outline" onAction={() => search("find")}>
            Найти заново
          </ActionButton>
        )}
        <Button
          variant="outline"
          onClick={() =>
            confirm({
              title: "Обновить витрину сейчас?",
              description: "Таймер начнётся заново, бот напишет о новых подарках тем, кто приглашает друзей.",
              label: "Обновить",
              action: () => (cfg.auto ? search("rotate") : api("friend-nft", { action: "rotate" }).then(reload)),
            })
          }
        >
          Обновить витрину сейчас
        </Button>
      </div>
    </Panel>
  );
}

function Sets({ data, reload }: { data: Data; reload: () => Promise<void> }) {
  const cfg = data.config, rot = data.rotation;
  const [sets, setSets] = useState<Data[][]>([]);
  const [links, setLinks] = useState<Record<string, string>>({});
  const [tons, setTons] = useState<Record<string, string>>({});
  useEffect(() => {
    setSets(cfg.sets || []);
    setLinks({});
    setTons({});
  }, [cfg]);
  const steps: number[] = cfg.steps || [];
  const key = (s: number, i: number) => `${s}:${i}`;
  const saveSets = async () => {
    const next: Data[][] = [];
    for (let s = 0; s < sets.length; s++) {
      const row: Data[] = [];
      for (let i = 0; i < steps.length; i++) {
        const k = key(s, i), old = sets[s]?.[i];
        const link = (links[k] ?? "").trim(), ton = tons[k];
        if (link && link !== old?.link) {
          const got = await api("friend-nft", { action: "gift", link, ton: Number(ton ?? old?.ton ?? 0) });
          row.push(got.gift);
        } else if (old) row.push(ton !== undefined ? { ...old, ton: Number(ton) || 0 } : old);
        else throw new Error(`Набор ${s + 1}: нет подарка для шага «${friends(steps[i])}»`);
      }
      next.push(row);
    }
    await api("friend-nft", { action: "save", config: { sets: next } });
    toast.success("Наборы подарков сохранены");
    await reload();
  };
  return (
    <Panel
      title={cfg.auto ? "Запасные наборы" : "Наборы подарков"}
      description={cfg.auto
        ? "Показываются, только если Fragment не ответил при обновлении витрины."
        : "Наборы идут по очереди при каждом обновлении. Последний шаг — «Главный подарок»: лучше самый дешёвый на чёрном фоне (Onyx Black)."}
      action={
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() =>
              setSets([...sets, steps.map(() => null as unknown as Data)])
            }
          >
            Добавить набор
          </Button>
        </div>
      }
    >
      <p className="text-sm text-muted-foreground mb-4">
        {!cfg.auto && <>Сейчас набор {rot.index + 1}, следующий — {(rot.next_index || 0) + 1}. </>}Вставьте ссылку вида
        t.me/nft/IceCream-162005 — модель, фон и узор подтянутся сами.
      </p>
      <div className="space-y-4">
        {sets.map((gifts, s) => (
          <div key={s} className={`rounded-lg border p-3 ${s === rot.index ? "border-primary" : ""}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm">
                Набор {s + 1} {s === rot.index && !cfg.auto && <Badge className="ml-1">сейчас</Badge>}
              </span>
              {sets.length > 1 && (
                <Button variant="ghost" size="sm" onClick={() => setSets(sets.filter((_, j) => j !== s))}>
                  Убрать
                </Button>
              )}
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              {steps.map((need, i) => {
                const g = gifts?.[i], k = key(s, i);
                return (
                  <div key={i} className="space-y-1.5">
                    <div className="text-xs text-muted-foreground">
                      {i === steps.length - 1 ? "Главный · " : ""}за {friends(need)}
                    </div>
                    {g ? <Gift g={g} small /> : <div className="text-sm text-muted-foreground">не выбран</div>}
                    <Input
                      placeholder={g?.link || "t.me/nft/…"}
                      value={links[k] ?? ""}
                      onChange={(e) => setLinks({ ...links, [k]: e.target.value })}
                    />
                    <Input
                      type="number"
                      placeholder="TON"
                      value={tons[k] ?? (g?.ton ?? "")}
                      onChange={(e) => setTons({ ...tons, [k]: e.target.value })}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <ActionButton onAction={saveSets}>Сохранить наборы</ActionButton>
      </div>
    </Panel>
  );
}

function Queue({ data, reload }: { data: Data; reload: () => Promise<void> }) {
  const [links, setLinks] = useState<Record<number, string>>({});
  const confirm = useConfirm();
  const rows: Data[] = data.queue || [];
  return (
    <Panel
      title="Выдать подарки"
      description="Купите подарок на Fragment (если этот номер уже продан — «Похожие дешевле»), передайте его человеку в Telegram, вставьте ссылку на переданный NFT и нажмите «Выдано» — бот напишет ему и покажет именно этот подарок. Перед выдачей посмотрите его друзей ниже."
    >
      <DataTable
        rows={rows}
        empty={<div className="p-6 text-sm text-muted-foreground text-center">Очередь пуста</div>}
        columns={[
          {
            key: "who",
            label: "Кому",
            cell: (r) => (
              <span>
                <b>{r.first_name || "без имени"}</b>
                <span className="block text-xs text-muted-foreground">
                  {r.username ? "@" + r.username : r.telegram_id} · засчитано {r.counted}
                </span>
              </span>
            ),
          },
          {
            key: "gift",
            label: "Подарок",
            cell: (r) => (
              <span className="space-y-1 block">
                <Gift g={r.gift} />
                {r.status === "wait" && <BuyLinks g={r.gift} />}
              </span>
            ),
          },
          { key: "need", label: "За", cell: (r) => friends(r.need) },
          { key: "created_at", label: "Заработал", cell: (r) => date(r.created_at) },
          {
            key: "act",
            label: "",
            cell: (r) =>
              r.status === "given" ? (
                <span className="text-sm">
                  <Badge variant="secondary">выдано {date(r.given_at)}</Badge>
                  {r.nft_link && (
                    <a className="ml-2 text-xs hover:underline" href={r.nft_link} target="_blank" rel="noreferrer">
                      NFT
                    </a>
                  )}
                </span>
              ) : (
                <div className="flex flex-wrap items-center gap-2 min-w-[300px]">
                  <Input
                    className="w-56"
                    placeholder="Ссылка на переданный NFT"
                    value={links[r.id] || ""}
                    onChange={(e) => setLinks({ ...links, [r.id]: e.target.value })}
                  />
                  <ActionButton
                    onAction={async () => {
                      await api("friend-nft", { action: "give", id: r.id, link: links[r.id] || "" });
                      toast.success("Отмечено: выдано. Бот написал человеку.");
                      await reload();
                    }}
                  >
                    Выдано
                  </ActionButton>
                  <Button variant="outline" asChild>
                    <a href={chat(r)} target="_blank" rel="noreferrer">
                      Открыть чат
                    </a>
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() =>
                      confirm({
                        title: "Отменить подарок?",
                        description: "Подарок уйдёт из очереди. Человеку бот не пишет — лучше сначала снять друга-накрутку ниже.",
                        label: "Отменить",
                        danger: true,
                        action: async () => {
                          await api("friend-nft", { action: "cancel", id: r.id });
                          await reload();
                        },
                      })
                    }
                  >
                    Отменить
                  </Button>
                </div>
              ),
          },
        ]}
      />
    </Panel>
  );
}

const STATUS: Record<string, [string, "default" | "secondary" | "destructive" | "outline"]> = {
  check: ["на проверке", "outline"],
  ok: ["засчитан", "default"],
  bad: ["не засчитан", "destructive"],
};

function Checks({ data, reload }: { data: Data; reload: () => Promise<void> }) {
  const [bad, setBad] = useState<Data | null>(null), [reason, setReason] = useState("");
  const [filter, setFilter] = useState("");
  const t = data.totals || {};
  const rows: Data[] = (data.checks || []).filter((r: Data) => !filter || r.status === filter);
  return (
    <Panel
      title="Друзья на проверке"
      description={`Друг засчитывается через ${data.config.check_days} дней после оплаты от ${data.config.min_rub} ₽, если включал VPN хотя бы ${data.config.online_days} дня. Свой второй аккаунт, та же карта или телефон — снимите с причиной: человек её увидит, неполученные подарки выше нового счёта отменятся.`}
      action={
        <div className="flex gap-1">
          {[["", `Все`], ["check", `Проверка · ${t.checking || 0}`], ["ok", `Засчитаны · ${t.ok || 0}`], ["bad", `Нет · ${t.bad || 0}`]].map(([v, l]) => (
            <Button key={v} size="sm" variant={filter === v ? "default" : "outline"} onClick={() => setFilter(v)}>
              {l}
            </Button>
          ))}
        </div>
      }
    >
      <DataTable
        rows={rows}
        empty={<div className="p-6 text-sm text-muted-foreground text-center">Пока никого</div>}
        columns={[
          {
            key: "friend",
            label: "Друг",
            cell: (r) => (
              <a href={chat(r, "invitee_id", "friend_username")} target="_blank" rel="noreferrer" className="hover:underline">
                <b>{r.friend_name || "без имени"}</b>
                <span className="block text-xs text-muted-foreground">{r.friend_username ? "@" + r.friend_username : r.invitee_id}</span>
              </a>
            ),
          },
          {
            key: "ref",
            label: "Пригласил",
            cell: (r) => (
              <span>
                {r.referrer_name || "без имени"}
                <span className="block text-xs text-muted-foreground">{r.referrer_username ? "@" + r.referrer_username : r.referrer_id}</span>
              </span>
            ),
          },
          { key: "paid_rub", label: "Оплатил", cell: (r) => `${r.paid_rub} ₽ · ${date(r.paid_at)}` },
          { key: "online", label: "Дней с VPN", cell: (r) => String(r.online) },
          {
            key: "status",
            label: "Статус",
            cell: (r) => (
              <span>
                <Badge variant={STATUS[r.status]?.[1]}>{STATUS[r.status]?.[0] || r.status}</Badge>
                {r.reason && <span className="block text-xs text-muted-foreground mt-1">{r.reason}{r.by_admin ? " · вручную" : ""}</span>}
              </span>
            ),
          },
          {
            key: "act",
            label: "",
            cell: (r) => (
              <div className="flex gap-2">
                {r.status !== "bad" && (
                  <Button variant="outline" size="sm" onClick={() => { setBad(r); setReason(""); }}>
                    Не засчитывать
                  </Button>
                )}
                {r.status !== "ok" && (
                  <ActionButton
                    variant="ghost"
                    onAction={async () => {
                      await api("friend-nft", { action: "friend", invitee_id: r.invitee_id, status: "ok" });
                      toast.success("Друг засчитан");
                      await reload();
                    }}
                  >
                    Засчитать
                  </ActionButton>
                )}
              </div>
            ),
          },
        ]}
      />
      <Dialog open={!!bad} onOpenChange={(o) => !o && setBad(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Не засчитывать {bad?.friend_name || "друга"}?</DialogTitle>
            <DialogDescription>Причину увидит {bad?.referrer_name || "пригласивший"} в боте и в кабинете.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-wrap gap-2">
            {["это ваш второй аккаунт", "оплатил вашей картой", "оплатил и не включал VPN", "платёж вернули", "уже был в боте до вашей ссылки"].map((x) => (
              <Button key={x} size="sm" variant="outline" onClick={() => setReason(x)}>
                {x}
              </Button>
            ))}
          </div>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Причина" />
          <ActionButton
            variant="destructive"
            disabled={!reason.trim()}
            onAction={async () => {
              const r = await api("friend-nft", { action: "friend", invitee_id: bad!.invitee_id, status: "bad", reason });
              toast.success(r.cancelled ? "Друг снят, неполученный подарок отменён" : "Друг снят");
              setBad(null);
              await reload();
            }}
          >
            Не засчитывать
          </ActionButton>
        </DialogContent>
      </Dialog>
    </Panel>
  );
}

export function FriendNftPanel() {
  const res = useResource("friend-nft");
  if (res.error) return <Failure message={res.error} retry={res.reload} />;
  if (!res.data) return <Loading />;
  const data = res.data, t = data.totals || {};
  return (
    <div className="space-y-5">
      <Rules cfg={data.config} reload={res.reload} />
      {(data.config.enabled || (data.queue || []).length > 0) && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              ["Ждут выдачи", t.wait || 0],
              ["Выдано", t.given || 0],
              ["Потрачено", `~${t.ton || 0} TON`],
              ["Друзей засчитано", t.ok || 0],
            ].map(([l, v]) => (
              <div key={String(l)} className="rounded-lg border p-3">
                <div className="text-xs text-muted-foreground">{l}</div>
                <div className="text-xl font-semibold">{v}</div>
              </div>
            ))}
          </div>
          <Queue data={data} reload={res.reload} />
        </>
      )}
      <Auto data={data} reload={res.reload} />
      <Sets data={data} reload={res.reload} />
      <Checks data={data} reload={res.reload} />
    </div>
  );
}
