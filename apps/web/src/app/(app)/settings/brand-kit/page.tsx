"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { brandKit, type BrandKit } from "@/features/documents/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";

const EMPTY: Partial<BrandKit> = {
  business_name: "",
  legal_name: "",
  tax_id: "",
  email: "",
  phone: "",
  website: "",
  address: "",
  primary_color: "#7C6CFF",
  accent_color: "#22C55E",
  text_color: "#16161D",
  currency: "ARS",
  default_tax_rate: "21",
  default_terms: "",
  footer_note: "",
};

function ColorField({
  label,
  value,
  fallback,
  onChange,
}: {
  label: string;
  value?: string;
  fallback: string;
  onChange: (v: string) => void;
}) {
  return (
    <Field label={label}>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={label}
          value={value || fallback}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-12 shrink-0 cursor-pointer rounded-lg border border-border bg-input p-1"
        />
        <Input
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={fallback}
          className="font-mono"
        />
      </div>
    </Field>
  );
}

export default function BrandKitSettingsPage() {
  const { data, isLoading } = brandKit.useRead();
  const update = brandKit.useUpdate();
  const [form, setForm] = useState<Partial<BrandKit>>(EMPTY);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const set = <K extends keyof BrandKit>(key: K, value: BrandKit[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        business_name: form.business_name,
        legal_name: form.legal_name,
        tax_id: form.tax_id,
        email: form.email,
        phone: form.phone,
        website: form.website,
        address: form.address,
        primary_color: form.primary_color,
        accent_color: form.accent_color,
        text_color: form.text_color,
        currency: form.currency,
        default_tax_rate: form.default_tax_rate,
        default_terms: form.default_terms,
        footer_note: form.footer_note,
      });
      toast.success("Kit de marca guardado");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <SettingsShell
      title="Kit de marca"
      description="Identidad visual y datos fiscales que llevan tus propuestas, presupuestos e informes."
      loading={isLoading}
    >
      <form onSubmit={save} className="space-y-4">
        <Card>
          <CardContent className="space-y-4">
            <Field label="Nombre comercial" htmlFor="bk-name">
              <Input
                id="bk-name"
                value={form.business_name ?? ""}
                onChange={(e) => set("business_name", e.target.value)}
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Razón social" htmlFor="bk-legal">
                <Input
                  id="bk-legal"
                  value={form.legal_name ?? ""}
                  onChange={(e) => set("legal_name", e.target.value)}
                />
              </Field>
              <Field label="CUIT / ID fiscal" htmlFor="bk-tax">
                <Input
                  id="bk-tax"
                  value={form.tax_id ?? ""}
                  onChange={(e) => set("tax_id", e.target.value)}
                />
              </Field>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Email" htmlFor="bk-email">
                <Input
                  id="bk-email"
                  type="email"
                  value={form.email ?? ""}
                  onChange={(e) => set("email", e.target.value)}
                />
              </Field>
              <Field label="Teléfono" htmlFor="bk-phone">
                <Input
                  id="bk-phone"
                  value={form.phone ?? ""}
                  onChange={(e) => set("phone", e.target.value)}
                />
              </Field>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Sitio web" htmlFor="bk-web">
                <Input
                  id="bk-web"
                  value={form.website ?? ""}
                  onChange={(e) => set("website", e.target.value)}
                  placeholder="miestudio.com"
                />
              </Field>
              <Field label="Dirección" htmlFor="bk-addr">
                <Input
                  id="bk-addr"
                  value={form.address ?? ""}
                  onChange={(e) => set("address", e.target.value)}
                />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <p className="text-sm font-medium text-foreground">Colores</p>
            <div className="grid gap-4 sm:grid-cols-3">
              <ColorField
                label="Primario"
                value={form.primary_color}
                fallback="#7C6CFF"
                onChange={(v) => set("primary_color", v)}
              />
              <ColorField
                label="Acento"
                value={form.accent_color}
                fallback="#22C55E"
                onChange={(v) => set("accent_color", v)}
              />
              <ColorField
                label="Texto"
                value={form.text_color}
                fallback="#16161D"
                onChange={(v) => set("text_color", v)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Moneda" htmlFor="bk-currency">
                <Select
                  id="bk-currency"
                  value={form.currency ?? "ARS"}
                  onChange={(e) => set("currency", e.target.value)}
                >
                  <option value="ARS">ARS — Peso argentino</option>
                  <option value="USD">USD — Dólar</option>
                  <option value="EUR">EUR — Euro</option>
                </Select>
              </Field>
              <Field
                label="Impuesto por defecto (%)"
                htmlFor="bk-tax-rate"
                hint="Se aplica a presupuestos y propuestas con ítems."
              >
                <Input
                  id="bk-tax-rate"
                  inputMode="decimal"
                  value={form.default_tax_rate ?? ""}
                  onChange={(e) => set("default_tax_rate", e.target.value)}
                  placeholder="21"
                />
              </Field>
            </div>
            <Field label="Condiciones por defecto" htmlFor="bk-terms">
              <Textarea
                id="bk-terms"
                value={form.default_terms ?? ""}
                onChange={(e) => set("default_terms", e.target.value)}
                placeholder="Forma de pago, validez, etc."
              />
            </Field>
            <Field label="Nota de pie" htmlFor="bk-footer" hint="Aparece al pie de cada documento.">
              <Input
                id="bk-footer"
                value={form.footer_note ?? ""}
                onChange={(e) => set("footer_note", e.target.value)}
                placeholder="Gracias por confiar en nosotros."
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
