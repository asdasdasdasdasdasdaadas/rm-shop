// Dashboard widgets in the cabinet style: count-up numbers, rings, sparkline charts and an action queue.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Area, AreaChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import {
  AppWindow,
  ArrowRight,
  BadgeRussianRuble,
  ChevronDown,
  CircleCheck,
  Flame,
  Gift,
  Hourglass,
  Moon,
  Plug,
  Radio,
  UserPlus,
  Users as UsersIcon,
} from "lucide-react";
import { money, useResource, who, type Data } from "@/lib/api";
import { useNavigate } from "./workspace";

const reduced = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Animates from the previous value to the new one with an ease-out curve. */
export function useCountUp(value: number, ms = 900) {
  // A background tab freezes animation frames; the number must still be right when someone looks.
  const still = () => reduced() || document.hidden;
  const [shown, setShown] = useState(still() ? value : 0);
  const from = useRef(0);
  useEffect(() => {
    if (still()) {
      from.current = value;
      return setShown(value);
    }
    const start = performance.now(), a = from.current;
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / ms), e = 1 - Math.pow(1 - k, 3);
      setShown(a + (value - a) * e);
      if (k < 1) raf = requestAnimationFrame(tick);
      else from.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return shown;
}

export function CountUp({ value, format = (n) => Math.round(n).toLocaleString("ru-RU") }: { value: number; format?: (n: number) => string }) {
  const n = useCountUp(Number(value) || 0);
  return <span className="tabular-nums">{format(n)}</span>;
}

/** Up/down change versus the previous period. */
export function Delta({ now, prev, suffix = "к прошлым суткам", invert = false }: { now: number; prev: number; suffix?: string; invert?: boolean }) {
  // No base to compare with (0 before) — a «+100%» there would be made up, so show nothing.
  if (!(prev > 0)) return null;
  const pct = Math.round(((now - prev) / prev) * 100);
  const tone = pct === 0 ? "flat" : (pct > 0) !== invert ? "up" : "down";
  return (
    <span className={"adm-delta " + tone} title={`${suffix}: было ${prev.toLocaleString("ru-RU")}`}>
      {pct === 0 ? "→" : pct > 0 ? "↑" : "↓"} {Math.abs(pct)}%
    </span>
  );
}

export function Ring({ value, max, size = 92, stroke = 9, color = "var(--primary)", children }: { value: number; max: number; size?: number; stroke?: number; color?: string; children?: ReactNode }) {
  const r = (size - stroke) / 2, c = 2 * Math.PI * r, k = max ? Math.max(0, Math.min(1, value / max)) : 0;
  const [on, setOn] = useState(false);
  useEffect(() => { const t = requestAnimationFrame(() => setOn(true)); return () => cancelAnimationFrame(t); }, []);
  return (
    <div className="adm-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--secondary)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={on ? c * (1 - k) : c} transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1)" }} />
      </svg>
      <div className="adm-ring-in">{children}</div>
    </div>
  );
}

export function Widget({ title, icon, tone, action, onAction, children, className = "" }: { title: string; icon: ReactNode; tone: string; action?: string; onAction?: () => void; children: ReactNode; className?: string }) {
  return (
    <section className={"adm-widget " + className}>
      <header>
        <span className="adm-tile" style={{ background: tone }}>{icon}</span>
        <h2>{title}</h2>
        {action && onAction && (
          <button type="button" className="adm-link" onClick={onAction}>
            {action} <ArrowRight className="size-3.5" />
          </button>
        )}
      </header>
      {children}
    </section>
  );
}

const dayLabel = (d: string) => new Date(d + "T12:00:00Z").toLocaleDateString("ru-RU", { day: "numeric", month: "short" });

function ChartTip({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="adm-tip">
      <small>{dayLabel(label)}</small>
      <b>{Number(payload[0].value || 0).toLocaleString("ru-RU")}{unit}</b>
    </div>
  );
}

function RevenueWidget({ series, previous }: { series: Data[]; previous?: Data }) {
  const navigate = useNavigate();
  const total = series.reduce((a, r) => a + Number(r.rub || 0), 0);
  const pays = series.reduce((a, r) => a + Number(r.payments || 0), 0);
  // Same stretch of time right before, cut at the same hour (server side), so the numbers are comparable.
  const before = Number(previous?.totals?.rub ?? 0);
  return (
    <Widget title="Выручка за 30 дней" icon={<BadgeRussianRuble />} tone="#22975a" action="Финансы" onAction={() => navigate("finance")} className="adm-span2">
      <div className="adm-big">
        <CountUp value={total} format={(n) => money(Math.round(n))} />
        <Delta now={total} prev={before} suffix="к предыдущим 30 дням" />
      </div>
      <p className="adm-sub">{pays.toLocaleString("ru-RU")} пополнений · средний чек {money(pays ? Math.round(total / pays) : 0)}</p>
      <div className="adm-chart">
        <ResponsiveContainer width="100%" height={150}>
          <AreaChart data={series} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="admRev" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.45} />
                <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="day" hide />
            <Tooltip content={<ChartTip unit=" ₽" />} cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }} />
            <Area type="monotone" dataKey="rub" stroke="var(--primary)" strokeWidth={2.5} fill="url(#admRev)" animationDuration={1200} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Widget>
  );
}

const hourLabel = (h: number) => String(h).padStart(2, "0") + ":00";

function HourTip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload || {};
  return (
    <div className="adm-tip">
      <b>{hourLabel(Number(row.hour || 0))} — {Number(row.registered || 0).toLocaleString("ru-RU")}</b>
    </div>
  );
}

/** «Сегодня» is since midnight in Moscow, so the bars are today's Moscow hours, 00:00 up to the current one. */
function SignupsWidget({ hourly, users }: { hourly: Data[]; users: Data }) {
  const navigate = useNavigate();
  return (
    <Widget title="Новые пользователи" icon={<UsersIcon />} tone="#3e88f7" action="Статистика" onAction={() => navigate("statistics?tab=dynamics&chart=acquisition&days=30")}>
      <div className="adm-big">
        <span className="adm-plus"><CountUp value={Number(users.new_1d || 0)} format={(n) => "+" + Math.round(n).toLocaleString("ru-RU")} /></span>
        <span className="adm-unit">сегодня</span>
      </div>
      <p className="adm-sub">{Number(users.new_7d || 0).toLocaleString("ru-RU")} за неделю · {Number(users.new_30d || 0).toLocaleString("ru-RU")} за месяц</p>
      <div className="adm-chart">
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={hourly} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
            <XAxis dataKey="hour" hide />
            <Tooltip content={<HourTip />} cursor={{ fill: "var(--secondary)", radius: 6 } as any} />
            <Bar dataKey="registered" fill="#3e88f7" radius={[4, 4, 4, 4]} minPointSize={2} animationDuration={900} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Widget>
  );
}

function OnlineWidget({ online, users }: { online: Data; users: Data }) {
  const navigate = useNavigate();
  const day = Number(online.day || 0), total = Number(users.users_total || 0);
  return (
    <Widget title="Онлайн" icon={<Radio />} tone="#5856d6" action="Кто онлайн" onAction={() => navigate("users?online=1d")}>
      <div className="adm-ringrow">
        <Ring value={day} max={total || 1} color="#7b79ff">
          <b><CountUp value={total ? Math.round((day / total) * 100) : 0} />%</b>
          <small>от всех</small>
        </Ring>
        <dl>
          <div><dt>Сутки</dt><dd><CountUp value={day} /></dd></div>
          <div><dt>Неделя</dt><dd><CountUp value={Number(online.week || 0)} /></dd></div>
          <div><dt>Месяц</dt><dd><CountUp value={Number(online.month || 0)} /></dd></div>
        </dl>
      </div>
    </Widget>
  );
}

function ConversionWidget({ funnel }: { funnel: Data }) {
  const navigate = useNavigate();
  const cur = funnel?.["30d"]?.current || {};
  const entered = Number(cur.entered || 0), paid = Number(cur.paid || 0), connected = Number(cur.connected || 0);
  return (
    <Widget title="Конверсия за 30 дней" icon={<CircleCheck />} tone="#ff9500" action="Воронка" onAction={() => navigate("statistics?tab=funnel&days=30")}>
      <div className="adm-ringrow">
        <Ring value={paid} max={entered || 1} color="#ff9f0a">
          <b><CountUp value={entered ? Math.round((paid / entered) * 100) : 0} />%</b>
          <small>оплатили</small>
        </Ring>
        <dl>
          <div><dt>Пришли</dt><dd><CountUp value={entered} /></dd></div>
          <div><dt>Подключились</dt><dd><CountUp value={connected} /></dd></div>
          <div><dt>Оплатили</dt><dd><CountUp value={paid} /></dd></div>
        </dl>
      </div>
    </Widget>
  );
}

function PaySoonWidget({ pay }: { pay: Data }) {
  const navigate = useNavigate();
  const people: Data[] = (pay?.people || []).slice(0, 5);
  return (
    <Widget title="Скоро закончится баланс" icon={<Hourglass />} tone="#af52de">
      {people.length ? (
        <ul className="adm-people">
          {people.map((p) => (
            <li key={p.telegram_id}>
              <button type="button" onClick={() => navigate("users?q=" + p.telegram_id)}>
                <Avatar row={p} />
                <span className="adm-p-name">
                  <b>{who(p)}</b>
                  <small>{p.reason || "Баланс заканчивается"}</small>
                </span>
                <span className="adm-p-val">
                  <b>{money(p.balance_rub)}</b>
                  <small>{p.days_left == null ? "—" : `≈ ${p.days_left} дн.`}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {people.length > 0 && Number(pay?.total || 0) > people.length && (
        <p className="adm-sub mt-2">И ещё {Number(pay.total) - people.length} — пользуются VPN регулярно, денег на 3 дня или меньше</p>
      )}
      {!people.length && (
        <div className="adm-calm"><span>✨</span><b>Никого</b><small>У всех, кто регулярно пользуется VPN, денег больше чем на 3 дня</small></div>
      )}
    </Widget>
  );
}

/** When the gift ends, in plain words: «через 5 ч», «завтра», «через 2 дн.», or «кончился 3 ч назад». */
function trialWhen(p: Data): string {
  const t = Date.parse(String(p.ends_at || ""));
  if (isNaN(t)) return "—";
  const h = Math.round((t - Date.now()) / 3600000);
  if (p.ended || h <= 0) {
    const ago = Math.max(0, -h);
    return ago < 1 ? "только что" : ago < 24 ? `${ago} ч назад` : `${Math.round(ago / 24)} дн. назад`;
  }
  if (h < 24) return `через ${h} ч`;
  const d = Math.round(h / 24);
  return d === 1 ? "через сутки" : `через ${d} дн.`;
}

const TRIAL_SHOWN = 5;

function TrialEndingWidget({ trial }: { trial: Data }) {
  const navigate = useNavigate();
  const all: Data[] = trial?.people || [];
  const [open, setOpen] = useState(false);
  const people = open ? all : all.slice(0, TRIAL_SHOWN);
  const ending = Number(trial?.ending || 0), waiting = Number(trial?.waiting || 0);
  return (
    <Widget title="Заканчивается подарок" icon={<Gift />} tone="#ff2d55">
      <p className="adm-sub">
        Ни разу не платили · ждём оплату <b>{waiting}</b> · кончится за {Number(trial?.days || 3)} дн. <b>{ending}</b>
      </p>
      {people.length ? (
        <ul className="adm-people mt-2">
          {people.map((p) => (
            <li key={p.telegram_id}>
              <button type="button" onClick={() => navigate("users?q=" + p.telegram_id)}>
                <Avatar row={p} />
                <span className="adm-p-name">
                  <b>{who(p)}</b>
                  <small>{p.ended ? (p.checkout ? "Открывал оплату" : "Ждём оплату") : p.checkout ? "Открывал оплату" : `Осталось ${money(p.balance_rub)}`}</small>
                </span>
                <span className="adm-p-val">
                  <b>{trialWhen(p)}</b>
                  <small>{p.ended ? "кончился" : "кончится"}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="adm-calm"><span>✨</span><b>Никого</b><small>Ни у кого подарок не кончается в ближайшие дни и никто не ждёт оплаты</small></div>
      )}
      {all.length > TRIAL_SHOWN && (
        <button type="button" className="adm-more" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? "Свернуть" : `Показать всех · ${all.length}`}
          <ChevronDown className={"size-4" + (open ? " rotate-180" : "")} />
        </button>
      )}
    </Widget>
  );
}

export const ago = (v: unknown) => {
  const t = Date.parse(String(v || ""));
  if (isNaN(t)) return "—";
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (m < 1) return "только что";
  if (m < 60) return m + " мин назад";
  const h = Math.round(m / 60);
  if (h < 24) return h + " ч назад";
  return Math.round(h / 24) + " дн назад";
};

const WD = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];

/** People who really use the VPN every day (online_days): the week as seven dots, streak and balance. */
const DAILY_SHOWN = 6;

function DailyUsersWidget({ daily }: { daily: Data }) {
  const navigate = useNavigate();
  const all: Data[] = daily?.people || [];
  const [open, setOpen] = useState(false);
  const people = open ? all : all.slice(0, DAILY_SHOWN);
  const labels = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - (6 - i));
    return i === 6 ? "сег" : WD[d.getUTCDay()];
  });
  return (
    <Widget title="Пользуются каждый день" icon={<Flame />} tone="#ff9500" action="Все пользователи" onAction={() => navigate("users")} className="adm-span2">
      <div className="adm-daily-k">
        <div>
          <b><CountUp value={Number(daily?.every_day || 0)} /></b>
          <small>каждый день<br />за неделю</small>
        </div>
        <div>
          <b><CountUp value={Number(daily?.most_days || 0)} /></b>
          <small>5–6 дней<br />из 7</small>
        </div>
        <div>
          <b><CountUp value={Number(daily?.today || 0)} /></b>
          <small>были онлайн<br />сегодня</small>
        </div>
      </div>
      {people.length ? (
        <ul className="adm-people adm-feed">
          {people.map((p) => (
            <li key={p.telegram_id}>
              <button type="button" onClick={() => navigate("users?q=" + p.telegram_id)}>
                <Avatar row={p} />
                <span className="adm-p-name">
                  <b>{who(p)}</b>
                  <small>{p.streak >= 2 ? `🔥 ${p.streak} ${p.streak % 10 === 1 && p.streak % 100 !== 11 ? "день" : p.streak % 10 >= 2 && p.streak % 10 <= 4 && (p.streak % 100 < 10 || p.streak % 100 >= 20) ? "дня" : "дней"} подряд` : `${p.week} из 7 дней`} · баланс {money(p.balance_rub)}</small>
                </span>
                <span className="adm-daily-w" aria-label={`Онлайн ${p.week} из 7 дней`}>
                  {(p.days || []).map((on: boolean, i: number) => (
                    <i key={i} className={on ? "on" : ""} title={labels[i]} />
                  ))}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="adm-calm"><span>🌱</span><b>Пока никого</b><small>Здесь появятся те, кто включает VPN 5 дней из 7 и чаще</small></div>
      )}
      {all.length > DAILY_SHOWN && (
        <button type="button" className="adm-more" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? "Свернуть" : `Показать всех · ${all.length.toLocaleString("ru-RU")}`}
          <ChevronDown className={"size-4" + (open ? " rotate-180" : "")} />
        </button>
      )}
    </Widget>
  );
}

const hours = (h: number) => (h < 10 ? h.toLocaleString("ru-RU", { maximumFractionDigits: 1 }) : Math.round(h).toLocaleString("ru-RU")) + " ч";

/** Friends who came by someone's link over 30 days: how far they got, bonuses paid out, the best inviters. */
function ReferralsWidget({ refs }: { refs: Data }) {
  const navigate = useNavigate();
  const people: Data[] = refs?.people || [];
  const month = Number(refs?.month || 0);
  return (
    <Widget title="Рефералы за 30 дней" icon={<UserPlus />} tone="#34c759">
      <div className="adm-big">
        <CountUp value={month} />
        <span className="adm-unit">друзей пришло</span>
      </div>
      <p className="adm-sub">{Number(refs?.week || 0).toLocaleString("ru-RU")} за неделю · {Number(refs?.total || 0).toLocaleString("ru-RU")} за всё время · выплачено бонусов {money(Number(refs?.paid_out_rub || 0))}</p>
      <dl className="adm-steps">
        <div><dt>Дошли до меню</dt><dd><CountUp value={Number(refs?.menu || 0)} /></dd></div>
        <div><dt>Подключили VPN</dt><dd><CountUp value={Number(refs?.connected || 0)} /></dd></div>
        <div><dt>Оплатили</dt><dd><CountUp value={Number(refs?.paid || 0)} /></dd></div>
      </dl>
      {people.length > 0 && (
        <ul className="adm-people adm-feed mt-2">
          {people.map((p) => (
            <li key={p.telegram_id}>
              <button type="button" onClick={() => navigate("users?q=" + p.telegram_id)}>
                <Avatar row={p} />
                <span className="adm-p-name">
                  <b>{who(p)}</b>
                  <small>подключили {p.connected} · оплатили {p.paid}</small>
                </span>
                <span className="adm-p-val"><b>{p.friends}</b><small>друзей</small></span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Widget>
  );
}

const RARITY_TONE: Record<string, string> = { l: "#ff9500", e: "#af52de", r: "#3e88f7", u: "#2fb46a", c: "var(--muted-foreground)" };

/** Кейсы с лягушкой: opened today / week / month, given and still waiting, the latest openings. */
function FrogCasesWidget({ cases }: { cases: Data }) {
  const navigate = useNavigate();
  const recent: Data[] = cases?.recent || [];
  const given: Data = cases?.given || {};
  const src = [["topup", "за пополнения"], ["subscription", "за подписку"], ["admin", "вручную"]]
    .filter(([k]) => Number(given[k] || 0) > 0).map(([k, l]) => `${given[k]} ${l}`);
  return (
    <Widget title="Кейсы с лягушкой" icon={<Gift />} tone="#2fb46a">
      <div className="adm-daily-k">
        <div><b><CountUp value={Number(cases?.today || 0)} /></b><small>открыли<br />сегодня</small></div>
        <div><b><CountUp value={Number(cases?.week || 0)} /></b><small>за 7 дней,<br />людей {Number(cases?.people_week || 0)}</small></div>
        <div><b><CountUp value={Number(cases?.month || 0)} /></b><small>за 30<br />дней</small></div>
      </div>
      <p className="adm-sub">
        Выдано за неделю {Number(cases?.given_week || 0).toLocaleString("ru-RU")}{src.length ? ` (${src.join(", ")})` : ""} · ждут открытия {Number(cases?.waiting || 0).toLocaleString("ru-RU")} у {Number(cases?.waiting_people || 0).toLocaleString("ru-RU")} чел.
      </p>
      {recent.length ? (
        <ul className="adm-people adm-feed mt-2">
          {recent.map((o, i) => (
            <li key={i}>
              <button type="button" onClick={() => navigate("users?q=" + o.telegram_id)}>
                <Avatar row={o} />
                <span className="adm-p-name">
                  <b>{who(o)}</b>
                  <small>{ago(o.at)}</small>
                </span>
                <span className="adm-p-val">
                  <b>{o.frog}</b>
                  <small style={{ color: RARITY_TONE[o.rarity] }}>{o.rarity_label}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="adm-calm"><span>🐸</span><b>Пока не открывали</b><small>Здесь появятся последние открытые кейсы</small></div>
      )}
    </Widget>
  );
}

/** Cabinet opens and the hours people spent in it, per day for two weeks. */
function CabinetWidget({ cab }: { cab: Data }) {
  const days: Data[] = cab?.days || [];
  const today: Data = cab?.today || {}, week: Data = cab?.week || {}, month: Data = cab?.month || {};
  const since = cab?.since ? new Date(cab.since).toLocaleDateString("ru-RU", { day: "numeric", month: "long" }) : null;
  return (
    <Widget title="Личный кабинет" icon={<AppWindow />} tone="#5ac8fa">
      <div className="adm-daily-k">
        <div><b><CountUp value={Number(today.opens || 0)} /></b><small>открытий сегодня,<br />людей {Number(today.people || 0)}</small></div>
        <div><b><CountUp value={Number(week.opens || 0)} /></b><small>за 7 дней,<br />людей {Number(week.people || 0)}</small></div>
        <div><b><CountUp value={Number(week.hours || 0)} format={(n) => hours(n)} /></b><small>провели в нём<br />за 7 дней</small></div>
      </div>
      <p className="adm-sub">Сегодня {hours(Number(today.hours || 0))} · за 30 дней {Number(month.opens || 0).toLocaleString("ru-RU")} открытий и {hours(Number(month.hours || 0))}{since ? ` · считаем с ${since}` : " · считаем с выкладки"}</p>
      <div className="adm-chart">
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={days} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
            <XAxis dataKey="day" hide />
            <Tooltip content={<CabinetTip />} cursor={{ fill: "var(--secondary)", radius: 6 } as any} />
            <Bar dataKey="opens" fill="#5ac8fa" radius={[6, 6, 6, 6]} animationDuration={900} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Widget>
  );
}

function CabinetTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d: Data = payload[0].payload || {};
  return (
    <div className="adm-tip">
      <small>{dayLabel(label)}</small>
      <b>{Number(d.opens || 0).toLocaleString("ru-RU")} открытий</b>
      <small>людей {Number(d.people || 0)} · {hours(Number(d.hours || 0))}</small>
    </div>
  );
}

/** Share of new people with VPN working in their first 24 hours: the last 7 finished days, the week before, and per day. */
function ActivationWidget({ act }: { act: Data }) {
  const week: Data = act?.week || {}, prev: Data = act?.prev || {};
  const days: Data[] = act?.days || [];
  const pct = week.pct == null ? null : Number(week.pct);
  const delta = pct != null && prev.pct != null ? pct - Number(prev.pct) : null;
  return (
    <Widget title="Подключились в первые сутки" icon={<Plug />} tone="#2fb46a">
      <div className="adm-act">
        <b className="adm-sleep-n">{pct == null ? "—" : <><CountUp value={pct} />%</>}</b>
        {delta != null && delta !== 0 && (
          <span className={"adm-act-d " + (delta > 0 ? "up" : "down")}>
            {delta > 0 ? "▲" : "▼"} {Math.abs(delta)} п.п. к прошлой неделе
          </span>
        )}
      </div>
      <p className="adm-sub">
        {Number(week.ok || 0)} из {Number(week.new || 0)} новых за 7 дней: VPN включился и пошёл трафик в первые 24 часа
      </p>
      <div className="adm-act-bars" aria-label="По дням">
        {days.map((d) => (
          <span
            key={d.day}
            className={d.done ? "" : "wait"}
            title={`${d.day}: ${d.done ? `${d.ok} из ${d.new} (${d.pct ?? 0}%)` : `ещё не прошли сутки, пока ${d.ok} из ${d.new}`}`}
          >
            <i style={{ height: `${Math.max(4, d.done ? Number(d.pct || 0) : 100)}%` }} />
          </span>
        ))}
      </div>
      <p className="adm-sub">14 дней по дате прихода · серые — сутки ещё не прошли</p>
    </Widget>
  );
}

function Bars({ rows }: { rows: [string, number][] }) {
  const max = Math.max(1, ...rows.map(([, n]) => n));
  return (
    <ul className="adm-sleep-bars">
      {rows.map(([label, n]) => (
        <li key={label}>
          <span>{label}</span>
          <b>{n}</b>
          <i style={{ width: `${(n / max) * 100}%` }} />
        </li>
      ))}
    </ul>
  );
}

/** «Спящие»: never online, never paid, the bot no longer writes to them; who they are. */
function SleepersWidget({ sleep }: { sleep: Data }) {
  const navigate = useNavigate();
  return (
    <Widget title="Спящие" icon={<Moon />} tone="#8e8e93" action="Рассылки" onAction={() => navigate("broadcast")} className="adm-span2">
      <div className="adm-sleep">
        <div>
          <b className="adm-sleep-n"><CountUp value={Number(sleep?.total || 0)} /></b>
          <small>ни разу не подключались и не платили — бот им больше не пишет, рассылки только с новостями</small>
          <p className="adm-sub">
            до месяца {Number(sleep?.month || 0)} · 1–3 мес. {Number(sleep?.quarter || 0)} · дольше {Number(sleep?.older || 0)}
          </p>
          {Number(sleep?.cleaned || 0) > 0 && (
            <p className="adm-sub">За 30 дней убрано из панели устройств без подключения: {Number(sleep.cleaned)}</p>
          )}
        </div>
        <div>
          <h4>Кто это</h4>
          <Bars rows={[
            ["Нет устройства", Number(sleep?.no_device || 0)],
            ["Устройство без подключения", Number(sleep?.no_online || 0)],
          ]} />
        </div>
      </div>
    </Widget>
  );
}

const AV = ["#ff6b6b", "#ff9f43", "#f7b731", "#2fb46a", "#3e88f7", "#5856d6", "#af52de", "#ff2d55"];
export function Avatar({ row, size = 36 }: { row: Data; size?: number }) {
  const name = String(row.first_name || row.username || row.telegram_id || "?");
  const ch = name.replace(/^@/, "").trim().charAt(0).toUpperCase() || "?";
  const color = AV[Math.abs(Number(row.telegram_id) || name.length) % AV.length];
  return (
    <span className="adm-avatar" style={{ width: size, height: size, background: `linear-gradient(160deg, ${color}, color-mix(in srgb, ${color} 70%, #000))`, fontSize: size * 0.42 }} aria-hidden="true">
      {ch}
    </span>
  );
}

/** The widget board shown on top of the overview page. */
export function DashboardWidgets({ s }: { s: Data }) {
  const stats = useResource("statistics?days=30");
  const series: Data[] = stats.data?.series || [];
  return (
    <div className="adm-board">
      <OnlineWidget online={s.online || {}} users={s.users || {}} />
      <ConversionWidget funnel={s.funnel || {}} />
      {series.length > 0 ? <RevenueWidget series={series} previous={stats.data?.previous} /> : <div className="adm-widget adm-span2 adm-skel" />}
      <SignupsWidget hourly={s.signups_hourly || []} users={s.users || {}} />
      <PaySoonWidget pay={s.pay_soon || {}} />
      <TrialEndingWidget trial={s.trial_ending || {}} />
      <DailyUsersWidget daily={s.daily_users || {}} />
      <ActivationWidget act={s.activation || {}} />
      <CabinetWidget cab={s.cabinet || {}} />
      <ReferralsWidget refs={s.referrals || {}} />
      <FrogCasesWidget cases={s.frog_cases || {}} />
      <SleepersWidget sleep={s.sleepers || {}} />
    </div>
  );
}

/** Tiny SVG sparkline (no chart library) that draws itself in. */
export function Spark({ values, color = "var(--primary)", height = 36 }: { values: number[]; color?: string; height?: number }) {
  const w = 120, h = height, n = values.length;
  if (n < 2) return null;
  const max = Math.max(...values, 1), min = Math.min(...values, 0);
  const pts = values.map((v, i) => [(i / (n - 1)) * w, h - 3 - ((v - min) / (max - min || 1)) * (h - 6)]);
  const line = pts.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + "," + y.toFixed(1)).join(" ");
  const id = "sp" + Math.abs(values.reduce((a, v, i) => a + v * (i + 1), n)).toString(36);
  return (
    <svg className="adm-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.35} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={`${line} L${w},${h} L0,${h} Z`} fill={`url(#${id})`} className="adm-spark-fill" />
      <path d={line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" pathLength={1} className="adm-spark-line" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
