"use client";

import { Plus, Search, ShieldCheck, Users as UsersIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Segmented, type SegmentedOption } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  statusLabel,
  statusTone,
  USER_ROLE_LABELS,
  USER_ROLE_OPTIONS,
  useCreateUser,
  useUpdateUser,
  useUsers,
  type UserPublic,
  type UserRole,
} from "@/features/settings/users-queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";
import { relativeTime } from "@/lib/format";

type StatusFilter = "all" | "active" | "inactive";

const STATUS_OPTIONS: SegmentedOption<StatusFilter>[] = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "inactive", label: "Inactivos" },
];

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-xl border border-border px-3 py-3"
        >
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function UserRow({ user }: { user: UserPublic }) {
  const update = useUpdateUser();

  async function toggleActive(next: boolean) {
    try {
      await update.mutateAsync({ id: user.id, is_active: next });
      toast.success(next ? "Usuario activado" : "Usuario desactivado");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo actualizar",
      );
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border px-3 py-3 transition-colors hover:bg-card-hover">
      <Avatar name={user.name} seed={user.id} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-medium text-foreground">
            {user.name || user.email}
          </p>
          <Badge tone={statusTone(user.is_active)} dot>
            {statusLabel(user.is_active)}
          </Badge>
          {user.is_superuser ? (
            <Badge tone="primary">
              <ShieldCheck className="h-3 w-3" />
              Owner
            </Badge>
          ) : user.is_staff ? (
            <Badge tone="info">Staff</Badge>
          ) : null}
        </div>
        <p className="truncate text-xs text-muted">{user.email}</p>
        {user.last_login_at && (
          <p className="text-[11px] text-muted">
            Último acceso {relativeTime(user.last_login_at)}
          </p>
        )}
      </div>
      <Switch
        checked={user.is_active}
        onCheckedChange={toggleActive}
        disabled={update.isPending}
        aria-label={`${user.is_active ? "Desactivar" : "Activar"} ${user.name || user.email}`}
      />
    </div>
  );
}

interface CreateForm {
  email: string;
  name: string;
  password: string;
  role: UserRole;
}

const EMPTY_FORM: CreateForm = {
  email: "",
  name: "",
  password: "",
  role: "viewer",
};

function CreateUserModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateUser();
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM);

  const set = <K extends keyof CreateForm>(key: K, value: CreateForm[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  function close() {
    setForm(EMPTY_FORM);
    onClose();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await create.mutateAsync({
        email: form.email.trim(),
        name: form.name.trim(),
        password: form.password,
        role: form.role,
      });
      toast.success("Usuario creado");
      close();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo crear el usuario",
      );
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Nuevo usuario"
      description="Creá una cuenta para un miembro del equipo."
      footer={
        <>
          <Button type="button" variant="secondary" onClick={close}>
            Cancelar
          </Button>
          <Button type="submit" form="create-user-form" loading={create.isPending}>
            Crear usuario
          </Button>
        </>
      }
    >
      <form id="create-user-form" onSubmit={submit} className="space-y-4">
        <Field label="Nombre" htmlFor="user-name">
          <Input
            id="user-name"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Ada Lovelace"
            required
          />
        </Field>
        <Field label="Email" htmlFor="user-email">
          <Input
            id="user-email"
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="ada@empresa.com"
            required
          />
        </Field>
        <Field
          label="Contraseña"
          htmlFor="user-password"
          hint="Mínimo 8 caracteres."
        >
          <Input
            id="user-password"
            type="password"
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            minLength={8}
            required
          />
        </Field>
        <Field label="Rol" htmlFor="user-role">
          <Select
            id="user-role"
            value={form.role}
            onChange={(e) => set("role", e.target.value as UserRole)}
          >
            {USER_ROLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
      </form>
    </Modal>
  );
}

export default function UsersSettingsPage() {
  const { data, isLoading, isError } = useUsers();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [createOpen, setCreateOpen] = useState(false);

  const users = useMemo(() => {
    const items = data?.items ?? [];
    const q = search.trim().toLowerCase();
    return items.filter((u) => {
      if (status === "active" && !u.is_active) return false;
      if (status === "inactive" && u.is_active) return false;
      if (!q) return true;
      return (
        u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
      );
    });
  }, [data, search, status]);

  return (
    <SettingsShell
      title="Usuarios"
      description="Miembros del equipo, roles y estado."
    >
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={() => setCreateOpen(true)}
          leftIcon={<Plus className="h-4 w-4" />}
        >
          Nuevo usuario
        </Button>
      </div>

      <Card>
        <CardContent className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative sm:flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nombre o email…"
                className="pl-9"
              />
            </div>
            <Segmented
              options={STATUS_OPTIONS}
              value={status}
              onChange={setStatus}
            />
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <EmptyState
              icon={UsersIcon}
              title="No se pudieron cargar"
              description="Revisá la conexión con el backend."
            />
          ) : users.length === 0 ? (
            <EmptyState
              icon={UsersIcon}
              title={search || status !== "all" ? "Sin resultados" : "Sin usuarios"}
              description={
                search || status !== "all"
                  ? "Probá con otro filtro o búsqueda."
                  : "Creá el primer usuario del equipo."
              }
              action={
                search || status !== "all" ? undefined : (
                  <Button
                    type="button"
                    onClick={() => setCreateOpen(true)}
                    leftIcon={<Plus className="h-4 w-4" />}
                  >
                    Nuevo usuario
                  </Button>
                )
              }
            />
          ) : (
            <div className="space-y-2">
              {users.map((u) => (
                <UserRow key={u.id} user={u} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted">
        El rol se asigna al crear el usuario. Roles disponibles:{" "}
        {USER_ROLE_OPTIONS.map((o) => USER_ROLE_LABELS[o.value]).join(" · ")}.
      </p>

      <CreateUserModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </SettingsShell>
  );
}
