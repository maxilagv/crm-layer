"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Textarea } from "@/components/ui/field";
import { ListEditor } from "@/components/ui/list-editor";
import { supportPolicy, type SupportPolicy } from "@/features/settings/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";

export default function SupportSettingsPage() {
  const { data, isLoading } = supportPolicy.useRead();
  const update = supportPolicy.useUpdate();
  const [form, setForm] = useState<Partial<SupportPolicy>>({});
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);
  const set = <K extends keyof SupportPolicy>(k: K, v: SupportPolicy[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        data_request_policy: form.data_request_policy,
        default_support_reply: form.default_support_reply,
        allowed_support_actions: form.allowed_support_actions,
        forbidden_support_actions: form.forbidden_support_actions,
        urgent_keywords: form.urgent_keywords,
        critical_ticket_rules: form.critical_ticket_rules,
      });
      toast.success("Política de soporte guardada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <SettingsShell
      title="Política de soporte"
      description="Cómo responde el agente en soporte y qué tiene prohibido."
      loading={isLoading}
    >
      <form onSubmit={save} className="space-y-4">
        <Card>
          <CardContent className="space-y-4">
            <Field
              label="Respuesta de soporte por defecto"
              htmlFor="reply"
              hint="Mensaje base cuando no hay info suficiente."
            >
              <Textarea
                id="reply"
                value={form.default_support_reply ?? ""}
                onChange={(e) => set("default_support_reply", e.target.value)}
              />
            </Field>
            <Field label="Política de pedido de datos" htmlFor="datapol">
              <Textarea
                id="datapol"
                value={form.data_request_policy ?? ""}
                onChange={(e) => set("data_request_policy", e.target.value)}
              />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <Field label="Acciones permitidas">
              <ListEditor
                value={form.allowed_support_actions ?? []}
                onChange={(v) => set("allowed_support_actions", v)}
              />
            </Field>
            <Field label="Acciones prohibidas" hint="Ej: pedir contraseñas o tokens.">
              <ListEditor
                value={form.forbidden_support_actions ?? []}
                onChange={(v) => set("forbidden_support_actions", v)}
              />
            </Field>
            <Field label="Palabras urgentes">
              <ListEditor
                value={form.urgent_keywords ?? []}
                onChange={(v) => set("urgent_keywords", v)}
              />
            </Field>
            <Field label="Reglas de ticket crítico">
              <ListEditor
                value={form.critical_ticket_rules ?? []}
                onChange={(v) => set("critical_ticket_rules", v)}
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
