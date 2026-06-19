"use client";

import { ListTodo, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/shell/page-container";
import { CreateTaskModal } from "@/features/tasks/create-task-modal";
import {
  TASK_PRIORITY_LABELS,
  useOrgUsers,
  useTasks,
  type OrgUser,
  type TaskFilters,
} from "@/features/tasks/queries";
import { SnoozeModal } from "@/features/tasks/snooze-modal";
import { TaskDetailModal } from "@/features/tasks/task-detail-modal";
import { TaskRow } from "@/features/tasks/task-row";

const STATUS_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Todas" },
  { value: "pending", label: "Pendientes" },
  { value: "in_progress", label: "En curso" },
  { value: "overdue", label: "Vencidas" },
  { value: "completed", label: "Completadas" },
];

const PRIORITY_OPTIONS: SegmentedOption<string>[] = [
  { value: "", label: "Toda prioridad" },
  { value: "urgent", label: TASK_PRIORITY_LABELS.urgent },
  { value: "high", label: TASK_PRIORITY_LABELS.high },
  { value: "medium", label: TASK_PRIORITY_LABELS.medium },
  { value: "low", label: TASK_PRIORITY_LABELS.low },
];

type DueWindow = "" | "today" | "overdue" | "upcoming";

const DUE_OPTIONS: SegmentedOption<DueWindow>[] = [
  { value: "", label: "Cualquier fecha" },
  { value: "overdue", label: "Vencidas" },
  { value: "today", label: "Hoy" },
  { value: "upcoming", label: "Próximas" },
];

/** Translate a due-window choice into the backend's due_before/due_after params. */
function dueRange(window: DueWindow): Pick<TaskFilters, "due_before" | "due_after"> {
  const now = new Date();
  if (window === "overdue") {
    return { due_before: now.toISOString() };
  }
  if (window === "today") {
    const end = new Date(now);
    end.setHours(23, 59, 59, 999);
    return { due_after: now.toISOString(), due_before: end.toISOString() };
  }
  if (window === "upcoming") {
    return { due_after: now.toISOString() };
  }
  return {};
}

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3"
        >
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3.5 w-2/3" />
            <Skeleton className="h-3 w-40" />
          </div>
          <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

export default function TasksPage() {
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [due, setDue] = useState<DueWindow>("");
  const [assignee, setAssignee] = useState("");
  const [search, setSearch] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [snoozeId, setSnoozeId] = useState<string | null>(null);

  const { data: users } = useOrgUsers();

  const filters: TaskFilters = useMemo(
    () => ({
      status: status || undefined,
      priority: priority || undefined,
      assigned_to_id: assignee || undefined,
      search: search || undefined,
      ...dueRange(due),
    }),
    [status, priority, assignee, search, due],
  );

  const { data, isLoading, isError } = useTasks(filters);
  const items = data?.items ?? [];

  const usersById = useMemo(() => {
    const map = new Map<string, OrgUser>();
    (users ?? []).forEach((u) => map.set(u.id, u));
    return map;
  }, [users]);

  const assigneeName = (id: string | null): string | null => {
    if (!id) return null;
    const u = usersById.get(id);
    return u ? u.name || u.email : null;
  };

  return (
    <PageContainer>
      <div className="space-y-6">
        <PageHeader
          title="Tareas"
          description="Pendientes, recordatorios y seguimiento del equipo."
          actions={
            <Button
              type="button"
              onClick={() => setCreateOpen(true)}
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Nueva tarea
            </Button>
          }
        />

        {/* Filters */}
        <div className="space-y-3">
          <div className="relative max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar tarea por título…"
              className="pl-9"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Segmented options={STATUS_OPTIONS} value={status} onChange={setStatus} />
            <Segmented
              options={PRIORITY_OPTIONS}
              value={priority}
              onChange={setPriority}
            />
            <Segmented options={DUE_OPTIONS} value={due} onChange={setDue} />
            {users && users.length > 0 && (
              <Select
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                className="w-auto min-w-[10rem]"
                aria-label="Filtrar por asignado"
              >
                <option value="">Todos los asignados</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name || u.email}
                  </option>
                ))}
              </Select>
            )}
          </div>
        </div>

        {/* List */}
        {isLoading ? (
          <ListSkeleton />
        ) : isError ? (
          <EmptyState
            icon={ListTodo}
            title="No se pudieron cargar las tareas"
            description="Revisá la conexión con el backend e intentá de nuevo."
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon={ListTodo}
            title="Sin tareas"
            description="No hay tareas que coincidan con los filtros. Creá una nueva para empezar."
            action={
              <Button
                type="button"
                variant="secondary"
                onClick={() => setCreateOpen(true)}
                leftIcon={<Plus className="h-4 w-4" />}
              >
                Nueva tarea
              </Button>
            }
          />
        ) : (
          <div className="space-y-2">
            {items.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                assigneeName={assigneeName(task.assigned_to_id)}
                onOpen={setDetailId}
                onSnooze={setSnoozeId}
              />
            ))}
          </div>
        )}
      </div>

      <CreateTaskModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <TaskDetailModal
        taskId={detailId}
        onClose={() => setDetailId(null)}
        onSnooze={setSnoozeId}
      />
      <SnoozeModal
        open={!!snoozeId}
        taskId={snoozeId}
        onClose={() => setSnoozeId(null)}
      />
    </PageContainer>
  );
}
