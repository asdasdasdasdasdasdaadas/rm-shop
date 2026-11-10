// Dashboard widgets in the cabinet style: count-up numbers, rings, sparkline charts and an action queue.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Area, AreaChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import {
  ArrowRight,
  BadgeRussianRuble,
  CircleCheck,
  Hourglass,
  LifeBuoy,
  Radio,
  Users as UsersIcon,
  Wallet,
  TriangleAlert,
} from "lucide-react";
import { money, useResource, who, type Data } from "@/lib/api";
import { useNavigate } from "./workspace";

const reduced = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Animates from the previous value to the new one with an ease-out curve. */
export function useCountUp(value: number, ms = 900) {
  const [shown, setShown] = useState(reduced() ? value : 0);
  const from = useRef(0);
  useEffect(() => {
    if (reduced()) return setShown(value);
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
export function Delta({ now, prev, suffix = "к прошлым суткам" }: { now: number; prev: number; suffix?: string }) {
  if (!prev && !now) return null;
  const pct = prev ? Math.round(((now - prev) / prev) * 100) : 100;
  const up = pct >= 0;
  return (
    <span className={"adm-delta " + (up ? "up" : "down")} title={suffix}>
      {up ? "↑" : "↓"} {Math.abs(pct)}%
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

function RevenueWidget({ series }: { series: Data[] }) {
  const navigate = useNavigate();
  const total = series.reduce((a, r) => a + Number(r.rub || 0), 0);
  const pays = series.reduce((a, r) => a + Number(r.payments || 0), 0);
  const last7 = series.slice(-7).reduce((a, r) => a + Number(r.rub || 0), 0);
  const prev7 = series.slice(-14, -7).reduce((a, r) => a + Number(r.rub || 0), 0);
  return (
    <Widget title="Выручка за 30 дней" icon={<BadgeRussianRuble />} tone="#22975a" action="Финансы" onAction={() => navigate("finance")} className="adm-span2">
      <div className="adm-big">
        <CountUp value={total} format={(n) => money(Math.round(n))} />
        <Delta now={last7} prev={prev7} suffix="последние 7 дней к предыдущим" />
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

function SignupsWidget({ series, users }: { series: Data[]; users: Data }) {
  const navigate = useNavigate();
  return (
    <Widget title="Новые пользователи" icon={<UsersIcon />} tone="#3e88f7" action="Клиенты" onAction={() => navigate("users")}>
      <div className="adm-big">
        <CountUp value={Number(users.new_1d || 0)} />
        <span className="adm-unit">за сутки</span>
      </div>
      <p className="adm-sub">{Number(users.new_7d || 0).toLocaleString("ru-RU")} за неделю · {Number(users.new_30d || 0).toLocaleString("ru-RU")} за месяц</p>
      <div className="adm-chart">
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={series.slice(-14)} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
            <XAxis dataKey="day" hide />
            <Tooltip content={<ChartTip unit="" />} cursor={{ fill: "var(--secondary)", radius: 6 } as any} />
            <Bar dataKey="registered" fill="#3e88f7" radius={[6, 6, 6, 6]} animationDuration={900} />
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
          <div><dt>Сутки</dt><dd><CountUp value={day} /> <Delta now={day} prev={Number(online.day_prev || 0)} /></dd></div>
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
    <Widget title="Конверсия за 30 дней" icon={<CircleCheck />} tone="#ff9500" action="Воронка" onAction={() => navigate("statistics")}>
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

function QueueWidget({ s }: { s: Data }) {
  const navigate = useNavigate();
  const items = [
    { n: Number(s.tickets_open || 0), label: "Открытых обращений", icon: <LifeBuoy />, tone: "#ff9500", go: "tickets" },
    { n: Number(s.users?.payouts_pending || 0), label: "Заявок на выплату", icon: <Wallet />, tone: "#ff2d55", go: "referrals" },
    { n: Number(s.billing_today?.errors || 0), label: "Ошибок списания сегодня", icon: <TriangleAlert />, tone: "#ef4444", go: "billing" },
  ];
  const busy = items.filter((i) => i.n > 0);
  return (
    <Widget title="Требует внимания" icon={<TriangleAlert />} tone="#ef4444">
      {busy.length ? (
        <ul className="adm-queue">
          {busy.map((i) => (
            <li key={i.label}>
              <button type="button" onClick={() => navigate(i.go)}>
                <span className="adm-tile" style={{ background: i.tone }}>{i.icon}</span>
                <span className="adm-q-label">{i.label}</span>
                <b className="adm-q-n"><CountUp value={i.n} /></b>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="adm-calm">
          <span>🐸</span>
          <b>Всё спокойно</b>
          <small>Нет обращений, выплат и ошибок</small>
        </div>
      )}
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
        <p className="adm-sub mt-2">И ещё {Number(pay.total) - people.length} — баланс на 3 дня или меньше</p>
      )}
      {!people.length && (
        <div className="adm-calm"><span>✨</span><b>Никого</b><small>У всех онлайн-пользователей баланс больше чем на 3 дня</small></div>
      )}
    </Widget>
  );
}

const ago = (v: unknown) => {
  const t = Date.parse(String(v || ""));
  if (isNaN(t)) return "—";
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (m < 1) return "только что";
  if (m < 60) return m + " мин назад";
  const h = Math.round(m / 60);
  if (h < 24) return h + " ч назад";
  return Math.round(h / 24) + " дн назад";
};

function PaymentsWidget() {
  const navigate = useNavigate();
  const res = useResource("orders?status=granted&limit=6", 60000);
  const rows: Data[] = res.data?.items || [];
  return (
    <Widget title="Последние оплаты" icon={<Wallet />} tone="#34aadc" action="Все платежи" onAction={() => navigate("orders")} className="adm-span2">
      {!res.data ? (
        <div className="adm-skel-rows">{[0, 1, 2, 3].map((i) => <i key={i} />)}</div>
      ) : rows.length ? (
        <ul className="adm-people adm-feed">
          {rows.map((r) => (
            <li key={r.order_id}>
              <button type="button" onClick={() => navigate("users?q=" + r.telegram_id)}>
                <Avatar row={r} />
                <span className="adm-p-name">
                  <b>{who(r)}</b>
                  <small>{ago(r.paid_at || r.created_at)}</small>
                </span>
                <span className="adm-pay-sum">+{money(r.amount_rub)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="adm-calm"><span>💸</span><b>Пока нет оплат</b><small>Здесь появятся последние пополнения</small></div>
      )}
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
      <QueueWidget s={s} />
      <OnlineWidget online={s.online || {}} users={s.users || {}} />
      <ConversionWidget funnel={s.funnel || {}} />
      {series.length > 0 ? <RevenueWidget series={series} /> : <div className="adm-widget adm-span2 adm-skel" />}
      {series.length > 0 ? <SignupsWidget series={series} users={s.users || {}} /> : <div className="adm-widget adm-skel" />}
      <PaySoonWidget pay={s.pay_soon || {}} />
      <PaymentsWidget />
    </div>
  );
}
