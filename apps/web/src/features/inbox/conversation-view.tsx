"use client";

import { MessageSquare } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Composer } from "./composer";
import { ConversationHeader } from "./conversation-header";
import { MessageThread } from "./message-thread";
import { useConversation } from "./queries";

export function ConversationView({
  conversationId,
}: {
  conversationId: string;
}) {
  const { data, isLoading, isError } = useConversation(conversationId);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner className="h-6 w-6 text-primary" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState
          icon={MessageSquare}
          title="Conversación no encontrada"
          description="Puede que se haya archivado o no exista en esta organización."
        />
      </div>
    );
  }

  const closed = data.status === "closed" || data.status === "archived";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ConversationHeader conversation={data} />
      <MessageThread conversationId={conversationId} />
      <Composer conversationId={conversationId} disabled={closed} />
    </div>
  );
}
