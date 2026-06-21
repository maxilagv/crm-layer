"use client";

import { Check, Inbox, ListChecks, Search, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { PageContainer } from "@/components/shell/page-container";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PROSPECT_STATUS_LABELS,
  type Prospect,
  fitScoreTone,
  prospectStatusTone,
  useCampaigns,
  useProspects,
  useUpdateProspect,
} from "@/features/cazador/queries";
import { cn } from "@/lib/cn";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "qualified", label: "Calificados" },
  { value: "approved", label: "Aprobados" },
  { value: "contacted", label: "Contactados" },
  { value: "interested", label: "Interesados" },
  { value: "", label: "Todos" },
];

function ProspectSkeleton() {
  return (
    <div className="space-y-1 p-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="grid gap-3 py-3 lg:grid-cols-[96px_1fr_180px]">
          <Skeleton className="h-16 w-full rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-5 w-72" />
          </div>
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
}

function ProspectRow({
  prospect,
  campaignName,
}: {
  prospect: Prospect;
  campaignName: string;
}) {
  return (
    <div className="grid gap-3 border-t border-border px-4 py-4 first:border-t-0 lg:grid-cols-[96px_1fr_190px]">
      <div className="flex h-20 flex-col items-center justify-center rounded-lg bg-bg-subtle">
        <div className="text-2xl font-semibold text-foreground">
          {prospect.fit_score ?? "—"}
        </div>
        <Badge tone={fitScoreTone(prospect.fit_score)} className="mt-1">
          fit
        </Badge>
      </div>

      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-sm font-semibold text-foreground">
            {prospect.business_name}
          </h2>
          <Badge tone={prospectStatusTone(prospect.status)} dot>
            {PROSPECT_STATUS_LABELS[prospect.status]}
          </Badge>
          {campaignName && <Badge tone="muted">{campaignName}</Badge>}
        </div>
        <p className="line-clamp-2 text-sm text-muted">
          {prospect.category || "Sin categoria"}
          {prospect.address ? ` · ${prospect.address}` : ""}
        </p>
        <div className="flex flex-wrap gap-2 text-xs text-muted">
          <span>{prospect.phone || "Sin telefono"}</span>
          {prospect.owner_email && <span>{prospect.owner_email}</span>}
          <span>{prospect.website ? "Con web" : "Sin web"}</span>
          <span>{prospect.reviews_count} reviews</span>
          <span>{prospect.photos_count} fotos</span>
          {prospect.rating && <span>Rating {prospect.rating}</span>}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(prospect.signals.length ? prospect.signals : ["sin_senales"]).map((signal) => (
            <Badge key={signal} tone="info">
              {signal}
            </Badge>
          ))}
        </div>
        {prospect.reasoning && (
          <p className="line-clamp-2 text-sm text-foreground/80">
            {prospect.reasoning}
          </p>
        )}
        {prospect.recommended_angle && (
          <p className="text-sm text-muted">{prospect.recommended_angle}</p>
        )}
      </div>

      <ProspectActions prospect={prospect} />
    </div>
  );
}

function ProspectActions({ prospect }: { prospect: Prospect }) {
  const update = useUpdateProspect(prospect.id);
  const canApprove = !["approved", "contacted", "interested", "do_not_contact"].includes(
    prospect.status,
  );
  const canDiscard = !["disqualified", "do_not_contact", "interested"].includes(
    prospect.status,
  );

  return (
    <div className="flex flex-col gap-2">
      <Button
        type="button"
        size="sm"
        leftIcon={<Check className="h-4 w-4" />}
        loading={update.isPending}
        disabled={!canApprove || update.isPending}
        onClick={() => update.mutate({ status: "approved" })}
      >
        Aprobar
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        leftIcon={<X className="h-4 w-4" />}
        loading={update.isPending}
        disabled={!canDiscard || update.isPending}
        onClick={() => update.mutate({ status: "disqualified" })}
      >
        Descartar
      </Button>
      {prospect.conversation_id && (
        <Link
          href={`/inbox/${prospect.conversation_id}`}
          className={cn(
            "inline-flex h-8 items-center justify-center gap-2 rounded-lg border border-border bg-transparent px-3 text-[13px] font-medium text-foreground outline-none transition-colors hover:bg-card focus-visible:shadow-focus",
          )}
        >
          <Inbox className="h-4 w-4" />
          Inbox
        </Link>
      )}
    </div>
  );
}

export default function CazadorProspectsPage() {
  const [status, setStatus] = useState("qualified");
  const [campaignId, setCampaignId] = useState("");
  const [search, setSearch] = useState("");
  const { data: campaigns } = useCampaigns();
  const { data, isLoading, isError } = useProspects({
    status: status || undefined,
    campaign_id: campaignId || undefined,
    search: search || undefined,
  });
  const campaignNameById = useMemo(() => {
    return new Map((campaigns?.items ?? []).map((campaign) => [campaign.id, campaign.name]));
  }, [campaigns]);

  return (
    <PageContainer>
      <PageHeader
        title="Prospectos"
        description="Cola de revisión para aprobar, descartar y seguir conversaciones."
      />

      <div className="mt-5 space-y-3">
        <div className="grid gap-2 lg:grid-cols-[1fr_280px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar negocio, zona o categoria..."
              className="pl-9"
            />
          </div>
          <Select value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
            <option value="">Todas las campañas</option>
            {(campaigns?.items ?? []).map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {campaign.name}
              </option>
            ))}
          </Select>
        </div>
        <Segmented
          options={STATUS_OPTIONS}
          value={status}
          onChange={setStatus}
          className="w-full flex-wrap"
        />
      </div>

      <Card className="mt-4 overflow-hidden p-0">
        {isLoading ? (
          <ProspectSkeleton />
        ) : isError ? (
          <div className="p-6">
            <EmptyState
              icon={ListChecks}
              title="No se pudieron cargar los prospectos"
              description="Revisá la conexión con el backend e intentá de nuevo."
            />
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-6">
            <EmptyState icon={ListChecks} title="Sin prospectos" />
          </div>
        ) : (
          <div>
            {data.items.map((prospect) => (
              <ProspectRow
                key={prospect.id}
                prospect={prospect}
                campaignName={campaignNameById.get(prospect.campaign) ?? ""}
              />
            ))}
          </div>
        )}
      </Card>
    </PageContainer>
  );
}
