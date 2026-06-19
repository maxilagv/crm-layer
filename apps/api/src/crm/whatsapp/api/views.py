import logging

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.audit.services import audit_event_create
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization
from crm.whatsapp.api.serializers import (
    TemplateSendSerializer,
    WhatsAppOutboundMessageSerializer,
    WhatsAppTemplateSerializer,
    WhatsAppWebhookEventRawSerializer,
    WhatsAppWebhookEventSerializer,
)
from crm.whatsapp.models import WhatsAppOutboundMessage, WhatsAppTemplate, WhatsAppWebhookEvent
from crm.whatsapp.services.template_sender import queue_template_message
from crm.whatsapp.services.webhook_events import persist_valid_webhook_event
from crm.whatsapp.services.webhook_verification import validate_signature, verify_token_matches

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("hub.mode", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.verify_token", str, OpenApiParameter.QUERY),
            OpenApiParameter("hub.challenge", str, OpenApiParameter.QUERY),
        ],
        responses={200: str, 403: str},
        tags=["whatsapp-webhook"],
    )
    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        if mode == "subscribe" and verify_token_matches(token):
            logger.info("WhatsApp webhook verified", extra={"event": "whatsapp.webhook.verify.ok"})
            return HttpResponse(challenge, status=200, content_type="text/plain")
        audit_event_create(
            event_type="whatsapp_webhook_verification_failed",
            metadata={"reason": "invalid_verify_token", "mode": mode or ""},
        )
        logger.warning(
            "WhatsApp webhook verification failed",
            extra={"event": "whatsapp.webhook.verify.failed", "metadata": {"mode": mode}},
        )
        return HttpResponse("Forbidden", status=403, content_type="text/plain")

    @extend_schema(
        request=dict,
        responses={200: dict, 400: dict, 403: dict},
        tags=["whatsapp-webhook"],
    )
    def post(self, request):
        signature = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
        raw_body = request.body
        if not validate_signature(raw_body=raw_body, signature_header=signature):
            audit_event_create(
                event_type="whatsapp_invalid_signature",
                metadata={"reason": "signature_mismatch"},
            )
            logger.warning(
                "WhatsApp webhook invalid signature",
                extra={"event": "whatsapp.webhook.invalid_signature"},
            )
            return Response({"status": "forbidden"}, status=403)

        result = persist_valid_webhook_event(raw_body=raw_body, signature_header=signature)
        if result.event.status == "failed":
            return Response({"status": "failed", "event_id": str(result.event.id)}, status=400)
        logger.info(
            "WhatsApp webhook received",
            extra={
                "event": "whatsapp.webhook.received",
                "organization_id": (
                    str(result.event.organization_id) if result.event.organization_id else None
                ),
                "metadata": {
                    "webhook_event_id": str(result.event.id),
                    "created": result.created,
                    "event_type": result.event.event_type,
                },
            },
        )
        return Response(
            {
                "status": "received" if result.created else "duplicate",
                "event_id": str(result.event.id),
            },
            status=200,
        )


class WhatsAppTemplatesView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value

    @extend_schema(responses={200: WhatsAppTemplateSerializer(many=True)}, tags=["whatsapp"])
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = WhatsAppTemplate.objects.filter(organization_id=organization.id).order_by(
            "name", "language"
        )
        for field in ("status", "category", "language"):
            value = request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = WhatsAppTemplateSerializer(page, many=True).data
        return paginator.get_paginated_response(data)


class WhatsAppTemplateSendView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.CONVERSATIONS_REPLY.value

    @extend_schema(
        request=TemplateSendSerializer,
        responses={201: WhatsAppOutboundMessageSerializer},
        tags=["whatsapp"],
    )
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = TemplateSendSerializer(
            data=request.data,
            context={"organization": organization},
        )
        serializer.is_valid(raise_exception=True)
        result = queue_template_message(
            organization=organization,
            conversation=serializer.validated_data["conversation"],
            contact=serializer.validated_data["contact"],
            template_name=serializer.validated_data["template_name"],
            language=serializer.validated_data["language"],
            components=serializer.validated_data.get("components", []),
            idempotency_key=serializer.validated_data.get("idempotency_key", ""),
            actor=request.user,
            request=request,
        )
        return success_response(
            request,
            WhatsAppOutboundMessageSerializer(result.outbound).data,
            status=201 if result.created else 200,
        )


class WhatsAppOutboundMessagesView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.CONVERSATIONS_VIEW.value

    @extend_schema(responses={200: WhatsAppOutboundMessageSerializer(many=True)}, tags=["whatsapp"])
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = WhatsAppOutboundMessage.objects.filter(organization_id=organization.id).order_by(
            "-created_at"
        )
        for field in ("status", "conversation_id", "contact_id", "external_message_id"):
            value = request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        created_from = request.query_params.get("created_from")
        created_to = request.query_params.get("created_to")
        if created_from:
            queryset = queryset.filter(created_at__gte=created_from)
        if created_to:
            queryset = queryset.filter(created_at__lte=created_to)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = WhatsAppOutboundMessageSerializer(page, many=True).data
        return paginator.get_paginated_response(data)


class WhatsAppWebhookEventsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.AUDIT_VIEW.value

    @extend_schema(responses={200: WhatsAppWebhookEventSerializer(many=True)}, tags=["whatsapp"])
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = WhatsAppWebhookEvent.objects.filter(organization_id=organization.id).order_by(
            "-received_at"
        )
        for field in ("status", "event_type", "event_id"):
            value = request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        received_from = request.query_params.get("received_from")
        received_to = request.query_params.get("received_to")
        if received_from:
            queryset = queryset.filter(received_at__gte=received_from)
        if received_to:
            queryset = queryset.filter(received_at__lte=received_to)
        serializer_class = (
            WhatsAppWebhookEventRawSerializer
            if request.query_params.get("include_raw") == "true"
            else WhatsAppWebhookEventSerializer
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = serializer_class(page, many=True).data
        return paginator.get_paginated_response(data)
