from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.audit.services import audit_event_create
from crm.conversations.models import Conversation
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain import events
from crm.leads.domain.enums import (
    LeadStage,
    StageChangedByType,
)
from crm.leads.domain.rules import score_from_factors, score_text_signals, temperature_for_score
from crm.leads.domain.value_objects import LeadScoreResult
from crm.leads.models import Lead, LeadScoreSnapshot

from .lead_lifecycle import change_stage

_URGENCY_POINTS = {"critical": 15, "high": 15, "medium": 10, "low": 4, "unknown": 2}
_AUTHORITY_POINTS = {
    "decision_maker": 15,
    "likely_decision_maker": 12,
    "influencer": 7,
    "unknown": 2,
}
_BUDGET_POINTS = {"confirmed": 10, "high": 10, "medium": 7, "low": 3, "unknown": 2, "none": 0}
_FIT_POINTS = {"high": 20, "medium": 12, "low": 4}
_TECH_POINTS = {"high": 10, "medium": 6, "low": 2}


def _conversation_for_lead(lead: Lead, conversation=None) -> Conversation | None:
    if conversation is not None:
        return conversation
    return (
        Conversation.objects.filter(organization_id=lead.organization_id, contact=lead.contact)
        .order_by("-last_message_at", "-created_at")
        .first()
    )


def _conversation_text(conversation: Conversation | None) -> tuple[str, int]:
    if conversation is None:
        return "", 0
    messages = list(conversation.messages.order_by("-created_at")[:20])
    return " ".join(message.body or "" for message in messages), len(messages)


def deterministic_factors_for_lead(lead: Lead, *, conversation=None) -> dict[str, int]:
    text, message_count = _conversation_text(_conversation_for_lead(lead, conversation))
    return score_text_signals(text, message_count=message_count).as_factors()


def _ai_factors(data: dict, *, message_count: int) -> dict[str, int]:
    return {
        "pain_clear": 20 if data.get("pain_points") else 5,
        "urgency": _URGENCY_POINTS.get(str(data.get("urgency", "unknown")), 2),
        "authority": _AUTHORITY_POINTS.get(str(data.get("authority_signal", "unknown")), 2),
        "budget_signal": _BUDGET_POINTS.get(str(data.get("budget_signal", "unknown")), 2),
        "business_fit": _FIT_POINTS.get(str(data.get("business_fit", "low")), 4),
        "engagement": min(10, max(1, message_count * 2)),
        "technical_match": _TECH_POINTS.get(str(data.get("technical_match", "low")), 2),
        "risk_penalty": min(20, int(data.get("risk_penalty") or 0)),
    }


def _stage_for_score(score: int, current_stage: str) -> str:
    if current_stage in {LeadStage.WON.value, LeadStage.LOST.value, LeadStage.UNQUALIFIED.value}:
        return current_stage
    if score >= 76:
        return LeadStage.HOT.value
    if score >= 56:
        return LeadStage.WARM.value
    if score >= 31:
        return LeadStage.QUALIFYING.value
    return current_stage or LeadStage.NEW.value


@transaction.atomic
def _apply_score(
    *,
    lead: Lead,
    factors: dict[str, int],
    reasoning_summary: str,
    ai_run_id=None,
    ai_data: dict | None = None,
    actor=None,
    request=None,
) -> LeadScoreResult:
    lead = Lead.objects.select_for_update().get(id=lead.id)
    score = score_from_factors(factors)
    temperature = temperature_for_score(score)
    ai_data = ai_data or {}

    lead.score = score
    lead.temperature = temperature
    lead.last_scored_at = timezone.now()
    lead.budget_signal = ai_data.get("budget_signal") or lead.budget_signal
    lead.urgency = ai_data.get("urgency") or lead.urgency
    lead.authority_signal = ai_data.get("authority_signal") or lead.authority_signal
    lead.pain_points = ai_data.get("pain_points") or lead.pain_points
    lead.next_best_action = ai_data.get("next_best_action") or lead.next_best_action
    if reasoning_summary:
        lead.summary = reasoning_summary[:4000]
    lead.save(
        update_fields=[
            "score",
            "temperature",
            "last_scored_at",
            "budget_signal",
            "urgency",
            "authority_signal",
            "pain_points",
            "next_best_action",
            "summary",
            "updated_at",
        ]
    )
    snapshot = LeadScoreSnapshot.objects.create(
        organization_id=lead.organization_id,
        lead=lead,
        score=score,
        temperature=temperature,
        reasoning_summary=reasoning_summary[:4000],
        factors=factors,
        ai_run_id=ai_run_id,
    )
    next_stage = _stage_for_score(score, lead.stage)
    if next_stage != lead.stage:
        lead = change_stage(
            lead=lead,
            to_stage=next_stage,
            reason="score_recalculated",
            changed_by_type=StageChangedByType.AI_AGENT.value
            if ai_run_id
            else StageChangedByType.SYSTEM.value,
            actor=actor,
            ai_run_id=ai_run_id,
            request=request,
        )
    create_outbox_event(
        event_type=events.LEAD_SCORED,
        organization_id=lead.organization_id,
        payload={
            "lead_id": str(lead.id),
            "score": score,
            "temperature": temperature,
            "snapshot_id": str(snapshot.id),
        },
    )
    audit_event_create(
        event_type="lead_scored",
        actor=actor,
        organization=_org_stub(lead.organization_id),
        request=request,
        resource_type="lead",
        resource_id=str(lead.id),
        metadata={"score": score, "temperature": temperature, "ai_run_id": str(ai_run_id or "")},
    )
    return LeadScoreResult(
        lead=lead,
        snapshot=snapshot,
        updated=True,
        ai_run_id=ai_run_id,
        reason="scored",
    )


def score_lead(
    *,
    lead: Lead,
    conversation=None,
    use_ai: bool = True,
    actor=None,
    request=None,
    metadata: dict | None = None,
) -> LeadScoreResult:
    conversation = _conversation_for_lead(lead, conversation)
    text, message_count = _conversation_text(conversation)
    if use_ai and conversation is not None:
        result = AIGateway.score_lead(
            conversation_id=conversation.id,
            lead_id=lead.id,
            actor=actor,
            metadata=metadata or {},
        )
        if not result.succeeded or not result.data:
            return LeadScoreResult(
                lead=lead,
                snapshot=None,
                updated=False,
                ai_run_id=result.run_id,
                reason=result.error_code or "ai_scoring_failed",
            )
        factors = _ai_factors(result.data, message_count=message_count)
        return _apply_score(
            lead=lead,
            factors=factors,
            reasoning_summary=str(result.data.get("reasoning_summary") or ""),
            ai_run_id=result.run_id,
            ai_data=result.data,
            actor=actor,
            request=request,
        )

    factors = score_text_signals(text, message_count=message_count).as_factors()
    return _apply_score(
        lead=lead,
        factors=factors,
        reasoning_summary="Scoring deterministico basado en historial conversacional.",
        actor=actor,
        request=request,
    )


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
