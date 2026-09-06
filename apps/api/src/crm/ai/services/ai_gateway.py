"""AIGateway: the single entry point for all AI usage in the backend.

Flow per call: validate input -> route model -> build context -> render active
prompt -> create AIRun -> call provider (with fallback) -> validate structured
output (1 repair retry) -> execute authorized tools -> SafetyGuard -> record
usage/cost -> finish AIRun -> return a semantic result.

Business modules never see SDKs, raw responses or unvalidated JSON.
"""

import logging

from crm.ai.domain.enums import (
    PURPOSES_REQUIRING_SCHEMA,
    AIPurpose,
    AIRunStatus,
    ModelCapability,
    SafetyDecision,
)
from crm.ai.domain.events import (
    EVENT_AI_HANDOFF_REQUESTED,
    EVENT_AI_REPLY_BLOCKED,
)
from crm.ai.domain.exceptions import AIError, AIProviderError
from crm.ai.domain.result import AIGatewayResult
from crm.ai.domain.value_objects import AIRequest, SafetyResult
from crm.ai.models import AIRun
from crm.ai.prompts.loader import PROMPT_FOLDERS
from crm.ai.prompts.registry import PromptRegistry
from crm.ai.prompts.renderer import PromptRenderer
from crm.ai.schemas import json_schema_for_purpose, schema_for_purpose
from crm.ai.tools import ToolContext, ToolExecutor, tools_for_purpose
from crm.core.request_context import get_correlation_id, get_request_id
from crm.core.services.outbox import create_outbox_event

from .ai_run_logger import AIRunLogger
from .context_builder import ContextBuilder
from .fallback_service import call_with_fallback
from .model_router import ModelRouter
from .risk_classifier import RiskClassifier
from .safety_guard import SafetyGuard
from .structured_output import StructuredOutputValidator
from .usage_recorder import UsageRecorder

logger = logging.getLogger(__name__)

_PROMPT_KEY_BY_PURPOSE = {purpose: key for key, purpose in PROMPT_FOLDERS.values()}

_SCHEMA_PURPOSES = {p.value for p in PURPOSES_REQUIRING_SCHEMA}


class AIGateway:
    # ------------------------------------------------------------------ core

    @staticmethod
    def _execute(
        *,
        organization_id,
        purpose: str,
        variables: dict,
        method_name: str,
        capabilities: tuple[str, ...] = (),
        metadata: dict | None = None,
        references: dict | None = None,
        allow_tools: bool = False,
        safety_inbound_text: str = "",
        request_extras: dict | None = None,
        actor=None,
        http_request=None,
    ) -> AIGatewayResult:
        references = references or {}
        metadata = dict(metadata or {})
        route = ModelRouter.route(
            organization_id=organization_id, purpose=purpose, required_capabilities=capabilities
        )

        prompt_version = None
        input_messages: list[dict[str, str]] = []
        prompt_key = _PROMPT_KEY_BY_PURPOSE.get(purpose)
        if prompt_key is not None:
            prompt_version = PromptRegistry.get_active_version(
                organization_id=organization_id, key=prompt_key
            )
            rendered = PromptRenderer.render(prompt_version, variables)
            input_messages = rendered.as_messages()

        run = AIRunLogger.start(
            organization_id=organization_id,
            purpose=purpose,
            input_messages=input_messages,
            input_context=variables,
            prompt_version=prompt_version,
            request_id=get_request_id() or "",
            correlation_id=get_correlation_id() or "",
            **references,
        )

        request = AIRequest(
            organization_id=organization_id,
            purpose=purpose,
            input_messages=list(input_messages),
            context=variables,
            expected_schema=(
                json_schema_for_purpose(purpose) if purpose in _SCHEMA_PURPOSES else None
            ),
            allowed_tools=(
                [tool.provider_spec() for tool in tools_for_purpose(purpose)] if allow_tools else []
            ),
            metadata=metadata,
            request_id=str(run.id),
            correlation_id=run.correlation_id,
            **(request_extras or {}),
        )

        fallback_used = False
        try:
            response, fallback_used = call_with_fallback(
                route=route, request=request, method_name=method_name
            )
        except AIProviderError as exc:
            AIRunLogger.finish(
                run, status=AIRunStatus.FAILED, error_code=exc.code, error_message=str(exc)
            )
            return AIGatewayResult(
                run_id=run.id,
                status=run.status,
                purpose=purpose,
                error_code=exc.code,
                error_message=str(exc),
            )

        # Structured validation with one repair retry. Purposes in
        # _SCHEMA_PURPOSES REQUIRE valid JSON (their output mutates data);
        # other schema-registered purposes validate opportunistically when the
        # provider returned JSON (e.g. conversation_summary).
        validated_data = None
        must_validate = purpose in _SCHEMA_PURPOSES or (
            response.json is not None and schema_for_purpose(purpose) is not None
        )
        if must_validate:
            validation = StructuredOutputValidator.validate(purpose, response.json)
            if not validation.is_valid:
                repair = StructuredOutputValidator.repair_instruction(validation.errors)
                request.input_messages = [
                    *request.input_messages,
                    {"role": "user", "content": repair},
                ]
                try:
                    response, retry_fallback = call_with_fallback(
                        route=route, request=request, method_name=method_name
                    )
                    fallback_used = fallback_used or retry_fallback
                except AIProviderError as exc:
                    AIRunLogger.record_response(run, response)
                    UsageRecorder.record(run=run, usage=response.usage)
                    AIRunLogger.finish(
                        run, status=AIRunStatus.FAILED, error_code=exc.code, error_message=str(exc)
                    )
                    return AIGatewayResult(
                        run_id=run.id,
                        status=run.status,
                        purpose=purpose,
                        error_code=exc.code,
                        error_message=str(exc),
                    )
                validation = StructuredOutputValidator.validate(purpose, response.json)
            if not validation.is_valid:
                # Two strikes: nothing touches the database with this output.
                # output_json only ever holds VALIDATED data; the invalid
                # payload moves to the sanitized debug blob.
                AIRunLogger.record_response(run, response)
                run.raw_response = {**run.raw_response, "invalid_output": run.output_json}
                run.output_json = None
                UsageRecorder.record(run=run, usage=response.usage)
                AIRunLogger.finish(
                    run,
                    status=AIRunStatus.SCHEMA_INVALID,
                    error_code="structured_output_invalid",
                    error_message="; ".join(validation.errors)[:2000],
                )
                return AIGatewayResult(
                    run_id=run.id,
                    status=run.status,
                    purpose=purpose,
                    error_code="structured_output_invalid",
                    error_message="; ".join(validation.errors)[:500],
                )
            validated_data = validation.data

        AIRunLogger.record_response(run, response)

        # Tool calls: the backend authorizes and executes; the model only asks.
        tool_results = []
        if response.tool_calls:
            tool_context = ToolContext(
                organization_id=organization_id,
                ai_run=run,
                actor=actor,
                conversation_id=references.get("conversation_id"),
                contact_id=references.get("contact_id"),
                message_id=references.get("message_id"),
                request=http_request,
                purpose=purpose,
            )
            for tool_request in response.tool_calls:
                tool_results.append(
                    ToolExecutor.execute(request=tool_request, context=tool_context)
                )

        # SafetyGuard for replies bound to humans.
        safety: SafetyResult | None = None
        if purpose in (AIPurpose.SALES_REPLY.value, AIPurpose.SUPPORT_REPLY.value):
            data = validated_data or {}
            safety = SafetyGuard.evaluate_reply(
                organization_id=organization_id,
                proposed_reply=str(data.get("reply", response.text)),
                inbound_text=safety_inbound_text,
                purpose=purpose,
                model_risk_level=str(data.get("risk_level", "low")),
                model_requests_handoff=bool(data.get("should_handoff", False)),
            )
            run.safety_result = safety.as_dict()
            if safety.decision != SafetyDecision.SEND.value:
                _emit_safety_events(run, safety, references)

        UsageRecorder.record(run=run, usage=response.usage)

        if safety is not None and safety.decision in (
            SafetyDecision.DO_NOT_REPLY.value,
            SafetyDecision.HANDOFF_TO_HUMAN.value,
        ):
            final_status = AIRunStatus.BLOCKED_BY_SAFETY
        elif fallback_used:
            final_status = AIRunStatus.FALLBACK_USED
        else:
            final_status = AIRunStatus.SUCCESS
        AIRunLogger.finish(run, status=final_status)

        return AIGatewayResult(
            run_id=run.id,
            status=run.status,
            purpose=purpose,
            text=response.text or response.transcription_text,
            data=validated_data if validated_data is not None else _media_data(response),
            safety=safety,
            tool_results=tool_results,
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
        )

    # -------------------------------------------------------------- methods

    @staticmethod
    def generate_sales_reply(
        *,
        conversation_id,
        message_id,
        lead_id=None,
        actor=None,
        metadata: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        conversation, message = _load_conversation_message(conversation_id, message_id)
        variables = ContextBuilder.for_sales_reply(
            conversation=conversation, current_message=message
        )
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.SALES_REPLY.value,
            variables=variables,
            method_name="generate_with_tools",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "message_id": message.id,
                "contact_id": conversation.contact_id,
                "lead_id": lead_id,
            },
            allow_tools=True,
            safety_inbound_text=message.body or "",
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def generate_support_reply(
        *,
        conversation_id,
        message_id,
        ticket_id=None,
        actor=None,
        metadata: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        conversation, message = _load_conversation_message(conversation_id, message_id)
        variables = ContextBuilder.for_support_reply(
            conversation=conversation, current_message=message
        )
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.SUPPORT_REPLY.value,
            variables=variables,
            method_name="generate_with_tools",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "message_id": message.id,
                "contact_id": conversation.contact_id,
                "ticket_id": ticket_id,
            },
            allow_tools=True,
            safety_inbound_text=message.body or "",
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def generate_assistant_reply(
        *, conversation_id, message_id, actor=None, metadata: dict | None = None, http_request=None
    ) -> AIGatewayResult:
        """Personal work-assistant reply for the owner (no SafetyGuard gating)."""
        conversation, message = _load_conversation_message(conversation_id, message_id)
        variables = ContextBuilder.for_assistant_reply(
            conversation=conversation, current_message=message
        )
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.ASSISTANT_REPLY.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "message_id": message.id,
                "contact_id": conversation.contact_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def generate_document_draft(
        *,
        organization_id,
        owner_request: str,
        doc_type: str,
        currency: str = "",
        tax_rate="",
        default_terms: str = "",
        client: dict | None = None,
        actor=None,
        metadata: dict | None = None,
        references: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        """Draft a structured document payload from a free-text request.

        Owner-only / internal: no SafetyGuard gating. Runs in generate_structured
        so it works on Gemini's json_object compat layer. The validated ``data``
        can be passed straight to ``DocumentService.generate(payload=...)``.
        """
        variables = ContextBuilder.for_document_draft(
            organization_id=organization_id,
            owner_request=owner_request,
            doc_type=doc_type,
            currency=currency,
            tax_rate=tax_rate,
            default_terms=default_terms,
            client=client,
        )
        return AIGateway._execute(
            organization_id=organization_id,
            purpose=AIPurpose.DOCUMENT_DRAFT.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references=references or {},
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def extract_memory(
        *, conversation_id, actor=None, metadata: dict | None = None, http_request=None
    ) -> AIGatewayResult:
        """Extract durable memory facts from a conversation (internal, no SafetyGuard)."""
        conversation = _load_conversation(conversation_id)
        variables = ContextBuilder.for_memory_extraction(conversation=conversation)
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.MEMORY_EXTRACTION.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "contact_id": conversation.contact_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def generate_project_brief(
        *,
        conversation_id,
        deal_value_hint: str = "",
        actor=None,
        metadata: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        """Draft a development-ready project brief from a conversation (internal)."""
        conversation = _load_conversation(conversation_id)
        variables = ContextBuilder.for_project_brief(
            conversation=conversation, deal_value_hint=deal_value_hint
        )
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.PROJECT_BRIEF.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "contact_id": conversation.contact_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def qualify_prospect(
        *, prospect_id, actor=None, metadata: dict | None = None, http_request=None
    ) -> AIGatewayResult:
        """Score a discovered prospect against its campaign criteria."""
        prospect = _load_prospect(prospect_id)
        variables = ContextBuilder.for_prospect_qualification(prospect=prospect)
        metadata = {**(metadata or {}), "prospect_id": str(prospect.id)}
        return AIGateway._execute(
            organization_id=prospect.organization_id,
            purpose=AIPurpose.PROSPECT_QUALIFICATION.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "contact_id": prospect.contact_id,
                "conversation_id": prospect.conversation_id,
                "lead_id": prospect.lead_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def draft_outreach_opener(
        *, prospect_id, actor=None, metadata: dict | None = None, http_request=None
    ) -> AIGatewayResult:
        """Draft the first WhatsApp opener for an approved prospect."""
        prospect = _load_prospect(prospect_id)
        variables = ContextBuilder.for_outreach_opener(prospect=prospect)
        metadata = {**(metadata or {}), "prospect_id": str(prospect.id)}
        return AIGateway._execute(
            organization_id=prospect.organization_id,
            purpose=AIPurpose.OUTREACH_OPENER.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "contact_id": prospect.contact_id,
                "conversation_id": prospect.conversation_id,
                "lead_id": prospect.lead_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def draft_outreach_email(
        *,
        prospect_id,
        unsubscribe_line: str = "",
        actor=None,
        metadata: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        """Draft the first email opener for an approved prospect."""
        prospect = _load_prospect(prospect_id)
        variables = ContextBuilder.for_outreach_email(
            prospect=prospect,
            unsubscribe_line=unsubscribe_line,
        )
        metadata = {**(metadata or {}), "prospect_id": str(prospect.id)}
        return AIGateway._execute(
            organization_id=prospect.organization_id,
            purpose=AIPurpose.OUTREACH_EMAIL.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "contact_id": prospect.contact_id,
                "conversation_id": prospect.conversation_id,
                "lead_id": prospect.lead_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def draft_prospect_reply(
        *,
        prospect_id,
        conversation_id=None,
        message_id=None,
        mode: str,
        intent: str = "",
        next_action: str = "",
        objection_type: str = "",
        last_outbound: str = "",
        actor=None,
        metadata: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        """Draft a follow-on reply or follow-up for a Cazador prospect."""
        prospect = _load_prospect(prospect_id)
        conversation = _load_conversation(conversation_id) if conversation_id else None
        message = _load_message(message_id, conversation_id=conversation_id) if message_id else None
        variables = ContextBuilder.for_outreach_reply(
            prospect=prospect,
            conversation=conversation,
            current_message=message,
            mode=mode,
            intent=intent,
            next_action=next_action,
            objection_type=objection_type,
            last_outbound=last_outbound,
        )
        metadata = {**(metadata or {}), "prospect_id": str(prospect.id), "mode": mode}
        return AIGateway._execute(
            organization_id=prospect.organization_id,
            purpose=AIPurpose.OUTREACH_REPLY.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation_id or prospect.conversation_id,
                "message_id": message_id,
                "contact_id": prospect.contact_id,
                "lead_id": prospect.lead_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def classify_prospect_reply(
        *,
        prospect_id,
        conversation_id=None,
        message_id=None,
        outbound_message: str = "",
        actor=None,
        metadata: dict | None = None,
        http_request=None,
    ) -> AIGatewayResult:
        """Classify a prospect's inbound reply after outbound contact."""
        prospect = _load_prospect(prospect_id)
        conversation = _load_conversation(conversation_id) if conversation_id else None
        message = _load_message(message_id, conversation_id=conversation_id) if message_id else None
        variables = ContextBuilder.for_reply_intent(
            prospect=prospect,
            conversation=conversation,
            current_message=message,
            outbound_message=outbound_message,
        )
        metadata = {**(metadata or {}), "prospect_id": str(prospect.id)}
        return AIGateway._execute(
            organization_id=prospect.organization_id,
            purpose=AIPurpose.REPLY_INTENT.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation_id or prospect.conversation_id,
                "message_id": message_id,
                "contact_id": prospect.contact_id,
                "lead_id": prospect.lead_id,
            },
            actor=actor,
            http_request=http_request,
        )

    @staticmethod
    def score_lead(
        *, conversation_id, lead_id=None, actor=None, metadata: dict | None = None
    ) -> AIGatewayResult:
        conversation = _load_conversation(conversation_id)
        variables = ContextBuilder.for_lead_scoring(conversation=conversation)
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.LEAD_SCORING.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "contact_id": conversation.contact_id,
                "lead_id": lead_id,
            },
            actor=actor,
        )

    @staticmethod
    def extract_tasks(
        *, conversation_id, message_id, actor=None, metadata: dict | None = None
    ) -> AIGatewayResult:
        conversation, message = _load_conversation_message(conversation_id, message_id)
        variables = ContextBuilder.for_task_extraction(
            conversation=conversation, current_message=message
        )
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.TASK_EXTRACTION.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "message_id": message.id,
                "contact_id": conversation.contact_id,
            },
            actor=actor,
        )

    @staticmethod
    def summarize_conversation(
        *, conversation_id, summary_type: str = "short", actor=None, metadata: dict | None = None
    ) -> AIGatewayResult:
        conversation = _load_conversation(conversation_id)
        variables = ContextBuilder.for_conversation_summary(
            conversation=conversation, summary_type=summary_type
        )
        return AIGateway._execute(
            organization_id=conversation.organization_id,
            purpose=AIPurpose.CONVERSATION_SUMMARY.value,
            variables=variables,
            method_name="generate_structured",
            metadata=metadata,
            references={
                "conversation_id": conversation.id,
                "contact_id": conversation.contact_id,
            },
            actor=actor,
        )

    @staticmethod
    def transcribe_audio(
        *,
        organization_id,
        audio_bytes: bytes,
        audio_format: str = "ogg",
        media_reference_id=None,
        metadata: dict | None = None,
        references: dict | None = None,
    ) -> AIGatewayResult:
        metadata = dict(metadata or {})
        if media_reference_id is not None:
            metadata["media_reference_id"] = str(media_reference_id)
        return AIGateway._execute(
            organization_id=organization_id,
            purpose=AIPurpose.AUDIO_TRANSCRIPTION.value,
            variables={},
            method_name="transcribe_audio",
            capabilities=(ModelCapability.AUDIO.value,),
            metadata=metadata,
            references=references or {},
            request_extras={"audio_bytes": audio_bytes, "audio_format": audio_format},
        )

    @staticmethod
    def extract_ticket_from_audio(
        *,
        organization_id,
        transcription: str,
        contact=None,
        actor=None,
        metadata: dict | None = None,
        references: dict | None = None,
    ) -> AIGatewayResult:
        variables = ContextBuilder.for_audio_ticket(
            organization_id=organization_id, contact=contact, transcription=transcription
        )
        return AIGateway._execute(
            organization_id=organization_id,
            purpose=AIPurpose.AUDIO_TICKET_EXTRACTION.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
            references=references or {},
            actor=actor,
        )

    @staticmethod
    def generate_image(
        *,
        organization_id,
        image_request: str,
        actor=None,
        metadata: dict | None = None,
        references: dict | None = None,
    ) -> AIGatewayResult:
        variables = ContextBuilder.for_image_generation(
            organization_id=organization_id, image_request=image_request
        )
        return AIGateway._execute(
            organization_id=organization_id,
            purpose=AIPurpose.IMAGE_GENERATION.value,
            variables=variables,
            method_name="generate_image",
            capabilities=(ModelCapability.IMAGES.value,),
            metadata=metadata,
            references=references or {},
            request_extras={"image_prompt": image_request},
            actor=actor,
        )

    @staticmethod
    def create_embedding(
        *, organization_id, owner_type: str, owner_id, text: str, metadata: dict | None = None
    ) -> AIGatewayResult:
        from .embedding_service import EmbeddingService

        return EmbeddingService.create(
            organization_id=organization_id,
            owner_type=owner_type,
            owner_id=owner_id,
            text=text,
            metadata=metadata,
        )

    @staticmethod
    def create_embedding_vector(
        *, organization_id, text: str, metadata: dict | None = None
    ) -> AIGatewayResult:
        from .embedding_service import EmbeddingService

        return EmbeddingService.create_vector(
            organization_id=organization_id,
            text=text,
            metadata=metadata,
        )

    @staticmethod
    def classify_risk(
        *,
        organization_id,
        proposed_reply: str,
        context: dict | None = None,
        use_model: bool = True,
        metadata: dict | None = None,
    ) -> AIGatewayResult:
        """Deterministic rules first; model classification only adds severity."""
        context = context or {}
        deterministic = SafetyGuard.evaluate_reply(
            organization_id=organization_id,
            proposed_reply=proposed_reply,
            inbound_text=str(context.get("current_message", "")),
        )
        inbound = RiskClassifier.classify_inbound(str(context.get("current_message", "")))
        worst = _worst_safety(deterministic, inbound)
        if not use_model or worst.decision != SafetyDecision.SEND.value:
            # Deterministic verdict is final when it already restricts: no
            # provider call happened, so there is no AIRun to reference.
            return AIGatewayResult(
                run_id=None,
                status=AIRunStatus.SUCCESS.value,
                purpose=AIPurpose.RISK_CLASSIFICATION.value,
                data=worst.as_dict(),
                safety=worst,
            )
        variables = ContextBuilder.for_risk_classification(
            organization_id=organization_id, proposed_reply=proposed_reply, context=context
        )
        result = AIGateway._execute(
            organization_id=organization_id,
            purpose=AIPurpose.RISK_CLASSIFICATION.value,
            variables=variables,
            method_name="generate_structured",
            capabilities=(ModelCapability.STRUCTURED_OUTPUTS.value,),
            metadata=metadata,
        )
        if result.succeeded and result.data:
            model_safety = SafetyResult(
                decision=result.data.get("decision", SafetyDecision.SEND.value),
                risk_level=result.data.get("risk_level", "low"),
                reasons=result.data.get("reasons", []),
                policy_violations=result.data.get("policy_violations", []),
                confidence=float(result.data.get("confidence", 0.5)),
            )
            combined = _worst_safety(worst, model_safety)
            return AIGatewayResult(
                run_id=result.run_id,
                status=result.status,
                purpose=result.purpose,
                data=combined.as_dict(),
                safety=combined,
                provider=result.provider,
                model=result.model,
                latency_ms=result.latency_ms,
            )
        return result


# ------------------------------------------------------------------ helpers


def _load_conversation(conversation_id):
    from crm.conversations.models import Conversation

    return Conversation.objects.select_related("contact").get(id=conversation_id)


def _load_message(message_id, *, conversation_id=None):
    from crm.conversations.models import Message

    qs = Message.objects.select_related("conversation__contact").filter(id=message_id)
    if conversation_id:
        qs = qs.filter(conversation_id=conversation_id)
    return qs.get()


def _load_conversation_message(conversation_id, message_id):
    from crm.conversations.models import Message

    message = Message.objects.select_related("conversation__contact").get(
        id=message_id, conversation_id=conversation_id
    )
    return message.conversation, message


def _load_prospect(prospect_id):
    from crm.prospecting.models import Prospect

    return Prospect.objects.select_related("campaign").get(id=prospect_id)


def _media_data(response) -> dict | None:
    data = {}
    if response.transcription_text:
        data["text"] = response.transcription_text
        data["audio_seconds"] = str(response.usage.audio_seconds)
    if response.image_b64:
        data["image_b64"] = response.image_b64
    if response.image_url:
        data["image_url"] = response.image_url
    if response.embedding_vector:
        data["vector"] = response.embedding_vector
    return data or None


_DECISION_ORDER = [
    SafetyDecision.SEND.value,
    SafetyDecision.REVISE.value,
    SafetyDecision.ASK_CLARIFYING_QUESTION.value,
    SafetyDecision.NOTIFY_OWNER.value,
    SafetyDecision.HANDOFF_TO_HUMAN.value,
    SafetyDecision.DO_NOT_REPLY.value,
]


def _worst_safety(a: SafetyResult, b: SafetyResult) -> SafetyResult:
    from crm.ai.domain.enums import max_risk

    worst_decision = max(
        a.decision,
        b.decision,
        key=lambda d: _DECISION_ORDER.index(d) if d in _DECISION_ORDER else 0,
    )
    return SafetyResult(
        decision=worst_decision,
        risk_level=max_risk(a.risk_level, b.risk_level),
        reasons=[*a.reasons, *b.reasons],
        blocked_phrases=[*a.blocked_phrases, *b.blocked_phrases],
        policy_violations=[*a.policy_violations, *b.policy_violations],
        requires_handoff=a.requires_handoff or b.requires_handoff,
        owner_notification_required=a.owner_notification_required or b.owner_notification_required,
        confidence=min(a.confidence, b.confidence),
    )


def _emit_safety_events(run: AIRun, safety: SafetyResult, references: dict) -> None:
    payload_data = {
        "ai_run_id": str(run.id),
        "decision": safety.decision,
        "risk_level": safety.risk_level,
        "reasons": safety.reasons[:10],
        "conversation_id": str(references.get("conversation_id") or "") or None,
    }
    create_outbox_event(
        event_type=EVENT_AI_REPLY_BLOCKED,
        organization_id=run.organization_id,
        payload={
            "event_type": EVENT_AI_REPLY_BLOCKED,
            "organization_id": str(run.organization_id),
            "data": payload_data,
            "metadata": {"request_id": run.request_id or None},
        },
    )
    if safety.requires_handoff:
        create_outbox_event(
            event_type=EVENT_AI_HANDOFF_REQUESTED,
            organization_id=run.organization_id,
            payload={
                "event_type": EVENT_AI_HANDOFF_REQUESTED,
                "organization_id": str(run.organization_id),
                "data": payload_data,
                "metadata": {"request_id": run.request_id or None},
            },
        )


__all__ = ["AIGateway", "AIError"]
