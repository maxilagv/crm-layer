import { format, formatDistanceToNow, isToday, isYesterday } from "date-fns";
import { es } from "date-fns/locale";

export function relativeTime(iso?: string | null): string {
  if (!iso) return "";
  return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: es });
}

export function shortTime(iso?: string | null): string {
  if (!iso) return "";
  return format(new Date(iso), "HH:mm");
}

export function shortDateTime(iso?: string | null): string {
  if (!iso) return "";
  return format(new Date(iso), "d MMM, HH:mm", { locale: es });
}

export function dayLabel(iso: string): string {
  const d = new Date(iso);
  if (isToday(d)) return "Hoy";
  if (isYesterday(d)) return "Ayer";
  return format(d, "EEEE d 'de' MMMM", { locale: es });
}

export function initialsName(name?: string | null, fallback = "?"): string {
  return name?.trim() || fallback;
}
