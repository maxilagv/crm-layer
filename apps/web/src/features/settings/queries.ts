"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";

/* ----------------------------------------------------------------- organization */

export interface OrganizationDetail {
  id: string;
  name: string;
  slug: string;
  status: string;
  plan: string;
  default_timezone: string;
  default_language: string;
  created_at: string;
  updated_at: string;
}

export function useOrganization() {
  return useQuery({
    queryKey: ["settings", "organization"],
    queryFn: () => apiGet<OrganizationDetail>("/api/v1/organizations/current/"),
  });
}

export function useUpdateOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (
      body: Partial<
        Pick<OrganizationDetail, "name" | "default_timezone" | "default_language">
      >,
    ) => apiPatch<OrganizationDetail>("/api/v1/organizations/current/", body),
    onSuccess: (data) => {
      qc.setQueryData(["settings", "organization"], data);
      void qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

/* -------------------------------------------------------------- policy singletons */

export interface BusinessProfile {
  id: string;
  business_name: string;
  owner_name: string;
  owner_phone: string;
  default_language: string;
  timezone: string;
  business_description: string;
  services_offered: string[];
  target_clients: string[];
  brand_tone: string;
  calendar_link: string;
  website_url: string;
  owner_writing_style: string;
  signature_phrases: string[];
}

export interface SalesPolicy {
  id: string;
  main_sales_goal: string;
  call_to_action: string;
  can_quote_prices: boolean;
  price_min: string | null;
  price_max: string | null;
  price_policy_text: string;
  must_handoff_for_price: boolean;
  common_objections: string[];
  forbidden_claims: string[];
  sales_tone: string;
}

export interface SupportPolicy {
  id: string;
  support_hours: Record<string, unknown>;
  allowed_support_actions: string[];
  forbidden_support_actions: string[];
  urgent_keywords: string[];
  critical_ticket_rules: string[];
  data_request_policy: string;
  default_support_reply: string;
}

export interface AiPolicy {
  id: string;
  default_provider: string;
  fallback_provider: string;
  default_sales_model: string;
  default_support_model: string;
  max_context_messages: number;
  temperature_sales: string;
  temperature_support: string;
  auto_reply_enabled: boolean;
  human_handoff_required_for_risks: boolean;
}

export interface NotificationPolicy {
  id: string;
  notify_on_new_lead: boolean;
  notify_on_human_handoff: boolean;
  notify_on_failed_ai_reply: boolean;
  notification_channels: string[];
  quiet_hours: Record<string, unknown>;
}

export interface WhatsappPolicy {
  id: string;
  auto_reply_enabled: boolean;
  business_hours: Record<string, unknown>;
  handoff_keywords: string[];
  opt_out_keywords: string[];
  allowed_outbound_templates: string[];
  media_download_enabled: boolean;
}

function singletonHooks<T>(key: string, path: string) {
  const useRead = () =>
    useQuery({ queryKey: ["settings", key], queryFn: () => apiGet<T>(path) });
  const useUpdate = () => {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (body: Partial<T>) => apiPatch<T>(path, body),
      onSuccess: (data) => qc.setQueryData(["settings", key], data),
    });
  };
  return { useRead, useUpdate };
}

export const businessProfile = singletonHooks<BusinessProfile>(
  "business-profile",
  "/api/v1/settings/business-profile/",
);
export const salesPolicy = singletonHooks<SalesPolicy>(
  "sales-policy",
  "/api/v1/settings/sales-policy/",
);
export const supportPolicy = singletonHooks<SupportPolicy>(
  "support-policy",
  "/api/v1/settings/support-policy/",
);
export const aiPolicy = singletonHooks<AiPolicy>(
  "ai-policy",
  "/api/v1/settings/ai-policy/",
);
export const notificationPolicy = singletonHooks<NotificationPolicy>(
  "notification-policy",
  "/api/v1/settings/notification-policy/",
);
export const whatsappPolicy = singletonHooks<WhatsappPolicy>(
  "whatsapp-policy",
  "/api/v1/settings/whatsapp-policy/",
);

/* ----------------------------------------------------------------- AI providers */

export interface AiProvider {
  id: string;
  name: string;
  provider_type: string;
  is_enabled: boolean;
  priority: number;
  created_at: string;
}

export interface AiConnectionProvider {
  provider_type: string;
  label: string;
  env_var: string | null;
  credential_configured: boolean;
  registered: boolean;
  enabled: boolean;
}

export interface AiConnection {
  providers: AiConnectionProvider[];
  active_model_configs: number;
}

export function useAiProviders() {
  return useQuery({
    queryKey: ["settings", "ai-providers"],
    queryFn: () => apiGet<AiProvider[]>("/api/v1/ai/providers/"),
  });
}

export function useAiConnection() {
  return useQuery({
    queryKey: ["settings", "ai-connection"],
    queryFn: () => apiGet<AiConnection>("/api/v1/ai/connection/"),
  });
}

export function useCreateAiProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; provider_type: string; priority?: number }) =>
      apiPost<AiProvider>("/api/v1/ai/providers/", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings", "ai-providers"] });
      void qc.invalidateQueries({ queryKey: ["settings", "ai-connection"] });
    },
  });
}

export function useUpdateAiProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<AiProvider>) =>
      apiPatch<AiProvider>(`/api/v1/ai/providers/${id}/`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings", "ai-providers"] });
      void qc.invalidateQueries({ queryKey: ["settings", "ai-connection"] });
    },
  });
}

/* ------------------------------------------------------------------- WhatsApp */

export interface WhatsappConnection {
  connected: boolean;
  credentials: {
    access_token: boolean;
    verify_token: boolean;
    app_secret: boolean;
  };
  accounts: number;
  phone_numbers: number;
  graph_api_version: string;
  webhook_path: string;
  env_vars: string[];
}

export interface WhatsappAccount {
  id: string;
  waba_id: string;
  name: string;
  status: string;
  created_at: string;
}

export interface WhatsappNumber {
  id: string;
  business_account_id: string;
  phone_number_id: string;
  display_phone_number: string;
  verified_name: string;
  status: string;
  created_at: string;
}

export function useWhatsappConnection() {
  return useQuery({
    queryKey: ["settings", "whatsapp-connection"],
    queryFn: () => apiGet<WhatsappConnection>("/api/v1/whatsapp/connection/"),
  });
}

export interface BridgeStatus {
  state: string;
  qr: string | null;
  info: Record<string, unknown>;
  updated_at: string | null;
}

export function useBridgeStatus() {
  return useQuery({
    queryKey: ["settings", "wa-bridge-status"],
    queryFn: () => apiGet<BridgeStatus>("/api/v1/whatsapp/bridge/status/"),
    refetchInterval: 3000,
  });
}

export function useWhatsappAccounts() {
  return useQuery({
    queryKey: ["settings", "whatsapp-accounts"],
    queryFn: () => apiGet<WhatsappAccount[]>("/api/v1/whatsapp/accounts/"),
  });
}

export function useWhatsappNumbers() {
  return useQuery({
    queryKey: ["settings", "whatsapp-numbers"],
    queryFn: () => apiGet<WhatsappNumber[]>("/api/v1/whatsapp/phone-numbers/"),
  });
}

export function useCreateWhatsappAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { waba_id: string; name: string }) =>
      apiPost<WhatsappAccount>("/api/v1/whatsapp/accounts/", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings", "whatsapp-accounts"] });
      void qc.invalidateQueries({ queryKey: ["settings", "whatsapp-connection"] });
    },
  });
}

export function useCreateWhatsappNumber() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      business_account_id: string;
      phone_number_id: string;
      display_phone_number?: string;
      verified_name?: string;
    }) => apiPost<WhatsappNumber>("/api/v1/whatsapp/phone-numbers/", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings", "whatsapp-numbers"] });
      void qc.invalidateQueries({ queryKey: ["settings", "whatsapp-connection"] });
    },
  });
}
