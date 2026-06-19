"use client";

import {
  Bot,
  CheckCircle2,
  MessageSquare,
  Paperclip,
  RotateCcw,
  Send,
  User,
  UserPlus,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, Input, Textarea } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { BackLink } from "@/components/shell/back-link";
import { cn } from "@/lib/cn";
import { shortDateTime } from "@/lib/format";
import { ApiError } from "@/lib/api/types";
import {
  ATTACHMENT_TYPE_LABELS,
  COMMENT_AUTHOR_LABELS,
  COMMENT_VISIBILITY_LABELS,
  TICKET_CATEGORY_LABELS,
  TICKET_PRIORITY_LABELS,
  TICKET_STATUS_LABELS,
  categoryTone,
  isClosedStatus,
  priorityTone,
  statusTone,
  useAddComment,
  useAssignTicket,
  useReopenTicket,
  useResolveTicket,
  useTicket,
  type CommentVisibility,
  type TicketComment,
  type TicketDetail as TicketDetailType,
} from "./queries";

const VISIBILITY_OPTIONS: SegmentedOption<CommentVisibility>[] = [
  { value: "internal", label: "Interno" },
  { value: "client", label: "Cliente" },
];

function reportApiError(err: unknown, fallback: string) {
  toast.error(
    err instanceof ApiError ? err.firstFieldError || err.message : fallback,
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-7 w-2/3" />
      <div className="flex gap-2">
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-24 rounded-full" />
      </div>
      <Skeleton className="h-32 w-full rounded-xl" />
      <Skeleton className="h-48 w-full rounded-xl" />
    </div>
  );
}

function CommentIcon({ type }: { type: TicketComment["author_type"] }) {
  if (type === "ai_agent")
    return <Bot className="h-4 w-4 text-primary" aria-hidden />;
  if (type === "user")
    return <User className="h-4 w-4 text-muted" aria-hidden />;
  return <MessageSquare className="h-4 w-4 text-muted" aria-hidden />;
}

function AssignModal({
  open,
  onClose,
  ticketId,
}: {
  open: boolean;
  onClose: () => void;
  ticketId: string;
}) {
  const assign = useAssignTicket(ticketId);
  const [userId, setUserId] = useState("");

  async function submit() {
    if (!userId.trim()) {
      toast.error("Ingresá el ID del usuario");
      return;
    }
    try {
      await assign.mutateAsync(userId.trim());
      toast.success("Ticket asignado");
      setUserId("");
      onClose();
    } catch (err) {
      reportApiError(err, "No se pudo asignar el ticket");
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Asignar ticket"
      description="Pegá el ID del miembro del equipo que se va a encargar."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={assign.isPending}>
            Asignar
          </Button>
        </>
      }
    >
      <Field
        label="ID de usuario"
        htmlFor="assign-user-id"
        hint="Debe ser un miembro activo de la organización."
        required
      >
        <Input
          id="assign-user-id"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
        />
      </Field>
    </Modal>
  );
}

function ResolveModal({
  open,
  onClose,
  ticketId,
}: {
  open: boolean;
  onClose: () => void;
  ticketId: string;
}) {
  const resolve = useResolveTicket(ticketId);
  const [summary, setSummary] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [steps, setSteps] = useState("");

  function reset() {
    setSummary("");
    setRootCause("");
    setSteps("");
  }

  async function submit() {
    if (!summary.trim()) {
      toast.error("Resumí cómo se resolvió");
      return;
    }
    try {
      await resolve.mutateAsync({
        summary: summary.trim(),
        root_cause: rootCause.trim(),
        resolution_steps: steps.trim(),
      });
      toast.success("Ticket resuelto");
      reset();
      onClose();
    } catch (err) {
      reportApiError(err, "No se pudo resolver el ticket");
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Resolver ticket"
      description="Dejá registro de la solución para futuras consultas."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={resolve.isPending}>
            Resolver
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Resumen de la solución" htmlFor="resolve-summary" required>
          <Textarea
            id="resolve-summary"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Qué se hizo para resolverlo."
          />
        </Field>
        <Field label="Causa raíz" htmlFor="resolve-root">
          <Input
            id="resolve-root"
            value={rootCause}
            onChange={(e) => setRootCause(e.target.value)}
            placeholder="Qué lo originó (opcional)."
          />
        </Field>
        <Field label="Pasos de resolución" htmlFor="resolve-steps">
          <Textarea
            id="resolve-steps"
            value={steps}
            onChange={(e) => setSteps(e.target.value)}
            placeholder="Pasos concretos que se siguieron (opcional)."
          />
        </Field>
      </div>
    </Modal>
  );
}

function ReopenModal({
  open,
  onClose,
  ticketId,
}: {
  open: boolean;
  onClose: () => void;
  ticketId: string;
}) {
  const reopen = useReopenTicket(ticketId);
  const [reason, setReason] = useState("");

  async function submit() {
    try {
      await reopen.mutateAsync(reason.trim());
      toast.success("Ticket reabierto");
      setReason("");
      onClose();
    } catch (err) {
      reportApiError(err, "No se pudo reabrir el ticket");
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Reabrir ticket"
      description="Indicá por qué se vuelve a abrir."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={reopen.isPending}>
            Reabrir
          </Button>
        </>
      }
    >
      <Field label="Motivo" htmlFor="reopen-reason">
        <Textarea
          id="reopen-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Por qué se reabre (opcional)."
        />
      </Field>
    </Modal>
  );
}

function CommentComposer({ ticketId }: { ticketId: string }) {
  const addComment = useAddComment(ticketId);
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState<CommentVisibility>("internal");

  async function submit() {
    if (!body.trim()) return;
    try {
      await addComment.mutateAsync({ body: body.trim(), visibility });
      setBody("");
      toast.success("Comentario agregado");
    } catch (err) {
      reportApiError(err, "No se pudo agregar el comentario");
    }
  }

  return (
    <div className="space-y-2">
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Escribí un comentario…"
      />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <Segmented
          options={VISIBILITY_OPTIONS}
          value={visibility}
          onChange={setVisibility}
        />
        <Button
          type="button"
          onClick={submit}
          loading={addComment.isPending}
          disabled={!body.trim()}
          leftIcon={<Send className="h-4 w-4" />}
        >
          Comentar
        </Button>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 text-sm">
      <span className="text-muted">{label}</span>
      <span className="min-w-0 truncate text-right font-medium text-foreground">
        {value}
      </span>
    </div>
  );
}

function TicketContent({ ticket }: { ticket: TicketDetailType }) {
  const [assignOpen, setAssignOpen] = useState(false);
  const [resolveOpen, setResolveOpen] = useState(false);
  const [reopenOpen, setReopenOpen] = useState(false);

  const closed = isClosedStatus(ticket.status);

  return (
    <>
      <BackLink href="/support" label="Tickets" />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-2">
          <h1 className="font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
            {ticket.title}
          </h1>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge tone={statusTone(ticket.status)}>
              {TICKET_STATUS_LABELS[ticket.status]}
            </Badge>
            <Badge tone={priorityTone(ticket.priority)} dot>
              {TICKET_PRIORITY_LABELS[ticket.priority]}
            </Badge>
            <Badge tone={categoryTone(ticket.category)}>
              {TICKET_CATEGORY_LABELS[ticket.category]}
            </Badge>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => setAssignOpen(true)}
            leftIcon={<UserPlus className="h-4 w-4" />}
          >
            Asignar
          </Button>
          {closed ? (
            <Button
              variant="secondary"
              onClick={() => setReopenOpen(true)}
              leftIcon={<RotateCcw className="h-4 w-4" />}
            >
              Reabrir
            </Button>
          ) : (
            <Button
              onClick={() => setResolveOpen(true)}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
            >
              Resolver
            </Button>
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_300px]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Descripción</CardTitle>
            </CardHeader>
            <CardContent>
              {ticket.description ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                  {ticket.description}
                </p>
              ) : (
                <p className="text-sm text-muted">Sin descripción.</p>
              )}
              {(ticket.ai_summary || ticket.technical_summary) && (
                <>
                  <Separator className="my-4" />
                  {ticket.ai_summary && (
                    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                      <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-primary">
                        <Bot className="h-3.5 w-3.5" aria-hidden />
                        Resumen IA
                      </p>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                        {ticket.ai_summary}
                      </p>
                    </div>
                  )}
                  {ticket.technical_summary && (
                    <div className="mt-3">
                      <p className="mb-1 text-xs font-medium text-muted">
                        Resumen técnico
                      </p>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                        {ticket.technical_summary}
                      </p>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Paperclip className="h-4 w-4 text-muted" aria-hidden />
                Adjuntos
                {ticket.attachments.length > 0 && (
                  <Badge tone="muted">{ticket.attachments.length}</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {ticket.attachments.length === 0 ? (
                <p className="text-sm text-muted">Sin adjuntos.</p>
              ) : (
                <ul className="space-y-2">
                  {ticket.attachments.map((a) => (
                    <li
                      key={a.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-border bg-bg-subtle px-3 py-2.5"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        <Paperclip
                          className="h-4 w-4 shrink-0 text-muted"
                          aria-hidden
                        />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {a.file_name || "Archivo adjunto"}
                          </p>
                          <p className="truncate text-xs text-muted">
                            {a.mime_type || "—"}
                          </p>
                        </div>
                      </div>
                      <Badge tone="muted">
                        {ATTACHMENT_TYPE_LABELS[a.attachment_type]}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-muted" aria-hidden />
                Comentarios
                {ticket.comments.length > 0 && (
                  <Badge tone="muted">{ticket.comments.length}</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {ticket.comments.length === 0 ? (
                <EmptyState
                  icon={MessageSquare}
                  title="Sin comentarios"
                  description="Dejá la primera nota interna o respuesta al cliente."
                />
              ) : (
                <ul className="space-y-3">
                  {ticket.comments.map((c) => (
                    <li
                      key={c.id}
                      className="rounded-lg border border-border bg-bg-subtle p-3"
                    >
                      <div className="mb-1.5 flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                          <CommentIcon type={c.author_type} />
                          {COMMENT_AUTHOR_LABELS[c.author_type]}
                        </span>
                        <span className="flex items-center gap-2">
                          <Badge
                            tone={c.visibility === "client" ? "info" : "muted"}
                          >
                            {COMMENT_VISIBILITY_LABELS[c.visibility]}
                          </Badge>
                          <span className="text-[11px] text-muted">
                            {shortDateTime(c.created_at)}
                          </span>
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                        {c.body}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
              <Separator />
              <CommentComposer ticketId={ticket.id} />
            </CardContent>
          </Card>
        </div>

        <Card className={cn("h-fit")}>
          <CardHeader>
            <CardTitle>Detalles</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-border py-0">
            <MetaRow
              label="Contacto"
              value={
                ticket.contact_id ? (
                  <span className="font-mono text-xs">{ticket.contact_id}</span>
                ) : (
                  "—"
                )
              }
            />
            <MetaRow
              label="Asignado a"
              value={
                ticket.assigned_user_id ? (
                  <span className="font-mono text-xs">
                    {ticket.assigned_user_id}
                  </span>
                ) : (
                  <span className="text-muted">Sin asignar</span>
                )
              }
            />
            <MetaRow
              label="Conversación"
              value={
                ticket.conversation_id ? (
                  <span className="font-mono text-xs">
                    {ticket.conversation_id}
                  </span>
                ) : (
                  "—"
                )
              }
            />
            <MetaRow
              label="Vencimiento"
              value={ticket.due_at ? shortDateTime(ticket.due_at) : "—"}
            />
            <MetaRow
              label="Resuelto"
              value={
                ticket.resolved_at ? shortDateTime(ticket.resolved_at) : "—"
              }
            />
            <MetaRow label="Creado" value={shortDateTime(ticket.created_at)} />
            <MetaRow
              label="Actualizado"
              value={shortDateTime(ticket.updated_at)}
            />
          </CardContent>
        </Card>
      </div>

      <AssignModal
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        ticketId={ticket.id}
      />
      <ResolveModal
        open={resolveOpen}
        onClose={() => setResolveOpen(false)}
        ticketId={ticket.id}
      />
      <ReopenModal
        open={reopenOpen}
        onClose={() => setReopenOpen(false)}
        ticketId={ticket.id}
      />
    </>
  );
}

export function TicketDetail({ ticketId }: { ticketId: string }) {
  const { data, isLoading, isError } = useTicket(ticketId);

  if (isLoading) return <DetailSkeleton />;

  if (isError || !data) {
    return (
      <>
        <BackLink href="/support" label="Tickets" />
        <EmptyState
          icon={MessageSquare}
          title="No se pudo cargar el ticket"
          description="Puede que no exista o que haya un problema de conexión."
        />
      </>
    );
  }

  return <TicketContent ticket={data} />;
}
