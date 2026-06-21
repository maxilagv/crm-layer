"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { BadgeTone } from "@/components/ui/badge";
import { apiGet, apiGetList, apiPatch, apiPost } from "@/lib/api/client";

export type CampaignStatus = "draft" | "active" | "paused" | "completed" | "archived";
export type ProspectStatus =
  | "discovered"
  | "qualified"
  | "approved"
  | "contacted"
  | "replied"
  | "interested"
  | "not_interested"
  | "disqualified"
  | "do_not_contact"
  | "failed";

export interface ProspectingCampaign {
  id: string;
  name: string;
  vertical: string;
  query: string;
  location_hint: string;
  status: CampaignStatus;
  channel: "whatsapp" | "sms" | "email";
  target_profile: string;
  min_fit_score: number;
  auto_contact: boolean;
  daily_cap: number;
  discovered_count: number;
  qualified_count: number;
  contacted_count: number;
  interested_count: number;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Prospect {
  id: string;
  campaign: string;
  place_id: string;
  business_name: string;
  category: string;
  address: string;
  phone: string;
  owner_email: string;
  website: string;
  rating: string | null;
  reviews_count: number;
  photos_count: number;
  status: ProspectStatus;
  fit_score: number | null;
  signals: string[];
  reasoning: string;
  recommended_angle: string;
  contact_id: string | null;
  conversation_id: string | null;
  lead_id: string | null;
  qualified_at: string | null;
  contacted_at: string | null;
  replied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignFilters {
  status?: string;
}

export interface ProspectFilters {
  campaign_id?: string;
  status?: string;
  min_fit_score?: number;
  search?: string;
}

export interface CreateCampaignInput {
  name: string;
  query: string;
  vertical?: string;
  location_hint?: string;
  target_profile?: string;
  min_fit_score?: number;
  auto_contact?: boolean;
  channel?: "whatsapp" | "sms" | "email";
  daily_cap?: number;
}

export interface UpdateCampaignInput {
  name?: string;
  vertical?: string;
  query?: string;
  location_hint?: string;
  status?: CampaignStatus;
  target_profile?: string;
  min_fit_score?: number;
  auto_contact?: boolean;
  channel?: "whatsapp" | "sms" | "email";
  daily_cap?: number;
}

export interface ProspectingPolicy {
  id: string;
  agent_paused: boolean;
  send_start_hour: number;
  send_cutoff_hour: number;
  org_daily_cap: number | null;
  updated_at: string;
}

export interface UpdateProspectingPolicyInput {
  agent_paused?: boolean;
  send_start_hour?: number;
  send_cutoff_hour?: number;
  org_daily_cap?: number | null;
}

export interface ProspectingReportContact {
  id: string;
  business_name: string;
  status: ProspectStatus;
  bucket: "respondieron" | "se_tuvo_charla" | "sin_dialogo";
  last_touch_at: string | null;
  fit_score: number | null;
  owner_email: string;
  phone: string;
}

export interface ProspectingReport {
  contacts: ProspectingReportContact[];
  buckets: Record<ProspectingReportContact["bucket"], number>;
  progress_pct: number;
  totals: {
    contactables: number;
    by_status: Array<{ status: ProspectStatus; total: number }>;
  };
}

export const CAMPAIGN_STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: "Borrador",
  active: "Activa",
  paused: "Pausada",
  completed: "Completada",
  archived: "Archivada",
};

export const PROSPECT_STATUS_LABELS: Record<ProspectStatus, string> = {
  discovered: "Descubierto",
  qualified: "Calificado",
  approved: "Aprobado",
  contacted: "Contactado",
  replied: "Respondio",
  interested: "Interesado",
  not_interested: "No interesado",
  disqualified: "Descartado",
  do_not_contact: "No contactar",
  failed: "Error",
};

export function campaignStatusTone(status: CampaignStatus): BadgeTone {
  if (status === "active") return "success";
  if (status === "paused") return "warning";
  if (status === "archived") return "muted";
  if (status === "completed") return "info";
  return "primary";
}

export function prospectStatusTone(status: ProspectStatus): BadgeTone {
  if (status === "interested") return "success";
  if (status === "approved" || status === "qualified") return "primary";
  if (status === "contacted" || status === "replied") return "info";
  if (status === "disqualified" || status === "not_interested") return "muted";
  if (status === "do_not_contact" || status === "failed") return "danger";
  return "warning";
}

export function fitScoreTone(score: number | null): BadgeTone {
  if (score === null) return "muted";
  if (score >= 75) return "success";
  if (score >= 60) return "primary";
  if (score >= 40) return "warning";
  return "muted";
}

export const cazadorKeys = {
  campaigns: (filters: CampaignFilters) => ["cazador", "campaigns", filters] as const,
  prospects: (filters: ProspectFilters) => ["cazador", "prospects", filters] as const,
  policy: () => ["cazador", "prospecting-policy"] as const,
  report: (filters: { campaign_id?: string }) => ["cazador", "report", filters] as const,
};

export function useProspectingPolicy() {
  return useQuery({
    queryKey: cazadorKeys.policy(),
    queryFn: () => apiGet<ProspectingPolicy>("/api/v1/settings/prospecting-policy/"),
    refetchInterval: 30_000,
  });
}

export function useUpdateProspectingPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateProspectingPolicyInput) =>
      apiPatch<ProspectingPolicy>("/api/v1/settings/prospecting-policy/", input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: cazadorKeys.policy() });
    },
  });
}

export function useCampaigns(filters: CampaignFilters = {}) {
  return useQuery({
    queryKey: cazadorKeys.campaigns(filters),
    queryFn: () =>
      apiGetList<ProspectingCampaign>("/api/v1/prospecting/campaigns/", {
        status: filters.status,
        page_size: 50,
      }),
    refetchInterval: 30_000,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCampaignInput) =>
      apiPost<ProspectingCampaign>("/api/v1/prospecting/campaigns/", input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cazador", "campaigns"] });
    },
  });
}

export function useUpdateCampaign(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateCampaignInput) =>
      apiPatch<ProspectingCampaign>(`/api/v1/prospecting/campaigns/${id}/`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cazador", "campaigns"] });
    },
  });
}

export function useDiscoverCampaign(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiPost<{ queued: boolean; campaign_id: string }>(
        `/api/v1/prospecting/campaigns/${id}/discover/`,
        {},
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cazador", "campaigns"] });
      void qc.invalidateQueries({ queryKey: ["cazador", "prospects"] });
    },
  });
}

export function useRunOutreach(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiPost<{ queued: boolean; campaign_id: string }>(
        `/api/v1/prospecting/campaigns/${id}/run-outreach/`,
        {},
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cazador", "campaigns"] });
      void qc.invalidateQueries({ queryKey: ["cazador", "prospects"] });
    },
  });
}

export function useProspectingReport(filters: { campaign_id?: string } = {}) {
  return useQuery({
    queryKey: cazadorKeys.report(filters),
    queryFn: () =>
      apiGet<ProspectingReport>("/api/v1/prospecting/report/", {
        campaign_id: filters.campaign_id,
        page_size: 200,
      }),
    refetchInterval: 30_000,
  });
}

export function useProspects(filters: ProspectFilters = {}) {
  return useQuery({
    queryKey: cazadorKeys.prospects(filters),
    queryFn: () =>
      apiGetList<Prospect>("/api/v1/prospecting/prospects/", {
        campaign_id: filters.campaign_id,
        status: filters.status,
        min_fit_score: filters.min_fit_score,
        search: filters.search,
        page_size: 50,
      }),
    refetchInterval: 20_000,
  });
}

export function useUpdateProspect(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { status: ProspectStatus }) =>
      apiPatch<Prospect>(`/api/v1/prospecting/prospects/${id}/`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cazador", "prospects"] });
      void qc.invalidateQueries({ queryKey: ["cazador", "campaigns"] });
    },
  });
}
