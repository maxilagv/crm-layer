import { Construction } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageContainer } from "./page-container";

export function ComingSoon({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <PageContainer>
      <PageHeader title={title} description={description} />
      <div className="mt-6">
        <EmptyState
          icon={Construction}
          title="Próximamente"
          description="Este módulo ya está conectado al backend. Lo construimos en la próxima etapa del frontend."
        />
      </div>
    </PageContainer>
  );
}
