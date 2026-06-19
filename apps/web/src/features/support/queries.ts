"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { BadgeTone } from "@/components/ui/badge";
import { apiGet, apiGetList, apiPost } from "@/lib/api/client";

/* ------------------------------------------------------------------ */
/* Enums (match crm/support/domain/enums.py exactly)                  */
/* ------------------------------------------------------------------ */

export type TicketStatus =
  | "open"
  | "waiting_client"
  | "triaged"
  | "in_progress"
  | "blocked"
  | "resolved"
  | "closed"
  | "cancelled";

export type TicketPriority = "low" | "medium" | "high" | "urgent" | "critical";

export type TicketCategory =
  | "bug"
  | "access"
  | "billing"
  | "feature_request"
  | "integration"
  | "performance"
  | "data_issue"
  | "unknown";

export type CommentVisibility = "internal" | "client";

export type CommentAuthorType =
  | "user"
  | "ai_agent"
  | "system"
  | "worker"
  | "webhook"
  | "client";

export type AttachmentType =
  | "audio"
  | "image"
  | "document"
  | "log"
  | "screenshot"
  | "generated_asset"
  | "other";

/* ------------------------------------------------------------------ */
/* Types (snake_case, match the support serializers exactly)          */
/* ------------------------------------------------------------------ */

export interface TicketComment {
  id: string;
  author_type: CommentAuthorType;
  author_id: string | null;
  body: string;
  visibility: CommentVisibility;
  created_at: string;
}

export interface TicketAttachment {
  id: string;
  media_asset_id: string | null;
  attachment_type: AttachmentType;
  mime_type: string | null;
  file_name: string | null;
  source_message_id: string | null;
  created_at: string;
}

export interface TicketListItem {
  id: string;
  title: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  client_id: string | null;
  contact_id: string | null;
  contact_display_name: string | null;
  assigned_user_id: string | null;
  conversation_id: string | null;
  due_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail {
  id: string;
  client_id: string | null;
  contact_id: string | null;
  conversation_id: string | null;
  source_message_id: string | null;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  title: string;
  description: string;
  technical_summary: string | null;
  ai_summary: string | null;
  assigned_user_id: string | null;
  due_at: string | null;
  resolved_at: string | null;
  metadata: Record<string, unknown>;
  comments: TicketComment[];
  attachments: TicketAttachment[];
  created_at: string;
  updated_at: string;
}

/** Contact summary from GET /api/v1/contacts/ (for the create-ticket picker). */
export interface ContactPickerItem {
  id: string;
  display_name: string | null;
  type: string;
  status: string;
  company_name: string | null;
  primary_phone: string | null;
}

/* ------------------------------------------------------------------ */
/* Label maps + tone helpers                                          */
/* ------------------------------------------------------------------ */

export const TICKET_STATUS_LABELS: Record<TicketStatus, string> = {
  open: "Abierto",
  waiting_client: "Esperando cliente",
  triaged: "Triado",
  in_progress: "En curso",
  blocked: "Bloqueado",
  resolved: "Resuelto",
  closed: "Cerrado",
  cancelled: "Cancelado",
};

export const TICKET_PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
  critical: "Crítica",
};

export const TICKET_CATEGORY_LABELS: Record<TicketCategory, string> = {
  bug: "Bug",
  access: "Acceso",
  billing: "Facturación",
  feature_request: "Mejora",
  integration: "Integración",
  performance: "Rendimiento",
  data_issue: "Datos",
  unknown: "Sin categoría",
};

export const COMMENT_VISIBILITY_LABELS: Record<CommentVisibility, string> = {
  internal: "Interno",
  client: "Cliente",
};

export const COMMENT_AUTHOR_LABELS: Record<CommentAuthorType, string> = {
  user: "Usuario",
  ai_agent: "Agente IA",
  system: "Sistema",
  worker: "Worker",
  webhook: "Webhook",
  client: "Cliente",
};

export const ATTACHMENT_TYPE_LABELS: Record<AttachmentType, string> = {
  audio: "Audio",
  image: "Imagen",
  document: "Documento",
  log: "Log",
  screenshot: "Captura",
  generated_asset: "Generado",
  other: "Otro",
};

export function statusTone(s: TicketStatus): BadgeTone {
  if (s === "resolved" || s === "closed") return "success";
  if (s === "open") return "info";
  if (s === "in_progress" || s === "triaged") return "primary";
  if (s === "waiting_client") return "warning";
  if (s === "blocked") return "danger";
  return "muted"; // cancelled
}

export function priorityTone(p: TicketPriority): BadgeTone {
  if (p === "critical" || p === "urgent") return "danger";
  if (p === "high") return "warning";
  if (p === "medium") return "info";
  return "muted"; // low
}

export function categoryTone(c: TicketCategory): BadgeTone {
  if (c === "bug" || c === "data_issue") return "danger";
  if (c === "billing") return "warning";
  if (c === "feature_request") return "primary";
  if (c === "unknown") return "muted";
  return "info";
}

/** True for statuses that represent a closed/done ticket (can be reopened). */
export function isClosedStatus(s: TicketStatus): boolean {
  return s === "resolved" || s === "closed" || s === "cancelled";
}

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

export interface TicketFilters {
  status?: string;
  priority?: string;
  category?: string;
  search?: string;
}

export const ticketKeys = {
  all: ["tickets"] as const,
  list: (filters: TicketFilters) => ["tickets", filters] as const,
  detail: (id: string) => ["ticket", id] as const,
  contactSearch: (search: string) => ["ticket-contacts", search] as const,
};

/* ------------------------------------------------------------------ */
/* Hooks                                                               */
/* ------------------------------------------------------------------ */

export function useTickets(filters: TicketFilters) {
  return useQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: () =>
      apiGetList<TicketListItem>("/api/v1/tickets/", {
        status: filters.status,
        priority: filters.priority,
        category: filters.category,
        search: filters.search,
        page_size: 50,
      }),
    refetchInterval: 30_000,
  });
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ticketKeys.detail(id),
    queryFn: () => apiGet<TicketDetail>(`/api/v1/tickets/${id}/`),
    enabled: !!id,
  });
}

/** Lightweight contact search for the create-ticket picker. */
export function useContactSearch(search: string) {
  return useQuery({
    queryKey: ticketKeys.contactSearch(search),
    queryFn: () =>
      apiGetList<ContactPickerItem>("/api/v1/contacts/", {
        search: search || undefined,
        page_size: 20,
      }),
  });
}

export interface CreateTicketInput {
  contact_id: string;
  title: string;
  description?: string;
  category?: TicketCategory;
  priority?: TicketPriority;
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTicketInput) =>
      apiPost<TicketDetail>("/api/v1/tickets/", input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useAssignTicket(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      apiPost<TicketDetail>(`/api/v1/tickets/${id}/assign/`, {
        user_id: userId,
      }),
    onSuccess: (data) => {
      qc.setQueryData(ticketKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export interface ResolveTicketInput {
  summary: string;
  root_cause?: string;
  resolution_steps?: string;
}

export function useResolveTicket(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ResolveTicketInput) =>
      apiPost<TicketDetail>(`/api/v1/tickets/${id}/resolve/`, input),
    onSuccess: (data) => {
      qc.setQueryData(ticketKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export function useReopenTicket(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) =>
      apiPost<TicketDetail>(`/api/v1/tickets/${id}/reopen/`, { reason }),
    onSuccess: (data) => {
      qc.setQueryData(ticketKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: ticketKeys.all });
    },
  });
}

export interface AddCommentInput {
  body: string;
  visibility: CommentVisibility;
}

export function useAddComment(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddCommentInput) =>
      apiPost<TicketComment>(`/api/v1/tickets/${id}/comments/`, input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ticketKeys.detail(id) });
    },
  });
}
