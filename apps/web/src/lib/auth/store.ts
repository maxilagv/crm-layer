import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

export interface SessionUser {
  id: string;
  email: string;
  name: string | null;
  is_staff?: boolean;
  is_superuser?: boolean;
}

export interface SessionMembership {
  organization_id: string;
  organization_name: string;
  role: string;
  status: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  organizationId: string | null;
  organizationName: string | null;
  role: string | null;
  user: SessionUser | null;
  permissions: string[];
  memberships: SessionMembership[];
  hydrated: boolean;

  setTokens: (t: { access: string; refresh?: string | null }) => void;
  clearOrganization: () => void;
  setSession: (s: {
    user: SessionUser;
    organizationId: string | null;
    organizationName?: string | null;
    role?: string | null;
    permissions: string[];
    memberships: SessionMembership[];
  }) => void;
  setOrganization: (id: string, name?: string | null) => void;
  clear: () => void;
}

const noopStorage: StateStorage = {
  getItem: () => null,
  setItem: () => undefined,
  removeItem: () => undefined,
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      organizationId: null,
      organizationName: null,
      role: null,
      user: null,
      permissions: [],
      memberships: [],
      hydrated: false,

      setTokens: ({ access, refresh }) =>
        set((s) => ({
          accessToken: access,
          refreshToken: refresh ?? s.refreshToken,
        })),

      clearOrganization: () =>
        set({ organizationId: null, organizationName: null, role: null }),

      setSession: ({ user, organizationId, organizationName, role, permissions, memberships }) =>
        set(() => ({
          user,
          permissions,
          memberships,
          organizationId,
          organizationName: organizationName ?? null,
          role: role ?? null,
        })),

      setOrganization: (id, name) =>
        set({ organizationId: id, organizationName: name ?? null }),

      clear: () =>
        set({
          accessToken: null,
          refreshToken: null,
          organizationId: null,
          organizationName: null,
          role: null,
          user: null,
          permissions: [],
          memberships: [],
        }),
    }),
    {
      name: "ai-crm-auth",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : noopStorage,
      ),
      partialize: (s) => ({
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        organizationId: s.organizationId,
        organizationName: s.organizationName,
        role: s.role,
        user: s.user,
        permissions: s.permissions,
        memberships: s.memberships,
      }),
    },
  ),
);

// Mark hydration complete so the auth gate can wait for localStorage to load.
if (typeof window !== "undefined") {
  const markHydrated = () => useAuthStore.setState({ hydrated: true });
  useAuthStore.persist.onFinishHydration(markHydrated);
  if (useAuthStore.persist.hasHydrated()) markHydrated();
}

/** Read-only helpers for non-React modules (e.g. the HTTP client). */
export const authSnapshot = () => useAuthStore.getState();
export const hasPermission = (perm: string) =>
  useAuthStore.getState().permissions.includes(perm);
