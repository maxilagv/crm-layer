import { MessageSquare } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function InboxIndexPage() {
  return (
    <div className="hidden flex-1 items-center justify-center p-6 md:flex">
      <EmptyState
        icon={MessageSquare}
        title="Elegí una conversación"
        description="Seleccioná un chat de la lista para ver el historial y responder."
      />
    </div>
  );
}
