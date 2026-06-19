"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGetArray, apiPost } from "@/lib/api/client";
import type { BadgeTone } from "@/components/ui/badge";

/* ------------------------------------------------------------------ types */

/** Mirrors APIKeySerializer (accounts/api/serializers.py). snake_case. */
export interface APIKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

/** POST response: APIKeyCreatedSerializer — same as APIKey plus the raw secret. */
export interface APIKeyCreated extends APIKey {
  key: string;
}

export interface CreateApiKeyInput {
  name: string;
  scopes?: string[];
  expires_at?: string | null;
}

/* -------------------------------------------------------------- derived state */

export type APIKeyState = "active" | "revoked" | "expired";

export function apiKeyState(k: APIKey): APIKeyState {
  if (k.revoked_at) return "revoked";
  if (k.expires_at && new Date(k.expires_at).getTime() <= Date.now()) {
    return "expired";
  }
  return "active";
}

export const API_KEY_STATE_LABELS: Record<APIKeyState, string> = {
  active: "Activa",
  revoked: "Revocada",
  expired: "Vencida",
};

export function apiKeyStateTone(s: APIKeyState): BadgeTone {
  if (s === "active") return "success";
  if (s === "expired") return "warning";
  return "muted";
}

/* ------------------------------------------------------------------ hooks */

const apiKeysKey = ["settings", "api-keys"] as const;

/** Non-paginated list (APIKeySerializer(many=True)). */
export function useApiKeys() {
  return useQuery({
    queryKey: apiKeysKey,
    queryFn: () => apiGetArray<APIKey>("/api/v1/api-keys/"),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateApiKeyInput) =>
      apiPost<APIKeyCreated>("/api/v1/api-keys/", {
        name: input.name,
        scopes: input.scopes ?? [],
        expires_at: input.expires_at ?? null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: apiKeysKey });
    },
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiDelete<{ status: string }>(`/api/v1/api-keys/${id}/`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: apiKeysKey });
    },
  });
}
