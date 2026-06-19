import { Sparkles } from "lucide-react";
import { cn } from "@/lib/cn";

export function Logo({
  collapsed = false,
  className,
}: {
  collapsed?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-primary-gradient shadow-glow-sm">
        <Sparkles className="h-4 w-4 text-white" />
      </span>
      {!collapsed && (
        <span className="font-display text-[15px] font-semibold tracking-tight text-foreground">
          AI CRM
        </span>
      )}
    </div>
  );
}
