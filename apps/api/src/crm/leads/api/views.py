from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.leads.api.serializers import (
    LeadConvertSerializer,
    LeadCreateSerializer,
    LeadDetailSerializer,
    LeadFollowupSerializer,
    LeadListSerializer,
    LeadMarkLostSerializer,
    LeadScoreRequestSerializer,
    LeadScoreSnapshotSerializer,
    LeadUpdateSerializer,
)
from crm.leads.selectors.lead_detail import lead_get_for_organization
from crm.leads.selectors.lead_list import lead_list_for_organization
from crm.leads.services.lead_conversion import convert_to_client
from crm.leads.services.lead_creation import create_manual_lead
from crm.leads.services.lead_followup import schedule_followup
from crm.leads.services.lead_lifecycle import change_stage, mark_lost
from crm.leads.services.lead_scoring import score_lead
from crm.organizations.selectors.organizations import resolve_current_organization


def _get_lead_or_404(organization, lead_id):
    lead = lead_get_for_organization(organization, lead_id)
    if lead is None:
        raise NotFound("Lead not found in current organization")
    return lead


class LeadsView(APIView):
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

    @extend_schema(responses={200: LeadListSerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = lead_list_for_organization(
            organization,
            stage=request.query_params.get("stage"),
            status=request.query_params.get("status"),
            temperature=request.query_params.get("temperature"),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering", "-updated_at"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(LeadListSerializer(page, many=True).data)

    @extend_schema(request=LeadCreateSerializer, responses={201: LeadDetailSerializer})
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = LeadCreateSerializer(data=request.data, context={"organization": organization})
        serializer.is_valid(raise_exception=True)
        result = create_manual_lead(
            organization=organization,
            contact=serializer.context["contact"],
            actor=request.user,
            request=request,
            source_type=serializer.validated_data["source_type"],
            metadata=serializer.validated_data.get("metadata", {}),
        )
        if result.lead is None:
            raise ValidationError({"contact_id": result.reason})
        lead = lead_get_for_organization(organization, result.lead.id)
        return success_response(
            request,
            LeadDetailSerializer(lead).data,
            status=201 if result.created else 200,
        )


class LeadDetailView(APIView):
    permission_classes = [RequiresPermission]

    def get_required_permission(self):
        return (
            PermissionCode.LEADS_UPDATE.value
            if self.request.method == "PATCH"
            else PermissionCode.LEADS_VIEW.value
        )

    @property
    def required_permission(self):
        return self.get_required_permission()

    @extend_schema(responses={200: LeadDetailSerializer})
    def get(self, request, lead_id):
        organization = resolve_current_organization(request)
        return success_response(
            request, LeadDetailSerializer(_get_lead_or_404(organization, lead_id)).data
        )

    @extend_schema(request=LeadUpdateSerializer, responses={200: LeadDetailSerializer})
    def patch(self, request, lead_id):
        organization = resolve_current_organization(request)
        lead = _get_lead_or_404(organization, lead_id)
        serializer = LeadUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        reason = data.pop("reason", "")
        to_stage = data.pop("stage", None)
        if to_stage:
            lead = change_stage(
                lead=lead, to_stage=to_stage, reason=reason, actor=request.user, request=request
            )
        mutable = [
            "status",
            "temperature",
            "service_interest",
            "budget_signal",
            "urgency",
            "authority_signal",
            "pain_points",
            "technical_needs",
            "business_needs",
            "next_best_action",
            "summary",
            "metadata",
        ]
        changed = []
        for field in mutable:
            if field in data:
                setattr(lead, field, data[field])
                changed.append(field)
        if changed:
            lead.updated_by_id = request.user.id
            lead.save(update_fields=[*changed, "updated_by_id", "updated_at"])
        lead = lead_get_for_organization(organization, lead.id)
        return success_response(request, LeadDetailSerializer(lead).data)


class LeadScoreView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.LEADS_UPDATE.value

    @extend_schema(request=LeadScoreRequestSerializer, responses={200: LeadScoreSnapshotSerializer})
    def post(self, request, lead_id):
        organization = resolve_current_organization(request)
        lead = _get_lead_or_404(organization, lead_id)
        serializer = LeadScoreRequestSerializer(
            data=request.data, context={"organization": organization}
        )
        serializer.is_valid(raise_exception=True)
        result = score_lead(
            lead=lead,
            conversation=serializer.context.get("conversation"),
            use_ai=serializer.validated_data.get("use_ai", True),
            actor=request.user,
            request=request,
        )
        if not result.updated:
            raise ValidationError({"ai": result.reason})
        return success_response(request, LeadScoreSnapshotSerializer(result.snapshot).data)


class LeadConvertToClientView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.LEADS_UPDATE.value

    @extend_schema(request=LeadConvertSerializer, responses={200: LeadDetailSerializer})
    def post(self, request, lead_id):
        organization = resolve_current_organization(request)
        lead = _get_lead_or_404(organization, lead_id)
        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = convert_to_client(
            lead=lead,
            actor=request.user,
            request=request,
            reason=serializer.validated_data.get("reason", ""),
        )
        return success_response(
            request, LeadDetailSerializer(lead_get_for_organization(organization, lead.id)).data
        )


class LeadMarkLostView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.LEADS_UPDATE.value

    @extend_schema(request=LeadMarkLostSerializer, responses={200: LeadDetailSerializer})
    def post(self, request, lead_id):
        organization = resolve_current_organization(request)
        lead = _get_lead_or_404(organization, lead_id)
        serializer = LeadMarkLostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = mark_lost(
            lead=lead,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            request=request,
        )
        return success_response(
            request, LeadDetailSerializer(lead_get_for_organization(organization, lead.id)).data
        )


class LeadScheduleFollowupView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.LEADS_UPDATE.value

    @extend_schema(request=LeadFollowupSerializer, responses={201: dict})
    def post(self, request, lead_id):
        organization = resolve_current_organization(request)
        lead = _get_lead_or_404(organization, lead_id)
        serializer = LeadFollowupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        followup, created = schedule_followup(
            lead=lead,
            due_at=serializer.validated_data.get("due_at"),
            title=serializer.validated_data.get("title", "Seguimiento comercial"),
            notes=serializer.validated_data.get("notes", ""),
            actor=request.user,
            idempotency_key=serializer.validated_data.get("idempotency_key", ""),
        )
        return success_response(
            request,
            {"id": str(followup.id), "created": created},
            status=201 if created else 200,
        )
