"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiGetList, apiPatch, apiPost } from "@/lib/api/client";
import type { BadgeTone } from "@/components/ui/badge";

export type ContactType =
  | "unknown"
  | "lead"
  | "client"
  | "internal"
  | "supplier"
  | "blocked";
export type ContactStatus = "active" | "inactive" | "blocked" | "archived";
export type ContactSource =
  | "unknown"
  | "manual"
  | "whatsapp"
  | "email"
  | "import"
  | "api"
  | "system";
export type NoteVisibility = "internal" | "team" | "private";

export interface ContactPhone {
  id: string;
  phone_e164: string;
  country_code: string | null;
  is_primary: boolean;
  is_whatsapp: boolean;
  verified_at: string | null;
}

export interface ContactEmail {
  id: string;
  email: string;
  normalized_email: string | null;
  is_primary: boolean;
  verified_at: string | null;
}

export interface ContactTag {
  id: string;
  name: string;
  slug: string;
  color: string;
}

export interface Company {
  id: string;
  name: string;
  website: string | null;
  industry: string | null;
  size: string | null;
  country: string | null;
}

export interface ContactCompany {
  id: string;
  company: Company;
  role: string | null;
  title: string | null;
  is_primary: boolean;
  started_at: string | null;
  ended_at: string | null;
}

export interface ContactNoteAuthor {
  id: string;
  name: string;
}

export interface ContactNote {
  id: string;
  body: string;
  visibility: NoteVisibility;
  author: ContactNoteAuthor | null;
  created_at: string;
  updated_at: string;
}

export interface ContactListItem {
  id: string;
  display_name: string | null;
  type: ContactType;
  status: ContactStatus;
  source: ContactSource;
  company_name: string | null;
  language: string | null;
  timezone: string | null;
  summary: string | null;
  primary_phone: string | null;
  primary_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactDetail {
  id: string;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  type: ContactType;
  status: ContactStatus;
  source: ContactSource;
  language: string | null;
  timezone: string | null;
  avatar_url: string | null;
  summary: string | null;
  metadata: Record<string, unknown>;
  primary_phone: string | null;
  primary_email: string | null;
  phones: ContactPhone[];
  emails: ContactEmail[];
  tags: ContactTag[];
  companies: ContactCompany[];
  created_at: string;
  updated_at: string;
}

export const CONTACT_TYPE_LABELS: Record<ContactType, string> = {
  unknown: "Sin clasificar",
  lead: "Lead",
  client: "Cliente",
  internal: "Interno",
  supplier: "Proveedor",
  blocked: "Bloqueado",
};

export const CONTACT_STATUS_LABELS: Record<ContactStatus, string> = {
  active: "Activo",
  inactive: "Inactivo",
  blocked: "Bloqueado",
  archived: "Archivado",
};

export const CONTACT_SOURCE_LABELS: Record<ContactSource, string> = {
  unknown: "Desconocido",
  manual: "Manual",
  whatsapp: "WhatsApp",
  email: "Email",
  import: "Importado",
  api: "API",
  system: "Sistema",
};

export function typeTone(t: ContactType): BadgeTone {
  if (t === "client") return "success";
  if (t === "lead") return "primary";
  if (t === "supplier") return "info";
  if (t === "blocked") return "danger";
  return "muted";
}

export function statusTone(s: ContactStatus): BadgeTone {
  if (s === "active") return "success";
  if (s === "blocked") return "danger";
  if (s === "inactive") return "warning";
  return "muted";
}

export interface ContactFilters {
  search?: string;
  type?: string;
  status?: string;
  source?: string;
  tag?: string;
  ordering?: string;
}

export const contactKeys = {
  all: ["contacts"] as const,
  list: (filters: ContactFilters) => ["contacts", filters] as const,
  detail: (id: string) => ["contact", id] as const,
};

export function useContacts(filters: ContactFilters) {
  return useQuery({
    queryKey: contactKeys.list(filters),
    queryFn: () =>
      apiGetList<ContactListItem>("/api/v1/contacts/", {
        search: filters.search,
        type: filters.type,
        status: filters.status,
        source: filters.source,
        tag: filters.tag,
        ordering: filters.ordering ?? "-updated_at",
        page_size: 50,
      }),
  });
}

export function useContact(id: string) {
  return useQuery({
    queryKey: contactKeys.detail(id),
    queryFn: () => apiGet<ContactDetail>(`/api/v1/contacts/${id}/`),
    enabled: !!id,
  });
}

export interface CreateContactInput {
  display_name?: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  type?: ContactType;
  status?: ContactStatus;
  source?: ContactSource;
  summary?: string;
  phones?: { phone: string; is_primary?: boolean; is_whatsapp?: boolean }[];
  emails?: { email: string; is_primary?: boolean }[];
}

export function useCreateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateContactInput) =>
      apiPost<ContactDetail>("/api/v1/contacts/", input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: contactKeys.all });
    },
  });
}

export interface UpdateContactInput {
  display_name?: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  type?: ContactType;
  status?: ContactStatus;
  source?: ContactSource;
  summary?: string;
}

export function useUpdateContact(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateContactInput) =>
      apiPatch<ContactDetail>(`/api/v1/contacts/${id}/`, input),
    onSuccess: (data) => {
      qc.setQueryData(contactKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: contactKeys.all });
    },
  });
}

export interface AddNoteInput {
  body: string;
  visibility?: NoteVisibility;
}

export function useAddNote(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddNoteInput) =>
      apiPost<ContactNote>(`/api/v1/contacts/${id}/notes/`, {
        body: input.body,
        visibility: input.visibility ?? "internal",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: contactKeys.detail(id) });
    },
  });
}

export interface AddTagInput {
  name: string;
  color?: string;
}

export function useAddTag(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddTagInput) =>
      apiPost<ContactTag[]>(`/api/v1/contacts/${id}/tags/`, {
        name: input.name,
        color: input.color ?? "",
      }),
    onSuccess: (tags) => {
      qc.setQueryData<ContactDetail | undefined>(
        contactKeys.detail(id),
        (prev) => (prev ? { ...prev, tags } : prev),
      );
      void qc.invalidateQueries({ queryKey: contactKeys.detail(id) });
    },
  });
}
