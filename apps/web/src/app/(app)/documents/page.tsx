"use client";

import { FileText, Search } from "lucide-react";
import { useState } from "react";
import { PageContainer } from "@/components/shell/page-container";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { DocumentRow } from "@/features/documents/document-row";
import { type DocumentFilters, useDocuments } from "@/features/documents/queries";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todos" },
  { value: "ready", label: "Listos" },
  { value: "sent", label: "Enviados" },
  { value: "draft", label: "Borradores" },
];

function ListSkeleton() {
  return (
    <div className="space-y-1 p-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 py-3">
          <Skeleton className="h-9 w-9 rounded-lg" />
          <div className="flex-1 space-y-2 py-1">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

export default function DocumentsPage() {
  const [type, setType] = useState("");
  const [format, setFormat] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");

  const filters: DocumentFilters = {
    doc_type: type || undefined,
    format: format || undefined,
    status: status || undefined,
    search: search || undefined,
  };
  const { data, isLoading, isError } = useDocuments(filters);

  return (
    <PageContainer>
      <PageHeader
        title="Documentos"
        description="Propuestas, presupuestos e informes generados por el agente y desde el panel."
      />

      <div className="mt-5 space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por título…"
            className="pl-9"
          />
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="sm:max-w-[220px]"
          >
            <option value="">Todos los tipos</option>
            <option value="proposal">Propuestas</option>
            <option value="quote">Presupuestos</option>
            <option value="invoice">Facturas</option>
            <option value="report">Informes</option>
            <option value="deck">Presentaciones</option>
          </Select>
          <Select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="sm:max-w-[180px]"
          >
            <option value="">Todos los formatos</option>
            <option value="pdf">PDF</option>
            <option value="xlsx">Excel</option>
            <option value="pptx">PowerPoint</option>
          </Select>
        </div>
        <Segmented options={STATUS_OPTIONS} value={status} onChange={setStatus} className="w-full" />
      </div>

      <Card className="mt-4 overflow-hidden p-0">
        {isLoading ? (
          <ListSkeleton />
        ) : isError ? (
          <div className="p-6">
            <EmptyState
              icon={FileText}
              title="No se pudieron cargar los documentos"
              description="Revisá la conexión con el backend e intentá de nuevo."
            />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={FileText}
              title="Sin documentos"
              description="Pedile al agente por WhatsApp «/propuesta …» o generá uno desde la API y va a aparecer acá."
            />
          </div>
        ) : (
          <div>
            {data.items.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} />
            ))}
          </div>
        )}
      </Card>
    </PageContainer>
  );
}
