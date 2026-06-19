"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { ApiError } from "@/lib/api/types";
import {
  CONTACT_TYPE_LABELS,
  useCreateContact,
  type ContactType,
} from "./queries";

const TYPE_VALUES: ContactType[] = [
  "lead",
  "client",
  "supplier",
  "internal",
  "unknown",
];

export function CreateContactModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const create = useCreateContact();
  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [type, setType] = useState<ContactType>("lead");

  function reset() {
    setDisplayName("");
    setPhone("");
    setEmail("");
    setType("lead");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!displayName.trim() && !phone.trim() && !email.trim()) {
      toast.error("Ingresá al menos nombre, teléfono o email");
      return;
    }
    try {
      const contact = await create.mutateAsync({
        display_name: displayName.trim() || undefined,
        type,
        phones: phone.trim()
          ? [{ phone: phone.trim(), is_primary: true }]
          : undefined,
        emails: email.trim()
          ? [{ email: email.trim(), is_primary: true }]
          : undefined,
      });
      toast.success("Contacto creado");
      reset();
      onClose();
      router.push(`/contacts/${contact.id}`);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo crear el contacto",
      );
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Nuevo contacto"
      description="Cargá los datos básicos. Después podés completar el resto."
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="create-contact-form"
            loading={create.isPending}
          >
            Crear contacto
          </Button>
        </>
      }
    >
      <form id="create-contact-form" onSubmit={submit} className="space-y-4">
        <Field label="Nombre a mostrar" htmlFor="ct-name">
          <Input
            id="ct-name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Juana Pérez"
            autoFocus
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Teléfono" htmlFor="ct-phone" hint="Formato internacional">
            <Input
              id="ct-phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+54 9 11 5555-5555"
            />
          </Field>
          <Field label="Email" htmlFor="ct-email">
            <Input
              id="ct-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="juana@correo.com"
            />
          </Field>
        </div>
        <Field label="Tipo" htmlFor="ct-type">
          <Select
            id="ct-type"
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
      </form>
    </Modal>
  );
}
