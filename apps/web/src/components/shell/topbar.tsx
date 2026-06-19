"use client";

import { Bell, Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { navItemForPath } from "@/lib/nav";

export function Topbar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const pathname = usePathname();
  const current = navItemForPath(pathname);
  const title = current?.label ?? "AI CRM";

  return (
    <header className="glass sticky top-0 z-20 flex h-16 shrink-0 items-center gap-3 border-b border-border px-4 sm:px-6">
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Abrir menú"
        className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-muted outline-none transition-colors hover:bg-card-hover hover:text-foreground focus-visible:shadow-focus lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>
      <h1 className="font-display text-base font-semibold tracking-tight text-foreground">
        {title}
      </h1>
      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <Link
          href="/notifications"
          aria-label="Notificaciones"
          className="relative inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-muted outline-none transition-colors hover:bg-card-hover hover:text-foreground focus-visible:shadow-focus"
        >
          <Bell className="h-[18px] w-[18px]" />
        </Link>
      </div>
    </header>
  );
}
