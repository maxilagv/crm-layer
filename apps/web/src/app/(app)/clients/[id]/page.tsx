"use client";

import { Briefcase, Plus, UserPlus, Users } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
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
import { Field, Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { BackLink } from "@/components/shell/back-link";
import { PageContainer } from "@/components/shell/page-container";
import {
  CLIENT_CONTACT_ROLE_LABELS,
  CLIENT_STATUS_LABELS,
  clientStatusTone,
  ONBOARDING_STATUS_LABELS,
  onboardingTone,
  SERVICE_STATUS_LABELS,
  SERVICE_TYPE_LABELS,
  serviceStatusTone,
  SUPPORT_LEVEL_LABELS,
  supportLevelTone,
  useAddClientContact,
  useAddClientService,
  useClient,
  useContactPicker,
  useUpdateClient,
  type ClientContactRole,
  type ClientDetail,
  type ClientStatus,
  type ServiceStatus,
  type ServiceType,
} from "@/features/clients/queries";
import { ApiError } from "@/lib/api/types";
import { relativeTime, shortDateTime } from "@/lib/format";

const STATUSES: ClientStatus[] = [
  "active",
  "onboarding",
  "paused",
  "delinquent",
  "cancelled",
  "archived",
];

const CONTACT_ROLES: ClientContactRole[] = [
  "owner",
  "admin",
  "technical",
  "billing",
  "user",
  "other",
];

const SERVICE_TYPES: ServiceType[] = [
  "crm",
  "automation",
  "whatsapp",
  "web",
  "integration",
  "support",
  "consulting",
  "other",
];

const SERVICE_STATUSES: ServiceStatus[] = [
  "active",
  "paused",
  "pending",
  "completed",
  "cancelled",
];

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="flex gap-4">
          <Skeleton className="h-11 w-11 rounded-full" />
          <div className="flex-1 space-y-2 py-1">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-24 rounded-full" />
        </div>
      </Card>
      <Skeleton className="h-40 w-full rounded-xl" />
      <Skeleton className="h-40 w-full rounded-xl" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Overview + status changer                                           */
/* ------------------------------------------------------------------ */

function OverviewCard({ client }: { client: ClientDetail }) {
  const update = useUpdateClient(client.id);
  const name = client.display_name || "Cliente";

  async function changeStatus(status: ClientStatus) {
    if (status === client.status) return;
    try {
      await update.mutateAsync({ status });
      toast.success(`Estado: ${CLIENT_STATUS_LABELS[status]}`);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo cambiar el estado",
      );
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4">
        <div className="flex items-start gap-4">
          <Avatar name={name} seed={client.id} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="truncate font-display text-xl font-semibold tracking-tight text-foreground">
              {name}
            </h1>
            <p className="text-sm text-muted">
              Alta {relativeTime(client.created_at)}
              {client.service_plan ? ` · ${client.service_plan}` : ""}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={clientStatusTone(client.status)} dot>
            {CLIENT_STATUS_LABELS[client.status]}
          </Badge>
          <Badge tone={supportLevelTone(client.support_level)}>
            {SUPPORT_LEVEL_LABELS[client.support_level]}
          </Badge>
          <Badge tone={onboardingTone(client.onboarding_status)}>
            Onboarding: {ONBOARDING_STATUS_LABELS[client.onboarding_status]}
          </Badge>
        </div>

        <Separator />

        <Field
          label="Cambiar estado"
          htmlFor="client-status"
          hint="Actualiza el ciclo de vida de la cuenta."
        >
          <Select
            id="client-status"
            value={client.status}
            disabled={update.isPending}
            onChange={(e) => changeStatus(e.target.value as ClientStatus)}
            className="sm:max-w-xs"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {CLIENT_STATUS_LABELS[s]}
              </option>
            ))}
          </Select>
        </Field>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Linked contacts                                                     */
/* ------------------------------------------------------------------ */

function AddContactModal({
  clientId,
  open,
  onClose,
}: {
  clientId: string;
  open: boolean;
  onClose: () => void;
}) {
  const add = useAddClientContact(clientId);
  const [search, setSearch] = useState("");
  const [contactId, setContactId] = useState("");
  const [role, setRole] = useState<ClientContactRole>("user");
  const [isPrimary, setIsPrimary] = useState(false);
  const [canRequestSupport, setCanRequestSupport] = useState(true);
  const [receivesNotifications, setReceivesNotifications] = useState(false);
  const { data, isLoading } = useContactPicker(search);

  function reset() {
    setSearch("");
    setContactId("");
    setRole("user");
    setIsPrimary(false);
    setCanRequestSupport(true);
    setReceivesNotifications(false);
  }

  function close() {
    reset();
    onClose();
  }

  async function submit() {
    if (!contactId) {
      toast.error("Elegí un contacto");
      return;
    }
    try {
      await add.mutateAsync({
        contact_id: contactId,
        role,
        is_primary: isPrimary,
        can_request_support: canRequestSupport,
        receives_notifications: receivesNotifications,
      });
      toast.success("Contacto vinculado");
      close();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo vincular",
      );
    }
  }

  const contacts = data?.items ?? [];

  return (
    <Modal
      open={open}
      onClose={close}
      title="Vincular contacto"
      description="Sumá una persona a esta cuenta de cliente."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={close}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={add.isPending}>
            Vincular
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Buscar contacto" htmlFor="add-contact-search">
          <Input
            id="add-contact-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Nombre o teléfono…"
          />
        </Field>
        <Field label="Contacto" required>
          <div className="max-h-44 space-y-1 overflow-y-auto rounded-lg border border-border p-1">
            {isLoading ? (
              <div className="space-y-1 p-1">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-md" />
                ))}
              </div>
            ) : contacts.length === 0 ? (
              <p className="px-2 py-6 text-center text-sm text-muted">
                Sin contactos para esa búsqueda.
              </p>
            ) : (
              contacts.map((c) => {
                const cname = c.display_name || c.primary_phone || "Sin nombre";
                const selected = c.id === contactId;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setContactId(c.id)}
                    className={
                      "flex w-full cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors " +
                      (selected
                        ? "bg-primary/12 ring-1 ring-inset ring-primary/30"
                        : "hover:bg-card-hover")
                    }
                  >
                    <Avatar name={cname} seed={c.id} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-foreground">{cname}</p>
                      {c.primary_phone && (
                        <p className="truncate text-xs text-muted">
                          {c.primary_phone}
                        </p>
                      )}
                    </div>
                    {selected && (
                      <Badge tone="primary" className="shrink-0">
                        Elegido
                      </Badge>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </Field>
        <Field label="Rol" htmlFor="add-contact-role">
          <Select
            id="add-contact-role"
            value={role}
            onChange={(e) => setRole(e.target.value as ClientContactRole)}
          >
            {CONTACT_ROLES.map((r) => (
              <option key={r} value={r}>
                {CLIENT_CONTACT_ROLE_LABELS[r]}
              </option>
            ))}
          </Select>
        </Field>
        <div className="space-y-3 rounded-lg border border-border px-3 py-3">
          <label className="flex cursor-pointer items-center justify-between gap-3">
            <span className="text-sm text-foreground">Contacto principal</span>
            <Switch
              checked={isPrimary}
              onCheckedChange={setIsPrimary}
              aria-label="Contacto principal"
            />
          </label>
          <label className="flex cursor-pointer items-center justify-between gap-3">
            <span className="text-sm text-foreground">Puede pedir soporte</span>
            <Switch
              checked={canRequestSupport}
              onCheckedChange={setCanRequestSupport}
              aria-label="Puede pedir soporte"
            />
          </label>
          <label className="flex cursor-pointer items-center justify-between gap-3">
            <span className="text-sm text-foreground">Recibe notificaciones</span>
            <Switch
              checked={receivesNotifications}
              onCheckedChange={setReceivesNotifications}
              aria-label="Recibe notificaciones"
            />
          </label>
        </div>
      </div>
    </Modal>
  );
}

function ContactsCard({ client }: { client: ClientDetail }) {
  const [open, setOpen] = useState(false);
  const links = client.client_contacts;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Contactos vinculados</CardTitle>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setOpen(true)}
          leftIcon={<UserPlus className="h-4 w-4" />}
        >
          Vincular
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        {links.length === 0 ? (
          <EmptyState
            icon={Users}
            title="Sin contactos vinculados"
            description="Sumá personas para gestionar soporte y notificaciones."
          />
        ) : (
          links.map((link) => {
            const cname = link.contact_display_name || "Sin nombre";
            return (
              <div
                key={link.id}
                className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5"
              >
                <Avatar name={cname} seed={link.contact_id} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {cname}
                  </p>
                  <p className="text-xs text-muted">
                    {CLIENT_CONTACT_ROLE_LABELS[link.role]}
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-1.5">
                  {link.is_primary && <Badge tone="primary">Principal</Badge>}
                  {link.can_request_support && (
                    <Badge tone="info">Soporte</Badge>
                  )}
                  {link.receives_notifications && (
                    <Badge tone="muted">Notifica</Badge>
                  )}
                </div>
              </div>
            );
          })
        )}
      </CardContent>
      <AddContactModal
        clientId={client.id}
        open={open}
        onClose={() => setOpen(false)}
      />
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Services                                                            */
/* ------------------------------------------------------------------ */

function AddServiceModal({
  clientId,
  open,
  onClose,
}: {
  clientId: string;
  open: boolean;
  onClose: () => void;
}) {
  const add = useAddClientService(clientId);
  const [name, setName] = useState("");
  const [serviceType, setServiceType] = useState<ServiceType>("other");
  const [status, setStatus] = useState<ServiceStatus>("active");

  function reset() {
    setName("");
    setServiceType("other");
    setStatus("active");
  }

  function close() {
    reset();
    onClose();
  }

  async function submit() {
    if (!name.trim()) {
      toast.error("Poné un nombre al servicio");
      return;
    }
    try {
      await add.mutateAsync({
        name: name.trim(),
        service_type: serviceType,
        status,
      });
      toast.success("Servicio agregado");
      close();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo agregar",
      );
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Agregar servicio"
      description="Registrá un servicio contratado por el cliente."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={close}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} loading={add.isPending}>
            Agregar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Nombre" htmlFor="add-service-name" required>
          <Input
            id="add-service-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej. CRM + automatización"
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Tipo" htmlFor="add-service-type">
            <Select
              id="add-service-type"
              value={serviceType}
              onChange={(e) => setServiceType(e.target.value as ServiceType)}
            >
              {SERVICE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {SERVICE_TYPE_LABELS[t]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Estado" htmlFor="add-service-status">
            <Select
              id="add-service-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as ServiceStatus)}
            >
              {SERVICE_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {SERVICE_STATUS_LABELS[s]}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </div>
    </Modal>
  );
}

function ServicesCard({ client }: { client: ClientDetail }) {
  const [open, setOpen] = useState(false);
  const services = client.services;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Servicios</CardTitle>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setOpen(true)}
          leftIcon={<Plus className="h-4 w-4" />}
        >
          Agregar
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        {services.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="Sin servicios"
            description="Agregá los servicios contratados por este cliente."
          />
        ) : (
          services.map((svc) => (
            <div
              key={svc.id}
              className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {svc.name}
                </p>
                <p className="text-xs text-muted">
                  {SERVICE_TYPE_LABELS[svc.service_type]}
                  {svc.started_at
                    ? ` · desde ${shortDateTime(svc.started_at)}`
                    : ""}
                </p>
              </div>
              <Badge tone={serviceStatusTone(svc.status)} dot>
                {SERVICE_STATUS_LABELS[svc.status]}
              </Badge>
            </div>
          ))
        )}
      </CardContent>
      <AddServiceModal
        clientId={client.id}
        open={open}
        onClose={() => setOpen(false)}
      />
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: client, isLoading, isError } = useClient(id);

  return (
    <PageContainer className="max-w-3xl">
      <BackLink href="/clients" label="Clientes" />
      {isLoading ? (
        <DetailSkeleton />
      ) : isError || !client ? (
        <EmptyState
          icon={Users}
          title="No se pudo cargar el cliente"
          description="Puede que no exista o que haya un problema de conexión."
        />
      ) : (
        <div className="space-y-4">
          <OverviewCard client={client} />
          <ContactsCard client={client} />
          <ServicesCard client={client} />
        </div>
      )}
    </PageContainer>
  );
}
