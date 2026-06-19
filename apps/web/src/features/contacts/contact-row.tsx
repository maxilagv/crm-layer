"use client";

import { Phone } from "lucide-react";
import Link from "next/link";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  CONTACT_STATUS_LABELS,
  CONTACT_TYPE_LABELS,
  statusTone,
  typeTone,
  type ContactListItem,
} from "./queries";

export function ContactRow({ c }: { c: ContactListItem }) {
  const name =
    c.display_name || c.company_name || c.primary_phone || "Sin nombre";

  return (
    <Link
      href={`/contacts/${c.id}`}
      className="flex cursor-pointer items-center gap-3 px-4 py-3 transition-colors hover:bg-card-hover"
    >
      <Avatar name={name} seed={c.id} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {name}
          </span>
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-[13px] text-muted">
          {c.primary_phone ? (
            <span className="inline-flex items-center gap-1 truncate">
              <Phone className="h-3 w-3 shrink-0" />
              {c.primary_phone}
            </span>
          ) : c.primary_email ? (
            <span className="truncate">{c.primary_email}</span>
          ) : (
            <span className="text-muted/70">Sin contacto</span>
          )}
        </div>
      </div>
      <div className="hidden shrink-0 items-center gap-1.5 sm:flex">
        <Badge tone={typeTone(c.type)}>{CONTACT_TYPE_LABELS[c.type]}</Badge>
        {c.status !== "active" && (
          <Badge tone={statusTone(c.status)} dot>
            {CONTACT_STATUS_LABELS[c.status]}
          </Badge>
        )}
      </div>
    </Link>
  );
}
