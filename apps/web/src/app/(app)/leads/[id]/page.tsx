"use client";

import {
  ArrowRightLeft,
  CalendarClock,
  Gauge,
  History,
  Sparkles,
  Target,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { BackLink } from "@/components/shell/back-link";
import { PageContainer } from "@/components/shell/page-container";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AUTHORITY_SIGNAL_LABELS,
  BUDGET_SIGNAL_LABELS,
  LEAD_SOURCE_TYPE_LABELS,
  LEAD_STAGE_LABELS,
  LEAD_STATUS_LABELS,
  LEAD_TEMPERATURE_LABELS,
  LEAD_URGENCY_LABELS,
  type LeadDetail,
  type LeadStage,
  STAGE_CHANGED_BY_LABELS,
  type StageChangedByType,
  scoreTone,
  stageTone,
  statusTone,
  temperatureTone,
  useChangeStage,
  useConvertToClient,
  useLead,
  useMarkLost,
  useScheduleFollowup,
  useScoreLead,
} from "@/features/leads/queries";
import { ApiError } from "@/lib/api/types";
import { shortDateTime } from "@/lib/format";

const STAGE_VALUES = Object.keys(LEAD_STAGE_LABELS) as LeadStage[];

function apiMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError
    ? err.firstFieldError || err.message
    : fallback;
}

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-7 w-48" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-40 w-full rounded-xl" />
      <Skeleton className="h-56 w-full rounded-xl" />
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-right text-sm font-medium text-foreground">
        {value}
      </span>
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  if (!items.length) return <span className="text-sm text-muted">—</span>;
  return (
    <div className="flex flex-wrap justify-end gap-1.5">
      {items.map((item) => (
        <Badge key={item} tone="muted">
          {item}
        </Badge>
      ))}
    </div>
  );
}

// --- Action: change stage ---

function ChangeStageModal({
  lead,
  open,
  onClose,
}: {
  lead: LeadDetail;
  open: boolean;
  onClose: () => void;
}) {
  const changeStage = useChangeStage(lead.id);
  const [stage, setStage] = useState<LeadStage>(lead.stage);
  const [reason, setReason] = useState("");

  async function submit() {
    try {
      await changeStage.mutateAsync({ stage, reason });
      toast.success("Etapa actualizada");
      onClose();
    } catch (err) {
      toast.error(apiMessage(err, "No se pudo cambiar la etapa"));
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Cambiar etapa"
      description="Movés el lead dentro del pipeline."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={changeStage.isPending}>
            Guardar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Etapa" htmlFor="stage-select">
          <Select
            id="stage-select"
            value={stage}
            onChange={(e) => setStage(e.target.value as LeadStage)}
          >
            {STAGE_VALUES.map((s) => (
              <option key={s} value={s}>
                {LEAD_STAGE_LABELS[s]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Motivo" htmlFor="stage-reason" hint="Opcional.">
          <Textarea
            id="stage-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Por qué cambiás la etapa…"
          />
        </Field>
      </div>
    </Modal>
  );
}

// --- Action: mark lost ---

function MarkLostModal({
  lead,
  open,
  onClose,
}: {
  lead: LeadDetail;
  open: boolean;
  onClose: () => void;
}) {
  const markLost = useMarkLost(lead.id);
  const [reason, setReason] = useState("");

  async function submit() {
    if (!reason.trim()) {
      toast.error("Indicá un motivo");
      return;
    }
    try {
      await markLost.mutateAsync(reason.trim());
      toast.success("Lead marcado como perdido");
      onClose();
    } catch (err) {
      toast.error(apiMessage(err, "No se pudo marcar como perdido"));
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Marcar como perdido"
      description="Cerrás el lead sin conversión."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={submit} loading={markLost.isPending}>
            Marcar perdido
          </Button>
        </>
      }
    >
      <Field label="Motivo" htmlFor="lost-reason" required>
        <Textarea
          id="lost-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Por qué se perdió el lead…"
        />
      </Field>
    </Modal>
  );
}

// --- Action: convert to client ---

function ConvertModal({
  lead,
  open,
  onClose,
}: {
  lead: LeadDetail;
  open: boolean;
  onClose: () => void;
}) {
  const convert = useConvertToClient(lead.id);
  const [reason, setReason] = useState("");

  async function submit() {
    try {
      await convert.mutateAsync(reason);
      toast.success("Lead convertido a cliente");
      onClose();
    } catch (err) {
      toast.error(apiMessage(err, "No se pudo convertir"));
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Convertir a cliente"
      description="Marcás el lead como ganado y lo registrás como cliente."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={convert.isPending}>
            Convertir
          </Button>
        </>
      }
    >
      <Field label="Nota" htmlFor="convert-reason" hint="Opcional.">
        <Textarea
          id="convert-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Contexto de la conversión…"
        />
      </Field>
    </Modal>
  );
}

// --- Action: schedule follow-up ---

function FollowupModal({
  lead,
  open,
  onClose,
}: {
  lead: LeadDetail;
  open: boolean;
  onClose: () => void;
}) {
  const followup = useScheduleFollowup(lead.id);
  const [title, setTitle] = useState("Seguimiento comercial");
  const [dueAt, setDueAt] = useState("");
  const [notes, setNotes] = useState("");

  async function submit() {
    try {
      await followup.mutateAsync({
        title,
        notes,
        due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
      });
      toast.success("Seguimiento agendado");
      onClose();
    } catch (err) {
      toast.error(apiMessage(err, "No se pudo agendar el seguimiento"));
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Agendar seguimiento"
      description="Creás una tarea de seguimiento para este lead."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={followup.isPending}>
            Agendar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Título" htmlFor="followup-title">
          <Input
            id="followup-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </Field>
        <Field label="Vencimiento" htmlFor="followup-due" hint="Opcional.">
          <Input
            id="followup-due"
            type="datetime-local"
            value={dueAt}
            onChange={(e) => setDueAt(e.target.value)}
          />
        </Field>
        <Field label="Notas" htmlFor="followup-notes" hint="Opcional.">
          <Textarea
            id="followup-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Detalles del seguimiento…"
          />
        </Field>
      </div>
    </Modal>
  );
}

// --- Action bar ---

function Actions({ lead }: { lead: LeadDetail }) {
  const scoreLead = useScoreLead(lead.id);
  const [stageOpen, setStageOpen] = useState(false);
  const [convertOpen, setConvertOpen] = useState(false);
  const [lostOpen, setLostOpen] = useState(false);
  const [followupOpen, setFollowupOpen] = useState(false);

  const closed = lead.status === "won" || lead.status === "lost";

  async function score() {
    try {
      const snapshot = await scoreLead.mutateAsync({ use_ai: true });
      toast.success(`Lead re-scoreado: ${snapshot.score}`);
    } catch (err) {
      toast.error(apiMessage(err, "No se pudo scorear el lead"));
    }
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          onClick={score}
          loading={scoreLead.isPending}
          leftIcon={<Sparkles className="h-4 w-4" />}
        >
          Scorear
        </Button>
        <Button
          variant="secondary"
          onClick={() => setStageOpen(true)}
          leftIcon={<ArrowRightLeft className="h-4 w-4" />}
        >
          Cambiar etapa
        </Button>
        <Button
          variant="secondary"
          onClick={() => setFollowupOpen(true)}
          leftIcon={<CalendarClock className="h-4 w-4" />}
        >
          Agendar follow-up
        </Button>
        <Button
          onClick={() => setConvertOpen(true)}
          disabled={closed}
          leftIcon={<UserCheck className="h-4 w-4" />}
        >
          Convertir a cliente
        </Button>
        <Button
          variant="outline"
          onClick={() => setLostOpen(true)}
          disabled={closed}
          leftIcon={<XCircle className="h-4 w-4" />}
        >
          Marcar perdido
        </Button>
      </div>

      <ChangeStageModal
        lead={lead}
        open={stageOpen}
        onClose={() => setStageOpen(false)}
      />
      <ConvertModal
        lead={lead}
        open={convertOpen}
        onClose={() => setConvertOpen(false)}
      />
      <MarkLostModal
        lead={lead}
        open={lostOpen}
        onClose={() => setLostOpen(false)}
      />
      <FollowupModal
        lead={lead}
        open={followupOpen}
        onClose={() => setFollowupOpen(false)}
      />
    </>
  );
}

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: lead, isLoading, isError } = useLead(id);

  return (
    <PageContainer className="max-w-5xl">
      <BackLink href="/leads" label="Volver a leads" />

      {isLoading ? (
        <DetailSkeleton />
      ) : isError || !lead ? (
        <EmptyState
          icon={Target}
          title="No se pudo cargar el lead"
          description="Puede que no exista o que no tengas acceso."
        />
      ) : (
        <LeadView lead={lead} />
      )}
    </PageContainer>
  );
}

function LeadView({ lead }: { lead: LeadDetail }) {
  const name = lead.contact.display_name || "Sin nombre";

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <Avatar name={name} seed={lead.contact.id} size="lg" />
          <div className="min-w-0">
            <h1 className="truncate font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
              {name}
            </h1>
            {lead.contact.company_name && (
              <p className="truncate text-sm text-muted">
                {lead.contact.company_name}
              </p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <Badge tone={stageTone(lead.stage)} dot>
                {LEAD_STAGE_LABELS[lead.stage]}
              </Badge>
              <Badge tone={statusTone(lead.status)}>
                {LEAD_STATUS_LABELS[lead.status]}
              </Badge>
              <Badge tone={temperatureTone(lead.temperature)}>
                {LEAD_TEMPERATURE_LABELS[lead.temperature]}
              </Badge>
              <Badge tone={scoreTone(lead.score)}>
                <Gauge className="h-3 w-3" />
                Score {lead.score}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <Actions lead={lead} />

      {lead.summary && (
        <Card>
          <CardContent className="text-sm leading-relaxed text-foreground">
            {lead.summary}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Calificación</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <InfoRow
              label="Interés de servicio"
              value={lead.service_interest || "—"}
            />
            <Separator className="my-1" />
            <InfoRow
              label="Presupuesto"
              value={BUDGET_SIGNAL_LABELS[lead.budget_signal]}
            />
            <Separator className="my-1" />
            <InfoRow
              label="Urgencia"
              value={LEAD_URGENCY_LABELS[lead.urgency]}
            />
            <Separator className="my-1" />
            <InfoRow
              label="Autoridad"
              value={AUTHORITY_SIGNAL_LABELS[lead.authority_signal]}
            />
            <Separator className="my-1" />
            <InfoRow
              label="Próxima acción"
              value={lead.next_best_action || "—"}
            />
            <Separator className="my-1" />
            <InfoRow
              label="Último scoring"
              value={
                lead.last_scored_at ? shortDateTime(lead.last_scored_at) : "—"
              }
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Necesidades</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <div className="flex items-start justify-between gap-4">
              <span className="text-sm text-muted">Dolores</span>
              <Chips items={lead.pain_points} />
            </div>
            <Separator />
            <div className="flex items-start justify-between gap-4">
              <span className="text-sm text-muted">Técnicas</span>
              <Chips items={lead.technical_needs} />
            </div>
            <Separator />
            <div className="flex items-start justify-between gap-4">
              <span className="text-sm text-muted">De negocio</span>
              <Chips items={lead.business_needs} />
            </div>
          </CardContent>
        </Card>
      </div>

      <ScoreHistory lead={lead} />
      <StageHistoryCard lead={lead} />
      <SourcesCard lead={lead} />
    </div>
  );
}

function ScoreHistory({ lead }: { lead: LeadDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Historial de scoring</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {lead.score_snapshots.length === 0 ? (
          <p className="text-sm text-muted">Todavía no hay snapshots de score.</p>
        ) : (
          <ul className="space-y-3">
            {lead.score_snapshots.map((snap) => (
              <li
                key={snap.id}
                className="flex items-start gap-3 rounded-lg border border-border bg-bg-subtle px-3 py-2.5"
              >
                <Badge tone={scoreTone(snap.score)}>{snap.score}</Badge>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone={temperatureTone(snap.temperature)}>
                      {LEAD_TEMPERATURE_LABELS[snap.temperature]}
                    </Badge>
                    <span className="shrink-0 text-[11px] text-muted">
                      {shortDateTime(snap.created_at)}
                    </span>
                  </div>
                  {snap.reasoning_summary && (
                    <p className="mt-1.5 text-sm text-muted">
                      {snap.reasoning_summary}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function StageHistoryCard({ lead }: { lead: LeadDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-4 w-4 text-muted" />
          Historial de etapas
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {lead.stage_history.length === 0 ? (
          <p className="text-sm text-muted">Sin cambios de etapa registrados.</p>
        ) : (
          <ul className="space-y-2.5">
            {lead.stage_history.map((entry) => {
              const from = entry.from_stage
                ? LEAD_STAGE_LABELS[entry.from_stage as LeadStage] ??
                  entry.from_stage
                : null;
              const changedBy =
                STAGE_CHANGED_BY_LABELS[
                  entry.changed_by_type as StageChangedByType
                ] ?? entry.changed_by_type;
              return (
                <li
                  key={entry.id}
                  className="flex items-start justify-between gap-3 border-b border-border/60 pb-2.5 last:border-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5 text-sm">
                      {from && (
                        <>
                          <span className="text-muted">{from}</span>
                          <ArrowRightLeft className="h-3 w-3 text-muted" />
                        </>
                      )}
                      <Badge tone={stageTone(entry.to_stage)}>
                        {LEAD_STAGE_LABELS[entry.to_stage]}
                      </Badge>
                    </div>
                    {entry.reason && (
                      <p className="mt-1 text-sm text-muted">{entry.reason}</p>
                    )}
                    <p className="mt-0.5 text-[11px] text-muted">
                      {changedBy}
                    </p>
                  </div>
                  <span className="shrink-0 text-[11px] text-muted">
                    {shortDateTime(entry.created_at)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function SourcesCard({ lead }: { lead: LeadDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Origen</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {lead.sources.length === 0 ? (
          <p className="text-sm text-muted">Sin fuentes registradas.</p>
        ) : (
          <ul className="space-y-2.5">
            {lead.sources.map((src) => (
              <li
                key={src.id}
                className="flex items-start justify-between gap-3 border-b border-border/60 pb-2.5 last:border-0 last:pb-0"
              >
                <div className="min-w-0">
                  <Badge tone="info">
                    {LEAD_SOURCE_TYPE_LABELS[src.source_type]}
                  </Badge>
                  {(src.source_detail || src.campaign || src.channel) && (
                    <p className="mt-1 text-sm text-muted">
                      {[src.channel, src.campaign, src.source_detail]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  )}
                </div>
                <span className="shrink-0 text-[11px] text-muted">
                  {shortDateTime(src.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
