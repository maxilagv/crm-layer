from django.db import transaction

from crm.audit.services import audit_event_create
from crm.whatsapp.clients.template_client import TemplateClient
from crm.whatsapp.domain.enums import WhatsAppTemplateCategory, WhatsAppTemplateStatus
from crm.whatsapp.models import WhatsAppBusinessAccount, WhatsAppTemplate


def _normal_choice(value: str, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").lower()
    return normalized if normalized in allowed else fallback


@transaction.atomic
def sync_templates_for_organization(*, organization, client: TemplateClient | None = None) -> int:
    client = client or TemplateClient()
    category_values = {choice.value for choice in WhatsAppTemplateCategory}
    status_values = {choice.value for choice in WhatsAppTemplateStatus}
    synced = 0
    for account in WhatsAppBusinessAccount.objects.filter(organization_id=organization.id):
        for item in client.list_templates(waba_id=account.waba_id):
            name = str(item.get("name") or "")
            language = str(item.get("language") or "")
            if not name or not language:
                continue
            WhatsAppTemplate.objects.update_or_create(
                organization_id=organization.id,
                name=name,
                language=language,
                defaults={
                    "category": _normal_choice(
                        item.get("category"),
                        category_values,
                        WhatsAppTemplateCategory.UTILITY.value,
                    ),
                    "status": _normal_choice(
                        item.get("status"),
                        status_values,
                        WhatsAppTemplateStatus.PENDING.value,
                    ),
                    "components": item.get("components") or [],
                    "metadata": {"source": "meta", "waba_id": account.waba_id},
                },
            )
            synced += 1
    return synced


def audit_template_sync_failed(*, organization, error: Exception) -> None:
    audit_event_create(
        event_type="whatsapp_template_sync_failed",
        organization=organization,
        metadata={"error": str(error)[:500]},
    )
