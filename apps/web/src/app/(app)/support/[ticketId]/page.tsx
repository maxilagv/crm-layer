"use client";

import { useParams } from "next/navigation";
import { PageContainer } from "@/components/shell/page-container";
import { TicketDetail } from "@/features/support/ticket-detail";

export default function TicketDetailPage() {
  const params = useParams();
  const ticketId = String(params.ticketId);
  return (
    <PageContainer className="max-w-5xl">
      <TicketDetail ticketId={ticketId} />
    </PageContainer>
  );
}
