"use client";

import { SendHorizontal } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/field";
import { ApiError } from "@/lib/api/types";
import { useSendMessage } from "./queries";

export function Composer({
  conversationId,
  disabled,
}: {
  conversationId: string;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");
  const send = useSendMessage(conversationId);

  async function submit() {
    const body = text.trim();
    if (!body || send.isPending) return;
    setText("");
    try {
      await send.mutateAsync(body);
    } catch (err) {
      setText(body);
      toast.error(
        err instanceof ApiError ? err.message : "No se pudo enviar el mensaje",
      );
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  }

  if (disabled) {
    return (
      <div className="border-t border-border p-4 text-center text-sm text-muted">
        Esta conversación está cerrada. Reabrila para responder.
      </div>
    );
  }

  return (
    <div className="border-t border-border bg-bg-subtle/40 p-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Escribí un mensaje…"
          className="max-h-40 min-h-[44px] flex-1"
        />
        <Button
          size="icon"
          onClick={() => void submit()}
          loading={send.isPending}
          disabled={!text.trim()}
          aria-label="Enviar mensaje"
        >
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
      <p className="mx-auto mt-1.5 max-w-3xl text-[11px] text-muted">
        Enter para enviar · Shift+Enter nueva línea · el envío es simulado por
        ahora (no llega a WhatsApp real todavía).
      </p>
    </div>
  );
}
