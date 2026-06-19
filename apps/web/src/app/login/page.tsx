"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/shell/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { ApiError } from "@/lib/api/types";
import { useLogin } from "@/lib/auth/session";
import { useAuthStore } from "@/lib/auth/store";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hydrated && accessToken) router.replace("/inbox");
  }, [hydrated, accessToken, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.replace("/inbox");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "request_throttled")
          setError("Demasiados intentos. Esperá unos minutos e intentá de nuevo.");
        else if (err.code === "authentication_failed" || err.status === 401)
          setError("Email o contraseña incorrectos.");
        else setError(err.message);
      } else {
        setError("No se pudo conectar con el servidor. ¿Está corriendo el backend?");
      }
    }
  }

  return (
    <div className="relative flex min-h-dvh bg-bg">
      <div className="absolute right-4 top-4 z-10">
        <ThemeToggle />
      </div>

      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden border-r border-border bg-bg-subtle p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0 bg-glow-radial" />
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-[0.4] [mask-image:radial-gradient(60%_60%_at_50%_30%,black,transparent)]" />
        <div className="relative">
          <Logo />
        </div>
        <div className="relative space-y-4">
          <h2 className="max-w-md font-display text-3xl font-semibold leading-tight tracking-tight text-foreground text-balance">
            Tu bot de WhatsApp con IA, bajo control total.
          </h2>
          <p className="max-w-md text-sm leading-relaxed text-muted">
            Conversaciones, leads, soporte y tareas en un solo lugar. La IA
            responde; vos decidís cuándo tomar el control.
          </p>
        </div>
        <p className="relative text-xs text-muted">
          AI CRM · panel operativo privado
        </p>
      </div>

      {/* Form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Iniciar sesión
          </h1>
          <p className="mt-1 text-sm text-muted">
            Ingresá con tu cuenta para administrar el CRM.
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <Field label="Email" htmlFor="email">
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="vos@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </Field>
            <Field label="Contraseña" htmlFor="password">
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Field>

            {error && (
              <div className="animate-fade-in rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              size="lg"
              loading={login.isPending}
              rightIcon={<ArrowRight className="h-4 w-4" />}
            >
              Entrar
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
