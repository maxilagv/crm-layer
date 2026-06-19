"use client";

import { Inbox as InboxIcon, Search } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/field";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationListItem } from "./conversation-list-item";
import { useConversations, type ConversationFilters } from "./queries";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todas" },
  { value: "open", label: "Abiertas" },
  { value: "pending", label: "Pendientes" },
  { value: "closed", label: "Cerradas" },
];

function ListSkeleton() {
  return (
    <div className="space-y-1 p-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex gap-3 py-3">
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-2 py-1">
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ConversationList() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const filters: ConversationFilters = {
    status: status || undefined,
    search: search || undefined,
  };
  const { data, isLoading, isError } = useConversations(filters);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="space-y-3 border-b border-border p-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar conversación…"
            className="pl-9"
          />
        </div>
        <Segmented
          options={STATUS_OPTIONS}
          value={status}
          onChange={setStatus}
          className="w-full justify-between"
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? (
          <ListSkeleton />
        ) : isError ? (
          <div className="p-4">
            <EmptyState
              icon={InboxIcon}
              title="No se pudieron cargar"
              description="Revisá la conexión con el backend."
            />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={InboxIcon}
              title="Sin conversaciones"
              description="Cuando lleguen mensajes por WhatsApp van a aparecer acá."
            />
          </div>
        ) : (
          data.items.map((c) => <ConversationListItem key={c.id} c={c} />)
        )}
      </div>
    </div>
  );
}
