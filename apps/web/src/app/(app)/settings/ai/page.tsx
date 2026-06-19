"use client";

import { CheckCircle2, Plus, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import {
  aiPolicy,
  type AiPolicy,
  useAiConnection,
  useAiProviders,
  useCreateAiProvider,
  useUpdateAiProvider,
} from "@/features/settings/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";

function ConnectionCard() {
  const { data } = useAiConnection();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Conexión</CardTitle>
        <p className="text-sm text-muted">
          La API key secreta se configura en el backend (variable de entorno).
          Acá ves el estado y gestionás los proveedores.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {(data?.providers ?? []).map((p) => (
          <div
            key={p.provider_type}
            className="flex items-center justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2.5"
          >
            <div className="flex items-center gap-2.5">
              {p.credential_configured ? (
                <CheckCircle2 className="h-4 w-4 text-success" />
              ) : (
                <XCircle className="h-4 w-4 text-muted" />
              )}
              <div>
                <p className="text-sm font-medium text-foreground">{p.label}</p>
                {p.env_var && (
                  <p className="font-mono text-[11px] text-muted">{p.env_var}</p>
                )}
              </div>
            </div>
            <Badge tone={p.credential_configured ? "success" : "muted"}>
              {p.credential_configured ? "Key configurada" : "Sin key"}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ProvidersCard() {
  const { data: providers } = useAiProviders();
  const create = useCreateAiProvider();
  const update = useUpdateAiProvider();
  const [name, setName] = useState("");
  const [type, setType] = useState("gemini");

  async function add() {
    if (!name.trim()) return;
    try {
      await create.mutateAsync({ name: name.trim(), provider_type: type });
      setName("");
      toast.success("Proveedor agregado");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo agregar");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proveedores</CardTitle>
        <p className="text-sm text-muted">
          El router usa el proveedor habilitado de menor prioridad.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {(providers ?? []).map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5"
          >
            <div>
              <p className="text-sm font-medium text-foreground">{p.name}</p>
              <p className="text-xs text-muted">
                {p.provider_type} · prioridad {p.priority}
              </p>
            </div>
            <Switch
              checked={p.is_enabled}
              onCheckedChange={(v) => update.mutate({ id: p.id, is_enabled: v })}
              aria-label={`Habilitar ${p.name}`}
            />
          </div>
        ))}
        <div className="flex flex-col gap-2 border-t border-border pt-3 sm:flex-row">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre del proveedor"
            className="sm:flex-1"
          />
          <Select value={type} onChange={(e) => setType(e.target.value)} className="sm:w-40">
            <option value="gemini">Google Gemini (gratis)</option>
            <option value="openai">OpenAI</option>
            <option value="fake">Fake (pruebas)</option>
          </Select>
          <Button
            type="button"
            variant="secondary"
            onClick={add}
            loading={create.isPending}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Agregar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function PolicyCard() {
  const { data } = aiPolicy.useRead();
  const update = aiPolicy.useUpdate();
  const [form, setForm] = useState<Partial<AiPolicy>>({});
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);
  const set = <K extends keyof AiPolicy>(k: K, v: AiPolicy[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    try {
      await update.mutateAsync({
        auto_reply_enabled: form.auto_reply_enabled,
        human_handoff_required_for_risks: form.human_handoff_required_for_risks,
        default_sales_model: form.default_sales_model,
        default_support_model: form.default_support_model,
        temperature_sales: form.temperature_sales,
        temperature_support: form.temperature_support,
        max_context_messages: form.max_context_messages,
      });
      toast.success("Comportamiento guardado");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comportamiento del agente</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">Auto-respuesta</p>
            <p className="text-xs text-muted">La IA responde sin intervención.</p>
          </div>
          <Switch
            checked={!!form.auto_reply_enabled}
            onCheckedChange={(v) => set("auto_reply_enabled", v)}
            aria-label="Auto-respuesta"
          />
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">
              Handoff ante riesgo
            </p>
            <p className="text-xs text-muted">
              Derivar a humano cuando el mensaje sea riesgoso.
            </p>
          </div>
          <Switch
            checked={!!form.human_handoff_required_for_risks}
            onCheckedChange={(v) => set("human_handoff_required_for_risks", v)}
            aria-label="Handoff ante riesgo"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Modelo de ventas" htmlFor="ai-sales-model">
            <Input
              id="ai-sales-model"
              value={form.default_sales_model ?? ""}
              onChange={(e) => set("default_sales_model", e.target.value)}
            />
          </Field>
          <Field label="Modelo de soporte" htmlFor="ai-support-model">
            <Input
              id="ai-support-model"
              value={form.default_support_model ?? ""}
              onChange={(e) => set("default_support_model", e.target.value)}
            />
          </Field>
          <Field label="Temperatura ventas" htmlFor="ai-temp-sales">
            <Input
              id="ai-temp-sales"
              value={form.temperature_sales ?? ""}
              onChange={(e) => set("temperature_sales", e.target.value)}
            />
          </Field>
          <Field label="Temperatura soporte" htmlFor="ai-temp-support">
            <Input
              id="ai-temp-support"
              value={form.temperature_support ?? ""}
              onChange={(e) => set("temperature_support", e.target.value)}
            />
          </Field>
          <Field label="Mensajes de contexto" htmlFor="ai-ctx">
            <Input
              id="ai-ctx"
              type="number"
              value={form.max_context_messages ?? 0}
              onChange={(e) =>
                set("max_context_messages", Number(e.target.value))
              }
            />
          </Field>
        </div>
        <div className="flex justify-end">
          <Button type="button" onClick={save} loading={update.isPending}>
            Guardar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AiSettingsPage() {
  return (
    <SettingsShell
      title="Inteligencia artificial"
      description="Proveedores, credenciales y comportamiento del agente."
    >
      <ConnectionCard />
      <ProvidersCard />
      <PolicyCard />
    </SettingsShell>
  );
}
