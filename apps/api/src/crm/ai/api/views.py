"""Thin DRF views for the AI admin panel."""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.ai.models import AIModelConfig, AIPrompt, AIPromptVersion, AIToolCall
from crm.ai.prompts.registry import PromptRegistry
from crm.ai.selectors.ai_runs import run_for_organization, runs_for_organization
from crm.ai.selectors.evals import eval_results_for_organization
from crm.ai.selectors.prompts import prompt_for_organization, prompts_for_organization
from crm.ai.selectors.usage import usage_by_day, usage_by_model, usage_by_purpose, usage_totals
from crm.ai.services.eval_runner import SUITES, EvalRunner
from crm.ai.tools import all_tools
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.organizations.selectors.organizations import resolve_current_organization

from .permissions import AIManagePermission, AIReadPermission
from .serializers import (
    AIEvalResultSerializer,
    AIMessageSerializer,
    AIModelConfigSerializer,
    AIPromptCreateSerializer,
    AIPromptSerializer,
    AIPromptUpdateSerializer,
    AIPromptVersionCreateSerializer,
    AIPromptVersionSerializer,
    AIRunDetailSerializer,
    AIRunListSerializer,
    AIToolCallSerializer,
    EvalRunRequestSerializer,
    ToolDefinitionSerializer,
)


def _get_run_or_404(organization, run_id):
    run = run_for_organization(organization, run_id)
    if run is None:
        raise NotFound("AI run not found in current organization")
    return run


def _get_prompt_or_404(organization, prompt_id) -> AIPrompt:
    prompt = prompt_for_organization(organization, prompt_id)
    if prompt is None:
        raise NotFound("Prompt not found in current organization")
    return prompt


# ----------------------------------------------------------------- AI runs


@extend_schema(responses=AIRunListSerializer(many=True))
class AIRunsView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = runs_for_organization(
            organization,
            purpose=request.query_params.get("purpose"),
            status=request.query_params.get("status"),
            provider=request.query_params.get("provider"),
            conversation_id=request.query_params.get("conversation_id"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AIRunListSerializer(page, many=True).data)


@extend_schema(responses=AIRunDetailSerializer)
class AIRunDetailView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request, run_id):
        organization = resolve_current_organization(request)
        run = _get_run_or_404(organization, run_id)
        return success_response(request, AIRunDetailSerializer(run).data)


@extend_schema(responses=AIMessageSerializer(many=True))
class AIRunMessagesView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request, run_id):
        organization = resolve_current_organization(request)
        run = _get_run_or_404(organization, run_id)
        messages = run.messages.order_by("created_at")
        return success_response(request, AIMessageSerializer(messages, many=True).data)


@extend_schema(responses=AIToolCallSerializer(many=True))
class AIRunToolCallsView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request, run_id):
        organization = resolve_current_organization(request)
        run = _get_run_or_404(organization, run_id)
        calls = run.tool_call_records.order_by("created_at")
        return success_response(request, AIToolCallSerializer(calls, many=True).data)


@extend_schema(request=None, responses=None)
class AIRunRetryView(APIView):
    permission_classes = [AIManagePermission]

    _RETRYABLE = {
        "sales_reply": "ai.generate_sales_reply",
        "support_reply": "ai.generate_support_reply",
        "lead_scoring": "ai.score_lead",
        "task_extraction": "ai.extract_tasks",
        "conversation_summary": "ai.summarize_conversation",
    }

    def post(self, request, run_id):
        from crm.ai import tasks as ai_tasks

        organization = resolve_current_organization(request)
        run = _get_run_or_404(organization, run_id)
        task_name = self._RETRYABLE.get(run.purpose)
        if task_name is None or run.conversation_id is None:
            raise ValidationError("This run cannot be retried automatically")

        kwargs = {"conversation_id": str(run.conversation_id)}
        if run.purpose in ("sales_reply", "support_reply", "task_extraction"):
            if run.message_id is None:
                raise ValidationError("Run lacks a message reference; cannot retry")
            kwargs["message_id"] = str(run.message_id)
        task = {
            "ai.generate_sales_reply": ai_tasks.generate_sales_reply,
            "ai.generate_support_reply": ai_tasks.generate_support_reply,
            "ai.score_lead": ai_tasks.score_lead,
            "ai.extract_tasks": ai_tasks.extract_tasks,
            "ai.summarize_conversation": ai_tasks.summarize_conversation,
        }[task_name]
        async_result = task.delay(**kwargs)
        return success_response(
            request, {"queued_task_id": str(async_result.id), "task": task_name}, status=202
        )


# ----------------------------------------------------------------- prompts


class AIPromptsView(APIView):
    permission_classes = [AIManagePermission]

    @extend_schema(responses=AIPromptSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = prompts_for_organization(
            organization, purpose=request.query_params.get("purpose")
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AIPromptSerializer(page, many=True).data)

    @extend_schema(request=AIPromptCreateSerializer, responses=AIPromptSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = AIPromptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if AIPrompt.objects.filter(
            organization_id=organization.id, key=serializer.validated_data["key"]
        ).exists():
            raise ValidationError({"key": "A prompt with this key already exists"})
        prompt = AIPrompt.objects.create(
            organization_id=organization.id,
            created_by_id=request.user.id,
            **serializer.validated_data,
        )
        return success_response(request, AIPromptSerializer(prompt).data, status=201)


class AIPromptDetailView(APIView):
    permission_classes = [AIManagePermission]

    @extend_schema(responses=AIPromptSerializer)
    def get(self, request, prompt_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        return success_response(request, AIPromptSerializer(prompt).data)

    @extend_schema(request=AIPromptUpdateSerializer, responses=AIPromptSerializer)
    def patch(self, request, prompt_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        serializer = AIPromptUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(prompt, field, value)
        prompt.save()
        return success_response(request, AIPromptSerializer(prompt).data)


class AIPromptVersionsView(APIView):
    permission_classes = [AIManagePermission]

    @extend_schema(responses=AIPromptVersionSerializer(many=True))
    def get(self, request, prompt_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        versions = prompt.versions.order_by("-version")
        return success_response(request, AIPromptVersionSerializer(versions, many=True).data)

    @extend_schema(request=AIPromptVersionCreateSerializer, responses=AIPromptVersionSerializer)
    def post(self, request, prompt_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        serializer = AIPromptVersionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = PromptRegistry.create_draft(
            prompt=prompt, created_by=request.user, **serializer.validated_data
        )
        return success_response(request, AIPromptVersionSerializer(version).data, status=201)


def _get_version_or_404(prompt: AIPrompt, version_id) -> AIPromptVersion:
    version = prompt.versions.filter(id=version_id).first()
    if version is None:
        raise NotFound("Prompt version not found")
    return version


@extend_schema(responses=AIPromptVersionSerializer)
class AIPromptVersionDetailView(APIView):
    permission_classes = [AIManagePermission]

    def get(self, request, prompt_id, version_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        version = _get_version_or_404(prompt, version_id)
        return success_response(request, AIPromptVersionSerializer(version).data)


@extend_schema(request=None, responses=AIPromptVersionSerializer)
class AIPromptVersionActivateView(APIView):
    permission_classes = [AIManagePermission]

    def post(self, request, prompt_id, version_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        version = _get_version_or_404(prompt, version_id)
        PromptRegistry.activate_version(version=version, actor=request.user, request=request)
        return success_response(request, AIPromptVersionSerializer(version).data)


@extend_schema(request=None, responses=AIPromptVersionSerializer)
class AIPromptVersionArchiveView(APIView):
    permission_classes = [AIManagePermission]

    def post(self, request, prompt_id, version_id):
        organization = resolve_current_organization(request)
        prompt = _get_prompt_or_404(organization, prompt_id)
        version = _get_version_or_404(prompt, version_id)
        PromptRegistry.archive_version(version=version, actor=request.user, request=request)
        return success_response(request, AIPromptVersionSerializer(version).data)


# ------------------------------------------------------------ model configs


class AIModelConfigsView(APIView):
    permission_classes = [AIManagePermission]

    @extend_schema(responses=AIModelConfigSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = (
            AIModelConfig.objects.filter(organization_id=organization.id)
            .select_related("provider")
            .order_by("purpose")
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AIModelConfigSerializer(page, many=True).data)

    @extend_schema(request=AIModelConfigSerializer, responses=AIModelConfigSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = AIModelConfigSerializer(
            data=request.data, context={"organization": organization}
        )
        serializer.is_valid(raise_exception=True)
        config = serializer.save(organization_id=organization.id, created_by_id=request.user.id)
        return success_response(request, AIModelConfigSerializer(config).data, status=201)


def _get_config_or_404(organization, config_id) -> AIModelConfig:
    config = (
        AIModelConfig.objects.filter(organization_id=organization.id, id=config_id)
        .select_related("provider")
        .first()
    )
    if config is None:
        raise NotFound("Model config not found in current organization")
    return config


class AIModelConfigDetailView(APIView):
    permission_classes = [AIManagePermission]

    @extend_schema(responses=AIModelConfigSerializer)
    def get(self, request, config_id):
        organization = resolve_current_organization(request)
        config = _get_config_or_404(organization, config_id)
        return success_response(request, AIModelConfigSerializer(config).data)

    @extend_schema(request=AIModelConfigSerializer, responses=AIModelConfigSerializer)
    def patch(self, request, config_id):
        organization = resolve_current_organization(request)
        config = _get_config_or_404(organization, config_id)
        serializer = AIModelConfigSerializer(
            config, data=request.data, partial=True, context={"organization": organization}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(request, AIModelConfigSerializer(config).data)


@extend_schema(request=None, responses=AIModelConfigSerializer)
class AIModelConfigActivateView(APIView):
    permission_classes = [AIManagePermission]

    def post(self, request, config_id):
        organization = resolve_current_organization(request)
        config = _get_config_or_404(organization, config_id)
        # Deactivate sibling configs of the same purpose; one active per purpose.
        AIModelConfig.objects.filter(
            organization_id=organization.id, purpose=config.purpose, is_active=True
        ).exclude(id=config.id).update(is_active=False)
        config.is_active = True
        config.save(update_fields=["is_active", "updated_at"])
        return success_response(request, AIModelConfigSerializer(config).data)


# ----------------------------------------------------------- project briefs


class ProjectBriefView(APIView):
    """Generate a development-ready project brief from a conversation (Phase 9.4)."""

    permission_classes = [AIReadPermission]

    def post(self, request):
        organization = resolve_current_organization(request)
        conversation_id = request.data.get("conversation_id")
        if not conversation_id:
            raise ValidationError({"conversation_id": "requerido"})

        from crm.conversations.models import Conversation

        conversation = Conversation.objects.filter(
            organization_id=organization.id, id=conversation_id
        ).first()
        if conversation is None:
            raise NotFound("Conversación no encontrada en esta organización")

        from crm.ai.services.ai_gateway import AIGateway

        result = AIGateway.generate_project_brief(
            conversation_id=conversation.id,
            deal_value_hint=str(request.data.get("deal_value_hint", "")),
            actor=request.user,
            http_request=request,
        )
        if not result.succeeded or not result.data:
            raise ValidationError("No se pudo generar el brief")
        return success_response(request, {"brief": result.data, "run_id": str(result.run_id)})


# ------------------------------------------------------------------- tools


@extend_schema(responses=ToolDefinitionSerializer(many=True))
class AIToolsView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        resolve_current_organization(request)
        data = [
            {
                "name": tool.definition.name,
                "version": tool.definition.version,
                "description": tool.definition.description,
                "argument_schema": tool.definition.argument_schema,
                "permissions_required": list(tool.definition.permissions_required),
                "allowed_purposes": list(tool.definition.allowed_purposes),
                "side_effects": tool.definition.side_effects,
                "risk_level": tool.definition.risk_level,
                "requires_human_approval": tool.definition.requires_human_approval,
            }
            for tool in all_tools()
        ]
        return success_response(request, data)


@extend_schema(responses=AIToolCallSerializer(many=True))
class AIToolCallsView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = AIToolCall.objects.filter(organization_id=organization.id).order_by(
            "-created_at"
        )
        tool_name = request.query_params.get("tool_name")
        status_filter = request.query_params.get("status")
        if tool_name:
            queryset = queryset.filter(tool_name=tool_name)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AIToolCallSerializer(page, many=True).data)


@extend_schema(responses=AIToolCallSerializer)
class AIToolCallDetailView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request, tool_call_id):
        organization = resolve_current_organization(request)
        call = AIToolCall.objects.filter(organization_id=organization.id, id=tool_call_id).first()
        if call is None:
            raise NotFound("Tool call not found in current organization")
        return success_response(request, AIToolCallSerializer(call).data)


# -------------------------------------------------------------------- usage


@extend_schema(responses={200: dict})
class AIUsageView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        return success_response(request, usage_totals(organization))


@extend_schema(responses={200: dict})
class AIUsageByPurposeView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        return success_response(request, usage_by_purpose(organization))


@extend_schema(responses={200: dict})
class AIUsageByModelView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        return success_response(request, usage_by_model(organization))


@extend_schema(responses={200: dict})
class AIUsageByDayView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        return success_response(request, usage_by_day(organization))


# -------------------------------------------------------------------- evals


@extend_schema(request=EvalRunRequestSerializer, responses=None)
class AIEvalRunView(APIView):
    permission_classes = [AIManagePermission]

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = EvalRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suite = serializer.validated_data["suite_name"]
        if suite and suite not in SUITES:
            raise ValidationError({"suite_name": f"Unknown suite. Options: {sorted(SUITES)}"})
        if suite:
            report = EvalRunner.run_suite(organization_id=organization.id, suite_name=suite)
        else:
            report = EvalRunner.run_all(organization_id=organization.id)
        return success_response(request, report)


@extend_schema(responses=AIEvalResultSerializer(many=True))
class AIEvalResultsView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = eval_results_for_organization(
            organization, suite_name=request.query_params.get("suite_name")
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AIEvalResultSerializer(page, many=True).data)


@extend_schema(responses=AIEvalResultSerializer)
class AIEvalResultDetailView(APIView):
    permission_classes = [AIReadPermission]

    def get(self, request, result_id):
        organization = resolve_current_organization(request)
        result = eval_results_for_organization(organization).filter(id=result_id).first()
        if result is None:
            raise NotFound("Eval result not found in current organization")
        return success_response(request, AIEvalResultSerializer(result).data)
