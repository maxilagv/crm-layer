"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input, Textarea } from "@/components/ui/field";
import { ListEditor } from "@/components/ui/list-editor";
import { businessProfile, type BusinessProfile } from "@/features/settings/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";

const EMPTY: Partial<BusinessProfile> = {
  business_name: "",
  owner_name: "",
  owner_phone: "",
  brand_tone: "",
  business_description: "",
  services_offered: [],
  target_clients: [],
  calendar_link: "",
  website_url: "",
  owner_writing_style: "",
  signature_phrases: [],
};

export default function BusinessSettingsPage() {
  const { data, isLoading } = businessProfile.useRead();
  const update = businessProfile.useUpdate();
  const [form, setForm] = useState<Partial<BusinessProfile>>(EMPTY);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const set = <K extends keyof BusinessProfile>(key: K, value: BusinessProfile[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        business_name: form.business_name,
        owner_name: form.owner_name,
        owner_phone: form.owner_phone,
        brand_tone: form.brand_tone,
        business_description: form.business_description,
        services_offered: form.services_offered,
        target_clients: form.target_clients,
        calendar_link: form.calendar_link,
        website_url: form.website_url,
        owner_writing_style: form.owner_writing_style,
        signature_phrases: form.signature_phrases,
      });
      toast.success("Perfil guardado");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <SettingsShell
      title="Perfil de negocio"
      description="Lo que define el contexto y el tono del agente de IA."
      loading={isLoading}
    >
      <form onSubmit={save} className="space-y-4">
        <Card>
          <CardContent className="space-y-4">
            <Field label="Nombre del negocio" htmlFor="biz-name">
              <Input
                id="biz-name"
                value={form.business_name ?? ""}
                onChange={(e) => set("business_name", e.target.value)}
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Responsable" htmlFor="biz-owner">
                <Input
                  id="biz-owner"
                  value={form.owner_name ?? ""}
                  onChange={(e) => set("owner_name", e.target.value)}
                />
              </Field>
              <Field label="Teléfono del responsable" htmlFor="biz-phone">
                <Input
                  id="biz-phone"
                  value={form.owner_phone ?? ""}
                  onChange={(e) => set("owner_phone", e.target.value)}
                />
              </Field>
            </div>
            <Field
              label="Tono de marca"
              htmlFor="biz-tone"
              hint="Cómo querés que suene el agente: cercano, profesional, directo…"
            >
              <Input
                id="biz-tone"
                value={form.brand_tone ?? ""}
                onChange={(e) => set("brand_tone", e.target.value)}
              />
            </Field>
            <Field label="Descripción del negocio" htmlFor="biz-desc">
              <Textarea
                id="biz-desc"
                value={form.business_description ?? ""}
                onChange={(e) => set("business_description", e.target.value)}
                placeholder="Qué hacés, a quién ayudás y cómo."
              />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <Field label="Servicios que ofrecés">
              <ListEditor
                value={form.services_offered ?? []}
                onChange={(v) => set("services_offered", v)}
                placeholder="Agregar servicio y Enter…"
              />
            </Field>
            <Field label="Clientes objetivo">
              <ListEditor
                value={form.target_clients ?? []}
                onChange={(v) => set("target_clients", v)}
                placeholder="Agregar perfil de cliente y Enter…"
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Link de agenda" htmlFor="biz-cal">
                <Input
                  id="biz-cal"
                  value={form.calendar_link ?? ""}
                  onChange={(e) => set("calendar_link", e.target.value)}
                  placeholder="https://cal.com/…"
                />
              </Field>
              <Field label="Sitio web" htmlFor="biz-web">
                <Input
                  id="biz-web"
                  value={form.website_url ?? ""}
                  onChange={(e) => set("website_url", e.target.value)}
                  placeholder="https://…"
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-foreground">Tu estilo</p>
              <p className="mt-0.5 text-xs text-muted">
                Cómo escribís vos. El agente lo usa para sonar como vos en ventas, soporte y
                propuestas.
              </p>
            </div>
            <Field
              label="Cómo escribís"
              htmlFor="biz-style"
              hint="Ej: directo y cálido, sin vueltas; tuteo rioplatense; cero formalismos."
            >
              <Textarea
                id="biz-style"
                value={form.owner_writing_style ?? ""}
                onChange={(e) => set("owner_writing_style", e.target.value)}
                placeholder="Describí tu tono y tu forma de escribir…"
              />
            </Field>
            <Field label="Frases típicas tuyas" hint="Muletillas o frases que usás seguido.">
              <ListEditor
                value={form.signature_phrases ?? []}
                onChange={(v) => set("signature_phrases", v)}
                placeholder="Agregar frase y Enter…"
              />
            </Field>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" loading={update.isPending}>
            Guardar cambios
          </Button>
        </div>
      </form>
    </SettingsShell>
  );
}
