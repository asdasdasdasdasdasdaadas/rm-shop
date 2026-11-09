import { useState } from "react";
import { api, useResource } from "@/lib/api";
import {
  ActionButton,
  DataTable,
  Failure,
  Field,
  Loading,
  useConfirm,
  useNavigate,
} from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Plus,
  Copy,
} from "lucide-react";
import { toast } from "sonner";
import { RecordsPage } from "./records";
export function AdsPage() {
  const resource = useResource("ads"),
    [open, setOpen] = useState(false),
    [title, setTitle] = useState(""),
    [slug, setSlug] = useState("");
  const confirm = useConfirm();
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Button onClick={() => setOpen(true)}>
          <Plus />
          Создать рекламную ссылку
        </Button>
      </div>
      <PartnersPanel onChange={resource.reload} />
      {resource.error ? (
        <Failure message={resource.error} retry={resource.reload} />
      ) : !resource.data ? (
        <Loading />
      ) : (
        <DataTable
          rows={resource.data.items || []}
          columns={[
            { key: "title", label: "Источник" },
            {
              key: "partner",
              label: "Рекламодатель",
              cell: (r) => r.partner || <span className="text-muted-foreground">—</span>,
            },
            { key: "clicks", label: "Переходы" },
            { key: "users", label: "Пользователи" },
            { key: "trial", label: "Пробный доступ" },
            {
              key: "connected",
              label: (
                <span title="Уникальные пользователи, хотя бы раз подключившиеся к VPN">
                  Вышли онлайн
                </span>
              ),
            },
            { key: "paid", label: "Оплатили" },
            {
              key: "actions",
              label: "",
              cell: (r) => (
                <div className="flex gap-2">
                  <ActionButton
                    variant="outline"
                    onAction={async () => {
                      await navigator.clipboard.writeText(r.url);
                      toast.success("Ссылка скопирована");
                    }}
                  >
                    <Copy />
                    Ссылка
                  </ActionButton>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      confirm({
                        title: "Скрыть источник?",
                        description:
                          "Он исчезнет из списка. Сама ссылка продолжит работать.",
                        action: async () => {
                          await api(`ads/${r.id}/archive`, {});
                          await resource.reload();
                        },
                      })
                    }
                  >
                    Скрыть
                  </Button>
                </div>
              ),
            },
          ]}
        />
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Новая рекламная ссылка</DialogTitle>
            <DialogDescription>
              Название поможет отличать источники в статистике.
            </DialogDescription>
          </DialogHeader>
          <Field label="Название источника">
            <Input
              aria-label="Название источника"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например, Telegram-канал о технологиях"
            />
          </Field>
          <Field
            label="Код ссылки"
            hint="Необязательно. Пустое поле — автоматическая генерация."
          >
            <Input
              aria-label="Код рекламной ссылки"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
          </Field>
          <ActionButton
            disabled={!title.trim()}
            onAction={async () => {
              await api("ads", { title, slug });
              setOpen(false);
              setTitle("");
              setSlug("");
              await resource.reload();
              toast.success("Ссылка создана");
            }}
          >
            Создать ссылку
          </ActionButton>
        </DialogContent>
      </Dialog>
    </div>
  );
}
export function ReferralsPage() {
  const navigate = useNavigate();
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Button
          variant="outline"
          onClick={() => navigate("settings?section=referrals")}
        >
          Настроить программу
        </Button>
      </div>
      <RecordsPage kind="referrals" />
    </div>
  );
}
