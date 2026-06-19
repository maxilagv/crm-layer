"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGetList, apiPatch, apiPost } from "@/lib/api/client";
import type { BadgeTone } from "@/components/ui/badge";

/* ------------------------------------------------------------------- types */

/** Role accepted by the create endpoint (UserCreateSerializer.role choices). */
export type UserRole = "admin" | "operator" | "viewer";

/** Matches UserPublicSerializer exactly (snake_case, all read-only). */
export interface UserPublic {
  id: string;
  email: string;
  name: string;
  phone: string;
  timezone: string;
  locale: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrador",
  operator: "Operador",
  viewer: "Lector",
};

export const USER_ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "admin", label: USER_ROLE_LABELS.admin },
  { value: "operator", label: USER_ROLE_LABELS.operator },
  { value: "viewer", label: USER_ROLE_LABELS.viewer },
];

export function statusTone(active: boolean): BadgeTone {
  return active ? "success" : "muted";
}

export function statusLabel(active: boolean): string {
  return active ? "Activo" : "Inactivo";
}

/* ------------------------------------------------------------------- queries */

const usersKey = ["settings", "users"] as const;

export function useUsers() {
  return useQuery({
    queryKey: usersKey,
    queryFn: () =>
      apiGetList<UserPublic>("/api/v1/users/", { page_size: 100 }),
  });
}

/* ----------------------------------------------------------------- mutations */

export interface CreateUserInput {
  email: string;
  name: string;
  phone?: string;
  password: string;
  role: UserRole;
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateUserInput) =>
      apiPost<UserPublic>("/api/v1/users/", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: usersKey });
    },
  });
}

/** PATCH /users/<id>/ — only fields accepted by UserPatchSerializer. */
export interface UpdateUserInput {
  id: string;
  name?: string;
  phone?: string;
  timezone?: string;
  locale?: string;
  is_active?: boolean;
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: UpdateUserInput) =>
      apiPatch<UserPublic>(`/api/v1/users/${id}/`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: usersKey });
    },
  });
}
