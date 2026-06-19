"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ApiError } from "@/lib/api/types";
import { useMe } from "@/lib/auth/session";
import { useAuthStore } from "@/lib/auth/store";
import { Logo } from "./logo";

function Splash() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg">
      <div className="animate-pulse-glow">
        <Logo />
      </div>
    </div>
  );
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);

  // Loads /me (and refreshes the cached permissions) when a token is present.
  const me = useMe(hydrated && !!accessToken);
  const authError =
    me.error instanceof ApiError &&
    (me.error.status === 401 || me.error.status === 403);

  useEffect(() => {
    if (hydrated && !accessToken) router.replace("/login");
  }, [hydrated, accessToken, router]);

  useEffect(() => {
    if (authError) {
      useAuthStore.getState().clear();
      queryClient.clear();
      router.replace("/login");
    }
  }, [authError, queryClient, router]);

  if (!hydrated || !accessToken || me.isPending || authError) return <Splash />;
  return <>{children}</>;
}
