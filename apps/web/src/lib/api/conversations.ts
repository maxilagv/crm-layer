import type { BadgeTone } from "@/components/ui/badge";

export type ConversationStatus = "open" | "pending" | "closed" | "archived";
export type ConversationMode =
  | "sales_ai"
  | "support_ai"
  | "internal_assistant"
  | "manual"
  | "paused"
  | "blocked";
export type MessageDirection = "inbound" | "outbound" | "internal" | "system";
export type MessageType =
  | "text"
  | "audio"
  | "image"
  | "document"
  | "video"
  | "sticker"
  | "location"
  | "contact_card"
  | "system";
export type MessageStatus =
  | "received"
  | "processed"
  | "queued"
  | "sent"
  | "delivered"
  | "read"
  | "failed"
  | "ignored";

export interface AssignedUser {
  id: string;
  name: string;
}

export interface ContactSummary {
  id: string;
  display_name: string | null;
  type: string;
  status: string;
  primary_phone: string | null;
}

export interface LastMessage {
  id: string;
  direction: MessageDirection | null;
  message_type: MessageType | null;
  body_preview: string;
  status: MessageStatus | null;
  created_at: string | null;
}

export interface ConversationInbox {
  id: string;
  channel: string;
  status: ConversationStatus;
  mode: ConversationMode;
  ai_enabled: boolean;
  assigned_user: AssignedUser | null;
  contact: ContactSummary;
  last_message: LastMessage | null;
  last_message_at: string | null;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  summary: string | null;
}

export interface ConversationDetail {
  id: string;
  channel: string;
  status: ConversationStatus;
  mode: ConversationMode;
  ai_enabled: boolean;
  assigned_user: AssignedUser | null;
  contact: ContactSummary;
  last_message_at: string | null;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  summary: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MessageAttachment {
  id: string;
  media_asset_id: string | null;
  external_media_id: string | null;
  mime_type: string | null;
  file_name: string | null;
  size_bytes: number | null;
}

export interface Message {
  id: string;
  direction: MessageDirection;
  message_type: MessageType;
  body: string | null;
  normalized_text: string | null;
  status: MessageStatus;
  external_message_id: string | null;
  external_timestamp: string | null;
  attachments: MessageAttachment[];
  created_at: string;
}

export const CONVERSATION_STATUS_LABELS: Record<ConversationStatus, string> = {
  open: "Abierta",
  pending: "Pendiente",
  closed: "Cerrada",
  archived: "Archivada",
};

export const CONVERSATION_MODE_LABELS: Record<ConversationMode, string> = {
  sales_ai: "Ventas IA",
  support_ai: "Soporte IA",
  internal_assistant: "Asistente",
  manual: "Manual",
  paused: "Pausada",
  blocked: "Bloqueada",
};

export const MESSAGE_TYPE_LABELS: Record<MessageType, string> = {
  text: "Texto",
  audio: "Audio",
  image: "Imagen",
  document: "Documento",
  video: "Video",
  sticker: "Sticker",
  location: "Ubicación",
  contact_card: "Contacto",
  system: "Sistema",
};

export function statusTone(s: ConversationStatus): BadgeTone {
  if (s === "open") return "success";
  if (s === "pending") return "warning";
  return "muted";
}

export function modeTone(m: ConversationMode): BadgeTone {
  if (m === "manual") return "info";
  if (m === "paused" || m === "blocked") return "muted";
  return "primary";
}
