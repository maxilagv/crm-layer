"use client";

import { MoreHorizontal } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sheet } from "@/components/ui/sheet";
import { useAuthStore } from "@/lib/auth/store";
import { MOBILE_PRIMARY_HREFS, NAV_GROUPS, NAV_ITEMS, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/cn";
import { Logo } from "./logo";
import { NavLink } from "./nav-link";
import { UserMenu } from "./user-menu";

export function MobileNav({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (value: boolean) => void;
}) {
  const pathname = usePathname();
  const permissions = useAuthStore((s) => s.permissions);
  const can = (p?: string) => !p || permissions.includes(p);

  const primary = MOBILE_PRIMARY_HREFS.map((href) =>
    NAV_ITEMS.find((item) => item.href === href),
  ).filter((item): item is NavItem => !!item && can(item.permission));

  return (
    <>
      <nav className="glass fixed inset-x-0 bottom-0 z-30 flex h-16 items-stretch border-t border-border lg:hidden">
        {primary.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 cursor-pointer flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors",
                active ? "text-primary" : "text-muted",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => onOpenChange(true)}
          className="flex flex-1 cursor-pointer flex-col items-center justify-center gap-1 text-[11px] font-medium text-muted"
        >
          <MoreHorizontal className="h-5 w-5" />
          Más
        </button>
      </nav>

      <Sheet open={open} onClose={() => onOpenChange(false)} side="left" label="Menú">
        <div className="flex h-full flex-col">
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
                    <NavLink
                      key={item.href}
                      {...item}
                      onNavigate={() => onOpenChange(false)}
                    />
                  ))}
                </div>
              );
            })}
          </nav>
          <div className="border-t border-border p-3">
            <UserMenu onNavigate={() => onOpenChange(false)} />
          </div>
        </div>
      </Sheet>
    </>
  );
}
