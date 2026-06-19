from django.db import models


class DocumentType(models.TextChoices):
    PROPOSAL = "proposal", "Propuesta"
    QUOTE = "quote", "Presupuesto"
    INVOICE = "invoice", "Factura"
    REPORT = "report", "Informe"
    DECK = "deck", "Presentación"


class DocumentFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    XLSX = "xlsx", "Excel"
    PPTX = "pptx", "PowerPoint"


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    READY = "ready", "Listo"
    SENT = "sent", "Enviado"
    FAILED = "failed", "Falló"


DOCUMENT_TYPE_LABELS: dict[str, str] = {
    DocumentType.PROPOSAL.value: "Propuesta",
    DocumentType.QUOTE.value: "Presupuesto",
    DocumentType.INVOICE.value: "Factura",
    DocumentType.REPORT.value: "Informe",
    DocumentType.DECK.value: "Presentación",
}

# Document types that carry priced line items / totals.
ITEMIZED_TYPES = {DocumentType.QUOTE.value, DocumentType.INVOICE.value, DocumentType.PROPOSAL.value}

MIME_BY_FORMAT: dict[str, str] = {
    DocumentFormat.PDF.value: "application/pdf",
    DocumentFormat.XLSX.value: (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    DocumentFormat.PPTX.value: (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
}

EXT_BY_FORMAT: dict[str, str] = {
    DocumentFormat.PDF.value: "pdf",
    DocumentFormat.XLSX.value: "xlsx",
    DocumentFormat.PPTX.value: "pptx",
}
