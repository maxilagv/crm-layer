"use client";

import { Download, FileSpreadsheet, FileText, Presentation } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, type BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api/client";
import { ApiError } from "@/lib/api/types";
import { relativeTime } from "@/lib/format";
import { fetchDocumentDownload, type GeneratedDocument } from "./queries";

const TYPE_LABELS: Record<string, string> = {
  proposal: "Propuesta",
  quote: "Presupuesto",
  invoice: "Factura",
  report: "Informe",
  deck: "Presentación",
};

const STATUS_META: Record<string, { label: string; tone: BadgeTone }> = {
  draft: { label: "Borrador", tone: "muted" },
  ready: { label: "Listo", tone: "info" },
  sent: { label: "Enviado", tone: "success" },
  failed: { label: "Falló", tone: "danger" },
};

const FORMAT_ICON: Record<string, typeof FileText> = {
  pdf: FileText,
  xlsx: FileSpreadsheet,
  pptx: Presentation,
};

export function DocumentRow({ doc }: { doc: GeneratedDocument }) {
  const [downloading, setDownloading] = useState(false);
  const Icon = FORMAT_ICON[doc.doc_format] ?? FileText;
  const status = STATUS_META[doc.status] ?? STATUS_META.ready;

  async function download() {
    setDownloading(true);
    try {
      const dl = await fetchDocumentDownload(doc.id);
      const href = dl.url.startsWith("http") ? dl.url : `${API_BASE}${dl.url}`;
      window.open(href, "_blank", "noopener");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo generar la descarga");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex items-center gap-3 border-b border-border px-4 py-3 last:border-0">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{doc.title}</p>
        <p className="mt-0.5 flex items-center gap-2 text-xs text-muted">
          <span>{TYPE_LABELS[doc.doc_type] ?? "Documento"}</span>
          <span aria-hidden>·</span>
          <span className="uppercase">{doc.doc_format}</span>
          <span aria-hidden>·</span>
          <span>{relativeTime(doc.created_at)}</span>
        </p>
      </div>
      <Badge tone={status.tone}>{status.label}</Badge>
      <Button
        variant="secondary"
        size="sm"
        onClick={download}
        loading={downloading}
        disabled={!doc.media_asset_id}
        leftIcon={<Download className="h-4 w-4" />}
      >
        Descargar
      </Button>
    </div>
  );
}
