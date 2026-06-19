"use client";

import {
  AlarmClockPlus,
  Ban,
  CheckCircle2,
  Clock,
  History,
  MessageSquare,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/types";
import { shortDateTime } from "@/lib/format";
import {
  TASK_PRIORITY_LABELS,
  TASK_REMINDER_CHANNEL_LABELS,
  TASK_REMINDER_STATUS_LABELS,
  TASK_SOURCE_LABELS,
  TASK_STATUS_LABELS,
  isTaskActive,
  priorityTone,
  reminderStatusTone,
  statusTone,
  useAddReminder,
  useCancelTask,
  useCompleteTask,
  useOrgUsers,
  useTask,
  type TaskReminderChannel,
} from "./queries";

const REMINDER_CHANNELS: TaskReminderChannel[] = [
  "dashboard",
  "whatsapp",
  "email",
  "system",
];

function SectionTitle({
  icon: Icon,
  children,
}: {
  icon: typeof Clock;
  children: React.ReactNode;
}) {
  return (
    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
      <Icon className="h-3.5 w-3.5" />
      {children}
    </p>
  );
}

export function TaskDetailModal({
  taskId,
  onClose,
  onSnooze,
}: {
  taskId: string | null;
  onClose: () => void;
  /** Opens the shared snooze modal for the current task. */
  onSnooze: (id: string) => void;
}) {
  const open = !!taskId;
  const { data: task, isLoading, isError } = useTask(taskId ?? "");
  const { data: users } = useOrgUsers();
  const complete = useCompleteTask();
  const cancel = useCancelTask();
  const addReminder = useAddReminder();

  const [remindAt, setRemindAt] = useState("");
  const [channel, setChannel] = useState<TaskReminderChannel>("dashboard");

  const userName = (id: string | null): string | null => {
    if (!id) return null;
    const u = users?.find((x) => x.id === id);
    return u ? u.name || u.email : null;
  };

  async function onComplete() {
    if (!task) return;
    try {
      await complete.mutateAsync(task.id);
      toast.success("Tarea completada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo completar",
      );
    }
  }

  async function onCancel() {
    if (!task) return;
    try {
      await cancel.mutateAsync(task.id);
      toast.success("Tarea cancelada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo cancelar",
      );
    }
  }

  async function onAddReminder(e: React.FormEvent) {
    e.preventDefault();
    if (!task || !remindAt) return;
    try {
      await addReminder.mutateAsync({
        id: task.id,
        remind_at: new Date(remindAt).toISOString(),
        channel,
      });
      toast.success("Recordatorio agregado");
      setRemindAt("");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo agregar el recordatorio",
      );
    }
  }

  const active = task ? isTaskActive(task.status) : false;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={task?.title ?? "Tarea"}
      className="sm:max-w-2xl"
      footer={
        task && active ? (
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
              loading={cancel.isPending}
              leftIcon={<Ban className="h-4 w-4" />}
            >
              Cancelar tarea
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => onSnooze(task.id)}
              leftIcon={<Clock className="h-4 w-4" />}
            >
              Posponer
            </Button>
            <Button
              type="button"
              onClick={onComplete}
              loading={complete.isPending}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
            >
              Completar
            </Button>
          </>
        ) : (
          <Button type="button" variant="secondary" onClick={onClose}>
            Cerrar
          </Button>
        )
      }
    >
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : isError || !task ? (
        <p className="py-6 text-center text-sm text-muted">
          No se pudo cargar la tarea. Probá de nuevo.
        </p>
      ) : (
        <div className="space-y-5">
          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone(task.status)} dot>
              {TASK_STATUS_LABELS[task.status]}
            </Badge>
            <Badge tone={priorityTone(task.priority)}>
              {TASK_PRIORITY_LABELS[task.priority]}
            </Badge>
            <Badge tone="muted">{TASK_SOURCE_LABELS[task.source_type]}</Badge>
          </div>

          {task.description && (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
              {task.description}
            </p>
          )}

          {/* Meta grid */}
          <div className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            <div className="flex justify-between gap-2">
              <span className="text-muted">Vencimiento</span>
              <span className="text-foreground">
                {task.due_at ? shortDateTime(task.due_at) : "Sin fecha"}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted">Asignada a</span>
              <span className="text-foreground">
                {userName(task.assigned_to_id) ??
                  (task.assigned_to_id ? "Miembro del equipo" : "Sin asignar")}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-muted">Creada</span>
              <span className="text-foreground">{shortDateTime(task.created_at)}</span>
            </div>
            {task.completed_at && (
              <div className="flex justify-between gap-2">
                <span className="text-muted">Completada</span>
                <span className="text-foreground">{shortDateTime(task.completed_at)}</span>
              </div>
            )}
          </div>

          <Separator />

          {/* Reminders */}
          <div className="space-y-3">
            <SectionTitle icon={Clock}>Recordatorios</SectionTitle>
            {task.reminders.length === 0 ? (
              <p className="text-sm text-muted">Sin recordatorios programados.</p>
            ) : (
              <ul className="space-y-1.5">
                {task.reminders.map((r) => (
                  <li
                    key={r.id}
                    className="flex items-center justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2 text-sm"
                  >
                    <span className="text-foreground">{shortDateTime(r.remind_at)}</span>
                    <span className="flex items-center gap-2">
                      <span className="text-xs text-muted">
                        {TASK_REMINDER_CHANNEL_LABELS[r.channel]}
                      </span>
                      <Badge tone={reminderStatusTone(r.status)}>
                        {TASK_REMINDER_STATUS_LABELS[r.status]}
                      </Badge>
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {active && (
              <form
                onSubmit={onAddReminder}
                className="flex flex-col gap-2 border-t border-border pt-3 sm:flex-row"
              >
                <Field label="" htmlFor="reminder-at" className="flex-1">
                  <Input
                    id="reminder-at"
                    type="datetime-local"
                    value={remindAt}
                    onChange={(e) => setRemindAt(e.target.value)}
                  />
                </Field>
                <Field label="" htmlFor="reminder-channel" className="sm:w-40">
                  <Select
                    id="reminder-channel"
                    value={channel}
                    onChange={(e) => setChannel(e.target.value as TaskReminderChannel)}
                  >
                    {REMINDER_CHANNELS.map((c) => (
                      <option key={c} value={c}>
                        {TASK_REMINDER_CHANNEL_LABELS[c]}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Button
                  type="submit"
                  variant="secondary"
                  loading={addReminder.isPending}
                  disabled={!remindAt}
                  leftIcon={<AlarmClockPlus className="h-4 w-4" />}
                  className="sm:self-end"
                >
                  Agregar
                </Button>
              </form>
            )}
          </div>

          {/* Comments */}
          {task.comments.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <SectionTitle icon={MessageSquare}>Comentarios</SectionTitle>
                <ul className="space-y-2">
                  {task.comments.map((c) => (
                    <li
                      key={c.id}
                      className="rounded-lg border border-border bg-bg-subtle px-3 py-2"
                    >
                      <p className="whitespace-pre-wrap text-sm text-foreground">{c.body}</p>
                      <p className="mt-1 text-[11px] text-muted">
                        {shortDateTime(c.created_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* History */}
          {task.status_history.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <SectionTitle icon={History}>Historial</SectionTitle>
                <ul className="space-y-1.5">
                  {task.status_history.map((h) => (
                    <li
                      key={h.id}
                      className="flex items-center justify-between gap-3 text-sm"
                    >
                      <span className="flex items-center gap-1.5">
                        {h.from_status && (
                          <span className="text-muted">
                            {TASK_STATUS_LABELS[
                              h.from_status as keyof typeof TASK_STATUS_LABELS
                            ] ?? h.from_status}
                          </span>
                        )}
                        <span className="text-muted">→</span>
                        <span className="text-foreground">
                          {TASK_STATUS_LABELS[
                            h.to_status as keyof typeof TASK_STATUS_LABELS
                          ] ?? h.to_status}
                        </span>
                      </span>
                      <span className="shrink-0 text-[11px] text-muted">
                        {shortDateTime(h.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      )}
    </Modal>
  );
}
