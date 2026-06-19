"use client";

import {
  AtSign,
  Building2,
  MessageSquarePlus,
  Phone,
  Plus,
  Tag,
  Users,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BackLink } from "@/components/shell/back-link";
import { PageContainer } from "@/components/shell/page-container";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/types";
import { shortDateTime } from "@/lib/format";
import {
  CONTACT_SOURCE_LABELS,
  CONTACT_STATUS_LABELS,
  CONTACT_TYPE_LABELS,
  statusTone,
  typeTone,
  useAddNote,
  useAddTag,
  useContact,
  useUpdateContact,
  type ContactDetail,
  type ContactStatus,
  type ContactType,
} from "@/features/contacts/queries";

const TYPE_VALUES: ContactType[] = [
  "lead",
  "client",
  "supplier",
  "internal",
  "unknown",
  "blocked",
];
const STATUS_VALUES: ContactStatus[] = [
  "active",
  "inactive",
  "blocked",
  "archived",
];

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-12 w-12 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <Skeleton className="h-40 w-full rounded-xl" />
      <Skeleton className="h-40 w-full rounded-xl" />
    </div>
  );
}

function ProfileCard({ contact }: { contact: ContactDetail }) {
  const update = useUpdateContact(contact.id);
  const [type, setType] = useState<ContactType>(contact.type);
  const [status, setStatus] = useState<ContactStatus>(contact.status);
  const [summary, setSummary] = useState(contact.summary ?? "");

  useEffect(() => {
    setType(contact.type);
    setStatus(contact.status);
    setSummary(contact.summary ?? "");
  }, [contact.type, contact.status, contact.summary]);

  const dirty =
    type !== contact.type ||
    status !== contact.status ||
    summary !== (contact.summary ?? "");

  async function save() {
    try {
      await update.mutateAsync({ type, status, summary });
      toast.success("Contacto actualizado");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo guardar",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Perfil</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Tipo" htmlFor="d-type">
            <Select
              id="d-type"
              value={type}
              onChange={(e) => setType(e.target.value as ContactType)}
            >
              {TYPE_VALUES.map((t) => (
                <option key={t} value={t}>
                  {CONTACT_TYPE_LABELS[t]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Estado" htmlFor="d-status">
            <Select
              id="d-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as ContactStatus)}
            >
              {STATUS_VALUES.map((s) => (
                <option key={s} value={s}>
                  {CONTACT_STATUS_LABELS[s]}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Resumen" htmlFor="d-summary">
          <Textarea
            id="d-summary"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Notas de contexto sobre este contacto."
          />
        </Field>
        <div className="flex justify-end">
          <Button onClick={save} loading={update.isPending} disabled={!dirty}>
            Guardar cambios
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ChannelsCard({ contact }: { contact: ContactDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Canales</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Teléfonos
          </p>
          {contact.phones.length === 0 ? (
            <p className="text-sm text-muted">Sin teléfonos.</p>
          ) : (
            contact.phones.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2"
              >
                <span className="inline-flex items-center gap-2 text-sm text-foreground">
                  <Phone className="h-4 w-4 text-muted" />
                  {p.phone_e164}
                </span>
                <div className="flex items-center gap-1.5">
                  {p.is_whatsapp && <Badge tone="success">WhatsApp</Badge>}
                  {p.is_primary && <Badge tone="primary">Principal</Badge>}
                </div>
              </div>
            ))
          )}
        </div>
        <div className="space-y-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Emails
          </p>
          {contact.emails.length === 0 ? (
            <p className="text-sm text-muted">Sin emails.</p>
          ) : (
            contact.emails.map((e) => (
              <div
                key={e.id}
                className="flex items-center justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2"
              >
                <span className="inline-flex items-center gap-2 truncate text-sm text-foreground">
                  <AtSign className="h-4 w-4 shrink-0 text-muted" />
                  {e.email}
                </span>
                {e.is_primary && <Badge tone="primary">Principal</Badge>}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CompanyCard({ contact }: { contact: ContactDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Empresa</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {contact.companies.length === 0 && !contact.company_name ? (
          <p className="text-sm text-muted">Sin empresa asociada.</p>
        ) : contact.companies.length === 0 ? (
          <div className="inline-flex items-center gap-2 text-sm text-foreground">
            <Building2 className="h-4 w-4 text-muted" />
            {contact.company_name}
          </div>
        ) : (
          contact.companies.map((link) => (
            <div
              key={link.id}
              className="flex items-start justify-between rounded-lg border border-border bg-bg-subtle px-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="inline-flex items-center gap-2 text-sm font-medium text-foreground">
                  <Building2 className="h-4 w-4 text-muted" />
                  {link.company.name}
                </p>
                {(link.title || link.role) && (
                  <p className="mt-0.5 text-xs text-muted">
                    {[link.title, link.role].filter(Boolean).join(" · ")}
                  </p>
                )}
                {link.company.industry && (
                  <p className="text-xs text-muted">{link.company.industry}</p>
                )}
              </div>
              {link.is_primary && <Badge tone="primary">Principal</Badge>}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function TagsCard({ contact }: { contact: ContactDetail }) {
  const addTag = useAddTag(contact.id);
  const [name, setName] = useState("");

  async function submit() {
    const value = name.trim();
    if (!value) return;
    try {
      await addTag.mutateAsync({ name: value });
      setName("");
      toast.success("Etiqueta agregada");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo agregar la etiqueta",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Etiquetas</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {contact.tags.length === 0 ? (
          <p className="text-sm text-muted">Sin etiquetas todavía.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {contact.tags.map((t) => (
              <Badge key={t.id} tone="info" dot>
                <Tag className="h-3 w-3" />
                {t.name}
              </Badge>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void submit();
              }
            }}
            placeholder="Nueva etiqueta…"
          />
          <Button
            type="button"
            variant="secondary"
            onClick={submit}
            loading={addTag.isPending}
            leftIcon={<Plus className="h-4 w-4" />}
          >
            Agregar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function NoteCard({ contact }: { contact: ContactDetail }) {
  const addNote = useAddNote(contact.id);
  const [body, setBody] = useState("");

  async function submit() {
    const value = body.trim();
    if (!value) return;
    try {
      await addNote.mutateAsync({ body: value });
      setBody("");
      toast.success("Nota agregada");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo agregar la nota",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agregar nota</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escribí una nota interna sobre este contacto…"
        />
        <div className="flex justify-end">
          <Button
            type="button"
            onClick={submit}
            loading={addNote.isPending}
            disabled={!body.trim()}
            leftIcon={<MessageSquarePlus className="h-4 w-4" />}
          >
            Guardar nota
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ContactDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: contact, isLoading, isError } = useContact(id);

  const name =
    contact?.display_name ||
    contact?.company_name ||
    contact?.primary_phone ||
    "Sin nombre";

  return (
    <PageContainer className="max-w-5xl">
      <BackLink href="/contacts" label="Contactos" />

      {isLoading ? (
        <DetailSkeleton />
      ) : isError || !contact ? (
        <EmptyState
          icon={Users}
          title="No se encontró el contacto"
          description="Puede que haya sido eliminado o que no tengas acceso."
        />
      ) : (
        <>
          <div className="flex items-center gap-3">
            <Avatar name={name} seed={contact.id} size="lg" />
            <div className="min-w-0">
              <h1 className="truncate font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
                {name}
              </h1>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <Badge tone={typeTone(contact.type)}>
                  {CONTACT_TYPE_LABELS[contact.type]}
                </Badge>
                <Badge tone={statusTone(contact.status)} dot>
                  {CONTACT_STATUS_LABELS[contact.status]}
                </Badge>
                <span className="text-xs text-muted">
                  {CONTACT_SOURCE_LABELS[contact.source]} · creado{" "}
                  {shortDateTime(contact.created_at)}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <ProfileCard contact={contact} />
              <ChannelsCard contact={contact} />
            </div>
            <div className="space-y-4">
              <CompanyCard contact={contact} />
              <TagsCard contact={contact} />
              <NoteCard contact={contact} />
            </div>
          </div>
        </>
      )}
    </PageContainer>
  );
}
