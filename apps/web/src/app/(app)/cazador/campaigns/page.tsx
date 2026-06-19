"use client";

import { Pause, Play, Plus, Radar, Search, Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { PageContainer } from "@/components/shell/page-container";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, Input, Textarea } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  CAMPAIGN_STATUS_LABELS,
  type CampaignStatus,
  type ProspectingCampaign,
  campaignStatusTone,
  useCampaigns,
  useCreateCampaign,
  useDiscoverCampaign,
  useRunOutreach,
  useUpdateCampaign,
} from "@/features/cazador/queries";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todas" },
  { value: "active", label: "Activas" },
  { value: "draft", label: "Borradores" },
  { value: "paused", label: "Pausadas" },
];

function CampaignSkeleton() {
  return (
    <div className="space-y-1 p-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="grid gap-3 py-3 md:grid-cols-[1fr_320px]">
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
}

function CampaignRow({ campaign }: { campaign: ProspectingCampaign }) {
  const update = useUpdateCampaign(campaign.id);
  const discover = useDiscoverCampaign(campaign.id);
  const outreach = useRunOutreach(campaign.id);
  const nextStatus: CampaignStatus =
    campaign.status === "active" ? "paused" : "active";
  const nextIcon =
    campaign.status === "active" ? (
      <Pause className="h-4 w-4" />
    ) : (
      <Play className="h-4 w-4" />
    );

  return (
    <div className="grid gap-3 border-t border-border px-4 py-4 first:border-t-0 md:grid-cols-[1fr_340px] md:items-center">
      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-sm font-semibold text-foreground">
            {campaign.name}
          </h2>
          <Badge tone={campaignStatusTone(campaign.status)} dot>
            {CAMPAIGN_STATUS_LABELS[campaign.status]}
          </Badge>
          {campaign.auto_contact && <Badge tone="info">Auto</Badge>}
        </div>
        <p className="line-clamp-2 text-sm text-muted">
          {campaign.query}
          {campaign.location_hint ? ` · ${campaign.location_hint}` : ""}
        </p>
        <div className="flex flex-wrap gap-2 text-xs text-muted">
          <span>{campaign.vertical || "Sin vertical"}</span>
          <span>Fit min {campaign.min_fit_score}</span>
          <span>Cap {campaign.daily_cap}/dia</span>
        </div>
      </div>
      <div className="space-y-2">
        <div className="grid grid-cols-4 gap-2 text-center">
          <Metric label="Desc." value={campaign.discovered_count} />
          <Metric label="Fit" value={campaign.qualified_count} />
          <Metric label="Cont." value={campaign.contacted_count} />
          <Metric label="Int." value={campaign.interested_count} />
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            leftIcon={<Search className="h-4 w-4" />}
            loading={discover.isPending}
            onClick={() => discover.mutate()}
            title="Buscar prospectos en Google Places"
          >
            Buscar
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            leftIcon={<Send className="h-4 w-4" />}
            loading={outreach.isPending}
            onClick={() => outreach.mutate()}
            title="Enviar el primer mensaje a los prospectos elegibles"
          >
            Contactar
          </Button>
          <Button
            type="button"
            variant={campaign.status === "active" ? "ghost" : "primary"}
            size="sm"
            leftIcon={nextIcon}
            loading={update.isPending}
            onClick={() => update.mutate({ status: nextStatus })}
          >
            {campaign.status === "active" ? "Pausar" : "Activar"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-bg-subtle px-2 py-2">
      <div className="text-sm font-semibold text-foreground">{value}</div>
      <div className="text-[11px] text-muted">{label}</div>
    </div>
  );
}

export default function CazadorCampaignsPage() {
  const [status, setStatus] = useState("");
  const [autoContact, setAutoContact] = useState(false);
  const [form, setForm] = useState({
    name: "",
    query: "",
    vertical: "",
    location_hint: "",
    target_profile: "",
    min_fit_score: "60",
    daily_cap: "20",
  });
  const { data, isLoading, isError } = useCampaigns({
    status: status || undefined,
  });
  const create = useCreateCampaign();

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    create.mutate(
      {
        name: form.name,
        query: form.query,
        vertical: form.vertical,
        location_hint: form.location_hint,
        target_profile: form.target_profile,
        min_fit_score: Number(form.min_fit_score || 60),
        daily_cap: Number(form.daily_cap || 20),
        auto_contact: autoContact,
      },
      {
        onSuccess: () => {
          setForm({
            name: "",
            query: "",
            vertical: "",
            location_hint: "",
            target_profile: "",
            min_fit_score: "60",
            daily_cap: "20",
          });
          setAutoContact(false);
        },
      },
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Campañas"
        description="Búsqueda, calificación y salida inicial de Cazador."
      />

      <div className="mt-5 grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Nueva campaña</CardTitle>
            <CardDescription>Consulta de Places y criterio comercial.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={submit}>
              <Field label="Nombre" required>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Gomerías Palermo"
                  required
                />
              </Field>
              <Field label="Query" required>
                <Input
                  value={form.query}
                  onChange={(e) => setForm({ ...form, query: e.target.value })}
                  placeholder="gomerías en Palermo"
                  required
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Vertical">
                  <Input
                    value={form.vertical}
                    onChange={(e) => setForm({ ...form, vertical: e.target.value })}
                    placeholder="gomerías"
                  />
                </Field>
                <Field label="Zona">
                  <Input
                    value={form.location_hint}
                    onChange={(e) =>
                      setForm({ ...form, location_hint: e.target.value })
                    }
                    placeholder="Palermo"
                  />
                </Field>
              </div>
              <Field label="Perfil objetivo">
                <Textarea
                  value={form.target_profile}
                  onChange={(e) =>
                    setForm({ ...form, target_profile: e.target.value })
                  }
                  placeholder="Sin web, pocas fotos, sin turnos online."
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Fit min.">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={form.min_fit_score}
                    onChange={(e) =>
                      setForm({ ...form, min_fit_score: e.target.value })
                    }
                  />
                </Field>
                <Field label="Cap diario">
                  <Input
                    type="number"
                    min={1}
                    max={500}
                    value={form.daily_cap}
                    onChange={(e) => setForm({ ...form, daily_cap: e.target.value })}
                  />
                </Field>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2">
                <span className="text-sm font-medium text-foreground">
                  Auto-contacto
                </span>
                <Switch
                  checked={autoContact}
                  onCheckedChange={setAutoContact}
                  aria-label="Auto-contacto"
                />
              </div>
              <Button
                type="submit"
                className="w-full"
                leftIcon={<Plus className="h-4 w-4" />}
                loading={create.isPending}
              >
                Crear
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <Segmented
            options={STATUS_OPTIONS}
            value={status}
            onChange={setStatus}
            className="w-full flex-wrap"
          />
          <Card className="overflow-hidden p-0">
            {isLoading ? (
              <CampaignSkeleton />
            ) : isError ? (
              <div className="p-6">
                <EmptyState
                  icon={Radar}
                  title="No se pudieron cargar las campañas"
                  description="Revisá la conexión con el backend e intentá de nuevo."
                />
              </div>
            ) : !data || data.items.length === 0 ? (
              <div className="p-6">
                <EmptyState icon={Radar} title="Sin campañas" />
              </div>
            ) : (
              <div>
                {data.items.map((campaign) => (
                  <CampaignRow key={campaign.id} campaign={campaign} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
