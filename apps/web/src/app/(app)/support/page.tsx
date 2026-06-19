"use client";

import { LifeBuoy, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/shell/page-container";
import { CreateTicketModal } from "@/features/support/create-ticket-modal";
import {
  TICKET_CATEGORY_LABELS,
  TICKET_PRIORITY_LABELS,
  TICKET_STATUS_LABELS,
  categoryTone,
  priorityTone,
  statusTone,
  useTickets,
  type TicketCategory,
  type TicketFilters,
  type TicketListItem,
  type TicketPriority,
} from "@/features/support/queries";
import { relativeTime } from "@/lib/format";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "open", label: "Abiertos" },
  { value: "in_progress", label: "En curso" },
  { value: "waiting_client", label: "Esperando" },
  { value: "resolved", label: "Resueltos" },
];

const PRIORITY_ENTRIES = Object.entries(TICKET_PRIORITY_LABELS) as [
  TicketPriority,
  string,
][];
const CATEGORY_ENTRIES = Object.entries(TICKET_CATEGORY_LABELS) as [
  TicketCategory,
  string,
][];

function TicketRow({ t }: { t: TicketListItem }) {
  return (
    <Link
      href={`/support/${t.id}`}
      className="block cursor-pointer rounded-xl border border-border bg-card p-4 transition-colors hover:border-border-strong hover:bg-card-hover"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="truncate text-sm font-medium text-foreground">
            {t.title}
          </p>
          <p className="truncate text-xs text-muted">
            {t.contact_display_name || "Contacto sin nombre"}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Badge tone={priorityTone(t.priority)} dot>
            {TICKET_PRIORITY_LABELS[t.priority]}
          </Badge>
          <span className="text-[11px] text-muted">
            {relativeTime(t.updated_at)}
          </span>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge tone={statusTone(t.status)}>
          {TICKET_STATUS_LABELS[t.status]}
        </Badge>
        <Badge tone={categoryTone(t.category)}>
          {TICKET_CATEGORY_LABELS[t.category]}
        </Badge>
      </div>
    </Link>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="space-y-3 rounded-xl border border-border bg-card p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3.5 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <div className="flex gap-1.5">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SupportPage() {
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const filters: TicketFilters = {
    status: status || undefined,
    priority: priority || undefined,
    category: category || undefined,
    search: search || undefined,
  };
  const { data, isLoading, isError } = useTickets(filters);
  const tickets = data?.items ?? [];

  return (
    <PageContainer>
      <PageHeader
        title="Soporte"
        description="Tickets, prioridad, categoría y resolución."
        actions={
          <Button
            onClick={() => setCreateOpen(true)}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Nuevo ticket
          </Button>
        }
      />

      <div className="mt-6 space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por título o contacto…"
            className="pl-9"
          />
        </div>
        <Segmented
          options={STATUS_OPTIONS}
          value={status}
          onChange={setStatus}
          className="w-full justify-between"
        />
        <div className="grid gap-2 sm:grid-cols-2">
          <Select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            aria-label="Prioridad"
          >
            <option value="">Toda prioridad</option>
            {PRIORITY_ENTRIES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <Select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-label="Categoría"
          >
            <option value="">Toda categoría</option>
            {CATEGORY_ENTRIES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="mt-4">
        {isLoading ? (
          <ListSkeleton />
        ) : isError ? (
          <EmptyState
            icon={LifeBuoy}
            title="No se pudieron cargar los tickets"
            description="Revisá la conexión con el backend e intentá de nuevo."
          />
        ) : tickets.length === 0 ? (
          <EmptyState
            icon={LifeBuoy}
            title="Sin tickets"
            description="Cuando se abran tickets de soporte van a aparecer acá."
            action={
              <Button
                onClick={() => setCreateOpen(true)}
                leftIcon={<Plus className="h-4 w-4" />}
              >
                Crear el primero
              </Button>
            }
          />
        ) : (
          <div className="space-y-3">
            {tickets.map((t) => (
              <TicketRow key={t.id} t={t} />
            ))}
          </div>
        )}
      </div>

      <CreateTicketModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          setCreateOpen(false);
          router.push(`/support/${id}`);
        }}
      />
    </PageContainer>
  );
}
