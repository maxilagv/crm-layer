"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { ApiError } from "@/lib/api/types";
import { useSnoozeTask } from "./queries";

/** Default snooze target: tomorrow at 09:00, formatted for `datetime-local`. */
function defaultSnooze(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(9, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

export function SnoozeModal({
  open,
  taskId,
  onClose,
}: {
  open: boolean;
  taskId: string | null;
  onClose: () => void;
}) {
  const snooze = useSnoozeTask();
  const [value, setValue] = useState(defaultSnooze);

  function close() {
    if (snooze.isPending) return;
    onClose();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!taskId || !value) return;
    const iso = new Date(value).toISOString();
    try {
      await snooze.mutateAsync({ id: taskId, snooze_until: iso });
      toast.success("Tarea pospuesta");
      onClose();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo posponer",
      );
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Posponer tarea"
      description="Elegí hasta cuándo querés dejar de ver esta tarea como pendiente."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={close}>
            Cancelar
          </Button>
          <Button type="submit" form="snooze-task-form" loading={snooze.isPending}>
            Posponer
          </Button>
        </>
      }
    >
      <form id="snooze-task-form" onSubmit={submit}>
        <Field label="Posponer hasta" htmlFor="snooze-until">
          <Input
            id="snooze-until"
            type="datetime-local"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
          />
        </Field>
      </form>
    </Modal>
  );
}
