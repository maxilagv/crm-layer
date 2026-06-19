"use client";

import { Ban, CalendarClock, CheckCircle2, Clock, User } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { relativeTime, shortDateTime } from "@/lib/format";
import { ApiError } from "@/lib/api/types";
import {
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
  isTaskActive,
  priorityTone,
  statusTone,
  useCancelTask,
  useCompleteTask,
  type Task,
} from "./queries";

function isOverdue(task: Task): boolean {
  if (!task.due_at || !isTaskActive(task.status)) return false;
  if (task.status === "completed") return false;
  return new Date(task.due_at).getTime() < Date.now();
}

export function TaskRow({
  task,
  assigneeName,
  onOpen,
  onSnooze,
}: {
  task: Task;
  assigneeName?: string | null;
  onOpen: (id: string) => void;
  onSnooze: (id: string) => void;
}) {
  const complete = useCompleteTask();
  const cancel = useCancelTask();
  const active = isTaskActive(task.status);
  const overdue = isOverdue(task);

  async function runComplete(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await complete.mutateAsync(task.id);
      toast.success("Tarea completada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo completar",
      );
    }
  }

  async function runCancel(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await cancel.mutateAsync(task.id);
      toast.success("Tarea cancelada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo cancelar",
      );
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onOpen(task.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(task.id);
        }
      }}
      className={cn(
        "group flex cursor-pointer flex-col gap-3 rounded-xl border border-border bg-card px-4 py-3 outline-none transition-colors",
        "hover:bg-card-hover focus-visible:shadow-focus sm:flex-row sm:items-center sm:justify-between",
        !active && "opacity-70",
      )}
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex items-center gap-2">
          <Badge tone={statusTone(task.status)} dot>
            {TASK_STATUS_LABELS[task.status]}
          </Badge>
          <Badge tone={priorityTone(task.priority)}>
            {TASK_PRIORITY_LABELS[task.priority]}
          </Badge>
        </div>
        <p
          className={cn(
            "truncate text-sm font-medium text-foreground",
            task.status === "completed" && "line-through decoration-muted",
          )}
        >
          {task.title}
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          {task.due_at ? (
            <span
              className={cn(
                "inline-flex items-center gap-1",
                overdue && "font-medium text-danger",
              )}
            >
              <CalendarClock className="h-3.5 w-3.5" />
              {shortDateTime(task.due_at)}
              {overdue && " · vencida"}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              actualizada {relativeTime(task.updated_at)}
            </span>
          )}
          {(assigneeName || task.assigned_to_id) && (
            <span className="inline-flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              {assigneeName ?? "Asignada"}
            </span>
          )}
        </div>
      </div>

      {active && (
        <div className="flex shrink-0 items-center gap-1.5 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100">
          <Button
            type="button"
            variant="subtle"
            size="sm"
            onClick={runComplete}
            loading={complete.isPending}
            leftIcon={<CheckCircle2 className="h-4 w-4" />}
          >
            Completar
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Posponer"
            onClick={(e) => {
              e.stopPropagation();
              onSnooze(task.id);
            }}
          >
            <Clock className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Cancelar"
            onClick={runCancel}
            loading={cancel.isPending}
          >
            <Ban className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
