import React, {
  Component,
  Suspense,
  lazy,
  useEffect,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";
import { createRoot } from "react-dom/client";
import { api, useResource } from "@/lib/api";
import {
  ConfirmProvider,
  Failure,
  Loading,
  Navigation,
  useConfirm,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Separator } from "@/components/ui/separator";
import { Toaster } from "sonner";
import {
  LayoutDashboard,
  Users,
  CreditCard,
  Gem,
  Receipt,
  LifeBuoy,
  Megaphone,
  Handshake,
  Send,
  MessagesSquare,
  Settings,
  DatabaseBackup,
  Search,
  Moon,
  Sun,
  Menu,
  LogOut,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { OverviewPage } from "@/pages/overview";
// Every other section is its own file, fetched when first opened (or when its menu item is hovered).
const RELOADED = "admin-chunk-reload";
function section<T extends Record<string, unknown>>(load: () => Promise<T>) {
  let pending: Promise<T> | null = null;
  const get = () =>
    (pending ||= load().then(
      (m) => {
        try { sessionStorage.removeItem(RELOADED); } catch {}
        return m;
      },
      (e) => {
        pending = null;
        // After a deploy the old page asks for pieces that are gone: reload once to get the new ones.
        try {
          if (!sessionStorage.getItem(RELOADED)) {
            sessionStorage.setItem(RELOADED, "1");
            location.reload();
          }
        } catch {}
        throw e;
      },
    ));
  const page = <K extends keyof T>(name: K) =>
    lazy(() => get().then((m) => ({ default: m[name] as unknown as ComponentType<any> })));
  return { get, page };
}
const users = section(() => import("@/pages/users")),
  finance = section(() => import("@/pages/finance")),
  statistics = section(() => import("@/pages/statistics")),
  records = section(() => import("@/pages/records")),
  settingsPage = section(() => import("@/pages/settings")),
  marketing = section(() => import("@/pages/marketing")),
  communications = section(() => import("@/pages/communications"));
const UsersPage = users.page("UsersPage"),
  FinancePage = finance.page("FinancePage"),
  StatisticsPage = statistics.page("StatisticsPage"),
  RecordsPage = records.page("RecordsPage"),
  BackupsPage = records.page("BackupsPage"),
  TonPage = records.page("TonPage"),
  SettingsPage = settingsPage.page("SettingsPage"),
  AdsPage = marketing.page("AdsPage"),
  ReferralsPage = marketing.page("ReferralsPage"),
  BroadcastPage = communications.page("BroadcastPage");
const PRELOAD: Record<string, () => Promise<unknown>> = {
  statistics: statistics.get, users: users.get, finance: finance.get, settings: settingsPage.get,
  ads: marketing.get, referrals: marketing.get, broadcast: communications.get,
  tickets: records.get, orders: records.get, billing: records.get, messages: records.get, ton: records.get, backups: records.get,
};
import "./theme.css";
// Telegram-settings style: every section gets its own coloured tile.
const TILE: Record<string, string> = {
  statistics: "#3e88f7", overview: "#5856d6", users: "#2fb46a", tickets: "#ff9500",
  finance: "#22975a", orders: "#34aadc", ton: "#30a1f5", billing: "#8e8e93",
  referrals: "#ff2d55", ads: "#af52de", broadcast: "#007aff",
  messages: "#ff9f0a", settings: "#636366", backups: "#a2845e",
};
const sections = [
  {
    id: "statistics",
    label: "Статистика",
    description: "Динамика сервиса, платежи и конверсия",
    group: "Аналитика",
    icon: LayoutDashboard,
  },
  {
    id: "overview",
    label: "Обзор",
    description: "Показатели сервиса и задачи, требующие внимания",
    group: "Работа с клиентами",
    icon: LayoutDashboard,
  },
  {
    id: "users",
    label: "Клиенты",
    description: "Найдите пользователя и решите вопрос с доступом или оплатой",
    group: "Работа с клиентами",
    icon: Users,
  },
  {
    id: "tickets",
    label: "Поддержка",
    description: "Обращения клиентов и переписка с поддержкой",
    group: "Работа с клиентами",
    icon: LifeBuoy,
  },
  {
    id: "finance",
    label: "Финансы",
    description: "Платежи, предстоящие продления и план дохода",
    group: "Финансы",
    icon: CreditCard,
  },
  {
    id: "orders",
    label: "Платежи",
    description: "Счета и успешные оплаты пользователей",
    group: "Финансы",
    icon: CreditCard,
  },
  {
    id: "ton",
    label: "Оплата в TON",
    description: "Платежи из кошелька Telegram и неопознанные переводы",
    group: "Финансы",
    icon: Gem,
  },
  {
    id: "billing",
    label: "Операции по балансу",
    description: "Списания, начисления и история изменения баланса",
    group: "Финансы",
    icon: Receipt,
  },
  {
    id: "referrals",
    label: "Реферальная программа",
    description: "Приглашения друзей и награды на баланс",
    group: "Привлечение и возврат",
    icon: Handshake,
  },
  {
    id: "ads",
    label: "Источники трафика",
    description: "Рекламные ссылки и конверсия привлечённых клиентов",
    group: "Привлечение и возврат",
    icon: Megaphone,
  },
  {
    id: "broadcast",
    label: "Рассылки",
    description: "Подготовьте сообщение для нужной аудитории",
    group: "Коммуникации",
    icon: Send,
  },
  {
    id: "messages",
    label: "Журнал доставки",
    description: "Проверяйте сообщения, ошибки и повторные отправки",
    group: "Коммуникации",
    icon: MessagesSquare,
  },
  {
    id: "settings",
    label: "Настройки",
    description: "Тарифы, доступ и тексты бота",
    group: "Управление",
    icon: Settings,
  },
  {
    id: "backups",
    label: "Резервные копии",
    description: "Создание, скачивание и восстановление базы данных",
    group: "Управление",
    icon: DatabaseBackup,
  },
];
const groups = [...new Set(sections.map((s) => s.group))];
function readRoute() {
  const raw =
    location.hash.slice(1) ||
    (location.pathname.endsWith("/stats")
      ? "statistics"
      : location.pathname.endsWith("/promo")
        ? "promo"
        : "overview");
  return sections.some((s) => s.id === raw.split("?")[0]) ? raw : "overview";
}
class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: string }
> {
  state = { error: "" };
  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }
  render() {
    return this.state.error ? (
      <Failure
        message="Не удалось открыть раздел. Обновите страницу; введённые на других экранах данные не изменены."
        retry={() => location.reload()}
      />
    ) : (
      this.props.children
    );
  }
}
function Admin() {
  const [auth, setAuth] = useState<boolean | null>(null),
    [brand, setBrand] = useState("VPN"),
    [theme, setTheme] = useState<"light" | "dark">(() =>
      localStorage.getItem("way-admin-theme") === "light" ? "light" : "dark",
    ),
    [password, setPassword] = useState(""),
    [loginError, setLoginError] = useState(""),
    [busy, setBusy] = useState(false),
    [sessionError, setSessionError] = useState("");
  const session = async () => {
    setSessionError("");
    try {
      const data = await api("session");
      setBrand(data.brand || "VPN");
      setAuth(true);
    } catch (e) {
      if (
        (e as Error).message.includes("авторизац") ||
        (e as Error).message.includes("(401)")
      )
        setAuth(false);
      else setSessionError((e as Error).message);
    }
  };
  useEffect(() => {
    void session();
    const unauthorized = () => setAuth(false);
    window.addEventListener("admin:unauthorized", unauthorized);
    return () => window.removeEventListener("admin:unauthorized", unauthorized);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("way-admin-theme", theme);
  }, [theme]);
  return (
    <>
      <Toaster
        theme={theme}
        richColors
        closeButton
        position="bottom-right"
        style={
          {
            "--success-text": theme === "light" ? "#166534" : "#86efac",
            "--error-text": theme === "light" ? "#991b1b" : "#fca5a5",
            "--info-text": theme === "light" ? "#1e40af" : "#93c5fd",
            "--warning-text": theme === "light" ? "#854d0e" : "#fde68a",
          } as React.CSSProperties
        }
      />
      <ConfirmProvider>
        {auth === true ? (
          <Workspace
            brand={brand}
            theme={theme}
            toggleTheme={() =>
              setTheme((t) => (t === "light" ? "dark" : "light"))
            }
            logout={async () => {
              await api("logout", {});
              setAuth(false);
              setPassword("");
            }}
          />
        ) : (
          <main className="adm-login min-h-dvh grid place-items-center p-6">
            {auth === null && !sessionError ? (
              <div className="w-80">
                <Loading />
              </div>
            ) : sessionError ? (
              <div className="max-w-md">
                <Failure message={sessionError} retry={session} />
              </div>
            ) : (
              <Card className="w-full max-w-sm">
                <CardHeader>
                  <img src="/icons/frog.png" alt="" className="adm-frog size-16 mb-5" />
                  <CardTitle className="text-2xl font-extrabold">Панель управления</CardTitle>
                  <CardDescription>
                    Войдите для работы с клиентами и сервисом.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form
                    className="space-y-4"
                    onSubmit={async (e) => {
                      e.preventDefault();
                      if (busy) return;
                      setBusy(true);
                      setLoginError("");
                      try {
                        const data = await api("login", { password });
                        setBrand(data.brand || "VPN");
                        setAuth(true);
                        setPassword("");
                      } catch (e) {
                        setLoginError((e as Error).message);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    <div className="space-y-2">
                      <Label htmlFor="admin-password">Пароль</Label>
                      <Input
                        id="admin-password"
                        type="password"
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoFocus
                      />
                    </div>
                    {loginError && (
                      <p role="alert" className="text-destructive text-sm">
                        {loginError}
                      </p>
                    )}
                    <Button className="w-full" disabled={busy} type="submit">
                      {busy && <Loader2 className="animate-spin" />}Войти
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}
          </main>
        )}
      </ConfirmProvider>
    </>
  );
}
function Workspace({
  brand,
  theme,
  toggleTheme,
  logout,
}: {
  brand: string;
  theme: string;
  toggleTheme: () => void;
  logout: () => Promise<void>;
}) {
  const [route, setRoute] = useState(readRoute),
    [mobile, setMobile] = useState(false),
    [command, setCommand] = useState(false);
  const dirty = useRef(false),
    routeRef = useRef(route),
    confirm = useConfirm();
  const current =
    sections.find((s) => s.id === route.split("?")[0]) || sections[0];
  const commit = (path: string) => {
    routeRef.current = path;
    history.pushState(null, "", "#" + path);
    setRoute(path);
    setMobile(false);
    setCommand(false);
    document.getElementById("workspace-main")?.scrollTo(0, 0);
  };
  const navigate = (path: string) => {
    if (path === routeRef.current) {
      setMobile(false);
      return;
    }
    if (dirty.current)
      confirm({
        title: "Несохранённые изменения",
        description:
          "При переходе введённые изменения будут потеряны. Вернитесь и сохраните их или продолжите без сохранения.",
        label: "Перейти без сохранения",
        action: async () => {
          dirty.current = false;
          commit(path);
        },
      });
    else commit(path);
  };
  useEffect(() => {
    const onDirty = (e: Event) => {
      dirty.current = !!(e as CustomEvent).detail;
    };
    const onHash = () => {
      const next = readRoute();
      if (dirty.current) {
        history.replaceState(null, "", "#" + routeRef.current);
        navigate(next);
      } else {
        setRoute(next);
        routeRef.current = next;
      }
    };
    const key = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommand((v) => !v);
      }
    };
    window.addEventListener("admin:dirty", onDirty);
    window.addEventListener("hashchange", onHash);
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("admin:dirty", onDirty);
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("keydown", key);
    };
  }, []);
  // Live counters on the menu from a cheap endpoint (the full «stats» is heavy): open tickets, payouts,
  // payments that came short and were not credited, billing errors today.
  const live = useResource("badges", 60000).data;
  const badge: Record<string, number> = {
    tickets: Number(live?.tickets_open || 0),
    referrals: Number(live?.payouts_pending || 0),
    orders: Number(live?.mismatch_orders || 0),
    billing: Number(live?.billing_errors || 0),
  };
  const badgeHint: Record<string, string> = {
    tickets: "открытых обращений",
    referrals: "заявок на выплату",
    orders: "оплат с несовпавшей суммой за 30 дней",
    billing: "ошибок списания сегодня",
  };
  const waiting = Object.values(badge).reduce((a, n) => a + n, 0);
  useEffect(() => {
    document.title = (waiting ? `(${waiting}) ` : "") + `${current.label} · ${brand}`;
  }, [waiting, current.label, brand]);
  const [search, setSearch] = useState("");
  const person = search.trim().replace(/^@/, "");
  const personLike = /^\d{3,}$/.test(person) || (/^[a-zA-Z][\w]{3,}$/.test(person) && search.trim().startsWith("@"));
  const nav = (
    <div className="flex min-h-full flex-col">
      <div className="flex items-center gap-3 px-3 py-5">
        <img src="/icons/frog.png" alt="" className="adm-frog" />
        <div className="min-w-0">
          <p className="font-semibold truncate">{brand}</p>
          <p className="text-xs text-muted-foreground">Управление сервисом</p>
        </div>
      </div>
      <nav aria-label="Разделы админки" className="space-y-5 flex-1 pb-6">
        {groups.map((group) => (
          <div key={group}>
            <p className="px-3 text-[11px] font-medium text-muted-foreground mb-2">
              {group}
            </p>
            <div className="space-y-1">
              {sections
                .filter((s) => s.group === group)
                .map((s) => (
                  <Button
                    key={s.id}
                    variant={s.id === current.id ? "secondary" : "ghost"}
                    className="w-full justify-start h-10 px-2 text-[13px] gap-3 rounded-[12px]"
                    aria-current={s.id === current.id ? "page" : undefined}
                    onClick={() => navigate(s.id)}
                    onPointerEnter={() => void PRELOAD[s.id]?.().catch(() => {})}
                    onFocus={() => void PRELOAD[s.id]?.().catch(() => {})}
                  >
                    <span className="adm-tile" style={{ background: TILE[s.id] || "#6b7280" }}>
                      <s.icon />
                    </span>
                    <span className="truncate">{s.label}</span>
                    {badge[s.id] > 0 && (
                      <span
                        className={"adm-badge" + (s.id === "orders" || s.id === "billing" ? " adm-badge-warn" : "")}
                        title={`${badge[s.id]} ${badgeHint[s.id]}`}
                      >
                        {badge[s.id]}
                        <span className="sr-only"> {badgeHint[s.id]}</span>
                      </span>
                    )}
                  </Button>
                ))}
            </div>
          </div>
        ))}
      </nav>
      <Separator />
      <Button
        variant="ghost"
        className="justify-start my-3"
        onClick={() =>
          confirm({
            title: "Выйти из админки?",
            description: dirty.current
              ? "Несохранённые изменения будут потеряны."
              : "Для следующего входа потребуется пароль.",
            label: "Выйти",
            action: logout,
          })
        }
      >
        <LogOut />
        Выйти
      </Button>
    </div>
  );
  const params = new URLSearchParams(route.split("?")[1] || "");
  let page: ReactNode;
  switch (current.id) {
    case "finance":
      page = <FinancePage />;
      break;
    case "statistics":
      page = <StatisticsPage />;
      break;
    case "overview":
      page = <OverviewPage />;
      break;
    case "users":
      page = <UsersPage />;
      break;
    case "settings":
      page = <SettingsPage initial={params.get("section") || "general"} />;
      break;
    case "promo":
      page = <OverviewPage />;
      break;
    case "ads":
      page = <AdsPage />;
      break;
    case "referrals":
      page = <ReferralsPage />;
      break;
    case "broadcast":
      page = <BroadcastPage />;
      break;
    case "backups":
      page = <BackupsPage />;
      break;
    case "ton":
      page = <TonPage />;
      break;
    default:
      page = (
        <RecordsPage
          kind={current.id as "orders" | "billing" | "tickets" | "messages"}
        />
      );
  }
  return (
    <Navigation.Provider value={navigate}>
      <div className="min-h-dvh lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="hidden lg:block sticky top-0 h-dvh overflow-y-auto bg-card px-3">
          {nav}
        </aside>
        <div className="min-w-0">
          <header className="sticky top-0 z-30 flex items-center justify-between gap-4 bg-background/80 backdrop-blur-xl px-4 sm:px-8 h-16">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden"
                aria-label="Открыть меню"
                onClick={() => setMobile(true)}
              >
                <Menu />
              </Button>
              <span className="text-sm text-muted-foreground hidden sm:block">
                {current.group}
              </span>
              <ChevronRight className="size-4 text-muted-foreground hidden sm:block" />
              <span className="text-sm font-medium truncate">
                {current.label}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCommand(true)}
                aria-label="Поиск по админке"
              >
                <Search />
                <span className="hidden md:inline">Поиск</span>
                <kbd className="text-xs text-muted-foreground hidden md:inline ml-5">
                  ⌘ K
                </kbd>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label="Переключить тему"
              >
                {theme === "light" ? <Moon /> : <Sun />}
              </Button>
            </div>
          </header>
          <main
            id="workspace-main"
            className="max-w-[1600px] mx-auto p-4 sm:p-8 space-y-7"
          >
            <div>
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
                {current.label}
              </h1>
              <p className="text-sm text-muted-foreground mt-2 max-w-3xl">
                {current.description}
              </p>
            </div>
            <ErrorBoundary key={route}>
              <Suspense fallback={<Loading />}>
                <div key={route}>{page}</div>
              </Suspense>
            </ErrorBoundary>
          </main>
        </div>
      </div>
      <Sheet open={mobile} onOpenChange={setMobile}>
        <SheetContent side="left" className="w-72 overflow-y-auto p-3">
          <SheetHeader className="sr-only">
            <SheetTitle>Меню админки</SheetTitle>
            <SheetDescription>Перейдите к нужному разделу.</SheetDescription>
          </SheetHeader>
          {nav}
        </SheetContent>
      </Sheet>
      <CommandDialog
        open={command}
        onOpenChange={(open) => {
          setCommand(open);
          if (!open) setSearch("");
        }}
        title="Поиск"
        description="Раздел админки или клиент по ID и @username"
      >
        <CommandInput placeholder="Раздел, Telegram ID или @username…" value={search} onValueChange={setSearch} />
        <CommandList>
          <CommandEmpty>
            {search.trim() ? (
              <button type="button" className="text-primary underline-offset-4 hover:underline" onClick={() => navigate("users?q=" + encodeURIComponent(search.trim()))}>
                Искать «{search.trim()}» среди клиентов
              </button>
            ) : "Раздел не найден"}
          </CommandEmpty>
          {personLike && (
            <CommandGroup heading="Клиент">
              <CommandItem value={"client " + search} onSelect={() => navigate("users?q=" + encodeURIComponent(person))}>
                <Users className="size-4" />
                Открыть клиента {search.trim()}
              </CommandItem>
              <CommandItem value={"payments " + search} onSelect={() => navigate("orders?q=" + encodeURIComponent(person))}>
                <CreditCard className="size-4" />
                Платежи клиента {search.trim()}
              </CommandItem>
            </CommandGroup>
          )}
          {groups.map((group) => (
            <CommandGroup key={group} heading={group}>
              {sections
                .filter((s) => s.group === group)
                .map((s) => (
                  <CommandItem
                    key={s.id}
                    value={`${s.label} ${s.description}`}
                    onSelect={() => navigate(s.id)}
                  >
                    <s.icon className="size-4" />
                    {s.label}
                  </CommandItem>
                ))}
            </CommandGroup>
          ))}
        </CommandList>
      </CommandDialog>
    </Navigation.Provider>
  );
}
createRoot(document.getElementById("admin-root")!).render(
  <ErrorBoundary>
    <Admin />
  </ErrorBoundary>,
);
