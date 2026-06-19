"use client";

import { Plus, Search, Users } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/shell/page-container";
import { ContactRow } from "@/features/contacts/contact-row";
import { CreateContactModal } from "@/features/contacts/create-contact-modal";
import {
  CONTACT_SOURCE_LABELS,
  useContacts,
  type ContactFilters,
  type ContactSource,
} from "@/features/contacts/queries";

const TYPE_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "lead", label: "Leads" },
  { value: "client", label: "Clientes" },
  { value: "supplier", label: "Proveedores" },
];

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "inactive", label: "Inactivos" },
  { value: "blocked", label: "Bloqueados" },
];

const SOURCE_VALUES: ContactSource[] = [
  "whatsapp",
  "email",
  "manual",
  "import",
  "api",
  "system",
];

function ListSkeleton() {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-4 py-3">
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="hidden h-5 w-16 rounded-full sm:block" />
        </div>
      ))}
    </div>
  );
}

export default function ContactsPage() {
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [tag, setTag] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const filters: ContactFilters = {
    search: search || undefined,
    type: type || undefined,
    status: status || undefined,
    source: source || undefined,
    tag: tag || undefined,
  };
  const { data, isLoading, isError } = useContacts(filters);

  const total = data?.pagination.total ?? 0;

  return (
    <PageContainer>
      <PageHeader
        title="Contactos"
        description="Personas y empresas: teléfonos, etiquetas y notas."
        actions={
          <Button
            onClick={() => setCreateOpen(true)}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Nuevo contacto
          </Button>
        }
      />

      <div className="mt-6 space-y-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, teléfono o email…"
              className="pl-9"
            />
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              aria-label="Origen"
              className="sm:w-40"
            >
              <option value="">Todos los orígenes</option>
              {SOURCE_VALUES.map((s) => (
                <option key={s} value={s}>
                  {CONTACT_SOURCE_LABELS[s]}
                </option>
              ))}
            </Select>
            <Input
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              placeholder="Etiqueta…"
              aria-label="Filtrar por etiqueta"
              className="sm:w-40"
            />
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Segmented options={TYPE_OPTIONS} value={type} onChange={setType} />
          <Segmented
            options={STATUS_OPTIONS}
            value={status}
            onChange={setStatus}
          />
        </div>
      </div>

      <Card className="mt-4 overflow-hidden p-0">
        {isLoading ? (
          <ListSkeleton />
        ) : isError ? (
          <div className="p-4">
            <EmptyState
              icon={Users}
              title="No se pudieron cargar los contactos"
              description="Revisá la conexión con el backend e intentá de nuevo."
            />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={Users}
              title="Sin contactos"
              description="Creá tu primer contacto o esperá a que lleguen mensajes por WhatsApp."
              action={
                <Button
                  variant="secondary"
                  onClick={() => setCreateOpen(true)}
                  leftIcon={<Plus className="h-4 w-4" />}
                >
                  Nuevo contacto
                </Button>
              }
            />
          </div>
        ) : (
          <>
            <div className="divide-y divide-border">
              {data.items.map((c) => (
                <ContactRow key={c.id} c={c} />
              ))}
            </div>
            <div className="border-t border-border px-4 py-2.5 text-xs text-muted">
              {total} {total === 1 ? "contacto" : "contactos"}
              {data.pagination.has_next && " · mostrando los primeros 50"}
            </div>
          </>
        )}
      </Card>

      <CreateContactModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </PageContainer>
  );
}
