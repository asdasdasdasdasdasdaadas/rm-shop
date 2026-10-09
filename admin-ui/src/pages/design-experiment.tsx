import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DataTable, Failure, Loading, Panel } from "@/components/workspace";
import { api, useResource, type Data } from "@/lib/api";

const rate = (n: number, total: number) =>
  total
    ? `${n} / ${total} · ${((100 * n) / total).toFixed(1)}%`
    : "Пока нет данных";
export function DesignExperiment() {
  const resource = useResource("design-experiment");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function toggle() {
    setBusy(true);
    setError("");
    try {
      await api("design-experiment", { active: !resource.data?.active });
      await resource.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (resource.error)
    return <Failure message={resource.error} retry={resource.reload} />;
  if (!resource.data) return <Loading />;
  return (
    <Panel
      title="A/B-тест кабинета · 50/50"
      description="Привычный дизайн против нового тёмного. Группа закреплена за аккаунтом; администраторы не участвуют."
    >
      <div className="flex gap-3 items-center flex-wrap mb-5">
        <span>{resource.data.active ? "Тест идёт" : "Тест остановлен"}</span>
        <Button variant="outline" disabled={busy} onClick={toggle}>
          {resource.data.active ? "Остановить тест" : "Продолжить тест"}
        </Button>
        <Button variant="ghost" onClick={() => void resource.reload()}>
          Обновить
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-destructive mb-4">
          {error}
        </p>
      )}
      <DataTable
        rows={resource.data.rows || []}
        columns={[
          {
            key: "variant",
            label: "Дизайн",
            cell: (r: Data) =>
              r.variant === "modern" ? "Новый тёмный" : "Привычный",
          },
          {
            key: "existing_customer",
            label: "Клиенты",
            cell: (r: Data) =>
              r.existing_customer ? "Ранее платили" : "Ещё не платили",
          },
          { key: "exposed", label: "Увидели", className: "whitespace-normal" },
          {
            key: "mature",
            label: "Прошло 7 дней",
            className: "whitespace-normal",
          },
          {
            key: "connected",
            label: "Подключились · 7 дней",
            className: "whitespace-normal",
            cell: (r: Data) => rate(r.connected, r.connection_base),
          },
          {
            key: "paid",
            label: "Оплатили · 7 дней",
            className: "whitespace-normal",
            cell: (r: Data) => rate(r.paid, r.mature),
          },
          { key: "topup", label: "Пополнение", className: "whitespace-normal" },
          { key: "wizard", label: "Настройка", className: "whitespace-normal" },
        ]}
      />
      <p className="text-sm text-muted-foreground mt-4">
        Подключения и оплаты сравниваются только у тех, у кого прошло полных 7
        дней с первого показа. В подключениях учитываются только клиенты без
        прежних подключений. Оплаты подтверждаются сервером; подарки и промокоды
        не считаются оплатой.
      </p>
      <p className="text-sm text-muted-foreground mt-2">
        Переходы показаны за первые 7 дней, включая ещё наблюдаемых участников.
        Это промежуточные данные, а не объявление победителя. После остановки
        вернётся личный выбор дизайна; группы и накопленная статистика
        сохранятся.
      </p>
    </Panel>
  );
}
