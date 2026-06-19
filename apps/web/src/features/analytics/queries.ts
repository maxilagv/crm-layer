"use client";

import { useQuery } from "@tanstack/react-query";
import type { BadgeTone } from "@/components/ui/badge";
import { apiGet, apiGetList } from "@/lib/api/client";

/**
 * Backend coerces non-integer Decimals to strings and keeps integers as
 * numbers, so totals/metrics can hold either. Costs come stringified.
 */
export type MetricValue = number | string;

export interface AnalyticsPeriod {
  start: string;
  end: string;
}

/** Free-form aggregate metrics keyed by snake_case metric name. */
export type AnalyticsTotals = Record<string, MetricValue>;

export interface FunnelScoreDistribution {
  "0_30": number;
  "31_55": number;
  "56_75": number;
  "76_100": number;
}

export interface FunnelTotals {
  leads: number;
}

export interface AnalyticsFunnel {
  stage_counts: Record<string, number>;
  status_counts: Record<string, number>;
  score_distribution: FunnelScoreDistribution;
  totals: FunnelTotals;
}

export interface AnalyticsFunnelResponse extends AnalyticsFunnel {
  date: string;
}

export interface AiCostRow {
  provider: string;
  model: string;
  purpose: string;
  currency: string;
  estimated_cost: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  audio_seconds: string;
  image_count: number;
  run_count: number;
}

export interface AiCostTotals {
  items: AiCostRow[];
}

export interface AnalyticsDashboard {
  period: AnalyticsPeriod;
  totals: AnalyticsTotals;
  funnel: AnalyticsFunnel;
  ai_costs: AiCostTotals;
  generated_at: string;
}

/** Persisted per-row snapshot returned by the paginated ai-costs endpoint. */
export interface AiCostSnapshot {
  id: string;
  date: string;
  provider: string;
  model: string;
  purpose: string;
  currency: string;
  estimated_cost: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  audio_seconds: string;
  image_count: number;
  run_count: number;
}

export interface AnalyticsRange {
  start_date?: string;
  end_date?: string;
}

export const LEAD_STAGE_LABELS: Record<string, string> = {
  new: "Nuevo",
  contacted: "Contactado",
  qualifying: "Calificando",
  warm: "Tibio",
  hot: "Caliente",
  call_requested: "Pidió llamada",
  call_scheduled: "Llamada agendada",
  proposal_pending: "Propuesta pendiente",
  won: "Ganado",
  lost: "Perdido",
  nurturing: "Nutrición",
  unqualified: "No calificado",
};

export const LEAD_STATUS_LABELS: Record<string, string> = {
  active: "Activo",
  won: "Ganado",
  lost: "Perdido",
  unqualified: "No calificado",
  nurturing: "Nutrición",
  archived: "Archivado",
};

export const SCORE_BUCKET_LABELS: Record<keyof FunnelScoreDistribution, string> = {
  "0_30": "Frío (0-30)",
  "31_55": "Templado (31-55)",
  "56_75": "Tibio (56-75)",
  "76_100": "Caliente (76-100)",
};

export function stageTone(stage: string): BadgeTone {
  if (stage === "won") return "success";
  if (stage === "lost" || stage === "unqualified") return "muted";
  if (stage === "hot" || stage === "call_requested" || stage === "call_scheduled")
    return "danger";
  if (stage === "warm" || stage === "proposal_pending") return "warning";
  return "primary";
}

export function statusTone(status: string): BadgeTone {
  if (status === "won" || status === "active") return "success";
  if (status === "lost") return "danger";
  if (status === "nurturing") return "info";
  return "muted";
}

export function stageLabel(stage: string): string {
  return LEAD_STAGE_LABELS[stage] ?? stage;
}

export function statusLabel(status: string): string {
  return LEAD_STATUS_LABELS[status] ?? status;
}

const ANALYTICS_BASE = "/api/v1/analytics";

function rangeQuery(range: AnalyticsRange) {
  return {
    start_date: range.start_date,
    end_date: range.end_date,
  };
}

export const analyticsKeys = {
  dashboard: (range: AnalyticsRange) => ["analytics", "dashboard", range] as const,
  funnel: (range: AnalyticsRange) => ["analytics", "funnel", range] as const,
  aiCosts: (range: AnalyticsRange) => ["analytics", "ai-costs", range] as const,
};

/**
 * These GETs recalculate snapshots on the backend, so we keep them fresh but
 * never poll aggressively.
 */
const STALE_TIME = 60_000;

export function useDashboard(range: AnalyticsRange) {
  return useQuery({
    queryKey: analyticsKeys.dashboard(range),
    queryFn: () =>
      apiGet<AnalyticsDashboard>(`${ANALYTICS_BASE}/dashboard/`, rangeQuery(range)),
    staleTime: STALE_TIME,
  });
}

export function useFunnel(range: AnalyticsRange) {
  return useQuery({
    queryKey: analyticsKeys.funnel(range),
    queryFn: () =>
      apiGet<AnalyticsFunnelResponse>(`${ANALYTICS_BASE}/funnel/`, rangeQuery(range)),
    staleTime: STALE_TIME,
  });
}

export function useAiCosts(range: AnalyticsRange) {
  return useQuery({
    queryKey: analyticsKeys.aiCosts(range),
    queryFn: () =>
      apiGetList<AiCostSnapshot>(`${ANALYTICS_BASE}/ai-costs/`, {
        ...rangeQuery(range),
        page_size: 100,
      }),
    staleTime: STALE_TIME,
  });
}
