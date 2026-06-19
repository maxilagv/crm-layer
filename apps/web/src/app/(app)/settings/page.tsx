import {
  Bell,
  Building2,
  Headphones,
  KeyRound,
  MessageCircle,
  Palette,
  Sparkles,
  Store,
  TrendingUp,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { PageContainer } from "@/components/shell/page-container";
import { PageHeader } from "@/components/ui/page-header";

interface Section {
  href: string;
  title: string;
  description: string;
  icon: LucideIcon;
}

const SECTIONS: Section[] = [
  {
    href: "/settings/organization",
    title: "Organización",
    description: "Nombre, zona horaria e idioma por defecto.",
    icon: Building2,
  },
  {
    href: "/settings/business",
    title: "Perfil de negocio",
    description: "Qué hacés, tono de voz, servicios y enlaces.",
    icon: Store,
  },
  {
    href: "/settings/ai",
    title: "Inteligencia artificial",
    description: "Proveedor, modelos, API key y auto-respuesta.",
    icon: Sparkles,
  },
  {
    href: "/settings/whatsapp",
    title: "WhatsApp",
    description: "Conexión del número, plantillas y auto-reply.",
    icon: MessageCircle,
  },
  {
    href: "/settings/brand-kit",
    title: "Kit de marca",
    description: "Logo, colores, moneda, impuestos y datos de tus documentos.",
    icon: Palette,
  },
  {
    href: "/settings/sales",
    title: "Política de ventas",
    description: "Objetivo, precios, objeciones y claims prohibidos.",
    icon: TrendingUp,
  },
  {
    href: "/settings/support",
    title: "Política de soporte",
    description: "Horarios, acciones permitidas y palabras urgentes.",
    icon: Headphones,
  },
  {
    href: "/settings/notifications",
    title: "Notificaciones",
    description: "Canales, alertas y horarios de silencio.",
    icon: Bell,
  },
  {
    href: "/settings/users",
    title: "Usuarios",
    description: "Miembros del equipo y sus roles.",
    icon: Users,
  },
  {
    href: "/settings/api-keys",
    title: "API Keys",
    description: "Claves para acceso programático al backend.",
    icon: KeyRound,
  },
];

export default function SettingsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Configuración"
        description="Personalizá el CRM, conectá WhatsApp y la IA, y ajustá las políticas del agente."
      />
      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          return (
            <Link
              key={s.href}
              href={s.href}
              className="group flex cursor-pointer items-start gap-4 rounded-xl border border-border bg-card p-4 shadow-card transition-[transform,background-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:bg-card-hover hover:shadow-soft"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary transition-colors group-hover:bg-primary/20">
                <Icon className="h-5 w-5" />
              </span>
              <span className="min-w-0">
                <span className="block font-medium text-foreground">
                  {s.title}
                </span>
                <span className="mt-0.5 block text-sm text-muted">
                  {s.description}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </PageContainer>
  );
}
