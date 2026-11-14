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
  if (response.status === 401)
    window.dispatchEvent(new Event("admin:unauthorized"));
  let data: Data;
  try {
    data = await response.json();
    if (!data || typeof data !== "object" || Array.isArray(data))
      throw new Error("Invalid JSON response");
  } catch {
    const hint = [404, 405].includes(response.status)
      ? "Обработчик запроса недоступен. После обновления кода пересоберите и перезапустите контейнер bot."
      : "Не удалось получить результат операции. Проверьте состояние устройства и логи bot перед повтором.";
    throw new Error(
      `Сервер вернул некорректный ответ (HTTP ${response.status}). ${hint}`,
    );
  }
  if (!response.ok || data.ok === false)
    throw new Error(
      data.error || `Не удалось выполнить запрос (${response.status})`,
    );
  return data;
}
export function useResource(path: string | null, interval = 0) {
  const [data, setData] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [updatedAt, setUpdatedAt] = useState(0);
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
      if (id === sequence.current) {
        setData(next);
        setUpdatedAt(Date.now());
      }
    } catch (e) {
      if (id === sequence.current) setError((e as Error).message);
    } finally {
      if (id === sequence.current) setLoading(false);
    }
  }, [path]);
  useEffect(() => {
    setData(null);
    void reload();
    // Polling skips hidden tabs (no load on the server for nobody) and catches up when the tab is shown.
    let last = Date.now();
    const tick = () => {
      if (document.hidden) return;
      last = Date.now();
      void reload();
    };
    const timer = interval ? setInterval(tick, interval) : null;
    const shown = () => {
      if (interval && !document.hidden && Date.now() - last >= interval) tick();
    };
    if (interval) document.addEventListener("visibilitychange", shown);
    return () => {
      sequence.current++;
      if (timer) clearInterval(timer);
      if (interval) document.removeEventListener("visibilitychange", shown);
    };
  }, [reload, interval]);
  return { data, error, loading, reload, setData, updatedAt };
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

/** A value kept in the page address (#section?key=value), so reload and links keep the chosen view.
 * replaceState does not fire hashchange, so the section is not re-mounted. */
export function useHashParam(key: string, fallback: string) {
  const read = () =>
    new URLSearchParams(location.hash.split("?")[1] || "").get(key) || fallback;
  const [value, setValue] = useState(read);
  const update = useCallback(
    (next: string) => {
      setValue(next);
      const [path, query] = location.hash.slice(1).split("?");
      const params = new URLSearchParams(query || "");
      if (next === fallback) params.delete(key);
      else params.set(key, next);
      const rest = params.toString();
      history.replaceState(history.state, "", "#" + path + (rest ? "?" + rest : ""));
    },
    [key, fallback],
  );
  return [value, update] as const;
}
/** Short axis numbers: 950, 4,5 тыс., 1,2 млн. */
export const compact = (value: unknown) => {
  const n = Number(value || 0), a = Math.abs(n);
  const f = (x: number) => x.toLocaleString("ru-RU", { maximumFractionDigits: x < 10 ? 1 : 0 });
  if (a >= 1e6) return f(n / 1e6) + " млн";
  if (a >= 1e3) return f(n / 1e3) + " тыс.";
  return f(n);
};
/** Change against a previous value in percent, or null when there is nothing to compare with. */
export const change = (now: unknown, prev: unknown) => {
  const a = Number(now || 0), b = Number(prev || 0);
  return b > 0 ? ((a - b) / b) * 100 : null;
};
