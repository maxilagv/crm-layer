"use client";

import { Bot, Hand } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar } from "@/components/ui/avatar";
import {
  CONVERSATION_STATUS_LABELS,
  type ConversationInbox,
} from "@/lib/api/conversations";
import { cn } from "@/lib/cn";
import { relativeTime } from "@/lib/format";

export function ConversationListItem({ c }: { c: ConversationInbox }) {
  const pathname = usePathname();
  const active = pathname === `/inbox/${c.id}`;
  const name = c.contact.display_name || c.contact.primary_phone || "Sin nombre";
  const preview = c.last_message?.body_preview || "Sin mensajes todavía";

  return (
    <Link
      href={`/inbox/${c.id}`}
      className={cn(
        "flex cursor-pointer items-start gap-3 border-b border-border/60 px-3 py-3 transition-colors",
        active ? "bg-primary/10" : "hover:bg-card-hover",
      )}
    >
      <Avatar name={name} seed={c.contact.id} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {name}
          </span>
          <span className="shrink-0 text-[11px] text-muted">
            {relativeTime(c.last_message_at)}
          </span>
        </div>
        <p className="mt-0.5 truncate text-[13px] text-muted">{preview}</p>
        <div className="mt-1.5 flex items-center gap-1.5">
          {c.ai_enabled ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/12 px-1.5 py-0.5 text-[10px] font-medium text-primary">
              <Bot className="h-3 w-3" />
              IA
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-card-hover px-1.5 py-0.5 text-[10px] font-medium text-muted">
              <Hand className="h-3 w-3" />
              Manual
            </span>
          )}
          {c.status !== "open" && (
            <span className="rounded-full bg-card-hover px-1.5 py-0.5 text-[10px] text-muted">
              {CONVERSATION_STATUS_LABELS[c.status]}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
