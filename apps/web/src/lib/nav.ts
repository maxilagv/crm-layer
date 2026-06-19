import {
  BarChart3,
  CheckSquare,
  Contact,
  FileText,
  Headphones,
  Inbox,
  ListChecks,
  Radar,
  Settings,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** PermissionCode required to see the item (owner has all). */
  permission?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Operación",
    items: [
      { label: "Bandeja", href: "/inbox", icon: Inbox, permission: "conversations.view" },
      { label: "Contactos", href: "/contacts", icon: Contact, permission: "contacts.view" },
    ],
  },
  {
    label: "CRM",
    items: [
      { label: "Leads", href: "/leads", icon: Target, permission: "leads.view" },
      { label: "Ventas", href: "/sales", icon: TrendingUp, permission: "leads.view" },
      { label: "Clientes", href: "/clients", icon: Users, permission: "clients.view" },
      { label: "Soporte", href: "/support", icon: Headphones, permission: "tickets.manage" },
      { label: "Tareas", href: "/tasks", icon: CheckSquare, permission: "tasks.manage" },
      { label: "Documentos", href: "/documents", icon: FileText, permission: "contacts.view" },
    ],
  },
  {
    label: "Inteligencia",
    items: [
      { label: "IA", href: "/ai", icon: Sparkles, permission: "prompts.manage" },
      { label: "Analítica", href: "/analytics", icon: BarChart3, permission: "audit.view" },
    ],
  },
  {
    label: "Cazador",
    items: [
      {
        label: "Campañas",
        href: "/cazador/campaigns",
        icon: Radar,
        permission: "prospecting.view",
      },
      {
        label: "Prospectos",
        href: "/cazador/prospects",
        icon: ListChecks,
        permission: "prospecting.view",
      },
    ],
  },
  {
    label: "Sistema",
    items: [
      { label: "Configuración", href: "/settings", icon: Settings, permission: "settings.manage" },
    ],
  },
];

/** Flat list, handy for lookups (e.g. page title from pathname). */
export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/** Primary items shown in the mobile bottom bar (rest live behind "Más"). */
export const MOBILE_PRIMARY_HREFS = ["/inbox", "/clients", "/support", "/tasks"];

export function navItemForPath(pathname: string): NavItem | undefined {
  return NAV_ITEMS.filter((item) => pathname.startsWith(item.href)).sort(
    (a, b) => b.href.length - a.href.length,
  )[0];
}
