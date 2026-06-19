"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiGetList, apiPatch } from "@/lib/api/client";

export type DocumentTypeValue = "proposal" | "quote" | "invoice" | "report" | "deck";
export type DocumentFormatValue = "pdf" | "xlsx" | "pptx";
export type DocumentStatusValue = "draft" | "ready" | "sent" | "failed";

export interface GeneratedDocument {
  id: string;
  doc_type: DocumentTypeValue;
  doc_format: DocumentFormatValue;
  title: string;
  status: DocumentStatusValue;
  payload: Record<string, unknown>;
  media_asset_id: string | null;
  client_id: string | null;
  lead_id: string | null;
  conversation_id: string | null;
  contact_id: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentFilters {
  doc_type?: string;
  status?: string;
  format?: string;
  search?: string;
}

export interface DocumentDownload {
  url: string;
  expires_in: number;
  file_name: string;
  mime_type: string;
  title: string;
}

export interface BrandKit {
  id: string;
  business_name: string;
  legal_name: string;
  tax_id: string;
  email: string;
  phone: string;
  website: string;
  address: string;
  logo_media_id: string | null;
  primary_color: string;
  accent_color: string;
  text_color: string;
  currency: string;
  default_tax_rate: string;
  default_terms: string;
  footer_note: string;
  created_at: string;
  updated_at: string;
}

export const documentKeys = {
  all: ["documents"] as const,
  list: (filters: DocumentFilters) => ["documents", filters] as const,
};

export function useDocuments(filters: DocumentFilters) {
  return useQuery({
    queryKey: documentKeys.list(filters),
    queryFn: () =>
      apiGetList<GeneratedDocument>("/api/v1/documents/", {
        doc_type: filters.doc_type,
        status: filters.status,
        format: filters.format,
        search: filters.search,
        page_size: 50,
      }),
    refetchInterval: 30_000,
  });
}

/** Fetch a fresh signed download URL (expires fast) — call on the download click. */
export function fetchDocumentDownload(id: string) {
  return apiGet<DocumentDownload>(`/api/v1/documents/${id}/download-url/`);
}

/** Brand Kit is a per-org singleton (GET/PATCH). */
export const brandKit = {
  useRead: () =>
    useQuery({
      queryKey: ["settings", "brand-kit"],
      queryFn: () => apiGet<BrandKit>("/api/v1/documents/brand-kit/"),
    }),
  useUpdate: () => {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (body: Partial<BrandKit>) =>
        apiPatch<BrandKit>("/api/v1/documents/brand-kit/", body),
      onSuccess: (data) => qc.setQueryData(["settings", "brand-kit"], data),
    });
  },
};
