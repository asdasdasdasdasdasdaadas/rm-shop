import {
  textError,
  titleError,
  hoursError,
  buttonError,
} from "@/lib/funnel-validation";
import {
  ButtonEditor,
  MessageEditor,
  type FunnelButton,
} from "@/components/funnel-editors";
import { useEffect, useState } from "react";
import { api, useResource } from "@/lib/api";
import { Failure, Loading, useConfirm } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { toast } from "sonner";
import {
  Plus,
  Trash2,
  GitBranch,
  MessageSquare,
  ArrowDown,
  ArrowUp,
  ArrowUpRight,
  Clock,
  Users,
  Settings2,
  Send,
  Check,
  Pencil,
  Search,
} from "lucide-react";

function previewText(text: string) {
  return text
    .replace(/<[^>]*>/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}
type Step = {
  id: string;
  condition: string;
  wait_hours: number | "";
  wait_from: "anchor" | "previous";
  text: string;
  buttons: FunnelButton[];
  enabled: boolean;
};
type Branch = { id: string; title: string; steps: Step[] };
type Graph = {
  branches: Branch[];
  main_menu?: { text: string; buttons: FunnelButton[] };
};
type Option = { id: string; label: string; hint?: string; button?: string };

const ONCE = new Set(["unpaid_invoice", "balance_low", "winback"]);

function nid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
}
function waitLabel(hours: number | "", from: string) {
  if (hours === "") return "Укажите время";
  const when =
    hours > 0 && hours % 24 === 0 ? `${hours / 24} дн.` : `${hours} ч`;
  if (!hours && from !== "previous") return "сразу";
  return from === "previous" ? `через ${when} после прошлого` : `через ${when}`;
}

export function FunnelPage() {
  const resource = useResource("funnel-board");
  const confirm = useConfirm();
  const [graph, setGraph] = useState<Graph | null>(null);
  const [saved, setSaved] = useState("");
  const [picked, setPicked] = useState<{ branch: string; step: string } | null>(
    null,
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [branchId, setBranchId] = useState("");
  const [search, setSearch] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [testing, setTesting] = useState(false);
  useEffect(() => {
    if (resource.data?.graph && !graph) {
      setGraph(resource.data.graph);
      setBranchId(resource.data.graph.branches[0]?.id || "");
      setSaved(JSON.stringify(resource.data.graph));
    }
  }, [resource.data, graph]);
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data || !graph) return <Loading />;
  const conditions = (resource.data.conditions || []) as Option[];
  const actions = (resource.data.actions || []) as Option[];
  const conditionOf = (id: string) => conditions.find((item) => item.id === id);
  const dirty = JSON.stringify(graph) !== saved;
  const selected = picked
    ? graph.branches
        .find((branch) => branch.id === picked.branch)
        ?.steps.find((step) => step.id === picked.step)
    : undefined;
  const selectedBranch = graph.branches.find(
    (branch) => branch.id === picked?.branch,
  );
  const change = (next: Graph) => {
    setGraph({ ...graph, ...next });
    setError("");
  };
  const updateBranch = (id: string, patch: Partial<Branch>) =>
    change({
      branches: graph.branches.map((branch) =>
        branch.id === id ? { ...branch, ...patch } : branch,
      ),
    });
  const updateStep = (branchId: string, stepId: string, patch: Partial<Step>) =>
    change({
      branches: graph.branches.map((branch) =>
        branch.id !== branchId
          ? branch
          : {
              ...branch,
              steps: branch.steps.map((step) =>
                step.id === stepId ? { ...step, ...patch } : step,
              ),
            },
      ),
    });
  const used = new Set(
    graph.branches.flatMap((branch) =>
      branch.steps.map((step) => step.condition),
    ),
  );
  const validateBeforeAction = (value: Graph) => {
    const issues: {
      message: string;
      branch?: string;
      step?: string;
      menu?: boolean;
    }[] = [];
    for (const b of value.branches) {
      if (titleError(b.title))
        issues.push({ message: titleError(b.title), branch: b.id });
      for (const step of b.steps) {
        const message =
          (!conditions.some((c) => c.id === step.condition)
            ? "Выберите условие отправки"
            : "") ||
          hoursError(step.wait_hours) ||
          (!["anchor", "previous"].includes(step.wait_from)
            ? "Выберите момент отсчёта паузы"
            : "") ||
          textError(step.text) ||
          step.buttons
            .map(
              (button) =>
                buttonError(
                  button,
                  actions.map((a) => a.id),
                )?.message,
            )
            .find(Boolean);
        if (message)
          issues.push({
            message: `${b.title || "Без названия"}: ${message}`,
            branch: b.id,
            step: step.id,
          });
      }
    }
    if (value.main_menu) {
      const m = value.main_menu;
      const message =
        textError(m.text) ||
        (!m.buttons.length
          ? "Добавьте хотя бы одну кнопку главного меню"
          : "") ||
        m.buttons
          .map(
            (b) =>
              buttonError(
                b,
                actions.map((a) => a.id),
              )?.message,
          )
          .find(Boolean);
      if (message)
        issues.push({ message: `Главное меню: ${message}`, menu: true });
    }
    if (!issues.length) return true;
    const first = issues[0];
    setError(first.message);
    setMenuOpen(!!first.menu);
    if (first.branch) setBranchId(first.branch);
    setPicked(first.step ? { branch: first.branch!, step: first.step } : null);
    requestAnimationFrame(() => {
      setTimeout(() => {
        const dialog = document.querySelector('[role="dialog"]');
        const field = (dialog || document).querySelector<HTMLElement>(
          '[aria-invalid="true"]',
        );
        field?.closest("details")?.setAttribute("open", "");
        field?.focus();
      }, 100);
    });
    return false;
  };
  const save = async (next = graph, reset = false) => {
    if (!reset && !validateBeforeAction(next)) return;
    setSaving(true);
    setError("");
    try {
      const response = await api(
        "funnel-board",
        reset ? { reset: true } : { graph: next },
      );
      setGraph(response.graph);
      setPicked(null);
      setSaved(JSON.stringify(response.graph));
      toast.success(reset ? "Исходная схема возвращена" : "Воронка сохранена");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const testBranch = async (id: string) => {
    if (
      !validateBeforeAction(
        id === "main-menu"
          ? {
              ...graph,
              main_menu: graph.main_menu || resource.data?.default_menu,
            }
          : graph,
      )
    )
      return;
    setTesting(true);
    try {
      const telegram_id = recipient || String(resource.data?.admins?.[0] || "");
      const response = await api("funnel-test", {
        telegram_id,
        scenario: id,
        graph:
          id === "main-menu"
            ? {
                ...graph,
                main_menu: graph.main_menu || resource.data?.default_menu,
              }
            : graph,
      });
      if (response.error)
        toast.error(
          `Отправлено ${response.sent}/${response.total}: ${response.error}`,
        );
      else toast.success(`Тест: отправлено ${response.sent} сообщений админу`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setTesting(false);
    }
  };
  const branch =
    graph.branches.find((b) => b.id === branchId) || graph.branches[0];
  const buttonInfo = (b: FunnelButton) => {
    const action = typeof b === "string" ? b : b.action;
    return {
      text:
        typeof b === "string"
          ? actions.find((a) => a.id === b)?.button || b
          : b.text,
      destination:
        action === "url"
          ? typeof b === "string"
            ? "Ссылка"
            : b.url || "Укажите адрес"
          : actions.find((a) => a.id === action)?.label || action,
    };
  };
  const addStep = (target: Branch) => {
    const step: Step = {
      id: nid("step"),
      condition: "no_device",
      wait_hours: 24,
      wait_from: target.steps.length ? "previous" : "anchor",
      text: "",
      buttons: ["cabinet"],
      enabled: true,
    };
    updateBranch(target.id, { steps: [...target.steps, step] });
    setPicked({ branch: target.id, step: step.id });
  };
  const moveBranch = (direction: number) => {
    if (!branch) return;
    const index = graph.branches.indexOf(branch),
      next = [...graph.branches];
    [next[index], next[index + direction]] = [
      next[index + direction],
      next[index],
    ];
    change({ branches: next });
  };
  const preview = (text: string, buttons: FunnelButton[]) => (
    <div className="flow-message">
      <p>{previewText(text) || "Здесь появится текст сообщения"}</p>
      <div className="flow-message-buttons">
        {buttons.map((b, i) => {
          const info = buttonInfo(b);
          return (
            <div key={i}>
              <span>{info.text || "Название кнопки"}</span>
              <ArrowUpRight className="size-3 shrink-0" />
              <small>{info.destination}</small>
            </div>
          );
        })}
      </div>
    </div>
  );
  return (
    <div className="space-y-4 min-w-0">
      <div className="flow-toolbar">
        <div className="flex flex-wrap gap-2">
          <Button
            variant={menuOpen ? "ghost" : "secondary"}
            onClick={() => setMenuOpen(false)}
          >
            <GitBranch />
            Автоматические сообщения
          </Button>
          <Button
            variant={menuOpen ? "secondary" : "ghost"}
            onClick={() => setMenuOpen(true)}
          >
            Главное меню бота
          </Button>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground" role="status">
            {dirty ? "Есть несохранённые изменения" : "Все изменения сохранены"}
          </span>
          <Button onClick={() => save()} disabled={!dirty || saving}>
            {saving ? "Сохраняем…" : "Сохранить воронку"}
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Поля со звёздочкой * обязательны. Пустые поля нужно заполнить перед
        сохранением и тестом.
      </p>
      {error && (
        <p
          role="alert"
          className="rounded-xl border border-destructive p-3 text-sm text-destructive"
        >
          {error}
        </p>
      )}
      {menuOpen ? (
        <div className="flow-menu-grid">
          <section className="rounded-xl border bg-card p-5 space-y-5">
            <div>
              <h2 className="font-semibold">Главное меню бота</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Что пользователь видит, когда открывает меню.
              </p>
            </div>
            <p className="text-sm font-medium">Текст главного меню *</p>
            <MessageEditor
              label="Текст главного меню"
              value={
                (graph.main_menu || resource.data.default_menu)?.text || ""
              }
              onChange={(text) =>
                change({
                  ...graph,
                  main_menu: {
                    ...(graph.main_menu || resource.data!.default_menu),
                    text,
                  },
                })
              }
            />
            <p className="text-xs text-muted-foreground">
              Подстановки: {"{name}"} — имя, {"{balance}"} — баланс, {"{price}"}{" "}
              — цена.
            </p>
            <h3 className="text-sm font-medium">Кнопки меню *</h3>
            {(graph.main_menu || resource.data.default_menu)?.buttons
              ?.length === 0 && (
              <p className="text-xs text-destructive">
                Добавьте хотя бы одну кнопку главного меню
              </p>
            )}
            <ButtonEditor
              actions={actions}
              value={
                (graph.main_menu || resource.data.default_menu)?.buttons || []
              }
              onChange={(buttons) =>
                change({
                  ...graph,
                  main_menu: {
                    ...(graph.main_menu || resource.data!.default_menu),
                    buttons,
                  },
                })
              }
            />
          </section>
          <section className="space-y-4">
            <h3 className="text-sm font-medium">Предпросмотр сообщения</h3>
            {preview(
              (graph.main_menu || resource.data.default_menu)?.text || "",
              (graph.main_menu || resource.data.default_menu)?.buttons || [],
            )}
            <p className="text-xs text-muted-foreground">
              Значения подставятся при отправке. Анимация эмодзи доступна в
              Telegram.
            </p>
            <Button
              variant="outline"
              disabled={testing}
              onClick={() => testBranch("main-menu")}
            >
              <Send />
              Тест меню на админе
            </Button>
          </section>
        </div>
      ) : (
        <div className="flow-layout">
          <aside
            className="flow-nav rounded-xl border bg-card"
            aria-label="Ветки воронки"
          >
            <div className="p-4 border-b space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Сценарии</h2>
                <span className="text-xs text-muted-foreground">
                  {graph.branches.length}/16
                </span>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  aria-label="Найти ветку"
                  placeholder="Найти сценарий…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Button
                variant="outline"
                className="w-full"
                disabled={graph.branches.length >= 16}
                onClick={() => {
                  const b: Branch = {
                    id: nid("branch"),
                    title: "Новый сценарий",
                    steps: [],
                  };
                  change({ branches: [...graph.branches, b] });
                  setBranchId(b.id);
                  setSearch("");
                }}
              >
                <Plus />
                Добавить ветку
              </Button>
            </div>
            <div className="flow-nav-list">
              {graph.branches
                .filter((b) =>
                  b.title.toLowerCase().includes(search.toLowerCase()),
                )
                .map((b) => (
                  <button
                    type="button"
                    key={b.id}
                    aria-pressed={b.id === branch?.id}
                    onClick={() => {
                      setBranchId(b.id);
                      setPicked(null);
                    }}
                    className="flow-nav-item"
                  >
                    <GitBranch className="size-4 shrink-0" />
                    <span>
                      <strong>{b.title}</strong>
                      <small>
                        {b.steps.length} сообщений ·{" "}
                        {b.steps.filter((s) => s.enabled).length} включено
                      </small>
                    </span>
                  </button>
                ))}
              {search &&
                !graph.branches.some((b) =>
                  b.title.toLowerCase().includes(search.toLowerCase()),
                ) && (
                  <p className="p-4 text-sm text-muted-foreground">
                    Ничего не найдено
                  </p>
                )}
            </div>
          </aside>
          <section
            className="flow-board rounded-xl border bg-card min-w-0"
            aria-label="Доска воронки"
          >
            {branch ? (
              <>
                <header className="p-5 border-b space-y-3">
                  <div className="flex flex-wrap justify-between items-start gap-3">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">
                        Сценарий
                      </p>
                      <h2 className="text-xl font-semibold">{branch.title}</h2>
                    </div>
                    <Button
                      variant="outline"
                      disabled={testing || !branch.steps.some((s) => s.enabled)}
                      onClick={() => testBranch(branch.id)}
                    >
                      <Send />
                      {testing ? "Отправляем…" : "Тест ветки на админе"}
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Каждый шаг проверяет своё условие. Настройки открываются по
                    нажатию на карточку.
                  </p>
                  <details className="flow-branch-settings">
                    <summary>
                      <Settings2 className="size-4" />
                      Настройки ветки
                    </summary>
                    <div className="pt-3 space-y-3">
                      <label className="block text-sm">
                        Название *
                        <Input
                          aria-label="Название ветки"
                          required
                          aria-invalid={!!titleError(branch.title)}
                          aria-describedby={
                            titleError(branch.title)
                              ? "branch-title-error"
                              : undefined
                          }
                          value={branch.title}
                          maxLength={80}
                          onChange={(e) =>
                            updateBranch(branch.id, { title: e.target.value })
                          }
                        />
                        {titleError(branch.title) && (
                          <p
                            id="branch-title-error"
                            className="text-xs text-destructive"
                          >
                            {titleError(branch.title)}
                          </p>
                        )}
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={graph.branches.indexOf(branch) === 0}
                          onClick={() => moveBranch(-1)}
                        >
                          <ArrowUp />
                          Выше в списке
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={
                            graph.branches.indexOf(branch) ===
                            graph.branches.length - 1
                          }
                          onClick={() => moveBranch(1)}
                        >
                          <ArrowDown />
                          Ниже в списке
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() =>
                            confirm({
                              title: `Удалить ветку «${branch.title}»?`,
                              description:
                                "Сообщения этой ветки больше не будут отправляться после сохранения.",
                              label: "Удалить",
                              action: async () => {
                                change({
                                  branches: graph.branches.filter(
                                    (b) => b.id !== branch.id,
                                  ),
                                });
                                setPicked(null);
                              },
                            })
                          }
                        >
                          <Trash2 />
                          Удалить ветку
                        </Button>
                      </div>
                    </div>
                  </details>
                </header>
                <div className="flow-path">
                  <div className="flow-path-start">
                    <GitBranch className="size-4" />
                    Проверка условий сценария
                  </div>
                  {branch.steps.map((step, index) => {
                    const enabledBefore = branch.steps
                      .slice(0, index)
                      .filter((s) => s.enabled && !ONCE.has(s.condition));
                    return (
                      <div key={step.id} className="flow-path-step">
                        <div className="flow-path-link">
                          <ArrowDown className="size-4" />
                          <span>
                            {ONCE.has(step.condition)
                              ? "Срок задан событием"
                              : step.wait_from === "previous" &&
                                  enabledBefore.length
                                ? "После предыдущего включённого шага"
                                : "От события пользователя"}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="flow-step-card"
                          data-disabled={!step.enabled}
                          aria-label={`Редактировать шаг ${index + 1}: ${conditionOf(step.condition)?.label || "Условие"}`}
                          onClick={() =>
                            setPicked({ branch: branch.id, step: step.id })
                          }
                        >
                          <div className="flow-step-heading">
                            <span className="flow-step-number">
                              {index + 1}
                            </span>
                            <strong>Сообщение {index + 1}</strong>
                            <span
                              className={
                                step.enabled
                                  ? "flow-status-on"
                                  : "flow-status-off"
                              }
                            >
                              {step.enabled ? "Включено" : "Выключено"}
                            </span>
                            <Pencil className="size-4 text-muted-foreground" />
                          </div>
                          <div className="flow-step-facts">
                            <div>
                              <Users className="size-4" />
                              <span>
                                <small>Кому</small>
                                <strong>
                                  {conditionOf(step.condition)?.label}
                                </strong>
                              </span>
                            </div>
                            <div>
                              <Clock className="size-4" />
                              <span>
                                <small>Когда</small>
                                <strong>
                                  {ONCE.has(step.condition)
                                    ? "По правилам события"
                                    : waitLabel(
                                        step.wait_hours,
                                        step.wait_from === "previous" &&
                                          enabledBefore.length
                                          ? "previous"
                                          : "anchor",
                                      )}
                                </strong>
                              </span>
                            </div>
                          </div>
                          {preview(step.text, step.buttons)}
                          <span className="flow-edit-hint">
                            Изменить условие, текст и кнопки{" "}
                            <ArrowUpRight className="size-3" />
                          </span>
                        </button>
                      </div>
                    );
                  })}
                  <div className="flow-path-link">
                    <ArrowDown className="size-4" />
                  </div>
                  <Button
                    variant="outline"
                    className="flow-add-step"
                    disabled={branch.steps.length >= 8}
                    onClick={() => addStep(branch)}
                  >
                    <Plus />
                    Добавить сообщение
                  </Button>
                  {!branch.steps.length && (
                    <p className="text-center text-sm text-muted-foreground mt-3">
                      Начните с первого сообщения: выберите аудиторию, время и
                      текст.
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-muted-foreground">
                <GitBranch className="mx-auto mb-3" />
                Добавьте ветку, чтобы собрать первый сценарий.
              </div>
            )}
          </section>
        </div>
      )}
      <details className="rounded-xl border bg-card p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Тестовая отправка и сброс
        </summary>
        <div className="mt-4 flex flex-wrap gap-4 items-center">
          <label className="text-sm space-y-2">
            <span className="block">Кому отправлять тест</span>
            <select
              aria-label="Админ для теста"
              className="h-9 rounded-md border bg-background px-3"
              value={recipient || String(resource.data.admins?.[0] || "")}
              onChange={(e) => setRecipient(e.target.value)}
            >
              {(resource.data.admins || []).map((id: number) => (
                <option key={id} value={id}>
                  Админ {id}
                </option>
              ))}
            </select>
          </label>
          <p className="text-xs text-muted-foreground max-w-md">
            Отправляется текущий черновик только админу, без ожидания. Кнопки
            тестовые: оплата и другие действия не выполняются.
          </p>
          <Button
            variant="ghost"
            disabled={saving}
            onClick={() =>
              confirm({
                title: "Вернуть исходную схему?",
                description:
                  "Все ваши тексты, кнопки и главное меню заменятся исходными. Уже отправленные шаги не повторятся.",
                label: "Вернуть",
                action: async () => save(graph, true),
              })
            }
          >
            Вернуть исходную схему
          </Button>
        </div>
      </details>
      <Sheet
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setPicked(null);
        }}
      >
        <SheetContent className="flow-editor-sheet overflow-y-auto w-full sm:max-w-xl">
          <SheetTitle>Настройка сообщения</SheetTitle>
          <SheetDescription>
            {selectedBranch?.title} · Изменения попадут в черновик. Сохраните
            воронку, чтобы применить их.
          </SheetDescription>
          {error && (
            <p role="alert" className="text-sm text-destructive mt-3">
              {error}
            </p>
          )}
          {selected && selectedBranch && (
            <div className="space-y-5 mt-6">
              <div className="flex justify-between items-center rounded-xl bg-muted p-3">
                <span className="text-sm">Отправлять это сообщение</span>
                <Switch
                  aria-label="Шаг включён"
                  checked={selected.enabled}
                  onCheckedChange={(enabled) =>
                    updateStep(selectedBranch.id, selected.id, { enabled })
                  }
                />
              </div>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium">1. Кому отправить *</span>
                <select
                  aria-label="Условие шага"
                  required
                  aria-invalid={!conditionOf(selected.condition)}
                  className="flex h-9 w-full rounded-md border bg-transparent px-3 text-sm"
                  value={selected.condition}
                  onChange={(event) =>
                    updateStep(selectedBranch.id, selected.id, {
                      condition: event.target.value,
                    })
                  }
                >
                  {conditions.map((item) => (
                    <option
                      key={item.id}
                      value={item.id}
                      disabled={
                        ONCE.has(item.id) &&
                        used.has(item.id) &&
                        item.id !== selected.condition
                      }
                    >
                      {item.label}
                    </option>
                  ))}
                </select>
                <span className="block text-xs text-muted-foreground">
                  {conditionOf(selected.condition)?.hint}
                </span>
              </label>
              <h3 className="text-sm font-medium">2. Когда отправить</h3>
              {ONCE.has(selected.condition) && (
                <p className="rounded-lg bg-muted p-3 text-sm">
                  {conditionOf(selected.condition)?.hint}
                </p>
              )}
              {!ONCE.has(selected.condition) && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-1.5">
                    <span className="text-sm">Через сколько часов *</span>
                    <Input
                      aria-label="Пауза в часах"
                      required
                      step={1}
                      aria-invalid={!!hoursError(selected.wait_hours)}
                      aria-describedby={
                        hoursError(selected.wait_hours)
                          ? "wait-hours-error"
                          : undefined
                      }
                      type="number"
                      min={0}
                      max={8760}
                      value={selected.wait_hours}
                      onChange={(event) =>
                        updateStep(selectedBranch.id, selected.id, {
                          wait_hours:
                            event.target.value === ""
                              ? ""
                              : Number(event.target.value),
                        })
                      }
                    />
                    {hoursError(selected.wait_hours) && (
                      <p
                        id="wait-hours-error"
                        className="text-xs text-destructive"
                      >
                        {hoursError(selected.wait_hours)}
                      </p>
                    )}
                  </label>
                  <label className="space-y-1.5">
                    <span className="text-sm">От какого момента *</span>
                    <select
                      aria-label="От чего считать паузу"
                      required
                      className="flex h-9 w-full rounded-md border bg-transparent px-3 text-sm"
                      value={selected.wait_from}
                      onChange={(event) =>
                        updateStep(selectedBranch.id, selected.id, {
                          wait_from: event.target.value as Step["wait_from"],
                        })
                      }
                    >
                      <option value="anchor">От события</option>
                      <option value="previous">После предыдущего шага</option>
                    </select>
                  </label>
                </div>
              )}
              <div className="block space-y-1.5">
                <h3 className="text-sm font-medium">3. Что отправить *</h3>
                <MessageEditor
                  value={selected.text}
                  onChange={(text) =>
                    updateStep(selectedBranch.id, selected.id, { text })
                  }
                />
                <span className="block text-xs text-muted-foreground">
                  Можно оставить {"{name}"}, {"{link}"}, {"{price}"}. Для
                  промокода ещё {"{code}"}, {"{devices}"} и {"{amount}"}. Один
                  человек получает не больше одного такого сообщения в сутки и
                  трёх в неделю.
                </span>
              </div>
              <h3 className="text-sm font-medium">4. Куда ведут кнопки</h3>
              <ButtonEditor
                actions={actions}
                value={selected.buttons}
                onChange={(buttons) =>
                  updateStep(selectedBranch.id, selected.id, { buttons })
                }
              />
              <div className="border-t pt-4 flex justify-between gap-3">
                <Button
                  variant="ghost"
                  className="text-destructive"
                  onClick={() =>
                    confirm({
                      title: "Удалить сообщение?",
                      description:
                        "После сохранения этот шаг больше не будет отправляться.",
                      label: "Удалить",
                      action: async () => {
                        updateBranch(selectedBranch.id, {
                          steps: selectedBranch.steps.filter(
                            (s) => s.id !== selected.id,
                          ),
                        });
                        setPicked(null);
                      },
                    })
                  }
                >
                  <Trash2 />
                  Удалить шаг
                </Button>
                <Button
                  aria-label="Закрыть редактор шага"
                  onClick={() => setPicked(null)}
                >
                  <Check />
                  Готово
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
