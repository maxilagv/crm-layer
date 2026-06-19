from datetime import timedelta

from django.utils import timezone

from crm.leads.domain import policies
from crm.leads.models import Lead


def schedule_followup(
    *,
    lead: Lead,
    due_at=None,
    title: str = "Seguimiento comercial",
    notes: str = "",
    actor=None,
    idempotency_key: str = "",
):
    from crm.sales.services.followup_service import create_followup

    due_at = due_at or timezone.now() + timedelta(days=policies.DEFAULT_FOLLOWUP_DAYS)
    return create_followup(
        lead=lead,
        due_at=due_at,
        title=title,
        notes=notes,
        actor=actor,
        idempotency_key=idempotency_key,
    )
