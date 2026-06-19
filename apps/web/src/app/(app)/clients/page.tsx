"use client";

import { Plus, Search, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/shell/page-container";
import { PageHeader } from "@/components/ui/page-header";
import {
  CLIENT_STATUS_LABELS,
  clientStatusTone,
  SUPPORT_LEVEL_LABELS,
  supportLevelTone,
  useClients,
  useContactPicker,
  useRegisterClient,
  type ClientFilters,
  type ClientListItem,
  type SupportLevel,
} from "@/features/clients/queries";
import { ApiError } from "@/lib/api/types";
import { relativeTime } from "@/lib/format";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "onboarding", label: "Onboarding" },
  { value: "paused", label: "Pausados" },
  { value: "delinquent", label: "Morosos" },
];

const SUPPORT_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "standard", label: "Estándar" },
  { value: "priority", label: "Prioritario" },
  { value: "vip", label: "VIP" },
  { value: "internal", label: "Interno" },
];

const SUPPORT_LEVELS: SupportLevel[] = ["standard", "priority", "vip", "internal"];

function GridSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="p-4">
          <div className="flex gap-3">
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="flex-1 space-y-2 py-0.5">
              <Skeleton className="h-3.5 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
        </Card>
      ))}
    </div>
  );
}

function ClientCard({ client }: { client: ClientListItem }) {
  const name = client.display_name || client.contact_display_name || "Cliente";
  return (
    <Link href={`/clients/${client.id}`} className="block cursor-pointer">
      <Card className="h-full p-4 transition-colors hover:bg-card-hover">
        <div className="flex items-start gap-3">
          <Avatar name={name} seed={client.id} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{name}</p>
            {client.contact_display_name &&
            client.contact_display_name !== name ? (
              <p className="truncate text-xs text-muted">
                {client.contact_display_name}
              </p>
            ) : client.service_plan ? (
              <p className="truncate text-xs text-muted">{client.service_plan}</p>
            ) : (
              <p className="text-xs text-muted">
                Alta {relativeTime(client.created_at)}
              </p>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge tone={clientStatusTone(client.status)} dot>
            {CLIENT_STATUS_LABELS[client.status]}
          </Badge>
          <Badge tone={supportLevelTone(client.support_level)}>
            {SUPPORT_LEVEL_LABELS[client.support_level]}
          </Badge>
        </div>
      </Card>
    </Link>
  );
}

function RegisterClientModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const register = useRegisterClient();
  const [contactSearch, setContactSearch] = useState("");
  const [contactId, setContactId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [supportLevel, setSupportLevel] = useState<SupportLevel>("standard");
  const { data: contactsData, isLoading: contactsLoading } =
    useContactPicker(contactSearch);

  function reset() {
    setContactSearch("");
    setContactId("");
    setDisplayName("");
    setSupportLevel("standard");
  }

  function close() {
    reset();
    onClose();
  }

  async function submit() {
    if (!contactId) {
      toast.error("Elegí un contacto");
      return;
    }
    try {
      await register.mutateAsync({
        contact_id: contactId,
        display_name: displayName.trim() || undefined,
        support_level: supportLevel,
      });
      toast.success("Cliente registrado");
      close();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo registrar",
      );
    }
  }

  const contacts = contactsData?.items ?? [];

  return (
    <Modal
      open={open}
      onClose={close}
      title="Registrar cliente"
      description="Convertí un contacto existente en una cuenta de cliente."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={close}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={register.isPending}>
            Registrar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Buscar contacto" htmlFor="client-contact-search">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              id="client-contact-search"
              value={contactSearch}
              onChange={(e) => setContactSearch(e.target.value)}
              placeholder="Nombre o teléfono…"
              className="pl-9"
            />
          </div>
        </Field>

        <Field
          label="Contacto"
          required
          hint="El cliente se asocia a este contacto."
        >
          <div className="max-h-52 space-y-1 overflow-y-auto rounded-lg border border-border p-1">
            {contactsLoading ? (
              <div className="space-y-1 p-1">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-md" />
                ))}
              </div>
            ) : contacts.length === 0 ? (
              <p className="px-2 py-6 text-center text-sm text-muted">
                Sin contactos para esa búsqueda.
              </p>
            ) : (
              contacts.map((c) => {
                const cname = c.display_name || c.primary_phone || "Sin nombre";
                const selected = c.id === contactId;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setContactId(c.id)}
                    className={
                      "flex w-full cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors " +
                      (selected
                        ? "bg-primary/12 ring-1 ring-inset ring-primary/30"
                        : "hover:bg-card-hover")
                    }
                  >
                    <Avatar name={cname} seed={c.id} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-foreground">{cname}</p>
                      {c.primary_phone && (
                        <p className="truncate text-xs text-muted">
                          {c.primary_phone}
                        </p>
                      )}
                    </div>
                    {selected && (
                      <Badge tone="primary" className="shrink-0">
                        Elegido
                      </Badge>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </Field>

        <Field
          label="Nombre a mostrar"
          htmlFor="client-display-name"
          hint="Opcional. Si lo dejás vacío se usa el del contacto."
        >
          <Input
            id="client-display-name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ej. Estudio Pérez"
          />
        </Field>

        <Field label="Nivel de soporte" htmlFor="client-support-level">
          <Select
            id="client-support-level"
            value={supportLevel}
            onChange={(e) => setSupportLevel(e.target.value as SupportLevel)}
          >
            {SUPPORT_LEVELS.map((lvl) => (
              <option key={lvl} value={lvl}>
                {SUPPORT_LEVEL_LABELS[lvl]}
              </option>
            ))}
          </Select>
        </Field>
      </div>
    </Modal>
  );
}

export default function ClientsPage() {
  const [status, setStatus] = useState("");
  const [supportLevel, setSupportLevel] = useState("");
  const [search, setSearch] = useState("");
  const [registerOpen, setRegisterOpen] = useState(false);

  const filters: ClientFilters = {
    status: status || undefined,
    support_level: supportLevel || undefined,
    search: search || undefined,
  };
  const { data, isLoading, isError } = useClients(filters);
  const clients = data?.items ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Clientes"
        description="Cuentas activas, nivel de soporte, contactos y servicios."
        actions={
          <Button
            onClick={() => setRegisterOpen(true)}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Registrar cliente
          </Button>
        }
      />

      <div className="mt-6 space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar cliente…"
            className="pl-9"
          />
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <Segmented options={STATUS_OPTIONS} value={status} onChange={setStatus} />
          <Segmented
            options={SUPPORT_OPTIONS}
            value={supportLevel}
            onChange={setSupportLevel}
          />
        </div>
      </div>

      <div className="mt-6">
        {isLoading ? (
          <GridSkeleton />
        ) : isError ? (
          <EmptyState
            icon={Users}
            title="No se pudieron cargar"
            description="Revisá la conexión con el backend."
          />
        ) : clients.length === 0 ? (
          <EmptyState
            icon={Users}
            title="Sin clientes"
            description="Registrá tu primer cliente a partir de un contacto."
            action={
              <Button
                onClick={() => setRegisterOpen(true)}
                leftIcon={<Plus className="h-4 w-4" />}
              >
                Registrar cliente
              </Button>
            }
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {clients.map((c) => (
              <ClientCard key={c.id} client={c} />
            ))}
          </div>
        )}
      </div>

      <RegisterClientModal
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
      />
    </PageContainer>
  );
}
