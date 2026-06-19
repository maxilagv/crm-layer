"""Thin conversation views: inbox list, detail, messages, and human actions.

Actions delegate to ConversationHandoffService; send-message delegates to
MessageIngestionService (simulated outbound — no real WhatsApp call).
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.conversations.constants import ACTIVE_STATUSES, MessageDirection
from crm.conversations.permissions import (
    ConversationReplyPermission,
    ConversationTakeoverPermission,
    ConversationViewPermission,
)
from crm.conversations.selectors import (
    conversation_get_for_organization,
    conversation_list_for_inbox,
    messages_for_conversation,
)
from crm.conversations.services import (
    ConversationHandoffService,
    MessageIngestionService,
)
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.organizations.models import Membership
from crm.organizations.selectors.organizations import resolve_current_organization

from .serializers import (
    ConversationActionSerializer,
    ConversationDetailSerializer,
    ConversationInboxSerializer,
    MessageSerializer,
    SendMessageSerializer,
)


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.lower() in {"1", "true", "yes", "on"}


def _get_conversation_or_404(organization, conversation_id):
    conversation = conversation_get_for_organization(organization, conversation_id)
    if conversation is None:
        raise NotFound("Conversation not found in current organization")
    return conversation


@extend_schema(responses=ConversationInboxSerializer(many=True))
class ConversationsView(APIView):
    permission_classes = [ConversationViewPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = conversation_list_for_inbox(
            organization,
            status=request.query_params.get("status"),
            mode=request.query_params.get("mode"),
            channel=request.query_params.get("channel"),
            assigned_user_id=request.query_params.get("assigned_user_id"),
            contact_id=request.query_params.get("contact_id"),
            ai_enabled=_parse_bool(request.query_params.get("ai_enabled")),
            search=request.query_params.get("search"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = ConversationInboxSerializer(page, many=True).data
        return paginator.get_paginated_response(data)


@extend_schema(responses=ConversationDetailSerializer)
class ConversationDetailView(APIView):
    permission_classes = [ConversationViewPermission]

    def get(self, request, conversation_id):
        organization = resolve_current_organization(request)
        conversation = _get_conversation_or_404(organization, conversation_id)
        return success_response(request, ConversationDetailSerializer(conversation).data)


@extend_schema(responses=MessageSerializer(many=True))
class ConversationMessagesView(APIView):
    permission_classes = [ConversationViewPermission]

    def get(self, request, conversation_id):
        organization = resolve_current_organization(request)
        conversation = _get_conversation_or_404(organization, conversation_id)
        queryset = messages_for_conversation(conversation)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = MessageSerializer(page, many=True).data
        return paginator.get_paginated_response(data)


@extend_schema(request=SendMessageSerializer, responses=MessageSerializer)
class ConversationSendMessageView(APIView):
    permission_classes = [ConversationReplyPermission]

    def post(self, request, conversation_id):
        organization = resolve_current_organization(request)
        conversation = _get_conversation_or_404(organization, conversation_id)
        if conversation.status not in [status.value for status in ACTIVE_STATUSES]:
            raise ValidationError("Cannot send a message to a closed conversation")

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = MessageIngestionService.ingest(
            organization=organization,
            conversation=conversation,
            contact=conversation.contact,
            channel=conversation.channel,
            direction=MessageDirection.OUTBOUND,
            message_type=serializer.validated_data["message_type"],
            body=serializer.validated_data["body"],
            actor=request.user,
            request=request,
        )
        return success_response(request, MessageSerializer(result.message).data, status=201)


class _ConversationActionView(APIView):
    """Base for mode/status actions; all require conversations.takeover."""

    permission_classes = [ConversationTakeoverPermission]

    def perform(self, request, organization, conversation):
        raise NotImplementedError

    def post(self, request, conversation_id):
        organization = resolve_current_organization(request)
        conversation = _get_conversation_or_404(organization, conversation_id)
        conversation = self.perform(request, organization, conversation)
        conversation = conversation_get_for_organization(organization, conversation.id)
        return success_response(request, ConversationDetailSerializer(conversation).data)


@extend_schema(request=ConversationActionSerializer, responses=ConversationDetailSerializer)
class ConversationTakeoverView(_ConversationActionView):
    def perform(self, request, organization, conversation):
        serializer = ConversationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned_user = request.user
        assigned_user_id = serializer.validated_data.get("assigned_user_id")
        if assigned_user_id is not None:
            membership = (
                Membership.objects.filter(
                    organization_id=organization.id,
                    user_id=assigned_user_id,
                    status=Membership.Status.ACTIVE,
                )
                .select_related("user")
                .first()
            )
            if membership is None:
                raise ValidationError(
                    {"assigned_user_id": "User is not an active member of this organization"}
                )
            assigned_user = membership.user
        return ConversationHandoffService.takeover(
            conversation=conversation,
            actor=request.user,
            assigned_user=assigned_user,
            request=request,
        )


@extend_schema(request=None, responses=ConversationDetailSerializer)
class ConversationPauseAIView(_ConversationActionView):
    def perform(self, request, organization, conversation):
        return ConversationHandoffService.pause_ai(
            conversation=conversation, actor=request.user, request=request
        )


@extend_schema(request=None, responses=ConversationDetailSerializer)
class ConversationResumeAIView(_ConversationActionView):
    def perform(self, request, organization, conversation):
        return ConversationHandoffService.resume_ai(
            conversation=conversation, actor=request.user, request=request
        )


@extend_schema(request=None, responses=ConversationDetailSerializer)
class ConversationCloseView(_ConversationActionView):
    def perform(self, request, organization, conversation):
        return ConversationHandoffService.close(
            conversation=conversation, actor=request.user, request=request
        )


@extend_schema(request=None, responses=ConversationDetailSerializer)
class ConversationReopenView(_ConversationActionView):
    def perform(self, request, organization, conversation):
        return ConversationHandoffService.reopen(
            conversation=conversation, actor=request.user, request=request
        )
