"use client";

import { useParams } from "next/navigation";
import { ConversationView } from "@/features/inbox/conversation-view";

export default function ConversationPage() {
  const params = useParams();
  const id = String(params.conversationId);
  return <ConversationView conversationId={id} />;
}
