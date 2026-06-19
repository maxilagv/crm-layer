"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Hand,
  MoreVertical,
  Pause,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  CONVERSATION_MODE_LABELS,
  CONVERSATION_STATUS_LABELS,
  type ConversationDetail,
  modeTone,
  statusTone,
} from "@/lib/api/conversations";
import { useConversationAction } from "./queries";

function MenuItem({
  icon: Icon,
  onClick,
  danger,
  children,
}: {
  icon: typeof Hand;
  onClick: () => void;
  danger?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
        danger
          ? "text-danger hover:bg-danger/10"
          : "text-muted hover:bg-card-hover hover:text-foreground"
      }`}
    >
      <Icon className="h-4 w-4" />
      {children}
    </button>
  );
}

export function ConversationHeader({
  conversation,
}: {
  conversation: ConversationDetail;
}) {
  const action = useConversationAction(conversation.id);
  const [menu, setMenu] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const name =
    conversation.contact.display_name ||
    conversation.contact.primary_phone ||
    "Sin nombre";
  const closed =
    conversation.status === "closed" || conversation.status === "archived";

  useEffect(() => {
    if (!menu) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [menu]);

  const run = (a: Parameters<typeof action.mutate>[0]) => {
    action.mutate(a);
    setMenu(false);
  };

  return (
    <header className="flex items-center gap-3 border-b border-border px-3 py-2.5">
      <Link
        href="/inbox"
        aria-label="Volver a la bandeja"
        className="inline-flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg text-muted transition-colors hover:bg-card-hover hover:text-foreground md:hidden"
      >
        <ArrowLeft className="h-5 w-5" />
      </Link>
      <Avatar name={name} seed={conversation.contact.id} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold text-foreground">
            {name}
          </span>
          <Badge tone={statusTone(conversation.status)}>
            {CONVERSATION_STATUS_LABELS[conversation.status]}
          </Badge>
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted">
          {conversation.contact.primary_phone && (
            <span className="truncate">{conversation.contact.primary_phone}</span>
          )}
          <Badge tone={modeTone(conversation.mode)}>
            {CONVERSATION_MODE_LABELS[conversation.mode]}
          </Badge>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="hidden items-center gap-2 sm:flex">
          <span className="text-xs text-muted">IA</span>
          <Switch
            checked={conversation.ai_enabled}
            disabled={action.isPending || closed}
            onCheckedChange={(v) => action.mutate(v ? "resume-ai" : "pause-ai")}
            aria-label="Activar o desactivar IA"
          />
        </label>

        <div ref={ref} className="relative">
          <button
            type="button"
            onClick={() => setMenu((o) => !o)}
            aria-label="Acciones de la conversación"
            className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-muted outline-none transition-colors hover:bg-card-hover hover:text-foreground focus-visible:shadow-focus"
          >
            <MoreVertical className="h-5 w-5" />
          </button>
          <AnimatePresence>
            {menu && (
              <motion.div
                initial={{ opacity: 0, y: 6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.98 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full z-30 mt-1 w-56 overflow-hidden rounded-xl border border-border bg-popover p-1 shadow-soft"
              >
                <MenuItem icon={Hand} onClick={() => run("takeover")}>
                  Tomar conversación
                </MenuItem>
                <div className="sm:hidden">
                  {conversation.ai_enabled ? (
                    <MenuItem icon={Pause} onClick={() => run("pause-ai")}>
                      Pausar IA
                    </MenuItem>
                  ) : (
                    <MenuItem icon={Bot} onClick={() => run("resume-ai")}>
                      Reanudar IA
                    </MenuItem>
                  )}
                </div>
                <div className="my-1 h-px bg-border" />
                {closed ? (
                  <MenuItem icon={RotateCcw} onClick={() => run("reopen")}>
                    Reabrir conversación
                  </MenuItem>
                ) : (
                  <MenuItem
                    icon={CheckCircle2}
                    danger
                    onClick={() => run("close")}
                  >
                    Cerrar conversación
                  </MenuItem>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
