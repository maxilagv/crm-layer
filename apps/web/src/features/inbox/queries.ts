"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiGetList, apiPost } from "@/lib/api/client";
import type {
  ConversationDetail,
  ConversationInbox,
  Message,
} from "@/lib/api/conversations";

export interface ConversationFilters {
  status?: string;
  mode?: string;
  search?: string;
  ai_enabled?: boolean;
  assigned_user_id?: string;
}

export function useConversations(filters: ConversationFilters) {
  return useQuery({
    queryKey: ["conversations", filters],
    queryFn: () =>
      apiGetList<ConversationInbox>("/api/v1/conversations/", {
        status: filters.status,
        mode: filters.mode,
        search: filters.search,
        ai_enabled: filters.ai_enabled,
        assigned_user_id: filters.assigned_user_id,
        page_size: 50,
      }),
    refetchInterval: 20_000,
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: () => apiGet<ConversationDetail>(`/api/v1/conversations/${id}/`),
    enabled: !!id,
  });
}

export function useMessages(id: string) {
  return useQuery({
    queryKey: ["messages", id],
    queryFn: () =>
      apiGet<Message[]>(`/api/v1/conversations/${id}/messages/`, {
        page_size: 200,
      }),
    enabled: !!id,
    refetchInterval: 15_000,
  });
}

export function useSendMessage(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) =>
      apiPost<Message>(`/api/v1/conversations/${id}/send-message/`, {
        body,
        message_type: "text",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["messages", id] });
      void qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export type ConversationAction =
  | "takeover"
  | "pause-ai"
  | "resume-ai"
  | "close"
  | "reopen";

export function useConversationAction(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: ConversationAction) =>
      apiPost<ConversationDetail>(
        `/api/v1/conversations/${id}/${action}/`,
        action === "takeover" ? {} : undefined,
      ),
    onSuccess: (data) => {
      qc.setQueryData(["conversation", id], data);
      void qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
