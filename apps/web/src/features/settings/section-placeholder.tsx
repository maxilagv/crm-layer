import { Construction } from "lucide-react";
import { BackLink } from "@/components/shell/back-link";
import { PageContainer } from "@/components/shell/page-container";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export function SettingsPlaceholder({
  title,
  description,
  note,
}: {
  title: string;
  description?: string;
  note?: string;
}) {
  return (
    <PageContainer className="max-w-2xl">
      <BackLink href="/settings" label="Configuración" />
      <PageHeader title={title} description={description} />
      <div className="mt-6">
        <EmptyState
          icon={Construction}
          title="Próximamente"
          description={
            note ??
            "Esta sección se conecta al backend; la construimos en el próximo paso."
          }
        />
      </div>
    </PageContainer>
  );
}
