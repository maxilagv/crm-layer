"""Celery workers for the autonomous sales agent."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="prospecting.discover_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    ignore_result=True,
)
def discover_batch(self, *, campaign_id: str) -> int:
    """Discover prospects for a campaign via Google Places. Returns # created."""
    from crm.prospecting.models import ProspectingCampaign
    from crm.prospecting.services.apollo import ApolloError
    from crm.prospecting.services.discovery import ProspectDiscoveryService
    from crm.prospecting.services.google_places import GooglePlacesError

    try:
        campaign = ProspectingCampaign.objects.get(id=campaign_id)
        result = ProspectDiscoveryService.discover(campaign=campaign)
        logger.info(
            "Prospect discovery done",
            extra={
                "event": "prospecting.discover_batch",
                "metadata": {
                    "campaign_id": campaign_id,
                    "created": len(result.created),
                    "skipped": result.skipped,
                },
            },
        )
        return len(result.created)
    except ProspectingCampaign.DoesNotExist:
        return 0
    except ApolloError as exc:
        if exc.is_transient:
            raise self.retry(exc=exc, countdown=120) from exc
        logger.warning(
            "Discovery stopped on permanent Apollo error; not retrying",
            extra={"event": "prospecting.discover_batch", "metadata": {"error": str(exc)[:200]}},
        )
        return 0
    except GooglePlacesError as exc:
        # Quota (429), auth (401/403) and bad-request (400) are PERMANENT — retrying
        # only burns more of the daily quota. Only 5xx is worth a retry.
        if exc.is_transient:
            raise self.retry(exc=exc, countdown=120) from exc
        logger.warning(
            "Discovery stopped on permanent Places error; not retrying",
            extra={"event": "prospecting.discover_batch", "metadata": {"error": str(exc)[:200]}},
        )
        return 0
    except Exception as exc:  # noqa: BLE001 — transient infra (DB/network): retry
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(
    name="prospecting.enrich_prospect",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    ignore_result=True,
)
def enrich_prospect(self, *, prospect_id: str, then_qualify: bool = True) -> str:
    """Investigate a prospect (website + reviews + Places extras), then qualify it."""
    from crm.prospecting.models import Prospect
    from crm.prospecting.services.enrichment import ProspectEnrichmentService

    try:
        prospect = Prospect.objects.select_related("campaign").get(id=prospect_id)
    except Prospect.DoesNotExist:
        return ""
    try:
        ProspectEnrichmentService.enrich(prospect=prospect)
    except Exception:  # noqa: BLE001 — enrichment is best-effort; must never block qualification
        logger.warning(
            "Prospect enrichment failed",
            extra={
                "event": "prospecting.enrich_prospect",
                "metadata": {"prospect_id": prospect_id},
            },
        )
    if then_qualify:
        qualify_prospect.delay(prospect_id=prospect_id)
    return prospect_id


@shared_task(
    name="prospecting.qualify_prospect",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def qualify_prospect(self, *, prospect_id: str) -> str:
    """Run AI qualification for one prospect."""
    from crm.prospecting.models import Prospect
    from crm.prospecting.services.qualification import ProspectQualificationService

    try:
        prospect = Prospect.objects.select_related("campaign").get(id=prospect_id)
        qualified = ProspectQualificationService.qualify(prospect=prospect)
        logger.info(
            "Prospect qualification done",
            extra={
                "event": "prospecting.qualify_prospect",
                "metadata": {
                    "prospect_id": prospect_id,
                    "status": qualified.status,
                    "fit_score": qualified.fit_score,
                },
            },
        )
        return str(qualified.id)
    except Prospect.DoesNotExist:
        return ""
    except Exception as exc:  # noqa: BLE001 - retry transient AI/provider failures
        raise self.retry(exc=exc, countdown=30) from exc


@shared_task(name="prospecting.run_outreach", bind=True, max_retries=3, default_retry_delay=30)
def run_outreach(self, *, campaign_id: str, limit: int = 50) -> int:
    """Queue outreach openers for eligible prospects in a campaign."""
    from crm.prospecting.models import ProspectingCampaign
    from crm.prospecting.services.outreach import ProspectOutreachService

    try:
        campaign = ProspectingCampaign.objects.get(id=campaign_id)
        attempts = ProspectOutreachService.run_campaign(campaign=campaign, limit=limit)
        return sum(1 for attempt in attempts if attempt.queued)
    except ProspectingCampaign.DoesNotExist:
        return 0
    except Exception as exc:  # noqa: BLE001 - retry transient AI/provider failures
        raise self.retry(exc=exc, countdown=30) from exc


@shared_task(name="prospecting.run_followups", bind=True, max_retries=3, default_retry_delay=60)
def run_followups(self, *, limit: int = 100) -> int:
    """Queue due Cazador follow-ups for campaigns that opted in."""
    from crm.prospecting.services.conversation_engine import run_due_followups

    try:
        return run_due_followups(limit=limit)
    except Exception as exc:  # noqa: BLE001 - retry transient AI/provider failures
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(name="prospecting.interpret_reply", bind=True, max_retries=3, default_retry_delay=30)
def interpret_reply(self, *, conversation_id: str, message_id: str) -> str:
    """Classify an inbound reply for a prospect conversation."""
    from crm.conversations.models import Message
    from crm.organizations.models import Organization
    from crm.prospecting.services.replies import ProspectReplyInterpreter

    try:
        message = Message.objects.select_related("conversation__contact").get(
            id=message_id,
            conversation_id=conversation_id,
        )
        organization = Organization.objects.get(id=message.organization_id)
        result = ProspectReplyInterpreter.interpret_inbound(
            organization=organization,
            conversation=message.conversation,
            contact=message.contact,
            message=message,
        )
        return str(result.prospect.id) if result else ""
    except Message.DoesNotExist:
        return ""
    except Exception as exc:  # noqa: BLE001 - retry transient AI/provider failures
        raise self.retry(exc=exc, countdown=30) from exc
