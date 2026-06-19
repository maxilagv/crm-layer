"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BackLink } from "@/components/shell/back-link";
import { PageContainer } from "@/components/shell/page-container";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useOrganization,
  useUpdateOrganization,
} from "@/features/settings/queries";
import { ApiError } from "@/lib/api/types";

const TIMEZONES = [
  "America/Argentina/Buenos_Aires",
  "America/Mexico_City",
  "America/Santiago",
  "America/Bogota",
  "America/Lima",
  "America/Montevideo",
  "America/Sao_Paulo",
  "Europe/Madrid",
  "UTC",
];

const LANGUAGES = [
  { value: "es", label: "Español" },
  { value: "en", label: "Inglés" },
  { value: "pt", label: "Portugués" },
];

export default function OrganizationSettingsPage() {
  const { data, isLoading } = useOrganization();
  const update = useUpdateOrganization();
  const [name, setName] = useState("");
  const [tz, setTz] = useState("");
  const [lang, setLang] = useState("es");

  useEffect(() => {
    if (data) {
      setName(data.name);
      setTz(data.default_timezone);
      setLang(data.default_language);
    }
  }, [data]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        name,
        default_timezone: tz,
        default_language: lang,
      });
      toast.success("Cambios guardados");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? err.firstFieldError || err.message
          : "No se pudo guardar",
      );
    }
  }

  return (
    <PageContainer className="max-w-2xl">
      <BackLink href="/settings" label="Configuración" />
      <h1 className="font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
        Organización
      </h1>
      <p className="mt-1 text-sm text-muted">
        Datos generales de tu organización.
      </p>

      {isLoading ? (
        <div className="mt-6 space-y-4">
          <Skeleton className="h-44 w-full rounded-xl" />
        </div>
      ) : (
        <form onSubmit={save} className="mt-6">
          <Card>
            <CardContent className="space-y-4">
              <Field label="Nombre" htmlFor="org-name">
                <Input
                  id="org-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </Field>
              <Field label="Zona horaria" htmlFor="org-tz">
                <Select
                  id="org-tz"
                  value={tz}
                  onChange={(e) => setTz(e.target.value)}
                >
                  {tz && !TIMEZONES.includes(tz) && (
                    <option value={tz}>{tz}</option>
                  )}
                  {TIMEZONES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Idioma por defecto" htmlFor="org-lang">
                <Select
                  id="org-lang"
                  value={lang}
                  onChange={(e) => setLang(e.target.value)}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </Select>
              </Field>
              {data && (
                <div className="flex flex-wrap gap-x-6 gap-y-1 border-t border-border pt-4 text-xs text-muted">
                  <span>
                    Plan: <span className="text-foreground">{data.plan}</span>
                  </span>
                  <span>
                    Estado:{" "}
                    <span className="text-foreground">{data.status}</span>
                  </span>
                  <span>
                    Slug:{" "}
                    <span className="font-mono text-foreground">
                      {data.slug}
                    </span>
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
          <div className="mt-4 flex justify-end">
            <Button type="submit" loading={update.isPending}>
              Guardar cambios
            </Button>
          </div>
        </form>
      )}
    </PageContainer>
  );
}
