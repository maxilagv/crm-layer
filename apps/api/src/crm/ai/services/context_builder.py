"""ContextBuilder: minimal, purpose-scoped context for prompts.

Hard rules: never include secrets/API keys/tokens, never include data from
other organizations' contacts, limit message volume, prefer summaries, and
redact obvious sensitive sequences. Everything returned here may end up inside
a prompt — treat it as outbound.
"""

from django.conf import settings
from django.utils import timezone

from crm.ai.domain.policies import SENSITIVE_DATA_PATTERNS
from crm.business_settings.models import (
    AIBehaviorPolicy,
    BusinessProfile,
    SalesPolicy,
    SupportPolicy,
)
from crm.conversations.selectors import messages_for_conversation
from crm.core.logging import sanitize

DEFAULT_MESSAGE_LIMIT = 20
_MAX_CHARS_PER_MESSAGE = 600

# Spanish labels for memory facts injected into prompts (Phase 9.1).
_MEMORY_LABELS = {
    "preference": "preferencia",
    "pain_point": "dolor",
    "technical_context": "contexto técnico",
    "commercial_context": "contexto comercial",
    "support_context": "contexto de soporte",
    "objection": "objeción",
    "commitment": "compromiso",
}


def redact_sensitive(text: str) -> str:
    for pattern in SENSITIVE_DATA_PATTERNS:
        text = pattern.sub("[REDACTADO]", text)
    return text


def _settings_for(model_class, organization_id):
    return model_class.objects.filter(organization_id=organization_id).first()


def _prospect_profile(prospect) -> dict:
    rating_raw = getattr(prospect, "rating", None)
    rating_value = None
    if rating_raw is not None and str(rating_raw).strip() != "":
        try:
            rating_value = float(rating_raw)
        except (TypeError, ValueError):
            rating_value = None
    profile = {
        "business_name": redact_sensitive(getattr(prospect, "business_name", "") or ""),
        "category": redact_sensitive(getattr(prospect, "category", "") or ""),
        "website_present": bool(getattr(prospect, "website", "") or ""),
        "website": redact_sensitive(getattr(prospect, "website", "") or ""),
        "reviews_count": int(getattr(prospect, "reviews_count", 0) or 0),
        "photos_count": int(getattr(prospect, "photos_count", 0) or 0),
        "rating": str(getattr(prospect, "rating", "") or ""),
        "rating_value": rating_value,
        "rating_present": rating_value is not None,
        "address": redact_sensitive(getattr(prospect, "address", "") or ""),
        "phone_present": bool(getattr(prospect, "phone", "") or ""),
    }
    investigation = _investigation_summary(prospect)
    if investigation:
        profile["investigation"] = investigation
    return profile


def _investigation_summary(prospect) -> dict:
    """Compact view of what the investigator step found (None until enriched)."""
    if getattr(prospect, "enriched_at", None) is None:
        return {}
    enrichment = getattr(prospect, "enrichment", None) or {}
    socials = enrichment.get("social_links") or {}
    pagespeed = enrichment.get("pagespeed") or {}
    summary = {
        "website_reachable": getattr(prospect, "website_reachable", None),
        "website_platform": getattr(prospect, "website_platform", "") or "",
        "mobile_friendly": enrichment.get("mobile_friendly"),
        "has_online_booking": getattr(prospect, "has_online_booking", None),
        "has_ecommerce": enrichment.get("has_ecommerce"),
        "has_instagram": bool(socials.get("instagram")),
        "has_facebook": bool(socials.get("facebook")),
        "latest_review_age_days": getattr(prospect, "latest_review_age_days", None),
        # PageSpeed mobile (0-100): low = slow site = strong, concrete pitch.
        "pagespeed_score": getattr(prospect, "pagespeed_score", None),
        "pagespeed_lcp_ms": pagespeed.get("lcp_ms"),
        "review_themes": enrichment.get("review_themes") or {},
        "editorial_summary": redact_sensitive((enrichment.get("editorial_summary") or "")[:300]),
        "owner_name": redact_sensitive(getattr(prospect, "owner_name", "") or ""),
        "owner_title": redact_sensitive(getattr(prospect, "owner_title", "") or ""),
        "owner_email_present": bool(getattr(prospect, "owner_email", "") or ""),
        "owner_email_score": getattr(prospect, "owner_email_score", None),
    }
    return {k: v for k, v in summary.items() if v not in (None, "", {}, [])}


class ContextBuilder:
    @staticmethod
    def _business(organization_id) -> dict:
        profile = _settings_for(BusinessProfile, organization_id)
        return {
            "business_name": getattr(profile, "business_name", "") or "el negocio",
            "services_offered": getattr(profile, "services_offered", []) or [],
        }

    @staticmethod
    def _owner_voice(organization_id) -> dict:
        """Compact 'how the owner writes' block so replies/documents sound like them."""
        profile = _settings_for(BusinessProfile, organization_id)
        style = (getattr(profile, "owner_writing_style", "") or "").strip()
        phrases = getattr(profile, "signature_phrases", None) or []
        parts = []
        if style:
            parts.append(style)
        sample = "; ".join(str(p).strip() for p in phrases[:5] if str(p).strip())
        if sample:
            parts.append(f"Frases típicas del dueño: {sample}.")
        voice = " ".join(parts).strip() or (
            "Tono natural, claro y profesional rioplatense; cercano sin ser informal de más."
        )
        return {"owner_voice": redact_sensitive(voice[:1200])}

    @staticmethod
    def _contact_memories(contact, organization_id, *, limit: int = 6) -> str:
        """Compact long-term memory block for a contact (top facts by importance)."""
        if contact is None:
            return "Sin datos previos del contacto."
        from crm.conversations.services import ConversationMemoryService

        memories = ConversationMemoryService.memories_for_contact(
            organization_id=organization_id, contact_id=contact.id, limit=limit
        )
        lines = [
            f"- ({_MEMORY_LABELS.get(m.memory_type, 'dato')}) "
            f"{redact_sensitive((m.content or '').strip())[:240]}"
            for m in memories
        ]
        return "\n".join(lines) if lines else "Sin datos previos del contacto."

    @staticmethod
    def _sales_policy(organization_id) -> dict:
        policy = _settings_for(SalesPolicy, organization_id)
        if policy is None:
            return {
                "can_quote_prices": False,
                "pricing_policy": "Sin política de precios configurada",
                "commercial_tone": "profesional y cercano",
            }
        pricing = "Sin política de precios configurada"
        if policy.can_quote_prices and policy.price_min is not None:
            pricing = f"Rango autorizado: {policy.price_min} a {policy.price_max}"
        return {
            "can_quote_prices": policy.can_quote_prices,
            "price_min": str(policy.price_min) if policy.price_min is not None else None,
            "price_max": str(policy.price_max) if policy.price_max is not None else None,
            "pricing_policy": pricing,
            "commercial_tone": getattr(policy, "main_sales_goal", "") or "profesional y cercano",
        }

    @staticmethod
    def _support_policy(organization_id) -> dict:
        policy = _settings_for(SupportPolicy, organization_id)
        return {
            "support_policy": getattr(policy, "support_hours", "") or "Sin política configurada",
            "support_hours": getattr(policy, "support_hours", "") or "no configurado",
            "urgent_keywords": getattr(policy, "urgent_keywords", []) or [],
        }

    @staticmethod
    def _message_limit(organization_id) -> int:
        policy = _settings_for(AIBehaviorPolicy, organization_id)
        return (
            getattr(policy, "max_context_messages", DEFAULT_MESSAGE_LIMIT) or DEFAULT_MESSAGE_LIMIT
        )

    @staticmethod
    def _recent_messages(conversation, limit: int) -> list[dict]:
        messages = list(messages_for_conversation(conversation).order_by("-created_at")[:limit])
        messages.reverse()
        return [
            {
                "direction": message.direction,
                "type": message.message_type,
                "text": redact_sensitive((message.body or "")[:_MAX_CHARS_PER_MESSAGE]),
                "at": message.created_at.isoformat(),
            }
            for message in messages
        ]

    @staticmethod
    def _contact_profile(contact) -> dict:
        return {
            "display_name": contact.display_name,
            "type": contact.type,
            "status": contact.status,
            "language": contact.language,
            "timezone": contact.timezone,
            "summary": redact_sensitive(contact.summary or ""),
        }

    # -- public builders -------------------------------------------------------

    @classmethod
    def for_sales_reply(cls, *, conversation, current_message) -> dict:
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        business = cls._business(organization_id)
        sales = cls._sales_policy(organization_id)
        context = {
            **business,
            **sales,
            **cls._owner_voice(organization_id),
            "lead_profile": cls._contact_profile(conversation.contact),
            "contact_memories": cls._contact_memories(conversation.contact, organization_id),
            "conversation_summary": redact_sensitive(conversation.summary or "Sin resumen previo"),
            "recent_messages": cls._recent_messages(conversation, limit),
            "current_message": redact_sensitive((current_message.body or "")[:2000]),
        }
        return sanitize(context)

    @classmethod
    def for_support_reply(
        cls, *, conversation, current_message, ticket_context: dict | None = None
    ) -> dict:
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        context = {
            **cls._business(organization_id),
            **cls._support_policy(organization_id),
            **cls._owner_voice(organization_id),
            "client_profile": cls._contact_profile(conversation.contact),
            "contact_memories": cls._contact_memories(conversation.contact, organization_id),
            "ticket_context": ticket_context or {"detail": "Sin ticket asociado"},
            "recent_messages": cls._recent_messages(conversation, limit),
            "current_message": redact_sensitive((current_message.body or "")[:2000]),
        }
        return sanitize(context)

    @classmethod
    def for_assistant_reply(cls, *, conversation, current_message) -> dict:
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        profile = _settings_for(BusinessProfile, organization_id)
        context = {
            **cls._business(organization_id),
            "owner_name": getattr(profile, "owner_name", "") or "vos",
            "conversation_summary": redact_sensitive(conversation.summary or "Sin resumen previo"),
            "recent_messages": cls._recent_messages(conversation, limit),
            "current_message": redact_sensitive((current_message.body or "")[:2000]),
        }
        return sanitize(context)

    @classmethod
    def for_document_draft(
        cls,
        *,
        organization_id,
        owner_request: str,
        doc_type: str,
        currency: str = "",
        tax_rate="",
        default_terms: str = "",
        client: dict | None = None,
    ) -> dict:
        """Context for drafting a business document from a free-text request."""
        from crm.documents.domain.enums import DOCUMENT_TYPE_LABELS

        profile = _settings_for(BusinessProfile, organization_id)
        client = client or {}
        client_parts = [f"{key}: {value}" for key, value in client.items() if value]
        client_block = "; ".join(client_parts) if client_parts else "Sin datos del cliente."
        context = {
            **cls._business(organization_id),
            **cls._owner_voice(organization_id),
            "owner_name": getattr(profile, "owner_name", "") or "el dueño",
            "doc_type_label": DOCUMENT_TYPE_LABELS.get(doc_type, "Documento"),
            "currency": currency or "",
            "default_tax_rate": str(tax_rate or "0"),
            "default_terms": default_terms or "",
            "client_block": redact_sensitive(client_block),
            "today": timezone.localtime().date().isoformat(),
            "owner_request": redact_sensitive((owner_request or "")[:4000]),
        }
        return sanitize(context)

    @classmethod
    def for_memory_extraction(cls, *, conversation) -> dict:
        """Context for extracting durable memory facts about a contact (9.1)."""
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        contact = conversation.contact
        context = {
            **cls._business(organization_id),
            "contact_name": getattr(contact, "display_name", "") or "el contacto",
            "conversation_summary": redact_sensitive(conversation.summary or "Sin resumen previo"),
            "existing_memories": cls._contact_memories(contact, organization_id, limit=10),
            "recent_messages": cls._recent_messages(conversation, limit),
        }
        return sanitize(context)

    @classmethod
    def for_project_brief(cls, *, conversation, deal_value_hint: str = "") -> dict:
        """Context for turning a conversation into a development-ready brief (9.4)."""
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        profile = _settings_for(BusinessProfile, organization_id)
        context = {
            **cls._business(organization_id),
            **cls._owner_voice(organization_id),
            "owner_name": getattr(profile, "owner_name", "") or "el dueño",
            "conversation_summary": redact_sensitive(conversation.summary or "Sin resumen previo"),
            "recent_messages": cls._recent_messages(conversation, limit),
            "deal_value_hint": redact_sensitive((deal_value_hint or "")[:500]),
        }
        return sanitize(context)

    @classmethod
    def for_lead_scoring(cls, *, conversation) -> dict:
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        context = {
            **cls._business(organization_id),
            "lead_profile": cls._contact_profile(conversation.contact),
            "commercial_history": redact_sensitive(
                conversation.summary or "Sin historial resumido"
            ),
            "recent_messages": cls._recent_messages(conversation, limit),
        }
        return sanitize(context)

    @classmethod
    def for_task_extraction(cls, *, conversation, current_message) -> dict:
        organization_id = conversation.organization_id
        now = timezone.localtime()
        context = {
            **cls._business(organization_id),
            "current_datetime": now.isoformat(),
            "timezone": str(now.tzinfo),
            "contact_profile": cls._contact_profile(conversation.contact),
            "recent_messages": cls._recent_messages(conversation, 6),
            "current_message": redact_sensitive((current_message.body or "")[:2000]),
        }
        return sanitize(context)

    @classmethod
    def for_audio_ticket(cls, *, organization_id, contact, transcription: str) -> dict:
        context = {
            **cls._business(organization_id),
            **cls._support_policy(organization_id),
            "client_profile": cls._contact_profile(contact) if contact else {},
            "recent_tickets": [],  # tickets module arrives in a later phase
            "transcription": redact_sensitive(transcription[:8000]),
        }
        return sanitize(context)

    @classmethod
    def for_conversation_summary(cls, *, conversation, summary_type: str) -> dict:
        organization_id = conversation.organization_id
        limit = cls._message_limit(organization_id)
        context = {
            **cls._business(organization_id),
            "summary_type": summary_type,
            "previous_summary": redact_sensitive(conversation.summary or "Ninguno"),
            "recent_messages": cls._recent_messages(conversation, limit),
        }
        return sanitize(context)

    @classmethod
    def for_risk_classification(
        cls, *, organization_id, proposed_reply: str, context: dict
    ) -> dict:
        built = {
            **cls._business(organization_id),
            "context_summary": sanitize(context or {}),
            "current_message": redact_sensitive(str(context.get("current_message", ""))[:2000]),
            "proposed_reply": redact_sensitive(proposed_reply[:4000]),
        }
        return sanitize(built)

    @classmethod
    def for_image_generation(cls, *, organization_id, image_request: str) -> dict:
        return sanitize(
            {
                **cls._business(organization_id),
                "brand_style": "limpio y profesional",
                "image_request": redact_sensitive(image_request[:2000]),
            }
        )

    @classmethod
    def for_prospect_qualification(cls, *, prospect) -> dict:
        campaign = prospect.campaign
        context = {
            **cls._business(prospect.organization_id),
            "campaign_vertical": redact_sensitive(campaign.vertical or campaign.name or ""),
            "campaign_target_profile": redact_sensitive(
                campaign.target_profile or "Sin perfil objetivo configurado."
            ),
            "min_fit_score": int(getattr(campaign, "min_fit_score", 60) or 60),
            "prospect_profile": _prospect_profile(prospect),
        }
        return sanitize(context)

    @classmethod
    def for_outreach_opener(cls, *, prospect) -> dict:
        campaign = prospect.campaign
        context = {
            **cls._business(prospect.organization_id),
            **cls._owner_voice(prospect.organization_id),
            "campaign_vertical": redact_sensitive(campaign.vertical or campaign.name or ""),
            "campaign_target_profile": redact_sensitive(
                campaign.target_profile or "Sin perfil objetivo configurado."
            ),
            "prospect_profile": _prospect_profile(prospect),
            "qualification_signals": prospect.signals or [],
            "recommended_angle": redact_sensitive(prospect.recommended_angle or ""),
        }
        return sanitize(context)

    @classmethod
    def for_outreach_email(cls, *, prospect, unsubscribe_line: str = "") -> dict:
        campaign = prospect.campaign
        profile = _settings_for(BusinessProfile, prospect.organization_id)
        context = {
            **cls._business(prospect.organization_id),
            **cls._owner_voice(prospect.organization_id),
            "owner_email": redact_sensitive(getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""),
            "owner_title": redact_sensitive(getattr(profile, "owner_name", "") or "Dueño"),
            "campaign_vertical": redact_sensitive(campaign.vertical or campaign.name or ""),
            "campaign_target_profile": redact_sensitive(
                campaign.target_profile or "Sin perfil objetivo configurado."
            ),
            "prospect_profile": _prospect_profile(prospect),
            "qualification_signals": prospect.signals or [],
            "recommended_angle": redact_sensitive(prospect.recommended_angle or ""),
            "unsubscribe_line": redact_sensitive(
                unsubscribe_line or "Si preferis que no vuelva a escribirte, avisame por este mail."
            ),
        }
        return sanitize(context)

    @classmethod
    def for_outreach_reply(
        cls,
        *,
        prospect,
        conversation=None,
        current_message=None,
        mode: str,
        intent: str = "",
        next_action: str = "",
        objection_type: str = "",
        last_outbound: str = "",
    ) -> dict:
        campaign = prospect.campaign
        recent_messages = []
        if conversation is not None:
            recent_messages = cls._recent_messages(conversation, 10)
        context = {
            **cls._business(prospect.organization_id),
            **cls._owner_voice(prospect.organization_id),
            "mode": mode,
            "intent": redact_sensitive(intent or ""),
            "next_action": redact_sensitive(next_action or ""),
            "objection_type": redact_sensitive(objection_type or ""),
            "campaign_vertical": redact_sensitive(campaign.vertical or campaign.name or ""),
            "campaign_target_profile": redact_sensitive(
                campaign.target_profile or "Sin perfil objetivo configurado."
            ),
            "prospect_profile": _prospect_profile(prospect),
            "last_outbound": redact_sensitive((last_outbound or "")[:1200]),
            "current_message": redact_sensitive(
                (getattr(current_message, "body", "") or "")[:2000]
            ),
            "recent_messages": recent_messages,
        }
        return sanitize(context)

    @classmethod
    def for_reply_intent(
        cls,
        *,
        prospect,
        conversation=None,
        current_message=None,
        outbound_message: str = "",
    ) -> dict:
        recent_messages = []
        if conversation is not None:
            recent_messages = cls._recent_messages(conversation, 8)
        context = {
            **cls._business(prospect.organization_id),
            "prospect_profile": _prospect_profile(prospect),
            "outbound_message": redact_sensitive((outbound_message or "")[:1200]),
            "reply_message": redact_sensitive((getattr(current_message, "body", "") or "")[:2000]),
            "recent_messages": recent_messages,
        }
        return sanitize(context)
