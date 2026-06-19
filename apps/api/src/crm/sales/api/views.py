from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization
from crm.sales.api.serializers import (
    SalesCallRequestMarkScheduledSerializer,
    SalesCallRequestSerializer,
    SalesOpportunityCreateSerializer,
    SalesOpportunitySerializer,
)
from crm.sales.selectors.call_requests import (
    call_request_get_for_organization,
    call_requests_for_organization,
)
from crm.sales.selectors.opportunities import opportunities_for_organization
from crm.sales.services.opportunity_service import create_opportunity
from crm.sales.services.sales_call_closer import mark_call_request_scheduled


class SalesOpportunitiesView(APIView):
    permission_classes = [RequiresPermission]

    def get_required_permission(self):
        return (
            PermissionCode.LEADS_UPDATE.value
            if self.request.method == "POST"
            else PermissionCode.LEADS_VIEW.value
        )

    @property
    def required_permission(self):
        return self.get_required_permission()

    @extend_schema(responses={200: SalesOpportunitySerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = opportunities_for_organization(
            organization,
            stage=request.query_params.get("stage"),
            lead_id=request.query_params.get("lead_id"),
            ordering=request.query_params.get("ordering", "-updated_at"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(SalesOpportunitySerializer(page, many=True).data)

    @extend_schema(
        request=SalesOpportunityCreateSerializer, responses={201: SalesOpportunitySerializer}
    )
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = SalesOpportunityCreateSerializer(
            data=request.data, context={"organization": organization}
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("lead_id", None)
        opportunity = create_opportunity(
            lead=serializer.context["lead"],
            actor=request.user,
            **data,
        )
        return success_response(request, SalesOpportunitySerializer(opportunity).data, status=201)


class SalesCallRequestsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.LEADS_VIEW.value

    @extend_schema(responses={200: SalesCallRequestSerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = call_requests_for_organization(
            organization,
            status=request.query_params.get("status"),
            lead_id=request.query_params.get("lead_id"),
            ordering=request.query_params.get("ordering", "-requested_at"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(SalesCallRequestSerializer(page, many=True).data)


class SalesCallRequestMarkScheduledView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.LEADS_UPDATE.value

    @extend_schema(
        request=SalesCallRequestMarkScheduledSerializer, responses={200: SalesCallRequestSerializer}
    )
    def post(self, request, call_request_id):
        organization = resolve_current_organization(request)
        call_request = call_request_get_for_organization(organization, call_request_id)
        if call_request is None:
            raise NotFound("Call request not found in current organization")
        serializer = SalesCallRequestMarkScheduledSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheduled = mark_call_request_scheduled(
            call_request=call_request,
            scheduled_at=serializer.validated_data["scheduled_at"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return success_response(request, SalesCallRequestSerializer(scheduled).data)
