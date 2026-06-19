"use client";

import { Search } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/cn";
import { ApiError } from "@/lib/api/types";
import {
  TICKET_CATEGORY_LABELS,
  TICKET_PRIORITY_LABELS,
  type ContactPickerItem,
  type TicketCategory,
  type TicketPriority,
  useContactSearch,
  useCreateTicket,
} from "./queries";

const CATEGORY_ENTRIES = Object.entries(TICKET_CATEGORY_LABELS) as [
  TicketCategory,
  string,
][];
const PRIORITY_ENTRIES = Object.entries(TICKET_PRIORITY_LABELS) as [
  TicketPriority,
  string,
][];

export function CreateTicketModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (ticketId: string) => void;
}) {
  const create = useCreateTicket();
  const [search, setSearch] = useState("");
  const [contact, setContact] = useState<ContactPickerItem | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<TicketCategory>("unknown");
  const [priority, setPriority] = useState<TicketPriority>("medium");

  const { data: contactsData, isLoading: contactsLoading } =
    useContactSearch(search);

  function reset() {
    setSearch("");
    setContact(null);
    setTitle("");
    setDescription("");
    setCategory("unknown");
    setPriority("medium");
  }

  function close() {
    reset();
    onClose();
  }

  async function submit() {
    if (!contact) {
      toast.error("Elegí un contacto");
      return;
    }
    if (!title.trim()) {
      toast.error("Falta el título");
      return;
    }
    try {
      const ticket = await create.mutateAsync({
        contact_id: contact.id,
        title: title.trim(),
        description: description.trim(),
        category,
        priority,
      });
      toast.success("Ticket creado");
      reset();
      onCreated(ticket.id);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo crear el ticket",
      );
    }
  }

  const contacts = contactsData?.items ?? [];

  return (
    <Modal
      open={open}
      onClose={close}
      title="Nuevo ticket"
      description="Asociá un contacto y describí el problema."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={close}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={create.isPending}>
            Crear ticket
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Contacto" required>
          {contact ? (
            <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-bg-subtle px-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">
                  {contact.display_name || "Contacto sin nombre"}
                </p>
                <p className="truncate text-xs text-muted">
                  {contact.primary_phone || contact.company_name || "—"}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setContact(null)}
              >
                Cambiar
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar contacto por nombre o teléfono…"
                  className="pl-9"
                />
              </div>
              <div className="max-h-48 overflow-y-auto rounded-lg border border-border">
                {contactsLoading ? (
                  <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted">
                    <Spinner className="h-4 w-4" />
                    Buscando…
                  </div>
                ) : contacts.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-muted">
                    Sin resultados.
                  </p>
                ) : (
                  contacts.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setContact(c)}
                      className={cn(
                        "flex w-full cursor-pointer items-center justify-between gap-3 border-b border-border px-3 py-2.5 text-left",
                        "transition-colors last:border-b-0 hover:bg-card-hover",
                      )}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-foreground">
                          {c.display_name || "Contacto sin nombre"}
                        </p>
                        <p className="truncate text-xs text-muted">
                          {c.primary_phone || c.company_name || "—"}
                        </p>
                      </div>
                      <Badge tone="muted">{c.type}</Badge>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </Field>

        <Field label="Título" htmlFor="ticket-title" required>
          <Input
            id="ticket-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Resumen corto del problema"
          />
        </Field>

        <Field label="Descripción" htmlFor="ticket-desc">
          <Textarea
            id="ticket-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detalle del problema, contexto, pasos para reproducir…"
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Categoría" htmlFor="ticket-category">
            <Select
              id="ticket-category"
              value={category}
              onChange={(e) => setCategory(e.target.value as TicketCategory)}
            >
              {CATEGORY_ENTRIES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Prioridad" htmlFor="ticket-priority">
            <Select
              id="ticket-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as TicketPriority)}
            >
              {PRIORITY_ENTRIES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </div>
    </Modal>
  );
}
