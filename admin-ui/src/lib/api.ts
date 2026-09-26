import { useCallback, useEffect, useRef, useState } from "react";
export type Data = Record<string, any>;
export async function api(
  path: string,
  body?: Data | FormData,
  method?: string,
): Promise<Data> {
  const response = await fetch("/admin/api/" + path, {
    method: method || (body ? "POST" : "GET"),
    credentials: "same-origin",
    headers:
      body && !(body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : undefined,
    body:
      body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  const data = await response
    .json()
    .catch(() => ({ error: "Сервер вернул некорректный ответ" }));
  if (response.status === 401)
    window.dispatchEvent(new Event("admin:unauthorized"));
  if (!response.ok || data.ok === false)
    throw new Error(
      data.error || `Не удалось выполнить запрос (${response.status})`,
    );
  return data;
}
export function useResource(path: string | null, interval = 0) {
  const [data, setData] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const sequence = useRef(0);
  const reload = useCallback(async () => {
    const id = ++sequence.current;
    if (!path) {
      setLoading(false);
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const next = await api(path);
      if (id === sequence.current) setData(next);
    } catch (e) {
      if (id === sequence.current) setError((e as Error).message);
    } finally {
      if (id === sequence.current) setLoading(false);
    }
  }, [path]);
  useEffect(() => {
    setData(null);
    void reload();
    const timer = interval ? setInterval(() => void reload(), interval) : null;
    return () => {
      sequence.current++;
      if (timer) clearInterval(timer);
    };
  }, [reload, interval]);
  return { data, error, loading, reload, setData };
}
export const money = (value: unknown) =>
  Number(value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 }) +
  " ₽";
export const date = (value: unknown) =>
  value && !isNaN(Date.parse(String(value)))
    ? new Intl.DateTimeFormat("ru-RU", {
        timeZone: "Europe/Moscow",
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(String(value)))
    : "—";
export const who = (row: Data) =>
  row.first_name ||
  (row.username
    ? "@" + row.username
    : String(row.telegram_id || row.referrer_id || "—"));
export const qs = (values: Data) =>
  new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v !== "" && v !== null && v !== undefined)
      .map(([k, v]) => [k, String(v)]),
  ).toString();
