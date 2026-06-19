"""Thin views for the Cazador: campaigns + prospects review queue."""

from django.core.cache import cache
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization
from crm.prospecting.models import Prospect, ProspectingCampaign

from .serializers import (
    CampaignCreateSerializer,
    CampaignUpdateSerializer,
    ProspectingCampaignSerializer,
    ProspectSerializer,
    ProspectUpdateSerializer,
)

# Cooldown locks: stop spam/double POSTs from launching concurrent runs that would
# each burn Google Places quota (discover) or OpenAI + WhatsApp (outreach). Atomic via
# cache.add; auto-expires so a crashed run never blocks forever.
_DISCOVER_LOCK_TTL = 300  # 5 min between discovery runs per campaign
_OUTREACH_LOCK_TTL = 120  # 2 min between outreach runs per campaign


def _acquire_run_lock(kind: str, campaign_id, ttl: int) -> bool:
    """Return True if we got the lock (no run in flight), False if one is already running."""
    return cache.add(f"prospecting:{kind}:{campaign_id}", 1, timeout=ttl)


_CAMPAIGN_WRITE_FIELDS = (
    "name",
    "vertical",
    "query",
    "location_hint",
    "status",
    "channel",
    "source",
    "target_profile",
    "min_fit_score",
    "auto_contact",
    "auto_reply",
    "auto_followup",
    "max_touches",
    "daily_cap",
)


def _get_campaign_or_404(organization, campaign_id) -> ProspectingCampaign:
    campaign = ProspectingCampaign.objects.filter(
        organization_id=organization.id, id=campaign_id
    ).first()
    if campaign is None:
        raise NotFound("Campaña no encontrada en esta organización")
    return campaign


def _get_prospect_or_404(organization, prospect_id) -> Prospect:
    prospect = Prospect.objects.filter(organization_id=organization.id, id=prospect_id).first()
    if prospect is None:
        raise NotFound("Prospecto no encontrado en esta organización")
    return prospect


class CampaignsView(APIView):
    permission_classes = [RequiresPermission]

    @property
    def required_permission(self):
        return (
            PermissionCode.PROSPECTING_MANAGE.value
            if self.request.method == "POST"
            else PermissionCode.PROSPECTING_VIEW.value
        )

    def get(self, request):
        organization = resolve_current_organization(request)
        qs = ProspectingCampaign.objects.filter(organization_id=organization.id)
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        qs = qs.order_by("-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProspectingCampaignSerializer(page, many=True).data)

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = ProspectingCampaign.objects.create(
            organization_id=organization.id,
            created_by_id=request.user.id,
            **serializer.validated_data,
        )
        return success_response(request, ProspectingCampaignSerializer(campaign).data, status=201)


class CampaignDetailView(APIView):
    permission_classes = [RequiresPermission]

    @property
    def required_permission(self):
        return (
            PermissionCode.PROSPECTING_MANAGE.value
            if self.request.method == "PATCH"
            else PermissionCode.PROSPECTING_VIEW.value
        )

    def get(self, request, campaign_id):
        organization = resolve_current_organization(request)
        campaign = _get_campaign_or_404(organization, campaign_id)
        return success_response(request, ProspectingCampaignSerializer(campaign).data)

    def patch(self, request, campaign_id):
        organization = resolve_current_organization(request)
        campaign = _get_campaign_or_404(organization, campaign_id)
        serializer = CampaignUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        dirty = [f for f in _CAMPAIGN_WRITE_FIELDS if f in serializer.validated_data]
        for field in dirty:
            setattr(campaign, field, serializer.validated_data[field])
        if dirty:
            campaign.updated_by_id = request.user.id
            campaign.save(update_fields=[*dirty, "updated_by_id", "updated_at"])
        return success_response(request, ProspectingCampaignSerializer(campaign).data)


class ProspectsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.PROSPECTING_VIEW.value

    def get(self, request):
        organization = resolve_current_organization(request)
        qs = Prospect.objects.filter(organization_id=organization.id)
        params = request.query_params
        if params.get("campaign_id"):
            qs = qs.filter(campaign_id=params["campaign_id"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("min_fit_score"):
            try:
                qs = qs.filter(fit_score__gte=int(params["min_fit_score"]))
            except (TypeError, ValueError):
                pass
        if params.get("search"):
            qs = qs.filter(business_name__icontains=params["search"])
        qs = qs.order_by("-fit_score", "-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProspectSerializer(page, many=True).data)


class ProspectDetailView(APIView):
    permission_classes = [RequiresPermission]

    @property
    def required_permission(self):
        return (
            PermissionCode.PROSPECTING_MANAGE.value
            if self.request.method == "PATCH"
            else PermissionCode.PROSPECTING_VIEW.value
        )

    def get(self, request, prospect_id):
        organization = resolve_current_organization(request)
        prospect = _get_prospect_or_404(organization, prospect_id)
        return success_response(request, ProspectSerializer(prospect).data)

    def patch(self, request, prospect_id):
        organization = resolve_current_organization(request)
        prospect = _get_prospect_or_404(organization, prospect_id)
        serializer = ProspectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prospect.status = serializer.validated_data["status"]
        prospect.updated_by_id = request.user.id
        prospect.save(update_fields=["status", "updated_by_id", "updated_at"])
        return success_response(request, ProspectSerializer(prospect).data)


class CampaignDiscoverView(APIView):
    """Kick off prospect discovery (Google Places) for a campaign."""

    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.PROSPECTING_MANAGE.value
    throttle_scope = "prospecting"

    def post(self, request, campaign_id):
        organization = resolve_current_organization(request)
        campaign = _get_campaign_or_404(organization, campaign_id)
        if not _acquire_run_lock("discover", campaign.id, _DISCOVER_LOCK_TTL):
            return success_response(
                request,
                {"queued": False, "reason": "discovery_already_running"},
                status=429,
            )
        from crm.prospecting.tasks import discover_batch

        discover_batch.delay(campaign_id=str(campaign.id))
        return success_response(
            request, {"queued": True, "campaign_id": str(campaign.id)}, status=202
        )


class CampaignRunOutreachView(APIView):
    """Queue outreach openers for eligible (approved / auto-contact) prospects."""

    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.PROSPECTING_MANAGE.value
    throttle_scope = "prospecting"

    def post(self, request, campaign_id):
        organization = resolve_current_organization(request)
        campaign = _get_campaign_or_404(organization, campaign_id)
        if not _acquire_run_lock("outreach", campaign.id, _OUTREACH_LOCK_TTL):
            return success_response(
                request,
                {"queued": False, "reason": "outreach_already_running"},
                status=429,
            )
        from crm.prospecting.tasks import run_outreach

        run_outreach.delay(campaign_id=str(campaign.id))
        return success_response(
            request, {"queued": True, "campaign_id": str(campaign.id)}, status=202
        )
