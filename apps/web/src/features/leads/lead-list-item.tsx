import Link from "next/link";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { relativeTime } from "@/lib/format";
import {
  LEAD_STAGE_LABELS,
  LEAD_TEMPERATURE_LABELS,
  type LeadListItem,
  scoreTone,
  stageTone,
  temperatureTone,
} from "./queries";

export function LeadListRow({ lead }: { lead: LeadListItem }) {
  const name = lead.contact.display_name || "Sin nombre";

  return (
    <Link
      href={`/leads/${lead.id}`}
      className="flex cursor-pointer items-start gap-3 border-b border-border/60 px-4 py-3.5 transition-colors hover:bg-card-hover"
    >
      <Avatar name={name} seed={lead.contact.id} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {name}
          </span>
          <span className="shrink-0 text-[11px] text-muted">
            {relativeTime(lead.updated_at)}
          </span>
        </div>
        {(lead.contact.company_name || lead.service_interest) && (
          <p className="mt-0.5 truncate text-[13px] text-muted">
            {[lead.contact.company_name, lead.service_interest]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <Badge tone={stageTone(lead.stage)} dot>
            {LEAD_STAGE_LABELS[lead.stage]}
          </Badge>
          <Badge tone={temperatureTone(lead.temperature)}>
            {LEAD_TEMPERATURE_LABELS[lead.temperature]}
          </Badge>
          <Badge tone={scoreTone(lead.score)}>Score {lead.score}</Badge>
        </div>
      </div>
    </Link>
  );
}
