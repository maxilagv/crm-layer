"""generate_document tool: the agent builds a draft document for owner review."""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.tools.base import BaseTool, ToolContext, ToolDefinition
from crm.ai.tools.responses import ok
from crm.core.security.permissions import PermissionCode

from .domain.enums import DocumentFormat, DocumentStatus, DocumentType


class GenerateDocumentTool(BaseTool):
    definition = ToolDefinition(
        name="generate_document",
        version="1",
        description=(
            "Genera un documento (propuesta, presupuesto, factura o informe) en PDF, Excel o "
            "PowerPoint a partir de datos estructurados. Queda como BORRADOR para que el dueño "
            "lo revise y envíe; nunca se envía solo."
        ),
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["doc_type", "format", "payload"],
            "properties": {
                "doc_type": {"type": "string", "enum": [t.value for t in DocumentType]},
                "format": {"type": "string", "enum": [f.value for f in DocumentFormat]},
                "payload": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "subtitle": {"type": "string"},
                        "intro": {"type": "string"},
                        "client": {"type": "object"},
                        "sections": {"type": "array", "items": {"type": "object"}},
                        "items": {"type": "array", "items": {"type": "object"}},
                        "currency": {"type": "string"},
                        "tax_rate": {"type": ["number", "string"]},
                        "notes": {"type": "string"},
                        "terms": {"type": "string"},
                        "valid_until": {"type": "string"},
                    },
                },
            },
        },
        permissions_required=(PermissionCode.CONTACTS_UPDATE.value,),
        allowed_purposes=(
            AIPurpose.ASSISTANT_REPLY.value,
            AIPurpose.SALES_REPLY.value,
            AIPurpose.SUPPORT_REPLY.value,
        ),
        side_effects="Crea un GeneratedDocument en estado borrador (no se envía solo).",
        audit_event="ai_tool_generate_document",
        risk_level=RiskLevel.MEDIUM.value,
        requires_human_approval=False,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        from crm.organizations.models import Organization

        from .services.document_service import DocumentService

        organization = Organization.objects.get(id=context.organization_id)
        doc = DocumentService.generate(
            organization=organization,
            doc_type=arguments["doc_type"],
            fmt=arguments["format"],
            payload=arguments.get("payload") or {},
            actor=context.actor,
            status=DocumentStatus.DRAFT.value,
            references={
                "conversation_id": context.conversation_id,
                "contact_id": context.contact_id,
                "ai_run_id": getattr(context.ai_run, "id", None),
            },
        )
        return ok(
            document_id=str(doc.id),
            title=doc.title,
            doc_type=doc.doc_type,
            format=doc.doc_format,
            status=doc.status,
        )
