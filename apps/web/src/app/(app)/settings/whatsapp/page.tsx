"use client";

import { CheckCircle2, Copy, Plus, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/field";
import { ListEditor } from "@/components/ui/list-editor";
import { Switch } from "@/components/ui/switch";
import {
  useBridgeStatus,
  useCreateWhatsappAccount,
  useCreateWhatsappNumber,
  useWhatsappAccounts,
  useWhatsappConnection,
  useWhatsappNumbers,
  whatsappPolicy,
  type WhatsappPolicy,
} from "@/features/settings/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { API_BASE } from "@/lib/api/client";
import { ApiError } from "@/lib/api/types";

function CredentialRow({ label, ok, hint }: { label: string; ok: boolean; hint?: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2.5">
      <div className="flex items-center gap-2.5">
        {ok ? (
          <CheckCircle2 className="h-4 w-4 text-success" />
        ) : (
          <XCircle className="h-4 w-4 text-muted" />
        )}
        <div>
          <p className="text-sm font-medium text-foreground">{label}</p>
          {hint && <p className="font-mono text-[11px] text-muted">{hint}</p>}
        </div>
      </div>
      <Badge tone={ok ? "success" : "muted"}>
        {ok ? "Configurado" : "Falta"}
      </Badge>
    </div>
  );
}

function BridgeCard() {
  const { data } = useBridgeStatus();
  const state = data?.state ?? "disconnected";
  const connected = state === "ready" || state === "authenticated";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Conexión por QR (puente de prueba)</CardTitle>
          <Badge
            tone={connected ? "success" : state === "qr" ? "warning" : "muted"}
            dot
          >
            {connected ? "Conectado" : state === "qr" ? "Escaneá el QR" : "Desconectado"}
          </Badge>
        </div>
        <p className="text-sm text-muted">
          Vía no oficial para probar ya mismo. Usá un número de prueba, no tu línea
          principal.
        </p>
      </CardHeader>
      <CardContent>
        {connected ? (
          <div className="flex items-center gap-3 rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-sm text-foreground">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
            El bot está conectado y responde por WhatsApp.
          </div>
        ) : state === "qr" && data?.qr ? (
          <div className="flex flex-col items-center gap-3 py-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={data.qr}
              alt="Código QR para vincular WhatsApp"
              className="h-56 w-56 rounded-xl bg-white p-2"
            />
            <p className="max-w-sm text-center text-sm text-muted">
              Abrí WhatsApp en el número de prueba › <b>Dispositivos vinculados</b> ›
              Vincular un dispositivo, y escaneá este QR.
            </p>
          </div>
        ) : (
          <div className="space-y-2 rounded-lg border border-border bg-bg-subtle px-4 py-3 text-sm text-muted">
            <p className="font-medium text-foreground">El puente no está corriendo.</p>
            <p>Arrancalo para generar el QR acá:</p>
            <code className="block rounded-md bg-card px-3 py-2 font-mono text-xs text-foreground">
              pnpm --filter @ai-crm/wa-bridge start
            </code>
            <p>
              Necesita <code className="font-mono">ORGANIZATION_ID</code> y la IA
              configurada (ver el README del puente).
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ConnectionCard() {
  const { data } = useWhatsappConnection();
  const webhookUrl = `${API_BASE}${data?.webhook_path ?? "/api/v1/webhooks/whatsapp/"}`;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Conexión</CardTitle>
          {data && (
            <Badge tone={data.connected ? "success" : "warning"} dot>
              {data.connected ? "Conectado" : "Pendiente"}
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted">
          Los tokens secretos se configuran en el backend (variables de entorno).
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        <CredentialRow
          label="Access token"
          ok={!!data?.credentials.access_token}
          hint="WHATSAPP_ACCESS_TOKEN"
        />
        <CredentialRow
          label="Verify token"
          ok={!!data?.credentials.verify_token}
          hint="WHATSAPP_VERIFY_TOKEN"
        />
        <CredentialRow
          label="App secret"
          ok={!!data?.credentials.app_secret}
          hint="WHATSAPP_APP_SECRET"
        />
        <div className="rounded-lg border border-border bg-bg-subtle px-3 py-2.5">
          <p className="text-xs text-muted">URL del webhook (configurala en Meta)</p>
          <div className="mt-1 flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
              {webhookUrl}
            </code>
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard?.writeText(webhookUrl);
                toast.success("URL copiada");
              }}
              aria-label="Copiar URL"
              className="cursor-pointer rounded-md p-1.5 text-muted transition-colors hover:bg-card-hover hover:text-foreground"
            >
              <Copy className="h-4 w-4" />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AccountsCard() {
  const { data: accounts } = useWhatsappAccounts();
  const create = useCreateWhatsappAccount();
  const [wabaId, setWabaId] = useState("");
  const [name, setName] = useState("");

  async function add() {
    if (!wabaId.trim()) return;
    try {
      await create.mutateAsync({ waba_id: wabaId.trim(), name: name.trim() });
      setWabaId("");
      setName("");
      toast.success("Cuenta registrada");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo registrar");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cuentas de WhatsApp (WABA)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {(accounts ?? []).map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5"
          >
            <div>
              <p className="text-sm font-medium text-foreground">{a.name || "Sin nombre"}</p>
              <p className="font-mono text-xs text-muted">{a.waba_id}</p>
            </div>
            <Badge tone="muted">{a.status}</Badge>
          </div>
        ))}
        <div className="flex flex-col gap-2 border-t border-border pt-3 sm:flex-row">
          <Input
            value={wabaId}
            onChange={(e) => setWabaId(e.target.value)}
            placeholder="WABA ID"
            className="sm:flex-1"
          />
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre"
            className="sm:flex-1"
          />
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

function NumbersCard() {
  const { data: accounts } = useWhatsappAccounts();
  const { data: numbers } = useWhatsappNumbers();
  const create = useCreateWhatsappNumber();
  const [accountId, setAccountId] = useState("");
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [display, setDisplay] = useState("");

  useEffect(() => {
    if (!accountId && accounts && accounts.length > 0) setAccountId(accounts[0].id);
  }, [accounts, accountId]);

  async function add() {
    if (!accountId || !phoneNumberId.trim()) return;
    try {
      await create.mutateAsync({
        business_account_id: accountId,
        phone_number_id: phoneNumberId.trim(),
        display_phone_number: display.trim(),
      });
      setPhoneNumberId("");
      setDisplay("");
      toast.success("Número registrado");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo registrar");
    }
  }

  const hasAccounts = (accounts ?? []).length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Números</CardTitle>
        {!hasAccounts && (
          <p className="text-sm text-muted">Registrá primero una cuenta WABA.</p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {(numbers ?? []).map((n) => (
          <div
            key={n.id}
            className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5"
          >
            <div>
              <p className="text-sm font-medium text-foreground">
                {n.display_phone_number || n.verified_name || "Número"}
              </p>
              <p className="font-mono text-xs text-muted">{n.phone_number_id}</p>
            </div>
            <Badge tone="muted">{n.status}</Badge>
          </div>
        ))}
        {hasAccounts && (
          <div className="space-y-2 border-t border-border pt-3">
            <Select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
              {(accounts ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name || a.waba_id}
                </option>
              ))}
            </Select>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={phoneNumberId}
                onChange={(e) => setPhoneNumberId(e.target.value)}
                placeholder="Phone number ID"
                className="sm:flex-1"
              />
              <Input
                value={display}
                onChange={(e) => setDisplay(e.target.value)}
                placeholder="+54 11 …"
                className="sm:flex-1"
              />
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
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PolicyCard() {
  const { data } = whatsappPolicy.useRead();
  const update = whatsappPolicy.useUpdate();
  const [form, setForm] = useState<Partial<WhatsappPolicy>>({});
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);
  const set = <K extends keyof WhatsappPolicy>(k: K, v: WhatsappPolicy[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    try {
      await update.mutateAsync({
        auto_reply_enabled: form.auto_reply_enabled,
        media_download_enabled: form.media_download_enabled,
        handoff_keywords: form.handoff_keywords,
        opt_out_keywords: form.opt_out_keywords,
      });
      toast.success("Política guardada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Política de WhatsApp</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">Auto-respuesta</p>
          <Switch
            checked={!!form.auto_reply_enabled}
            onCheckedChange={(v) => set("auto_reply_enabled", v)}
            aria-label="Auto-respuesta WhatsApp"
          />
        </div>
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">Descargar media</p>
          <Switch
            checked={!!form.media_download_enabled}
            onCheckedChange={(v) => set("media_download_enabled", v)}
            aria-label="Descargar media"
          />
        </div>
        <Field label="Palabras de handoff" hint="Disparan derivación a un humano.">
          <ListEditor
            value={form.handoff_keywords ?? []}
            onChange={(v) => set("handoff_keywords", v)}
          />
        </Field>
        <Field label="Palabras de opt-out" hint="El contacto pide no recibir más mensajes.">
          <ListEditor
            value={form.opt_out_keywords ?? []}
            onChange={(v) => set("opt_out_keywords", v)}
          />
        </Field>
        <div className="flex justify-end">
          <Button type="button" onClick={save} loading={update.isPending}>
            Guardar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function WhatsappSettingsPage() {
  return (
    <SettingsShell
      title="WhatsApp"
      description="Conectá tu número, registrá las cuentas y ajustá la política."
    >
      <BridgeCard />
      <ConnectionCard />
      <AccountsCard />
      <NumbersCard />
      <PolicyCard />
    </SettingsShell>
  );
}
