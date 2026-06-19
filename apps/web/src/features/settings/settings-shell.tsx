"use client";

import { BackLink } from "@/components/shell/back-link";
import { PageContainer } from "@/components/shell/page-container";
import { Skeleton } from "@/components/ui/skeleton";

export function SettingsShell({
  title,
  description,
  loading,
  children,
}: {
  title: string;
  description?: string;
  loading?: boolean;
  children: React.ReactNode;
}) {
  return (
    <PageContainer className="max-w-2xl">
      <BackLink href="/settings" label="Configuración" />
      <h1 className="font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
        {title}
      </h1>
      {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      <div className="mt-6 space-y-4">
        {loading ? <Skeleton className="h-64 w-full rounded-xl" /> : children}
      </div>
    </PageContainer>
  );
}
