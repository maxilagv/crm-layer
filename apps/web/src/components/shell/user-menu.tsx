"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronsUpDown, LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { useLogout } from "@/lib/auth/session";
import { useAuthStore } from "@/lib/auth/store";

export function UserMenu({ onNavigate }: { onNavigate?: () => void }) {
  const user = useAuthStore((s) => s.user);
  const orgName = useAuthStore((s) => s.organizationName);
  const role = useAuthStore((s) => s.role);
  const logout = useLogout();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const name = user?.name || user?.email || "Usuario";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full cursor-pointer items-center gap-3 rounded-lg p-2 text-left outline-none transition-colors hover:bg-card-hover focus-visible:shadow-focus"
      >
        <Avatar name={name} seed={user?.id} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-foreground">
            {name}
          </span>
          <span className="block truncate text-xs text-muted">
            {orgName ?? user?.email}
          </span>
        </span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-0 z-30 mb-2 w-full min-w-[220px] overflow-hidden rounded-xl border border-border bg-popover p-1 shadow-soft"
          >
            <div className="px-3 py-2">
              <p className="truncate text-sm font-medium text-foreground">
                {name}
              </p>
              <p className="truncate text-xs text-muted">{user?.email}</p>
              {role && (
                <p className="mt-1 text-[11px] uppercase tracking-wide text-primary">
                  {role}
                </p>
              )}
            </div>
            <div className="my-1 h-px bg-border" />
            <Link
              href="/settings"
              onClick={() => {
                setOpen(false);
                onNavigate?.();
              }}
              className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-card-hover hover:text-foreground"
            >
              <Settings className="h-4 w-4" />
              Configuración
            </Link>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                logout.mutate();
              }}
              className="flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-danger transition-colors hover:bg-danger/10"
            >
              <LogOut className="h-4 w-4" />
              Cerrar sesión
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
