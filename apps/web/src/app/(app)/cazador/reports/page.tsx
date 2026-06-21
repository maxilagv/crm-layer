"use client";

import { BarChart3, MessageCircle, PhoneCall, SearchX } from "lucide-react";
import { useState } from "react";
import { PageContainer } from "@/components/shell/page-container";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PROSPECT_STATUS_LABELS,
  type ProspectingReportContact,
  prospectStatusTone,
  useCampaigns,
  useProspectingReport,
} from "@/features/cazador/queries";

const BUCKET_LABELS: Record<ProspectingReportContact["bucket"], string> = {
  respondieron: "Respondieron",
  se_tuvo_charla: "Se tuvo charla",
  sin_dialogo: "Sin dialogo",
};

function ReportSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-24 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-lg" />
    </div>
  );
}

function BucketCard({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: number;
  icon: typeof BarChart3;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-sm text-muted">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bg-subtle">
          <Icon className="h-5 w-5 text-muted" />
        </div>
      </CardContent>
    </Card>
  );
}

function ContactRow({ contact }: { contact: ProspectingReportContact }) {
  return (
    <tr className="border-t border-border">
      <td className="px-4 py-3">
        <div className="font-medium text-foreground">{contact.business_name}</div>
        <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted">
          {contact.owner_email && <span>{contact.owner_email}</span>}
          {contact.phone && <span>{contact.phone}</span>}
        </div>
      </td>
      <td className="px-4 py-3">
        <Badge tone={prospectStatusTone(contact.status)} dot>
          {PROSPECT_STATUS_LABELS[contact.status]}
        </Badge>
      </td>
      <td className="px-4 py-3 text-sm text-muted">{BUCKET_LABELS[contact.bucket]}</td>
      <td className="px-4 py-3 text-sm text-muted">{contact.fit_score ?? "-"}</td>
      <td className="px-4 py-3 text-sm text-muted">
        {contact.last_touch_at ? new Date(contact.last_touch_at).toLocaleDateString() : "-"}
      </td>
    </tr>
  );
}

export default function CazadorReportsPage() {
  const [campaignId, setCampaignId] = useState("");
  const { data: campaigns } = useCampaigns();
  const { data, isLoading, isError } = useProspectingReport({
    campaign_id: campaignId || undefined,
  });

  return (
    <PageContainer>
      <PageHeader
        title="Reporte Cazador"
        description="Avance comercial por respuestas, conversaciones y prospectos sin diálogo."
      />

      <div className="mt-5 max-w-sm">
        <Select value={campaignId} onChange={(event) => setCampaignId(event.target.value)}>
          <option value="">Todas las campañas</option>
          {(campaigns?.items ?? []).map((campaign) => (
            <option key={campaign.id} value={campaign.id}>
              {campaign.name}
            </option>
          ))}
        </Select>
      </div>

      <div className="mt-5">
        {isLoading ? (
          <ReportSkeleton />
        ) : isError || !data ? (
          <Card>
            <CardContent className="p-6">
              <EmptyState
                icon={BarChart3}
                title="No se pudo cargar el reporte"
                description="Revisá la conexión con el backend e intentá de nuevo."
              />
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <BucketCard
                title="Respondieron"
                value={data.buckets.respondieron}
                icon={MessageCircle}
              />
              <BucketCard
                title="Se tuvo charla"
                value={data.buckets.se_tuvo_charla}
                icon={PhoneCall}
              />
              <BucketCard
                title="Sin diálogo"
                value={data.buckets.sin_dialogo}
                icon={SearchX}
              />
            </div>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-foreground">Progreso</p>
                    <p className="text-sm text-muted">
                      {data.totals.contactables} prospectos contactables
                    </p>
                  </div>
                  <div className="text-2xl font-semibold text-foreground">
                    {data.progress_pct}%
                  </div>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-bg-subtle">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.min(100, data.progress_pct)}%` }}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden p-0">
              <CardHeader>
                <CardTitle>Contactos</CardTitle>
              </CardHeader>
              {data.contacts.length === 0 ? (
                <div className="p-6">
                  <EmptyState icon={BarChart3} title="Sin contactos para reportar" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="bg-bg-subtle text-xs uppercase text-muted">
                      <tr>
                        <th className="px-4 py-3 font-medium">Negocio</th>
                        <th className="px-4 py-3 font-medium">Estado</th>
                        <th className="px-4 py-3 font-medium">Bucket</th>
                        <th className="px-4 py-3 font-medium">Fit</th>
                        <th className="px-4 py-3 font-medium">Último toque</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.contacts.map((contact) => (
                        <ContactRow key={contact.id} contact={contact} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
