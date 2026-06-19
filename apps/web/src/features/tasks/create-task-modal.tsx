"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { ApiError } from "@/lib/api/types";
import {
  TASK_PRIORITY_LABELS,
  useCreateTask,
  useOrgUsers,
  type CreateTaskInput,
  type TaskPriority,
} from "./queries";

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

/** `datetime-local` → ISO; empty string → null. */
function toIso(local: string): string | null {
  if (!local) return null;
  const d = new Date(local);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function CreateTaskModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateTask();
  const { data: users } = useOrgUsers();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [dueAt, setDueAt] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);

  function reset() {
    setTitle("");
    setDescription("");
    setPriority("medium");
    setDueAt("");
    setAssignedTo("");
    setTitleError(null);
  }

  function close() {
    if (create.isPending) return;
    reset();
    onClose();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setTitleError("El título es obligatorio");
      return;
    }
    const body: CreateTaskInput = {
      title: title.trim(),
      description: description.trim() || undefined,
      priority,
      due_at: toIso(dueAt),
      assigned_to_id: assignedTo || null,
    };
    try {
      await create.mutateAsync(body);
      toast.success("Tarea creada");
      reset();
      onClose();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo crear la tarea",
      );
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Nueva tarea"
      description="Creá un pendiente y, si querés, asignalo a alguien del equipo."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={close}>
            Cancelar
          </Button>
          <Button type="submit" form="create-task-form" loading={create.isPending}>
            Crear tarea
          </Button>
        </>
      }
    >
      <form id="create-task-form" onSubmit={submit} className="space-y-4">
        <Field label="Título" htmlFor="task-title" required error={titleError}>
          <Input
            id="task-title"
            value={title}
            invalid={!!titleError}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
            placeholder="Llamar al cliente, enviar propuesta…"
            autoFocus
          />
        </Field>

        <Field label="Descripción" htmlFor="task-desc">
          <Textarea
            id="task-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detalles, contexto o pasos a seguir."
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Prioridad" htmlFor="task-priority">
            <Select
              id="task-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as TaskPriority)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {TASK_PRIORITY_LABELS[p]}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Vencimiento" htmlFor="task-due">
            <Input
              id="task-due"
              type="datetime-local"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
            />
          </Field>
        </div>

        {users && users.length > 0 && (
          <Field label="Asignar a" htmlFor="task-assignee">
            <Select
              id="task-assignee"
              value={assignedTo}
              onChange={(e) => setAssignedTo(e.target.value)}
            >
              <option value="">Sin asignar</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name || u.email}
                </option>
              ))}
            </Select>
          </Field>
        )}
      </form>
    </Modal>
  );
}
