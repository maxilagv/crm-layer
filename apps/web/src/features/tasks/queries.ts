"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiGet, apiGetList, apiPost } from "@/lib/api/client";
import type { BadgeTone } from "@/components/ui/badge";

/* ----------------------------------------------------------------- enums */

export type TaskStatus =
  | "pending"
  | "in_progress"
  | "waiting"
  | "completed"
  | "cancelled"
  | "overdue"
  | "snoozed";

export type TaskPriority = "low" | "medium" | "high" | "urgent";

export type TaskSourceType =
  | "manual"
  | "conversation"
  | "lead"
  | "ticket"
  | "ai_extracted"
  | "automation"
  | "system";

export type TaskReminderChannel = "whatsapp" | "dashboard" | "email" | "system";

export type TaskReminderStatus =
  | "pending"
  | "queued"
  | "sent"
  | "acknowledged"
  | "snoozed"
  | "cancelled"
  | "failed"
  | "expired";

export type TaskAuthorType = "user" | "ai_agent" | "system" | "worker";

/* ----------------------------------------------------------------- types (snake_case, match serializers) */

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  source_type: TaskSourceType;
  source_id: string | null;
  contact_id: string | null;
  lead_id: string | null;
  client_id: string | null;
  ticket_id: string | null;
  conversation_id: string | null;
  assigned_to_id: string | null;
  due_at: string | null;
  completed_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TaskReminder {
  id: string;
  remind_at: string;
  channel: TaskReminderChannel;
  status: TaskReminderStatus;
  sent_at: string | null;
  acknowledged_at: string | null;
  snoozed_until: string | null;
  notification_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface TaskComment {
  id: string;
  author_type: TaskAuthorType;
  author_id: string | null;
  body: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface TaskStatusHistory {
  id: string;
  from_status: string;
  to_status: string;
  reason: string;
  changed_by_id: string | null;
  changed_by_type: TaskAuthorType;
  created_at: string;
}

export interface TaskSource {
  id: string;
  source_type: TaskSourceType;
  source_id: string | null;
  source_message_id: string | null;
  ai_run_id: string | null;
  normalized_title: string;
  created_at: string;
}

export interface TaskDetail extends Task {
  reminders: TaskReminder[];
  comments: TaskComment[];
  status_history: TaskStatusHistory[];
  sources: TaskSource[];
}

/* ----------------------------------------------------------------- label maps + tones */

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "Pendiente",
  in_progress: "En curso",
  waiting: "En espera",
  completed: "Completada",
  cancelled: "Cancelada",
  overdue: "Vencida",
  snoozed: "Pospuesta",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

export const TASK_SOURCE_LABELS: Record<TaskSourceType, string> = {
  manual: "Manual",
  conversation: "Conversación",
  lead: "Lead",
  ticket: "Ticket",
  ai_extracted: "Extraída por IA",
  automation: "Automatización",
  system: "Sistema",
};

export const TASK_REMINDER_CHANNEL_LABELS: Record<TaskReminderChannel, string> = {
  whatsapp: "WhatsApp",
  dashboard: "Panel",
  email: "Email",
  system: "Sistema",
};

export const TASK_REMINDER_STATUS_LABELS: Record<TaskReminderStatus, string> = {
  pending: "Pendiente",
  queued: "En cola",
  sent: "Enviado",
  acknowledged: "Confirmado",
  snoozed: "Pospuesto",
  cancelled: "Cancelado",
  failed: "Falló",
  expired: "Expirado",
};

export function statusTone(s: TaskStatus): BadgeTone {
  if (s === "completed") return "success";
  if (s === "overdue") return "danger";
  if (s === "in_progress") return "info";
  if (s === "pending") return "primary";
  if (s === "waiting" || s === "snoozed") return "warning";
  return "muted"; // cancelled
}

export function priorityTone(p: TaskPriority): BadgeTone {
  if (p === "urgent") return "danger";
  if (p === "high") return "warning";
  if (p === "medium") return "info";
  return "muted"; // low
}

export function reminderStatusTone(s: TaskReminderStatus): BadgeTone {
  if (s === "sent" || s === "acknowledged") return "success";
  if (s === "failed" || s === "expired") return "danger";
  if (s === "cancelled") return "muted";
  if (s === "snoozed") return "warning";
  return "info"; // pending | queued
}

/** Active (non-terminal) statuses can be completed / snoozed / cancelled. */
export function isTaskActive(status: TaskStatus): boolean {
  return status !== "completed" && status !== "cancelled";
}

/* ----------------------------------------------------------------- query keys */

export const taskKeys = {
  all: ["tasks"] as const,
  list: (filters: TaskFilters) => ["tasks", "list", filters] as const,
  detail: (id: string) => ["tasks", "detail", id] as const,
};

/* ----------------------------------------------------------------- filters */

export interface TaskFilters {
  status?: string;
  priority?: string;
  assigned_to_id?: string;
  due_before?: string;
  due_after?: string;
  search?: string;
  ordering?: string;
}

/* ----------------------------------------------------------------- queries */

export function useTasks(filters: TaskFilters) {
  return useQuery({
    queryKey: taskKeys.list(filters),
    queryFn: () =>
      apiGetList<Task>("/api/v1/tasks/", {
        status: filters.status,
        priority: filters.priority,
        assigned_to_id: filters.assigned_to_id,
        due_before: filters.due_before,
        due_after: filters.due_after,
        search: filters.search,
        ordering: filters.ordering ?? "-updated_at",
        page_size: 50,
      }),
    refetchInterval: 30_000,
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: () => apiGet<TaskDetail>(`/api/v1/tasks/${id}/`),
    enabled: !!id,
  });
}

/* ----------------------------------------------------------------- mutations */

export interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: TaskPriority;
  due_at?: string | null;
  assigned_to_id?: string | null;
  contact_id?: string | null;
  lead_id?: string | null;
  client_id?: string | null;
  ticket_id?: string | null;
  conversation_id?: string | null;
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateTaskInput) =>
      apiPost<TaskDetail>("/api/v1/tasks/", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: taskKeys.all });
    },
  });
}

function patchDetailCache(qc: ReturnType<typeof useQueryClient>, task: TaskDetail) {
  qc.setQueryData(taskKeys.detail(task.id), task);
  void qc.invalidateQueries({ queryKey: taskKeys.all });
}

export function useCompleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiPost<TaskDetail>(`/api/v1/tasks/${id}/complete/`),
    onSuccess: (data) => patchDetailCache(qc, data),
  });
}

export function useCancelTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiPost<TaskDetail>(`/api/v1/tasks/${id}/cancel/`),
    onSuccess: (data) => patchDetailCache(qc, data),
  });
}

export function useSnoozeTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, snooze_until }: { id: string; snooze_until: string }) =>
      apiPost<TaskDetail>(`/api/v1/tasks/${id}/snooze/`, { snooze_until }),
    onSuccess: (data) => patchDetailCache(qc, data),
  });
}

export interface AddReminderInput {
  id: string;
  remind_at: string;
  channel?: TaskReminderChannel;
}

export function useAddReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, remind_at, channel }: AddReminderInput) =>
      apiPost<TaskReminder>(`/api/v1/tasks/${id}/reminders/`, {
        remind_at,
        channel: channel ?? "dashboard",
      }),
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: taskKeys.detail(variables.id) });
    },
  });
}

/* ----------------------------------------------------------------- org members (for assignee filter / selector) */

export interface OrgUser {
  id: string;
  name: string;
  email: string;
}

/**
 * Org members, used to label/filter by assignee. The `/users/` endpoint
 * requires SETTINGS_MANAGE, which a task-only operator may lack, so this query
 * fails soft: callers must tolerate `undefined` (we hide the selector then).
 */
export function useOrgUsers() {
  return useQuery({
    queryKey: ["tasks", "org-users"],
    queryFn: () =>
      apiGetList<OrgUser>("/api/v1/users/", { page_size: 100 }).then(
        (res) => res.items,
      ),
    retry: false,
    staleTime: 5 * 60_000,
  });
}
