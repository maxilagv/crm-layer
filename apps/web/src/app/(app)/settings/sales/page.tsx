"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input, Textarea } from "@/components/ui/field";
import { ListEditor } from "@/components/ui/list-editor";
import { Switch } from "@/components/ui/switch";
import { salesPolicy, type SalesPolicy } from "@/features/settings/queries";
import { SettingsShell } from "@/features/settings/settings-shell";
import { ApiError } from "@/lib/api/types";

export default function SalesSettingsPage() {
  const { data, isLoading } = salesPolicy.useRead();
  const update = salesPolicy.useUpdate();
  const [form, setForm] = useState<Partial<SalesPolicy>>({});
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);
  const set = <K extends keyof SalesPolicy>(k: K, v: SalesPolicy[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await update.mutateAsync({
        main_sales_goal: form.main_sales_goal,
        call_to_action: form.call_to_action,
        can_quote_prices: form.can_quote_prices,
        price_min: form.price_min,
        price_max: form.price_max,
        price_policy_text: form.price_policy_text,
        must_handoff_for_price: form.must_handoff_for_price,
        common_objections: form.common_objections,
        forbidden_claims: form.forbidden_claims,
        sales_tone: form.sales_tone,
      });
      toast.success("Política de ventas guardada");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.firstFieldError || err.message : "No se pudo guardar",
      );
    }
  }

  return (
    <SettingsShell
      title="Política de ventas"
      description="Cómo vende el agente: objetivo, precios y límites."
      loading={isLoading}
    >
      <form onSubmit={save} className="space-y-4">
        <Card>
          <CardContent className="space-y-4">
            <Field label="Objetivo principal de ventas" htmlFor="goal">
              <Input
                id="goal"
                value={form.main_sales_goal ?? ""}
                onChange={(e) => set("main_sales_goal", e.target.value)}
              />
            </Field>
            <Field label="Llamado a la acción" htmlFor="cta">
              <Input
                id="cta"
                value={form.call_to_action ?? ""}
                onChange={(e) => set("call_to_action", e.target.value)}
              />
            </Field>
            <Field label="Tono de ventas" htmlFor="tone">
              <Input
                id="tone"
                value={form.sales_tone ?? ""}
                onChange={(e) => set("sales_tone", e.target.value)}
              />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-foreground">Puede cotizar precios</p>
              <Switch
                checked={!!form.can_quote_prices}
                onCheckedChange={(v) => set("can_quote_prices", v)}
                aria-label="Puede cotizar precios"
              />
            </div>
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-foreground">
                Derivar a humano para precio
              </p>
              <Switch
                checked={!!form.must_handoff_for_price}
                onCheckedChange={(v) => set("must_handoff_for_price", v)}
                aria-label="Derivar para precio"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Precio mínimo" htmlFor="pmin">
                <Input
                  id="pmin"
                  value={form.price_min ?? ""}
                  onChange={(e) => set("price_min", e.target.value)}
                  placeholder="0.00"
                />
              </Field>
              <Field label="Precio máximo" htmlFor="pmax">
                <Input
                  id="pmax"
                  value={form.price_max ?? ""}
                  onChange={(e) => set("price_max", e.target.value)}
                  placeholder="0.00"
                />
              </Field>
            </div>
            <Field label="Política de precios (texto)" htmlFor="ppolicy">
              <Textarea
                id="ppolicy"
                value={form.price_policy_text ?? ""}
                onChange={(e) => set("price_policy_text", e.target.value)}
              />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <Field label="Objeciones comunes">
              <ListEditor
                value={form.common_objections ?? []}
                onChange={(v) => set("common_objections", v)}
              />
            </Field>
            <Field label="Claims prohibidos" hint="Lo que el agente nunca debe afirmar.">
              <ListEditor
                value={form.forbidden_claims ?? []}
                onChange={(v) => set("forbidden_claims", v)}
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
