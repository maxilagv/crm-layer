"""AI qualification for Cazador prospects."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.prospecting.domain import events
from crm.prospecting.domain.enums import ProspectStatus
from crm.prospecting.models import Prospect

# Don't re-run the qualification AI call on a prospect already scored within this
# window (protects against duplicate calls from retries / re-triggers). Pass
# force=True for an explicit re-qualify.
_QUALIFY_TTL_HOURS = 168  # 7 days


class ProspectQualificationService:
    @staticmethod
    def qualify(*, prospect: Prospect, actor=None, request=None, force: bool = False) -> Prospect:
        if (
            not force
            and prospect.qualified_at is not None
            and prospect.status != ProspectStatus.FAILED.value
        ):
            age_hours = (timezone.now() - prospect.qualified_at).total_seconds() / 3600
            if age_hours < _QUALIFY_TTL_HOURS:
                return prospect

        result = AIGateway.qualify_prospect(
            prospect_id=prospect.id,
            actor=actor,
            http_request=request,
            metadata={"source": "prospecting_qualification"},
        )
        if not result.succeeded or not result.data:
            return ProspectQualificationService._mark_failed(
                prospect=prospect,
                error=result.error_code or result.error_message or "ai_qualification_failed",
                ai_run_id=result.run_id,
                actor=actor,
                request=request,
            )

        data = result.data
        fit_score = int(data["fit_score"])
        status = (
            ProspectStatus.QUALIFIED.value
            if fit_score >= prospect.campaign.min_fit_score
            else ProspectStatus.DISQUALIFIED.value
        )
        with transaction.atomic():
            locked = (
                Prospect.objects.select_for_update()
                .select_related("campaign")
                .get(id=prospect.id, organization_id=prospect.organization_id)
            )
            before_status = locked.status
            locked.fit_score = fit_score
            locked.signals = list(data.get("signals") or [])
            locked.reasoning = str(data.get("reasoning") or "")
            locked.recommended_angle = str(data.get("recommended_angle") or "")
            locked.ai_run_id = result.run_id
            locked.qualified_at = timezone.now()
            locked.status = status
            locked.error_message = ""
            locked.updated_by_id = getattr(actor, "id", None)
            locked.save(
                update_fields=[
                    "fit_score",
                    "signals",
                    "reasoning",
                    "recommended_angle",
                    "ai_run_id",
                    "qualified_at",
                    "status",
                    "error_message",
                    "updated_by_id",
                    "updated_at",
                ]
            )
            _refresh_qualified_count(campaign_id=locked.campaign_id)
            event_type = (
                events.PROSPECT_QUALIFIED
                if status == ProspectStatus.QUALIFIED.value
                else events.PROSPECT_DISQUALIFIED
            )
            create_outbox_event(
                event_type=event_type,
                organization_id=locked.organization_id,
                payload={
                    "prospect_id": str(locked.id),
                    "campaign_id": str(locked.campaign_id),
                    "fit_score": locked.fit_score,
                    "status": locked.status,
                    "ai_run_id": str(result.run_id or ""),
                },
            )
            audit_event_create(
                event_type="prospect_qualified",
                actor=actor,
                organization=_org_stub(locked.organization_id),
                request=request,
                resource_type="prospecting_prospect",
                resource_id=str(locked.id),
                changes={"status": {"before": before_status, "after": locked.status}},
                metadata={"fit_score": locked.fit_score, "ai_run_id": str(result.run_id or "")},
            )
            return locked

    @staticmethod
    @transaction.atomic
    def _mark_failed(*, prospect: Prospect, error: str, ai_run_id=None, actor=None, request=None):
        locked = Prospect.objects.select_for_update().get(
            id=prospect.id, organization_id=prospect.organization_id
        )
        before_status = locked.status
        locked.status = ProspectStatus.FAILED.value
        locked.ai_run_id = ai_run_id
        locked.error_message = str(error)[:500]
        locked.updated_by_id = getattr(actor, "id", None)
        locked.save(
            update_fields=[
                "status",
                "ai_run_id",
                "error_message",
                "updated_by_id",
                "updated_at",
            ]
        )
        _refresh_qualified_count(campaign_id=locked.campaign_id)
        create_outbox_event(
            event_type=events.PROSPECT_QUALIFICATION_FAILED,
            organization_id=locked.organization_id,
            payload={
                "prospect_id": str(locked.id),
                "campaign_id": str(locked.campaign_id),
                "error": locked.error_message,
                "ai_run_id": str(ai_run_id or ""),
            },
        )
        audit_event_create(
            event_type="prospect_qualification_failed",
            actor=actor,
            organization=_org_stub(locked.organization_id),
            request=request,
            resource_type="prospecting_prospect",
            resource_id=str(locked.id),
            changes={"status": {"before": before_status, "after": locked.status}},
            metadata={"error": locked.error_message, "ai_run_id": str(ai_run_id or "")},
        )
        return locked


def _refresh_qualified_count(*, campaign_id) -> None:
    from crm.prospecting.models import ProspectingCampaign

    count = Prospect.objects.filter(
        campaign_id=campaign_id,
        status=ProspectStatus.QUALIFIED.value,
        deleted_at__isnull=True,
    ).count()
    ProspectingCampaign.objects.filter(id=campaign_id).update(
        qualified_count=count,
        updated_at=timezone.now(),
    )


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
