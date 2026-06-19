"use client";

import { Fragment, useEffect, useRef } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { dayLabel } from "@/lib/format";
import { MessageBubble } from "./message-bubble";
import { useMessages } from "./queries";

function DayDivider({ label }: { label: string }) {
  return (
    <div className="my-3 flex items-center justify-center">
      <span className="rounded-full bg-card px-3 py-1 text-[11px] font-medium capitalize text-muted ring-1 ring-border">
        {label}
      </span>
    </div>
  );
}

export function MessageThread({ conversationId }: { conversationId: string }) {
  const { data, isLoading } = useMessages(conversationId);
  const endRef = useRef<HTMLDivElement>(null);

  const messages = (data ?? [])
    .slice()
    .sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "auto" });
  }, [messages.length, conversationId]);

  if (isLoading) {
    return (
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className={i % 2 ? "flex justify-end" : "flex justify-start"}
          >
            <Skeleton className="h-12 w-52 rounded-2xl" />
          </div>
        ))}
      </div>
    );
  }

  let lastDay = "";
  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-1.5">
        {messages.map((m) => {
          const day = dayLabel(m.created_at);
          const showDay = day !== lastDay;
          lastDay = day;
          return (
            <Fragment key={m.id}>
              {showDay && <DayDivider label={day} />}
              <MessageBubble m={m} />
            </Fragment>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
