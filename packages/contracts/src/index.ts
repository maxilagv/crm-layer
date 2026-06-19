import { z } from "zod";

export const ContactKind = z.enum([
  "lead",
  "client",
  "provider",
  "internal",
  "unknown",
]);
export type ContactKind = z.infer<typeof ContactKind>;

export const LeadStatus = z.enum([
  "new",
  "contacted",
  "qualified",
  "proposal",
  "won",
  "lost",
  "nurture",
]);
export type LeadStatus = z.infer<typeof LeadStatus>;

export const ClientStatus = z.enum(["active", "paused", "at_risk", "churned"]);
export type ClientStatus = z.infer<typeof ClientStatus>;

export const ConversationChannel = z.enum(["whatsapp"]);
export type ConversationChannel = z.infer<typeof ConversationChannel>;

export const MessageDirection = z.enum(["inbound", "outbound"]);
export type MessageDirection = z.infer<typeof MessageDirection>;

export const MessageContentType = z.enum([
  "text",
  "audio",
  "image",
  "document",
  "interactive",
  "unknown",
]);
export type MessageContentType = z.infer<typeof MessageContentType>;

export const TicketPriority = z.enum(["low", "medium", "high", "urgent"]);
export type TicketPriority = z.infer<typeof TicketPriority>;

export const TaskStatus = z.enum(["pending", "done", "postponed", "cancelled"]);
export type TaskStatus = z.infer<typeof TaskStatus>;

export const ContactSchema = z.object({
  id: z.string().uuid(),
  kind: ContactKind,
  fullName: z.string().nullable(),
  phoneE164: z.string(),
  companyName: z.string().nullable(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});
export type Contact = z.infer<typeof ContactSchema>;

export const ConversationSummarySchema = z.object({
  id: z.string().uuid(),
  channel: ConversationChannel,
  contactId: z.string().uuid(),
  lastMessageAt: z.string().datetime().nullable(),
  humanHandoffRequired: z.boolean(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});
export type ConversationSummary = z.infer<typeof ConversationSummarySchema>;

export const LeadScoreSchema = z.object({
  id: z.string().uuid(),
  leadId: z.string().uuid(),
  score: z.number().int().min(0).max(100),
  band: z.enum(["cold", "warm", "good", "priority"]),
  explanation: z.string(),
  createdAt: z.string().datetime(),
});
export type LeadScore = z.infer<typeof LeadScoreSchema>;
