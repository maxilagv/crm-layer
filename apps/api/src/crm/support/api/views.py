"""Thin support views: ticket CRUD + actions, known issues."""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.contacts.models import Contact
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.organizations.selectors.organizations import resolve_current_organization
from crm.support.api.filters import known_issue_filters, ticket_filters
from crm.support.api.permissions import SupportPermission
from crm.support.api.serializers import (
    KnownIssueCreateSerializer,
    KnownIssueSerializer,
    KnownIssueUpdateSerializer,
    SupportTicketCommentSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
    SupportTicketUpdateSerializer,
    TicketAssignSerializer,
    TicketAttachmentCreateSerializer,
    TicketCommentCreateSerializer,
    TicketReopenSerializer,
    TicketResolveSerializer,
)
from crm.support.models import SupportKnownIssue
from crm.support.selectors.known_issues import (
    known_issue_for_organization,
    known_issues_for_organization,
)
from crm.support.selectors.ticket_detail import ticket_detail_for_organization
from crm.support.selectors.ticket_list import ticket_list_for_organization
from crm.support.services.ticket_creator import SupportTicketCreator
from crm.support.services.ticket_lifecycle import TicketLifecycleService


def _get_ticket_or_404(organization, ticket_id):
    ticket = ticket_detail_for_organization(organization, ticket_id)
    if ticket is None:
        raise NotFound("Ticket not found in current organization")
    return ticket


class TicketsView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(responses=SupportTicketListSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = ticket_list_for_organization(
            organization, **ticket_filters(request.query_params)
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(SupportTicketListSerializer(page, many=True).data)

    @extend_schema(request=SupportTicketCreateSerializer, responses=SupportTicketDetailSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        contact = Contact.objects.filter(
            organization_id=organization.id, id=data["contact_id"]
        ).first()
        if contact is None:
            raise ValidationError({"contact_id": "Contact not found in current organization"})
        result = SupportTicketCreator.create_manual(
            organization=organization,
            contact=contact,
            payload=data,
            created_by=request.user,
            request=request,
        )
        ticket = ticket_detail_for_organization(organization, result.ticket.id)
        return success_response(request, SupportTicketDetailSerializer(ticket).data, status=201)


class TicketDetailView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(responses=SupportTicketDetailSerializer)
    def get(self, request, ticket_id):
        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        return success_response(request, SupportTicketDetailSerializer(ticket).data)

    @extend_schema(request=SupportTicketUpdateSerializer, responses=SupportTicketDetailSerializer)
    def patch(self, request, ticket_id):
        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        serializer = SupportTicketUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        simple = []
        for field in ("title", "description", "priority", "category", "due_at"):
            if field in data:
                setattr(ticket, field, data[field])
                simple.append(field)
        if simple:
            ticket.save(update_fields=[*simple, "updated_at"])
        if "status" in data:
            TicketLifecycleService.change_status(
                ticket=ticket,
                status=data["status"],
                reason="api_update",
                actor=request.user,
                request=request,
            )
        ticket = ticket_detail_for_organization(organization, ticket.id)
        return success_response(request, SupportTicketDetailSerializer(ticket).data)


class TicketAssignView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(request=TicketAssignSerializer, responses=SupportTicketDetailSerializer)
    def post(self, request, ticket_id):
        from crm.organizations.models import Membership

        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        serializer = TicketAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = (
            Membership.objects.filter(
                organization_id=organization.id,
                user_id=serializer.validated_data["user_id"],
                status=Membership.Status.ACTIVE,
            )
            .select_related("user")
            .first()
        )
        if membership is None:
            raise ValidationError({"user_id": "User is not an active member of this organization"})
        TicketLifecycleService.assign(
            ticket=ticket, user=membership.user, actor=request.user, request=request
        )
        ticket = ticket_detail_for_organization(organization, ticket.id)
        return success_response(request, SupportTicketDetailSerializer(ticket).data)


class TicketResolveView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(request=TicketResolveSerializer, responses=SupportTicketDetailSerializer)
    def post(self, request, ticket_id):
        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        serializer = TicketResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        TicketLifecycleService.resolve(
            ticket=ticket, resolution=serializer.validated_data, actor=request.user, request=request
        )
        ticket = ticket_detail_for_organization(organization, ticket.id)
        return success_response(request, SupportTicketDetailSerializer(ticket).data)


class TicketReopenView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(request=TicketReopenSerializer, responses=SupportTicketDetailSerializer)
    def post(self, request, ticket_id):
        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        serializer = TicketReopenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        TicketLifecycleService.reopen(
            ticket=ticket,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            request=request,
        )
        ticket = ticket_detail_for_organization(organization, ticket.id)
        return success_response(request, SupportTicketDetailSerializer(ticket).data)


class TicketCommentsView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(request=TicketCommentCreateSerializer, responses=SupportTicketCommentSerializer)
    def post(self, request, ticket_id):
        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        serializer = TicketCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = TicketLifecycleService.add_comment(
            ticket=ticket,
            body=serializer.validated_data["body"],
            visibility=serializer.validated_data["visibility"],
            actor=request.user,
            request=request,
        )
        return success_response(request, SupportTicketCommentSerializer(comment).data, status=201)


class TicketAttachmentsView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(request=TicketAttachmentCreateSerializer, responses=None)
    def post(self, request, ticket_id):
        organization = resolve_current_organization(request)
        ticket = _get_ticket_or_404(organization, ticket_id)
        serializer = TicketAttachmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = TicketLifecycleService.add_attachment(
            ticket=ticket,
            media_asset_id=serializer.validated_data["media_asset_id"],
            attachment_type=serializer.validated_data["attachment_type"],
            source_message_id=serializer.validated_data["source_message_id"],
            actor=request.user,
            request=request,
        )
        return success_response(
            request, {"id": str(attachment.id), "ticket_id": str(ticket.id)}, status=201
        )


class KnownIssuesView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(responses=KnownIssueSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = known_issues_for_organization(
            organization, **known_issue_filters(request.query_params)
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(KnownIssueSerializer(page, many=True).data)

    @extend_schema(request=KnownIssueCreateSerializer, responses=KnownIssueSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = KnownIssueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = SupportKnownIssue.objects.create(
            organization_id=organization.id,
            created_by_id=request.user.id,
            **serializer.validated_data,
        )
        return success_response(request, KnownIssueSerializer(issue).data, status=201)


class KnownIssueDetailView(APIView):
    permission_classes = [SupportPermission]

    @extend_schema(responses=KnownIssueSerializer)
    def get(self, request, issue_id):
        organization = resolve_current_organization(request)
        issue = known_issue_for_organization(organization, issue_id)
        if issue is None:
            raise NotFound("Known issue not found in current organization")
        return success_response(request, KnownIssueSerializer(issue).data)

    @extend_schema(request=KnownIssueUpdateSerializer, responses=KnownIssueSerializer)
    def patch(self, request, issue_id):
        organization = resolve_current_organization(request)
        issue = known_issue_for_organization(organization, issue_id)
        if issue is None:
            raise NotFound("Known issue not found in current organization")
        serializer = KnownIssueUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(issue, field, value)
        issue.save()
        return success_response(request, KnownIssueSerializer(issue).data)
