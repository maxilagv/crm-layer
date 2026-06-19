from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from crm.audit.api.filters import apply_audit_filters
from crm.audit.api.permissions import AuditReadPermission
from crm.audit.api.serializers import (
    AuditAIDecisionSerializer,
    AuditDataAccessLogSerializer,
    AuditExternalRequestSerializer,
    AuditLogSerializer,
    AuditSecurityEventSerializer,
)
from crm.audit.selectors.audit_logs import (
    ai_decisions_for_organization,
    audit_logs_for_organization,
    data_access_logs_for_organization,
    external_requests_for_organization,
    security_events_for_organization,
)
from crm.core.api.pagination import StandardPagination
from crm.organizations.selectors.organizations import resolve_current_organization


class _AuditListView(APIView):
    permission_classes = [AuditReadPermission]
    serializer_class = None
    queryset_factory = None

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = apply_audit_filters(self.queryset_factory(organization), request.query_params)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(self.serializer_class(page, many=True).data)


class AuditLogsView(_AuditListView):
    serializer_class = AuditLogSerializer
    queryset_factory = staticmethod(audit_logs_for_organization)

    @extend_schema(responses=AuditLogSerializer(many=True))
    def get(self, request):
        return super().get(request)


class AuditDataAccessLogsView(_AuditListView):
    serializer_class = AuditDataAccessLogSerializer
    queryset_factory = staticmethod(data_access_logs_for_organization)

    @extend_schema(responses=AuditDataAccessLogSerializer(many=True))
    def get(self, request):
        return super().get(request)


class AuditSecurityEventsView(_AuditListView):
    serializer_class = AuditSecurityEventSerializer
    queryset_factory = staticmethod(security_events_for_organization)

    @extend_schema(responses=AuditSecurityEventSerializer(many=True))
    def get(self, request):
        return super().get(request)


class AuditAIDecisionsView(_AuditListView):
    serializer_class = AuditAIDecisionSerializer
    queryset_factory = staticmethod(ai_decisions_for_organization)

    @extend_schema(responses=AuditAIDecisionSerializer(many=True))
    def get(self, request):
        return super().get(request)


class AuditExternalRequestsView(_AuditListView):
    serializer_class = AuditExternalRequestSerializer
    queryset_factory = staticmethod(external_requests_for_organization)

    @extend_schema(responses=AuditExternalRequestSerializer(many=True))
    def get(self, request):
        return super().get(request)
