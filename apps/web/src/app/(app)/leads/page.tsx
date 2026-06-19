"use client";

import { Search, Target } from "lucide-react";
import { useState } from "react";
import { PageContainer } from "@/components/shell/page-container";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { LeadListRow } from "@/features/leads/lead-list-item";
import { type LeadFilters, useLeads } from "@/features/leads/queries";

const STAGE_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "new", label: "Nuevos" },
  { value: "qualifying", label: "Calificando" },
  { value: "hot", label: "Calientes" },
  { value: "proposal_pending", label: "Propuesta" },
  { value: "won", label: "Ganados" },
];

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "nurturing", label: "Nutrición" },
  { value: "won", label: "Ganados" },
  { value: "lost", label: "Perdidos" },
];

const TEMPERATURE_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todas" },
  { value: "cold", label: "Frío" },
  { value: "warm", label: "Tibio" },
  { value: "hot", label: "Caliente" },
  { value: "critical", label: "Crítico" },
];

function ListSkeleton() {
  return (
    <div className="space-y-1 p-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex gap-3 py-3">
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-2 py-1">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-4 w-40" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LeadsPage() {
  const [stage, setStage] = useState("");
  const [status, setStatus] = useState("");
  const [temperature, setTemperature] = useState("");
  const [search, setSearch] = useState("");

  const filters: LeadFilters = {
    stage: stage || undefined,
    status: status || undefined,
    temperature: temperature || undefined,
    search: search || undefined,
  };
  const { data, isLoading, isError } = useLeads(filters);

  return (
    <PageContainer>
      <PageHeader
        title="Leads"
        description="Pipeline comercial, scoring y próxima acción."
      />

      <div className="mt-5 space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por contacto, empresa o interés…"
            className="pl-9"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Segmented
            options={STAGE_OPTIONS}
            value={stage}
            onChange={setStage}
            className="w-full"
          />
          <div className="flex flex-col gap-2 sm:flex-row">
            <Segmented
              options={STATUS_OPTIONS}
              value={status}
              onChange={setStatus}
              className="sm:flex-1"
            />
            <Segmented
              options={TEMPERATURE_OPTIONS}
              value={temperature}
              onChange={setTemperature}
              className="sm:flex-1"
            />
          </div>
        </div>
      </div>

      <Card className="mt-4 overflow-hidden p-0">
        {isLoading ? (
          <ListSkeleton />
        ) : isError ? (
          <div className="p-6">
            <EmptyState
              icon={Target}
              title="No se pudieron cargar los leads"
              description="Revisá la conexión con el backend e intentá de nuevo."
            />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Target}
              title="Sin leads"
              description="Cuando se generen leads desde WhatsApp o se carguen manualmente van a aparecer acá."
            />
          </div>
        ) : (
          <div>
            {data.items.map((lead) => (
              <LeadListRow key={lead.id} lead={lead} />
            ))}
          </div>
        )}
      </Card>
    </PageContainer>
  );
}
