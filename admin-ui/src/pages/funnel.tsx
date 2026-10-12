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
import { toast } from "sonner";
import { Plus, Trash2, Minus, X, GitBranch, MessageSquare } from "lucide-react";

type Step = {
  id: string;
  condition: string;
  wait_hours: number;
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
function waitLabel(hours: number, from: string) {
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
  const [zoom, setZoom] = useState(1);
  const [menuOpen, setMenuOpen] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [testing, setTesting] = useState(false);
  useEffect(() => {
    if (resource.data?.graph && !graph) {
      setGraph(resource.data.graph);
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
  const save = async (next = graph, reset = false) => {
    setSaving(true);
    setError("");
    try {
      const response = await api(
        "funnel-board",
        reset ? { reset: true } : { graph: next },
      );
      setGraph(response.graph);
      setSaved(JSON.stringify(response.graph));
      toast.success(reset ? "Исходная схема возвращена" : "Воронка сохранена");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const testBranch = async (id: string) => {
    setTesting(true);
    try {
      const telegram_id = recipient || String(resource.data?.admins?.[0] || "");
      const response = await api("funnel-test", {
        telegram_id,
        scenario: id,
        graph,
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
  return (
    <div className="space-y-5 min-w-0">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          onClick={() => {
            if (!graph.main_menu)
              change({ ...graph, main_menu: resource.data?.default_menu });
            setMenuOpen(!menuOpen);
          }}
        >
          Главное меню бота
        </Button>
        <select
          aria-label="Админ для теста"
          className="h-9 rounded-md border bg-background px-2 text-sm"
          value={recipient || String(resource.data?.admins?.[0] || "")}
          onChange={(e) => setRecipient(e.target.value)}
        >
          {(resource.data?.admins || []).map((id: number) => (
            <option key={id} value={id}>
              Админ {id}
            </option>
          ))}
        </select>
        <Button onClick={() => save()} disabled={!dirty || saving}>
          Сохранить воронку
        </Button>
        <Button
          variant="outline"
          disabled={saving}
          onClick={() =>
            confirm({
              title: "Вернуть исходную схему?",
              description:
                "Тексты и кнопки заменятся текущей воронкой бота. Шаги, которые уже ушли, повторно не отправятся.",
              label: "Вернуть",
              action: async () => save(graph, true),
            })
          }
        >
          Вернуть исходную схему
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Тест отправляет текущий черновик только выбранному админу, без задержек
        и действий с аккаунтом. Включённые шаги — по порядку.
      </p>
      {menuOpen && graph.main_menu && (
        <section className="rounded-xl border p-4 space-y-4">
          <h2 className="font-medium">Главное меню бота</h2>
          <p className="text-sm text-muted-foreground">
            Текст при открытии меню. Подстановки: {"{name}"}, {"{balance}"},{" "}
            {"{price}"}.
          </p>
          <MessageEditor
            label="Текст главного меню"
            value={graph.main_menu.text}
            onChange={(text) =>
              change({ ...graph, main_menu: { ...graph.main_menu!, text } })
            }
          />
          <ButtonEditor
            actions={actions}
            value={graph.main_menu.buttons}
            onChange={(buttons) =>
              change({ ...graph, main_menu: { ...graph.main_menu!, buttons } })
            }
          />
          <Button
            variant="outline"
            disabled={testing}
            onClick={() => testBranch("main-menu")}
          >
            Тест меню на админе
          </Button>
        </section>
      )}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <div className="funnel-workspace">
        <div className="funnel-board rounded-xl border bg-card min-w-0">
          <div className="flex flex-wrap items-center gap-2 border-b p-3">
            <GitBranch className="size-4" />
            <span className="text-sm font-medium">Карта воронки</span>
            <span className="text-xs text-muted-foreground mr-auto">
              Ветки: {graph.branches.length} · Шаги:{" "}
              {graph.branches.reduce((n, b) => n + b.steps.length, 0)}
            </span>
            <Button
              variant="outline"
              size="icon"
              aria-label="Уменьшить масштаб"
              disabled={zoom <= 0.4}
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
            >
              <Minus />
            </Button>
            <Button
              variant="ghost"
              onClick={() => setZoom(1)}
              aria-label="Сбросить масштаб"
            >
              {Math.round(zoom * 100)}%
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Увеличить масштаб"
              disabled={zoom >= 1.4}
              onClick={() => setZoom((z) => Math.min(1.4, z + 0.2))}
            >
              <Plus />
            </Button>
          </div>
          <p className="px-3 py-2 text-xs text-muted-foreground">
            Прокручивайте доску в любую сторону. Нажмите на сообщение, чтобы
            изменить его. Ветки проверяются независимо; линии показывают порядок
            шагов.
          </p>
          <div
            className="funnel-viewport"
            tabIndex={0}
            role="region"
            aria-label="Доска воронки"
          >
            <div className="funnel-canvas" style={{ zoom }}>
              <div className="funnel-root">
                <GitBranch className="size-5" />
                <strong>События пользователя</strong>
                <span>Проверка условий каждой ветки</span>
              </div>
              <div className="funnel-branches">
                {graph.branches.map((branch, index) => (
                  <section key={branch.id} className="funnel-branch">
                    <div className="funnel-branch-head rounded-xl border bg-card p-3 space-y-2">
                      <Input
                        aria-label={`Название ветки ${index + 1}`}
                        value={branch.title}
                        maxLength={80}
                        onChange={(event) =>
                          updateBranch(branch.id, { title: event.target.value })
                        }
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={
                          testing || !branch.steps.some((s) => s.enabled)
                        }
                        onClick={() => testBranch(branch.id)}
                      >
                        Тест ветки на админе
                      </Button>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={index === 0}
                          onClick={() => {
                            const branches = [...graph.branches];
                            [branches[index - 1], branches[index]] = [
                              branches[index],
                              branches[index - 1],
                            ];
                            change({ branches });
                          }}
                        >
                          Левее
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={index === graph.branches.length - 1}
                          onClick={() => {
                            const branches = [...graph.branches];
                            [branches[index + 1], branches[index]] = [
                              branches[index],
                              branches[index + 1],
                            ];
                            change({ branches });
                          }}
                        >
                          Правее
                        </Button>
                      </div>
                    </div>
                    {branch.steps.map((step, stepIndex) => {
                      const condition = conditionOf(step.condition);
                      const active =
                        picked?.branch === branch.id && picked.step === step.id;
                      return (
                        <div className="funnel-step" key={step.id}>
                          <span className="funnel-link-label">
                            {stepIndex === 0 || step.wait_from === "anchor"
                              ? "От события"
                              : "После предыдущего сообщения"}
                          </span>
                          <button
                            type="button"
                            aria-pressed={active}
                            onClick={() =>
                              setPicked({ branch: branch.id, step: step.id })
                            }
                            className={`funnel-node w-full rounded-xl border bg-card p-4 text-left space-y-2 ${
                              active ? "border-primary" : ""
                            } ${step.enabled ? "" : "opacity-50"}`}
                          >
                            <span className="flex items-center gap-2 text-xs text-muted-foreground">
                              <MessageSquare className="size-3" />
                              Шаг {stepIndex + 1} ·{" "}
                              {step.enabled ? "Включён" : "Выключен"}
                            </span>
                            <span className="block text-sm font-medium">
                              {condition?.label || "Условие"}
                            </span>
                            <span className="block text-xs text-muted-foreground">
                              {ONCE.has(step.condition)
                                ? "По правилам события"
                                : waitLabel(step.wait_hours, step.wait_from)}
                            </span>
                            <span className="block text-xs line-clamp-3 whitespace-pre-wrap">
                              {step.text || "Добавьте текст сообщения"}
                            </span>
                            <span className="flex flex-wrap gap-1">
                              {step.buttons.map((id) => (
                                <span
                                  key={
                                    typeof id === "string"
                                      ? id
                                      : step.buttons.indexOf(id)
                                  }
                                  className="rounded border px-2 py-1 text-xs text-muted-foreground"
                                >
                                  {typeof id === "string"
                                    ? actions.find((a) => a.id === id)
                                        ?.button || id
                                    : id.text}
                                </span>
                              ))}
                            </span>
                          </button>
                        </div>
                      );
                    })}
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => {
                        const step: Step = {
                          id: nid("step"),
                          condition: "no_device",
                          wait_hours: 24,
                          wait_from: branch.steps.length
                            ? "previous"
                            : "anchor",
                          text: "",
                          buttons: ["cabinet"],
                          enabled: true,
                        };
                        updateBranch(branch.id, {
                          steps: [...branch.steps, step],
                        });
                        setPicked({ branch: branch.id, step: step.id });
                      }}
                    >
                      <Plus />
                      Добавить шаг
                    </Button>
                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={() =>
                        confirm({
                          title: `Удалить ветку «${branch.title}»?`,
                          description:
                            "Шаги этой ветки больше не будут отправляться.",
                          label: "Удалить",
                          action: async () => {
                            change({
                              branches: graph.branches.filter(
                                (item) => item.id !== branch.id,
                              ),
                            });
                            if (picked?.branch === branch.id) setPicked(null);
                          },
                        })
                      }
                    >
                      <Trash2 />
                      Удалить ветку
                    </Button>
                  </section>
                ))}
                <Button
                  variant="outline"
                  className="shrink-0 mt-8"
                  onClick={() => {
                    const step: Step = {
                      id: nid("step"),
                      condition: "no_device",
                      wait_hours: 24,
                      wait_from: "anchor",
                      text: "",
                      buttons: ["cabinet"],
                      enabled: true,
                    };
                    const branch: Branch = {
                      id: nid("branch"),
                      title: "Новая ветка",
                      steps: [step],
                    };
                    change({ branches: [...graph.branches, branch] });
                    setPicked({ branch: branch.id, step: step.id });
                  }}
                >
                  <Plus />
                  Добавить ветку
                </Button>
              </div>
            </div>
          </div>
        </div>
        {selected && selectedBranch && (
          <section
            aria-label="Редактор шага"
            className="funnel-inspector rounded-xl border bg-card p-4 space-y-4"
          >
            <div className="flex items-center justify-between gap-4">
              <h2 className="font-medium">
                Шаг ветки «{selectedBranch.title}»
              </h2>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Закрыть редактор шага"
                onClick={() => setPicked(null)}
              >
                <X />
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm">Включён</span>
                <Switch
                  aria-label="Шаг включён"
                  checked={selected.enabled}
                  onCheckedChange={(value) =>
                    updateStep(selectedBranch.id, selected.id, {
                      enabled: value,
                    })
                  }
                />
              </div>
            </div>
            <label className="block space-y-1.5">
              <span className="text-sm">Условие</span>
              <select
                aria-label="Условие шага"
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
            {!ONCE.has(selected.condition) && (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="space-y-1.5">
                  <span className="text-sm">Пауза, часов</span>
                  <Input
                    aria-label="Пауза в часах"
                    type="number"
                    min={0}
                    max={8760}
                    value={selected.wait_hours}
                    onChange={(event) =>
                      updateStep(selectedBranch.id, selected.id, {
                        wait_hours: Number(event.target.value || 0),
                      })
                    }
                  />
                </label>
                <label className="space-y-1.5">
                  <span className="text-sm">Считать паузу</span>
                  <select
                    aria-label="От чего считать паузу"
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
              <span className="text-sm">Сообщение</span>
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
            <h3 className="text-sm font-medium">Кнопки сообщения</h3>
            <ButtonEditor
              actions={actions}
              value={selected.buttons}
              onChange={(buttons) =>
                updateStep(selectedBranch.id, selected.id, { buttons })
              }
            />
            <fieldset className="space-y-2">
              <legend className="text-sm">Быстрый выбор действий</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {actions.map((action) => (
                  <label
                    key={action.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      aria-label={action.label}
                      checked={selected.buttons.some(
                        (b) =>
                          (typeof b === "string" ? b : b.action) === action.id,
                      )}
                      onChange={() => {
                        const buttons = selected.buttons.some(
                          (b) =>
                            (typeof b === "string" ? b : b.action) ===
                            action.id,
                        )
                          ? selected.buttons.filter(
                              (item) => item !== action.id,
                            )
                          : [...selected.buttons, action.id];
                        updateStep(selectedBranch.id, selected.id, { buttons });
                      }}
                    />
                    <span>
                      {action.label}
                      <span className="text-muted-foreground">
                        {" "}
                        · {action.button}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
            <Button
              variant="outline"
              onClick={() => {
                updateBranch(selectedBranch.id, {
                  steps: selectedBranch.steps.filter(
                    (step) => step.id !== selected.id,
                  ),
                });
                setPicked(null);
              }}
            >
              <Trash2 />
              Удалить шаг
            </Button>
          </section>
        )}
      </div>
    </div>
  );
}
