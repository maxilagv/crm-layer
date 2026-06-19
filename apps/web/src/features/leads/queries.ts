"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { BadgeTone } from "@/components/ui/badge";
import { apiGet, apiGetList, apiPatch, apiPost } from "@/lib/api/client";

// --- Enums (match crm.leads.domain.enums exactly) ---

export type LeadStatus =
  | "active"
  | "won"
  | "lost"
  | "unqualified"
  | "nurturing"
  | "archived";

export type LeadStage =
  | "new"
  | "contacted"
  | "qualifying"
  | "warm"
  | "hot"
  | "call_requested"
  | "call_scheduled"
  | "proposal_pending"
  | "won"
  | "lost"
  | "nurturing"
  | "unqualified";

export type LeadTemperature = "cold" | "warm" | "hot" | "critical";

export type BudgetSignal =
  | "none"
  | "unknown"
  | "low"
  | "medium"
  | "high"
  | "confirmed";

export type LeadUrgency = "unknown" | "low" | "medium" | "high" | "critical";

export type AuthoritySignal =
  | "unknown"
  | "influencer"
  | "decision_maker"
  | "likely_decision_maker";

export type StageChangedByType =
  | "user"
  | "ai_agent"
  | "system"
  | "automation"
  | "worker";

export type LeadSourceType =
  | "whatsapp"
  | "manual"
  | "website"
  | "referral"
  | "campaign"
  | "import"
  | "unknown";

// --- Resource shapes (match serializers exactly) ---

export interface LeadContact {
  id: string;
  display_name: string;
  type: string;
  status: string;
  company_name: string;
}

export interface LeadScoreSnapshot {
  id: string;
  score: number;
  temperature: LeadTemperature;
  reasoning_summary: string;
  factors: Record<string, unknown>;
  ai_run_id: string | null;
  created_at: string;
}

export interface LeadStageHistory {
  id: string;
  from_stage: string;
  to_stage: LeadStage;
  reason: string;
  changed_by_id: string | null;
  changed_by_type: StageChangedByType;
  ai_run_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface LeadSource {
  id: string;
  source_type: LeadSourceType;
  source_detail: string;
  campaign: string;
  channel: string;
  first_touch_message_id: string | null;
  first_touch_conversation_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface LeadListItem {
  id: string;
  contact: LeadContact;
  status: LeadStatus;
  stage: LeadStage;
  score: number;
  temperature: LeadTemperature;
  service_interest: string;
  budget_signal: BudgetSignal;
  urgency: LeadUrgency;
  authority_signal: AuthoritySignal;
  next_best_action: string;
  last_scored_at: string | null;
  summary: string;
  created_at: string;
  updated_at: string;
}

export interface LeadDetail extends LeadListItem {
  pain_points: string[];
  technical_needs: string[];
  business_needs: string[];
  metadata: Record<string, unknown>;
  score_snapshots: LeadScoreSnapshot[];
  stage_history: LeadStageHistory[];
  sources: LeadSource[];
}

// --- Label maps (Spanish) ---

export const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  active: "Activo",
  won: "Ganado",
  lost: "Perdido",
  unqualified: "No calificado",
  nurturing: "En nutrición",
  archived: "Archivado",
};

export const LEAD_STAGE_LABELS: Record<LeadStage, string> = {
  new: "Nuevo",
  contacted: "Contactado",
  qualifying: "Calificando",
  warm: "Tibio",
  hot: "Caliente",
  call_requested: "Llamada pedida",
  call_scheduled: "Llamada agendada",
  proposal_pending: "Propuesta pendiente",
  won: "Ganado",
  lost: "Perdido",
  nurturing: "En nutrición",
  unqualified: "No calificado",
};

export const LEAD_TEMPERATURE_LABELS: Record<LeadTemperature, string> = {
  cold: "Frío",
  warm: "Tibio",
  hot: "Caliente",
  critical: "Crítico",
};

export const BUDGET_SIGNAL_LABELS: Record<BudgetSignal, string> = {
  none: "Sin presupuesto",
  unknown: "Desconocido",
  low: "Bajo",
  medium: "Medio",
  high: "Alto",
  confirmed: "Confirmado",
};

export const LEAD_URGENCY_LABELS: Record<LeadUrgency, string> = {
  unknown: "Desconocida",
  low: "Baja",
  medium: "Media",
  high: "Alta",
  critical: "Crítica",
};

export const AUTHORITY_SIGNAL_LABELS: Record<AuthoritySignal, string> = {
  unknown: "Desconocida",
  influencer: "Influenciador",
  decision_maker: "Decisor",
  likely_decision_maker: "Probable decisor",
};

export const LEAD_SOURCE_TYPE_LABELS: Record<LeadSourceType, string> = {
  whatsapp: "WhatsApp",
  manual: "Manual",
  website: "Sitio web",
  referral: "Referido",
  campaign: "Campaña",
  import: "Importación",
  unknown: "Desconocido",
};

export const STAGE_CHANGED_BY_LABELS: Record<StageChangedByType, string> = {
  user: "Usuario",
  ai_agent: "Agente IA",
  system: "Sistema",
  automation: "Automatización",
  worker: "Worker",
};

// --- Tone helpers (semantic badges) ---

export function statusTone(s: LeadStatus): BadgeTone {
  if (s === "won") return "success";
  if (s === "lost" || s === "unqualified") return "danger";
  if (s === "active") return "primary";
  if (s === "nurturing") return "info";
  return "muted";
}

export function stageTone(s: LeadStage): BadgeTone {
  if (s === "won") return "success";
  if (s === "lost" || s === "unqualified") return "danger";
  if (s === "hot" || s === "call_requested" || s === "call_scheduled") {
    return "warning";
  }
  if (s === "proposal_pending") return "info";
  if (s === "new" || s === "contacted" || s === "nurturing") return "muted";
  return "primary";
}

export function temperatureTone(t: LeadTemperature): BadgeTone {
  if (t === "critical") return "danger";
  if (t === "hot") return "warning";
  if (t === "warm") return "info";
  return "muted";
}

export function scoreTone(score: number): BadgeTone {
  if (score >= 75) return "success";
  if (score >= 50) return "warning";
  if (score >= 25) return "info";
  return "muted";
}

// --- Query keys ---

export interface LeadFilters {
  stage?: string;
  status?: string;
  temperature?: string;
  search?: string;
  ordering?: string;
}

export const leadKeys = {
  all: ["leads"] as const,
  list: (filters: LeadFilters) => ["leads", filters] as const,
  detail: (id: string) => ["lead", id] as const,
};

// --- Hooks ---

export function useLeads(filters: LeadFilters) {
  return useQuery({
    queryKey: leadKeys.list(filters),
    queryFn: () =>
      apiGetList<LeadListItem>("/api/v1/leads/", {
        stage: filters.stage,
        status: filters.status,
        temperature: filters.temperature,
        search: filters.search,
        ordering: filters.ordering,
        page_size: 50,
      }),
    refetchInterval: 30_000,
  });
}

export function useLead(id: string) {
  return useQuery({
    queryKey: leadKeys.detail(id),
    queryFn: () => apiGet<LeadDetail>(`/api/v1/leads/${id}/`),
    enabled: !!id,
  });
}

export interface ScoreLeadInput {
  use_ai?: boolean;
  conversation_id?: string;
}

export function useScoreLead(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ScoreLeadInput = {}) =>
      apiPost<LeadScoreSnapshot>(`/api/v1/leads/${id}/score/`, {
        use_ai: input.use_ai ?? true,
        ...(input.conversation_id
          ? { conversation_id: input.conversation_id }
          : {}),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: leadKeys.detail(id) });
      void qc.invalidateQueries({ queryKey: leadKeys.all });
    },
  });
}

export interface ChangeStageInput {
  stage: LeadStage;
  reason?: string;
}

export function useChangeStage(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ChangeStageInput) =>
      apiPatch<LeadDetail>(`/api/v1/leads/${id}/`, {
        stage: input.stage,
        reason: input.reason ?? "",
      }),
    onSuccess: (data) => {
      qc.setQueryData(leadKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: leadKeys.all });
    },
  });
}

export function useConvertToClient(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason?: string) =>
      apiPost<LeadDetail>(`/api/v1/leads/${id}/convert-to-client/`, {
        reason: reason ?? "",
      }),
    onSuccess: (data) => {
      qc.setQueryData(leadKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: leadKeys.all });
    },
  });
}

export function useMarkLost(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) =>
      apiPost<LeadDetail>(`/api/v1/leads/${id}/mark-lost/`, { reason }),
    onSuccess: (data) => {
      qc.setQueryData(leadKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: leadKeys.all });
    },
  });
}

export interface ScheduleFollowupInput {
  due_at?: string;
  title?: string;
  notes?: string;
  idempotency_key?: string;
}

export interface FollowupResult {
  id: string;
  created: boolean;
}

export function useScheduleFollowup(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ScheduleFollowupInput) =>
      apiPost<FollowupResult>(`/api/v1/leads/${id}/schedule-followup/`, {
        ...(input.due_at ? { due_at: input.due_at } : {}),
        title: input.title || "Seguimiento comercial",
        notes: input.notes ?? "",
        ...(input.idempotency_key
          ? { idempotency_key: input.idempotency_key }
          : {}),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: leadKeys.detail(id) });
    },
  });
}
