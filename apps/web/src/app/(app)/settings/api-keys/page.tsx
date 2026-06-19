"use client";

import {
  AlertTriangle,
  Check,
  Copy,
  KeyRound,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, Input } from "@/components/ui/field";
import { ListEditor } from "@/components/ui/list-editor";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { SettingsShell } from "@/features/settings/settings-shell";
import {
  API_KEY_STATE_LABELS,
  apiKeyState,
  apiKeyStateTone,
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  type APIKey,
  type APIKeyCreated,
} from "@/features/settings/api-keys-queries";
import { ApiError } from "@/lib/api/types";
import { shortDateTime } from "@/lib/format";

/* ----------------------------------------------------------------- skeleton */

function ListSkeleton() {
  return (
    <Card>
      <CardContent className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-3"
          >
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3.5 w-1/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

/* --------------------------------------------------------------- secret card */

function SecretReveal({ created }: { created: APIKeyCreated }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
      toast.success("Clave copiada");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("No se pudo copiar");
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2.5 rounded-lg border border-warning/20 bg-warning/10 px-3 py-2.5">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <p className="text-sm text-foreground">
          Guardala ahora: por seguridad{" "}
          <span className="font-medium">no se vuelve a mostrar</span>.
        </p>
      </div>
      <Field label="Clave secreta" hint={`Para "${created.name}"`}>
        <div className="flex gap-2">
          <Input
            readOnly
            value={created.key}
            onFocus={(e) => e.currentTarget.select()}
            className="font-mono text-xs"
          />
          <Button
            type="button"
            variant="secondary"
            size="icon"
            onClick={copy}
            aria-label="Copiar clave"
          >
            {copied ? (
              <Check className="h-4 w-4 text-success" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        </div>
      </Field>
    </div>
  );
}

/* ----------------------------------------------------------------- key row */

function ApiKeyRow({ k, onRevoke }: { k: APIKey; onRevoke: (k: APIKey) => void }) {
  const state = apiKeyState(k);
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-medium text-foreground">{k.name}</p>
          <Badge tone={apiKeyStateTone(state)} dot>
            {API_KEY_STATE_LABELS[state]}
          </Badge>
        </div>
        <p className="font-mono text-xs text-muted">{k.prefix}…</p>
        {k.scopes.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {k.scopes.map((s) => (
              <Badge key={s} tone="muted">
                {s}
              </Badge>
            ))}
          </div>
        )}
        <p className="text-xs text-muted">
          Creada {shortDateTime(k.created_at)}
          {k.expires_at ? ` · Vence ${shortDateTime(k.expires_at)}` : " · Sin vencimiento"}
        </p>
      </div>
      {state !== "revoked" ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onRevoke(k)}
          leftIcon={<Trash2 className="h-4 w-4" />}
          className="shrink-0 self-start text-danger hover:text-danger sm:self-center"
        >
          Revocar
        </Button>
      ) : null}
    </div>
  );
}

/* ----------------------------------------------------------------- page */

export default function ApiKeysSettingsPage() {
  const { data, isLoading, isError } = useApiKeys();
  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const [secret, setSecret] = useState<APIKeyCreated | null>(null);
  const [toRevoke, setToRevoke] = useState<APIKey | null>(null);

  function openCreate() {
    setName("");
    setScopes([]);
    setCreateOpen(true);
  }

  async function submitCreate() {
    if (!name.trim()) {
      toast.error("Poné un nombre para identificar la clave");
      return;
    }
    try {
      const created = await create.mutateAsync({
        name: name.trim(),
        scopes,
      });
      setCreateOpen(false);
      setSecret(created);
      toast.success("API key creada");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo crear la clave",
      );
    }
  }

  async function confirmRevoke() {
    if (!toRevoke) return;
    try {
      await revoke.mutateAsync(toRevoke.id);
      toast.success("API key revocada");
      setToRevoke(null);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo revocar la clave",
      );
    }
  }

  return (
    <SettingsShell
      title="API Keys"
      description="Claves para acceso programático al backend. El secreto se muestra una sola vez al crearlo."
    >
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={openCreate}
          leftIcon={<Plus className="h-4 w-4" />}
        >
          Nueva API key
        </Button>
      </div>

      {isLoading ? (
        <ListSkeleton />
      ) : isError ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={KeyRound}
              title="No se pudieron cargar las claves"
              description="Revisá la conexión con el backend e intentá de nuevo."
            />
          </CardContent>
        </Card>
      ) : !data || data.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={KeyRound}
              title="Sin API keys"
              description="Creá una clave para conectar tus integraciones con el backend."
              action={
                <Button
                  type="button"
                  onClick={openCreate}
                  leftIcon={<Plus className="h-4 w-4" />}
                >
                  Nueva API key
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="space-y-3">
            {data.map((k) => (
              <ApiKeyRow key={k.id} k={k} onRevoke={setToRevoke} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Crear */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Nueva API key"
        description="El secreto se mostrará una sola vez al finalizar."
        footer={
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setCreateOpen(false)}
            >
              Cancelar
            </Button>
            <Button type="button" onClick={submitCreate} loading={create.isPending}>
              Crear clave
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Nombre" htmlFor="key-name" hint="Para reconocer dónde se usa.">
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Integración Zapier"
              autoFocus
            />
          </Field>
          <Field
            label="Scopes"
            hint="Opcional. Limitá los permisos de esta clave."
          >
            <ListEditor
              value={scopes}
              onChange={setScopes}
              placeholder="Agregar scope y Enter…"
            />
          </Field>
        </div>
      </Modal>

      {/* Secreto (una sola vez) */}
      <Modal
        open={!!secret}
        onClose={() => setSecret(null)}
        title="Tu nueva API key"
        footer={
          <Button type="button" onClick={() => setSecret(null)}>
            Ya la guardé
          </Button>
        }
      >
        {secret && <SecretReveal created={secret} />}
      </Modal>

      {/* Revocar */}
      <Modal
        open={!!toRevoke}
        onClose={() => setToRevoke(null)}
        title="Revocar API key"
        description={
          toRevoke
            ? `"${toRevoke.name}" dejará de funcionar de inmediato. Esta acción no se puede deshacer.`
            : undefined
        }
        footer={
          <>
            <Button type="button" variant="ghost" onClick={() => setToRevoke(null)}>
              Cancelar
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={confirmRevoke}
              loading={revoke.isPending}
              leftIcon={<Trash2 className="h-4 w-4" />}
            >
              Revocar
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted">
          Cualquier integración que use esta clave perderá acceso.
        </p>
      </Modal>
    </SettingsShell>
  );
}
