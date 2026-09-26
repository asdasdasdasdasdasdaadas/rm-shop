import {
  cloneElement,
  isValidElement,
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type ReactElement,
} from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "./ui/select";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "./ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { Skeleton } from "./ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./ui/dialog";
import { Badge } from "./ui/badge";
import {
  Loader2,
  RefreshCw,
  Inbox,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { type Data } from "@/lib/api";
export const Navigation = createContext<(path: string) => void>(() => {});
export const useNavigate = () => useContext(Navigation);
export function Panel({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle className="text-base">{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div>
        {isValidElement(children)
          ? cloneElement(children as ReactElement<any>, {
              id,
              "aria-describedby": hint ? id + "-hint" : undefined,
            })
          : children}
      </div>
      {hint && (
        <p
          id={id + "-hint"}
          className="text-xs text-muted-foreground leading-relaxed"
        >
          {hint}
        </p>
      )}
    </div>
  );
}
export function Choice({
  value,
  onChange,
  options,
  label,
  disabled = false,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
  label: string;
  disabled?: boolean;
  id?: string;
}) {
  return (
    <Select
      value={value || "__all"}
      onValueChange={(v) => onChange(v === "__all" ? "" : v)}
      disabled={disabled}
    >
      <SelectTrigger id={id} aria-label={label}>
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {options.map(([v, l]) => (
          <SelectItem key={v} value={v || "__all"}>
            {l}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
export function Failure({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="size-4" />
      <AlertTitle>Не удалось загрузить данные</AlertTitle>
      <AlertDescription className="space-y-3">
        <p>{message}</p>
        {retry && (
          <Button variant="outline" size="sm" onClick={retry}>
            <RefreshCw />
            Повторить
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
export function Loading() {
  return (
    <div className="space-y-3" aria-label="Загрузка" role="status">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}
export function Empty({
  title = "Пока нет данных",
  description = "Здесь появятся записи, когда пользователи начнут взаимодействовать с сервисом.",
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-5 text-center gap-3">
      <Inbox className="size-8 text-muted-foreground" />
      <h3 className="font-medium">{title}</h3>
      <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      {action}
    </div>
  );
}
export type Column = {
  key: string;
  label: ReactNode;
  cell?: (row: Data) => ReactNode;
  className?: string;
};
export function DataTable({
  rows,
  columns,
  empty,
  loading = false,
}: {
  rows: Data[];
  columns: Column[];
  empty?: ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="rounded-lg border overflow-hidden" aria-busy={loading}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((c) => (
              <TableHead key={c.key} className={c.className}>
                {c.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => (
            <TableRow key={r.id || r.order_id || r.telegram_id || i}>
              {columns.map((c) => (
                <TableCell key={c.key} className={c.className}>
                  {c.cell ? c.cell(r) : String(r[c.key] ?? "—")}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!rows.length && (empty || <Empty />)}
    </div>
  );
}
export function Pager({
  page,
  total,
  limit = 25,
  onChange,
}: {
  page: number;
  total: number;
  limit?: number;
  onChange: (p: number) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground py-3">
      <span>
        {total.toLocaleString("ru-RU")} записей · страница {page} из{" "}
        {Math.max(1, Math.ceil(total / limit))}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Предыдущая страница"
        >
          <ChevronLeft />
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page * limit >= total}
          onClick={() => onChange(page + 1)}
          aria-label="Следующая страница"
        >
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
export function Status({ value }: { value: unknown }) {
  const labels: Data = {
    granted: "Оплачено",
    paid: "Оплачено",
    pending: "Ожидает",
    created: "Создан",
    expired: "Истёк",
    failed: "Ошибка",
    sent: "Доставлено",
    open: "Ждёт ответа",
    closed: "Закрыто",
    ACTIVE: "Активен",
    DISABLED: "Отключён",
    EXPIRED: "Истёк",
  };
  const s = String(value || "—");
  return (
    <Badge
      variant={
        ["failed", "DISABLED", "EXPIRED"].includes(s)
          ? "destructive"
          : "secondary"
      }
    >
      {labels[s] || s}
    </Badge>
  );
}
export function ActionButton({
  onAction,
  children,
  variant = "default",
  disabled = false,
}: {
  onAction: () => Promise<unknown>;
  children: ReactNode;
  variant?: "default" | "outline" | "destructive" | "ghost";
  disabled?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  return (
    <Button
      type="button"
      variant={variant}
      disabled={busy || disabled}
      onClick={async () => {
        if (lock.current) return;
        lock.current = true;
        setBusy(true);
        try {
          await onAction();
        } catch (e) {
          toast.error((e as Error).message);
        } finally {
          lock.current = false;
          setBusy(false);
        }
      }}
    >
      {busy && <Loader2 className="animate-spin" />}
      {children}
    </Button>
  );
}
type ConfirmOptions = {
  title: string;
  description: string;
  label?: string;
  danger?: boolean;
  phrase?: string;
  action: () => Promise<unknown>;
};
const Confirmation = createContext<(options: ConfirmOptions) => void>(() => {});
export const useConfirm = () => useContext(Confirmation);
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [item, setItem] = useState<ConfirmOptions | null>(null),
    [phrase, setPhrase] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const lock = useRef(false);
  return (
    <Confirmation.Provider
      value={(v) => {
        setItem(v);
        setPhrase("");
        setError("");
      }}
    >
      {children}
      <Dialog
        open={!!item}
        onOpenChange={(open) => {
          if (!open && !busy) setItem(null);
        }}
      >
        <DialogContent
          onEscapeKeyDown={(e) => {
            if (busy) e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            if (busy) e.preventDefault();
          }}
        >
          <DialogHeader>
            <DialogTitle>{item?.title}</DialogTitle>
            <DialogDescription className="whitespace-pre-line">
              {item?.description}
            </DialogDescription>
          </DialogHeader>
          {item?.phrase && (
            <Field label={`Введите «${item.phrase}» для подтверждения`}>
              <Input
                aria-label="Подтверждение действия"
                value={phrase}
                onChange={(e) => setPhrase(e.target.value)}
              />
            </Field>
          )}
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => setItem(null)}
            >
              Отмена
            </Button>
            <Button
              variant={item?.danger ? "destructive" : "default"}
              disabled={busy || (!!item?.phrase && phrase !== item.phrase)}
              onClick={async () => {
                if (lock.current || !item) return;
                lock.current = true;
                setBusy(true);
                setError("");
                try {
                  await item.action();
                  setItem(null);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  lock.current = false;
                  setBusy(false);
                }
              }}
            >
              {busy && <Loader2 className="animate-spin" />}
              {item?.label || "Подтвердить"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Confirmation.Provider>
  );
}
export function useDirty(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    window.dispatchEvent(new CustomEvent("admin:dirty", { detail: true }));
    return () => {
      window.removeEventListener("beforeunload", handler);
      window.dispatchEvent(new CustomEvent("admin:dirty", { detail: false }));
    };
  }, [dirty]);
}
