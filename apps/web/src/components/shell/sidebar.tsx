"use client";

import { useAuthStore } from "@/lib/auth/store";
import { NAV_GROUPS } from "@/lib/nav";
import { Logo } from "./logo";
import { NavLink } from "./nav-link";
import { UserMenu } from "./user-menu";

export function Sidebar() {
  const permissions = useAuthStore((s) => s.permissions);
  const can = (p?: string) => !p || permissions.includes(p);

  return (
    <aside className="hidden shrink-0 flex-col border-r border-border bg-bg-subtle lg:flex lg:w-[260px]">
      <div className="flex h-16 items-center px-5">
        <Logo />
      </div>
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
        {NAV_GROUPS.map((group) => {
          const items = group.items.filter((i) => can(i.permission));
          if (!items.length) return null;
          return (
            <div key={group.label} className="space-y-1">
              <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-muted/70">
                {group.label}
              </p>
              {items.map((item) => (
                <NavLink key={item.href} {...item} />
              ))}
            </div>
          );
        })}
      </nav>
      <div className="border-t border-border p-3">
        <UserMenu />
      </div>
    </aside>
  );
}
