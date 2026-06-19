"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api/client";
import type { LoginResponse, MeResponse } from "@/lib/api/auth";
import { useAuthStore } from "./store";

function applyMe(me: MeResponse) {
  useAuthStore.getState().setSession({
    user: {
      id: me.user.id,
      email: me.user.email,
      name: me.user.name,
      is_staff: me.user.is_staff,
      is_superuser: me.user.is_superuser,
    },
    organizationId: me.organization?.id ?? null,
    organizationName: me.organization?.name ?? null,
    role: me.membership?.role ?? null,
    permissions: me.permissions ?? [],
    memberships: me.memberships ?? [],
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      const tokens = await apiPost<LoginResponse>(
        "/api/v1/auth/login/",
        creds,
        { auth: false },
      );
      useAuthStore.getState().clear();
      useAuthStore.getState().setTokens({
        access: tokens.access,
        refresh: tokens.refresh,
      });
      const me = await apiGet<MeResponse>("/api/v1/auth/me/");
      applyMe(me);
      return me;
    },
    onSuccess: () => {
      void qc.invalidateQueries();
    },
  });
}

export function useMe(enabled = true) {
  const accessToken = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ["auth", "me"],
    enabled: enabled && !!accessToken,
    staleTime: 60_000,
    retry: false,
    queryFn: async () => {
      const me = await apiGet<MeResponse>("/api/v1/auth/me/");
      applyMe(me);
      return me;
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const refresh = useAuthStore.getState().refreshToken;
      try {
        if (refresh) await apiPost("/api/v1/auth/logout/", { refresh });
      } catch {
        // best-effort; clear locally regardless
      }
    },
    onSettled: () => {
      useAuthStore.getState().clear();
      qc.clear();
    },
  });
}

export function usePermissions() {
  return useAuthStore((s) => s.permissions);
}

export function useHasPermission(perm: string) {
  return useAuthStore((s) => s.permissions.includes(perm));
}

export function useCurrentUser() {
  return useAuthStore((s) => s.user);
}
