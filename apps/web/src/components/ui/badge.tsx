import * as React from "react";
import { cn } from "@/lib/cn";

export type BadgeTone =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "muted";

const tones: Record<BadgeTone, string> = {
  default: "bg-card-hover text-foreground ring-border",
  primary: "bg-primary/12 text-primary ring-primary/20",
  success: "bg-success/12 text-success ring-success/20",
  warning: "bg-warning/12 text-warning ring-warning/20",
  danger: "bg-danger/12 text-danger ring-danger/20",
  info: "bg-info/12 text-info ring-info/20",
  muted: "bg-card-hover text-muted ring-border",
};

const dotTones: Record<BadgeTone, string> = {
  default: "bg-muted",
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
  muted: "bg-muted",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  dot?: boolean;
}

export function Badge({
  className,
  tone = "default",
  dot = false,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        tones[tone],
        className,
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn("h-1.5 w-1.5 rounded-full", dotTones[tone])}
          aria-hidden
        />
      )}
      {children}
    </span>
  );
}
