"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { BadgeTone } from "@/components/ui/badge";
import { apiGet, apiGetArray, apiGetList, apiPatch, apiPost } from "@/lib/api/client";

/* ------------------------------------------------------------------ */
/* Enums (match crm.clients.domain.enums)                              */
/* ------------------------------------------------------------------ */

export type ClientStatus =
  | "active"
  | "paused"
  | "cancelled"
  | "onboarding"
  | "delinquent"
  | "archived";

export type SupportLevel = "standard" | "priority" | "vip" | "internal";

export type OnboardingStatus = "not_started" | "in_progress" | "completed";

export type ClientContactRole =
  | "owner"
  | "admin"
  | "technical"
  | "billing"
  | "user"
  | "other";

export type ServiceType =
  | "crm"
  | "automation"
  | "whatsapp"
  | "web"
  | "integration"
  | "support"
  | "consulting"
  | "other";

export type ServiceStatus =
  | "active"
  | "paused"
  | "cancelled"
  | "completed"
  | "pending";

/* ------------------------------------------------------------------ */
/* Resource types (match the serializers exactly)                      */
/* ------------------------------------------------------------------ */

export interface ClientContactLink {
  id: string;
  contact_id: string;
  contact_display_name: string | null;
  role: ClientContactRole;
  is_primary: boolean;
  can_request_support: boolean;
  receives_notifications: boolean;
  created_at: string;
}

export interface ClientService {
  id: string;
  name: string;
  service_type: ServiceType;
  status: ServiceStatus;
  started_at: string | null;
  ended_at: string | null;
  configuration: Record<string, unknown>;
  created_at: string;
}

export interface ClientListItem {
  id: string;
  contact_id: string;
  contact_display_name: string | null;
  display_name: string;
  status: ClientStatus;
  service_plan: string;
  support_level: SupportLevel;
  onboarding_status: OnboardingStatus;
  created_at: string;
  updated_at: string;
}

export interface ClientDetail {
  id: string;
  contact_id: string;
  company_id: string | null;
  display_name: string;
  status: ClientStatus;
  service_plan: string;
  support_level: SupportLevel;
  onboarding_status: OnboardingStatus;
  started_at: string | null;
  ended_at: string | null;
  metadata: Record<string, unknown>;
  client_contacts: ClientContactLink[];
  services: ClientService[];
  created_at: string;
  updated_at: string;
}

/** Light contact shape for the registration picker (from /api/v1/contacts/). */
export interface ContactPickerItem {
  id: string;
  display_name: string | null;
  primary_phone: string | null;
}

/* ------------------------------------------------------------------ */
/* Label maps + tone helpers (like conversations.ts)                   */
/* ------------------------------------------------------------------ */

export const CLIENT_STATUS_LABELS: Record<ClientStatus, string> = {
  active: "Activo",
  paused: "Pausado",
  cancelled: "Cancelado",
  onboarding: "Onboarding",
  delinquent: "Moroso",
  archived: "Archivado",
};

export const SUPPORT_LEVEL_LABELS: Record<SupportLevel, string> = {
  standard: "Estándar",
  priority: "Prioritario",
  vip: "VIP",
  internal: "Interno",
};

export const ONBOARDING_STATUS_LABELS: Record<OnboardingStatus, string> = {
  not_started: "Sin iniciar",
  in_progress: "En curso",
  completed: "Completado",
};

export const CLIENT_CONTACT_ROLE_LABELS: Record<ClientContactRole, string> = {
  owner: "Dueño",
  admin: "Administrador",
  technical: "Técnico",
  billing: "Facturación",
  user: "Usuario",
  other: "Otro",
};

export const SERVICE_TYPE_LABELS: Record<ServiceType, string> = {
  crm: "CRM",
  automation: "Automatización",
  whatsapp: "WhatsApp",
  web: "Web",
  integration: "Integración",
  support: "Soporte",
  consulting: "Consultoría",
  other: "Otro",
};

export const SERVICE_STATUS_LABELS: Record<ServiceStatus, string> = {
  active: "Activo",
  paused: "Pausado",
  cancelled: "Cancelado",
  completed: "Completado",
  pending: "Pendiente",
};

export function clientStatusTone(s: ClientStatus): BadgeTone {
  if (s === "active") return "success";
  if (s === "onboarding") return "info";
  if (s === "paused") return "warning";
  if (s === "delinquent") return "danger";
  return "muted";
}

export function supportLevelTone(l: SupportLevel): BadgeTone {
  if (l === "vip") return "primary";
  if (l === "priority") return "info";
  if (l === "internal") return "muted";
  return "default";
}

export function onboardingTone(o: OnboardingStatus): BadgeTone {
  if (o === "completed") return "success";
  if (o === "in_progress") return "info";
  return "muted";
}

export function serviceStatusTone(s: ServiceStatus): BadgeTone {
  if (s === "active") return "success";
  if (s === "completed") return "info";
  if (s === "paused" || s === "pending") return "warning";
  return "muted";
}

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

export const clientKeys = {
  list: (filters: ClientFilters) => ["clients", filters] as const,
  detail: (id: string) => ["client", id] as const,
  contacts: (id: string) => ["client", id, "contacts"] as const,
  services: (id: string) => ["client", id, "services"] as const,
  contactPicker: (search: string) => ["client-contact-picker", search] as const,
};

/* ------------------------------------------------------------------ */
/* Queries                                                             */
/* ------------------------------------------------------------------ */

export interface ClientFilters {
  status?: string;
  support_level?: string;
  search?: string;
}

export function useClients(filters: ClientFilters) {
  return useQuery({
    queryKey: clientKeys.list(filters),
    queryFn: () =>
      apiGetList<ClientListItem>("/api/v1/clients/", {
        status: filters.status,
        support_level: filters.support_level,
        search: filters.search,
        page_size: 50,
      }),
  });
}

export function useClient(id: string) {
  return useQuery({
    queryKey: clientKeys.detail(id),
    queryFn: () => apiGet<ClientDetail>(`/api/v1/clients/${id}/`),
    enabled: !!id,
  });
}

export function useClientContacts(id: string) {
  return useQuery({
    queryKey: clientKeys.contacts(id),
    queryFn: () => apiGetArray<ClientContactLink>(`/api/v1/clients/${id}/contacts/`),
    enabled: !!id,
  });
}

export function useClientServices(id: string) {
  return useQuery({
    queryKey: clientKeys.services(id),
    queryFn: () => apiGetArray<ClientService>(`/api/v1/clients/${id}/services/`),
    enabled: !!id,
  });
}

/** Contact search used by the "Registrar cliente" picker. */
export function useContactPicker(search: string) {
  return useQuery({
    queryKey: clientKeys.contactPicker(search),
    queryFn: () =>
      apiGetList<ContactPickerItem>("/api/v1/contacts/", {
        search: search || undefined,
        page_size: 20,
      }),
  });
}

/* ------------------------------------------------------------------ */
/* Mutations                                                           */
/* ------------------------------------------------------------------ */

export interface RegisterClientInput {
  contact_id: string;
  display_name?: string;
  service_plan?: string;
  support_level?: SupportLevel;
}

export function useRegisterClient() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: RegisterClientInput) =>
      apiPost<ClientDetail>("/api/v1/clients/", input),
    onSuccess: (data) => {
      qc.setQueryData(clientKeys.detail(data.id), data);
      void qc.invalidateQueries({ queryKey: ["clients"] });
    },
  });
}

export interface UpdateClientInput {
  display_name?: string;
  service_plan?: string;
  support_level?: SupportLevel;
  status?: ClientStatus;
  onboarding_status?: OnboardingStatus;
}

export function useUpdateClient(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateClientInput) =>
      apiPatch<ClientDetail>(`/api/v1/clients/${id}/`, input),
    onSuccess: (data) => {
      qc.setQueryData(clientKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: ["clients"] });
    },
  });
}

export interface AddClientContactInput {
  contact_id: string;
  role?: ClientContactRole;
  is_primary?: boolean;
  can_request_support?: boolean;
  receives_notifications?: boolean;
}

export function useAddClientContact(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddClientContactInput) =>
      apiPost<ClientContactLink>(`/api/v1/clients/${id}/contacts/`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clientKeys.contacts(id) });
      void qc.invalidateQueries({ queryKey: clientKeys.detail(id) });
    },
  });
}

export interface AddClientServiceInput {
  name: string;
  service_type?: ServiceType;
  status?: ServiceStatus;
  configuration?: Record<string, unknown>;
}

export function useAddClientService(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddClientServiceInput) =>
      apiPost<ClientService>(`/api/v1/clients/${id}/services/`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clientKeys.services(id) });
      void qc.invalidateQueries({ queryKey: clientKeys.detail(id) });
    },
  });
}
