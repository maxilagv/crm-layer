"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { ListEditor } from "@/components/ui/list-editor";
import { Switch } from "@/components/ui/switch";
import {
  notificationPolicy,
  type NotificationPolicy,
} from "@/features/settings/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description && <p className="text-xs text-muted">{description}</p>}
      </div>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={label} />
    </div>
  );
}

export default function NotificationSettingsPage() {
  const { data, isLoading } = notificationPolicy.useRead();
  const update = notificationPolicy.useUpdate();
  const [form, setForm] = useState<Partial<NotificationPolicy>>({});
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);
  const set = <K extends keyof NotificationPolicy>(k: K, v: NotificationPolicy[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        notify_on_new_lead: form.notify_on_new_lead,
        notify_on_human_handoff: form.notify_on_human_handoff,
        notify_on_failed_ai_reply: form.notify_on_failed_ai_reply,
        notification_channels: form.notification_channels,
      });
      toast.success("Notificaciones guardadas");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <SettingsShell
      title="Notificaciones"
      description="Qué eventos te avisan y por qué canales."
      loading={isLoading}
    >
      <form onSubmit={save} className="space-y-4">
        <Card>
          <CardContent className="space-y-4">
            <ToggleRow
              label="Nuevo lead"
              description="Avisar cuando entra un lead nuevo."
              checked={!!form.notify_on_new_lead}
              onChange={(v) => set("notify_on_new_lead", v)}
            />
            <ToggleRow
              label="Handoff a humano"
              description="Avisar cuando una conversación necesita intervención."
              checked={!!form.notify_on_human_handoff}
              onChange={(v) => set("notify_on_human_handoff", v)}
            />
            <ToggleRow
              label="Falla de respuesta IA"
              description="Avisar cuando la IA no pudo responder."
              checked={!!form.notify_on_failed_ai_reply}
              onChange={(v) => set("notify_on_failed_ai_reply", v)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Field label="Canales de notificación" hint="Ej: whatsapp, email.">
              <ListEditor
                value={form.notification_channels ?? []}
                onChange={(v) => set("notification_channels", v)}
              />
            </Field>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" loading={update.isPending}>
            Guardar cambios
          </Button>
        </div>
      </form>
    </SettingsShell>
  );
}
