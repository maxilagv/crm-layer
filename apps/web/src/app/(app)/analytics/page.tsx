"use client";

import {
  BarChart3,
  Bot,
  CalendarCheck,
  CheckCircle2,
  Filter,
  Flame,
  MessageSquare,
  PhoneCall,
  Ticket,
  TrendingUp,
  UserPlus,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/shell/page-container";
import {
  type AiCostSnapshot,
  type AnalyticsRange,
  type AnalyticsTotals,
  type FunnelScoreDistribution,
  SCORE_BUCKET_LABELS,
  stageLabel,
  stageTone,
  statusLabel,
  statusTone,
  useAiCosts,
  useDashboard,
  useFunnel,
} from "@/features/analytics/queries";
import { cn } from "@/lib/cn";

type RangePreset = "7" | "30" | "90" | "custom";

const RANGE_OPTIONS: SegmentedOption<RangePreset>[] = [
  { value: "7", label: "7 días" },
  { value: "30", label: "30 días" },
  { value: "90", label: "90 días" },
  { value: "custom", label: "Personalizado" },
];

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - (days - 1));
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function toNumber(value: number | string | undefined): number {
  if (value === undefined) return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatInt(value: number | string | undefined): string {
  return toNumber(value).toLocaleString("es-AR");
}

function formatMoney(value: string | number, currency: string): string {
  const n = toNumber(value);
  const code = currency?.toUpperCase() || "USD";
  try {
    return new Intl.NumberFormat("es-AR", {
      style: "currency",
      currency: code,
      maximumFractionDigits: 4,
    }).format(n);
  } catch {
    return `${code} ${n.toFixed(4)}`;
  }
}

interface MetricSpec {
  key: string;
  label: string;
  icon: typeof UserPlus;
  tone: "primary" | "success" | "warning" | "danger" | "info";
}

const METRIC_CARDS: MetricSpec[] = [
  { key: "leads_created_total", label: "Leads nuevos", icon: UserPlus, tone: "primary" },
  { key: "hot_leads_total", label: "Leads calientes", icon: Flame, tone: "danger" },
  { key: "calls_scheduled_total", label: "Llamadas agendadas", icon: CalendarCheck, tone: "success" },
  { key: "messages_received_total", label: "Mensajes recibidos", icon: MessageSquare, tone: "info" },
  { key: "messages_sent_total", label: "Mensajes enviados", icon: TrendingUp, tone: "primary" },
  { key: "calls_requested_total", label: "Llamadas pedidas", icon: PhoneCall, tone: "warning" },
  { key: "tickets_created_total", label: "Tickets creados", icon: Ticket, tone: "info" },
  { key: "tickets_resolved_total", label: "Tickets resueltos", icon: CheckCircle2, tone: "success" },
];

const TONE_TEXT: Record<MetricSpec["tone"], string> = {
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  info: "text-info",
};

const TONE_BG: Record<MetricSpec["tone"], string> = {
  primary: "bg-primary/12",
  success: "bg-success/12",
  warning: "bg-warning/12",
  danger: "bg-danger/12",
  info: "bg-info/12",
};

function MetricCard({ spec, totals }: { spec: MetricSpec; totals: AnalyticsTotals }) {
  const Icon = spec.icon;
  return (
    <Card className="overflow-hidden">
      <CardContent className="flex items-center gap-3 py-4">
        <span
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
            TONE_BG[spec.tone],
          )}
        >
          <Icon className={cn("h-5 w-5", TONE_TEXT[spec.tone])} />
        </span>
        <div className="min-w-0">
          <p className="font-display text-2xl font-semibold leading-none tracking-tight text-foreground">
            {formatInt(totals[spec.key])}
          </p>
          <p className="mt-1 truncate text-xs text-muted">{spec.label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function MetricCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="flex items-center gap-3 py-4">
            <Skeleton className="h-10 w-10 rounded-xl" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-12" />
              <Skeleton className="h-3 w-20" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

interface FunnelRow {
  key: string;
  label: string;
  count: number;
  tone: ReturnType<typeof stageTone>;
}

const BAR_TONE: Record<string, string> = {
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
  muted: "bg-muted",
  default: "bg-muted",
};

function StageBar({ row, max }: { row: FunnelRow; max: number }) {
  const pct = max > 0 ? Math.round((row.count / max) * 100) : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="truncate text-foreground">{row.label}</span>
        <span className="shrink-0 font-medium tabular-nums text-muted">
          {row.count.toLocaleString("es-AR")}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-bg-subtle">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500 ease-out",
            BAR_TONE[row.tone] ?? "bg-primary",
          )}
          style={{ width: `${Math.max(pct, row.count > 0 ? 4 : 0)}%` }}
        />
      </div>
    </div>
  );
}

const SCORE_BUCKET_ORDER: (keyof FunnelScoreDistribution)[] = [
  "0_30",
  "31_55",
  "56_75",
  "76_100",
];

const SCORE_BUCKET_TONE: Record<keyof FunnelScoreDistribution, string> = {
  "0_30": "bg-muted",
  "31_55": "bg-info",
  "56_75": "bg-warning",
  "76_100": "bg-danger",
};

function FunnelCard({ range }: { range: AnalyticsRange }) {
  const { data, isLoading, isError } = useFunnel(range);

  const stageRows = useMemo<FunnelRow[]>(() => {
    if (!data) return [];
    return Object.entries(data.stage_counts)
      .map(([key, count]) => ({
        key,
        label: stageLabel(key),
        count,
        tone: stageTone(key),
      }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  const statusRows = useMemo<FunnelRow[]>(() => {
    if (!data) return [];
    return Object.entries(data.status_counts)
      .map(([key, count]) => ({
        key,
        label: statusLabel(key),
        count,
        tone: statusTone(key),
      }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  const maxStage = Math.max(1, ...stageRows.map((r) => r.count));
  const scoreTotal = data
    ? SCORE_BUCKET_ORDER.reduce((sum, k) => sum + data.score_distribution[k], 0)
    : 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Embudo de leads</CardTitle>
        {data && (
          <Badge tone="primary" dot>
            {data.totals.leads.toLocaleString("es-AR")} totales
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-3 w-1/3" />
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <EmptyState
            icon={Filter}
            title="No se pudo cargar el embudo"
            description="Revisá la conexión con el backend e intentá de nuevo."
          />
        ) : !data || data.totals.leads === 0 ? (
          <EmptyState
            icon={Filter}
            title="Sin leads en el período"
            description="Cuando ingresen leads vas a ver acá su distribución por etapa."
          />
        ) : (
          <>
            <div className="space-y-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">
                Por etapa
              </p>
              {stageRows.map((row) => (
                <StageBar key={row.key} row={row} max={maxStage} />
              ))}
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">
                Distribución de score
              </p>
              <div className="flex h-3 w-full overflow-hidden rounded-full bg-bg-subtle">
                {SCORE_BUCKET_ORDER.map((bucket) => {
                  const value = data.score_distribution[bucket];
                  const pct = scoreTotal > 0 ? (value / scoreTotal) * 100 : 0;
                  if (pct <= 0) return null;
                  return (
                    <div
                      key={bucket}
                      className={cn("h-full", SCORE_BUCKET_TONE[bucket])}
                      style={{ width: `${pct}%` }}
                      title={`${SCORE_BUCKET_LABELS[bucket]}: ${value}`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {SCORE_BUCKET_ORDER.map((bucket) => (
                  <span
                    key={bucket}
                    className="inline-flex items-center gap-1.5 text-xs text-muted"
                  >
                    <span
                      className={cn(
                        "h-2 w-2 rounded-full",
                        SCORE_BUCKET_TONE[bucket],
                      )}
                    />
                    {SCORE_BUCKET_LABELS[bucket]}
                    <span className="font-medium tabular-nums text-foreground">
                      {data.score_distribution[bucket]}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            {statusRows.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted">
                  Por estado
                </p>
                <div className="flex flex-wrap gap-2">
                  {statusRows.map((row) => (
                    <Badge key={row.key} tone={row.tone}>
                      {row.label}
                      <span className="ml-1 tabular-nums opacity-80">
                        {row.count}
                      </span>
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function aggregateCost(rows: AiCostSnapshot[]): {
  cost: number;
  currency: string;
  inputTokens: number;
  outputTokens: number;
  runs: number;
} {
  let cost = 0;
  let inputTokens = 0;
  let outputTokens = 0;
  let runs = 0;
  let currency = "USD";
  for (const row of rows) {
    cost += toNumber(row.estimated_cost);
    inputTokens += row.input_tokens;
    outputTokens += row.output_tokens;
    runs += row.run_count;
    if (row.currency) currency = row.currency;
  }
  return { cost, currency, inputTokens, outputTokens, runs };
}

function AiCostsCard({ range }: { range: AnalyticsRange }) {
  const { data, isLoading, isError } = useAiCosts(range);
  const rows = useMemo<AiCostSnapshot[]>(() => data?.items ?? [], [data]);

  const grouped = useMemo(() => {
    const byProvider = new Map<string, AiCostSnapshot[]>();
    for (const row of rows) {
      const key = `${row.provider} · ${row.model}`;
      const list = byProvider.get(key) ?? [];
      list.push(row);
      byProvider.set(key, list);
    }
    return Array.from(byProvider.entries())
      .map(([key, list]) => ({ key, ...aggregateCost(list) }))
      .sort((a, b) => b.cost - a.cost);
  }, [rows]);

  const totals = useMemo(() => aggregateCost(rows), [rows]);
  const maxCost = Math.max(1, ...grouped.map((g) => g.cost));

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Costos de IA</CardTitle>
        {rows.length > 0 && (
          <Badge tone="primary">
            {formatMoney(totals.cost, totals.currency)}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-3 w-2/5" />
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <EmptyState
            icon={Bot}
            title="No se pudieron cargar los costos"
            description="Revisá la conexión con el backend e intentá de nuevo."
          />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={Bot}
            title="Sin consumo de IA"
            description="Cuando el agente procese mensajes vas a ver el costo estimado acá."
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-border bg-bg-subtle px-3 py-2.5">
                <p className="text-xs text-muted">Tokens entrada</p>
                <p className="font-display text-lg font-semibold tabular-nums text-foreground">
                  {formatInt(totals.inputTokens)}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-bg-subtle px-3 py-2.5">
                <p className="text-xs text-muted">Tokens salida</p>
                <p className="font-display text-lg font-semibold tabular-nums text-foreground">
                  {formatInt(totals.outputTokens)}
                </p>
              </div>
              <div className="col-span-2 rounded-lg border border-border bg-bg-subtle px-3 py-2.5 sm:col-span-1">
                <p className="text-xs text-muted">Ejecuciones</p>
                <p className="font-display text-lg font-semibold tabular-nums text-foreground">
                  {formatInt(totals.runs)}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">
                Por modelo
              </p>
              {grouped.map((g) => {
                const pct =
                  maxCost > 0 ? Math.round((g.cost / maxCost) * 100) : 0;
                return (
                  <div key={g.key} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="truncate text-foreground">{g.key}</span>
                      <span className="shrink-0 font-medium tabular-nums text-muted">
                        {formatMoney(g.cost, g.currency)}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-bg-subtle">
                      <div
                        className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
                        style={{ width: `${Math.max(pct, g.cost > 0 ? 4 : 0)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const [preset, setPreset] = useState<RangePreset>("30");
  const [customStart, setCustomStart] = useState(isoDaysAgo(30));
  const [customEnd, setCustomEnd] = useState(todayIso());

  const range = useMemo<AnalyticsRange>(() => {
    if (preset === "custom") {
      return { start_date: customStart, end_date: customEnd };
    }
    return { start_date: isoDaysAgo(Number(preset)), end_date: todayIso() };
  }, [preset, customStart, customEnd]);

  const { data: dashboard, isLoading, isError } = useDashboard(range);

  return (
    <PageContainer>
      <div className="space-y-6">
        <PageHeader
          title="Analítica"
          description="Métricas, embudo de leads y costos de IA del período."
          actions={
            <Segmented
              options={RANGE_OPTIONS}
              value={preset}
              onChange={setPreset}
            />
          }
        />

        {preset === "custom" && (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex flex-col gap-1.5 text-sm">
              <span className="font-medium text-foreground">Desde</span>
              <Input
                type="date"
                value={customStart}
                max={customEnd}
                onChange={(e) => setCustomStart(e.target.value)}
                className="sm:w-44"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-sm">
              <span className="font-medium text-foreground">Hasta</span>
              <Input
                type="date"
                value={customEnd}
                min={customStart}
                max={todayIso()}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="sm:w-44"
              />
            </label>
          </div>
        )}

        {isLoading ? (
          <MetricCardsSkeleton />
        ) : isError ? (
          <Card>
            <CardContent className="py-8">
              <EmptyState
                icon={BarChart3}
                title="No se pudieron cargar las métricas"
                description="Revisá la conexión con el backend e intentá de nuevo."
              />
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {METRIC_CARDS.map((spec) => (
              <MetricCard
                key={spec.key}
                spec={spec}
                totals={dashboard?.totals ?? {}}
              />
            ))}
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <FunnelCard range={range} />
          <AiCostsCard range={range} />
        </div>
      </div>
    </PageContainer>
  );
}
