"""Thin client views: CRUD + contacts/services sub-resources."""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.clients.api.filters import client_filters
from crm.clients.api.permissions import ClientsPermission
from crm.clients.api.serializers import (
    ClientContactCreateSerializer,
    ClientContactSerializer,
    ClientCreateSerializer,
    ClientDetailSerializer,
    ClientListSerializer,
    ClientServiceCreateSerializer,
    ClientServiceSerializer,
    ClientUpdateSerializer,
)
from crm.clients.models import Client
from crm.clients.selectors.client_contacts import contacts_for_client, services_for_client
from crm.clients.selectors.client_detail import client_detail_for_organization
from crm.clients.selectors.client_list import client_list_for_organization
from crm.clients.services.client_contact import ClientContactService
from crm.clients.services.client_lifecycle import change_status
from crm.clients.services.client_registration import ClientRegistrationService
from crm.clients.services.client_service_manager import ClientServiceManager
from crm.contacts.models import Contact
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.organizations.selectors.organizations import resolve_current_organization

UPDATABLE_FIELDS = ("display_name", "service_plan", "support_level", "onboarding_status")


def _get_client_or_404(organization, client_id) -> Client:
    client = client_detail_for_organization(organization, client_id)
    if client is None:
        raise NotFound("Client not found in current organization")
    return client


def _get_contact_or_400(organization, contact_id) -> Contact:
    contact = Contact.objects.filter(organization_id=organization.id, id=contact_id).first()
    if contact is None:
        raise ValidationError({"contact_id": "Contact not found in current organization"})
    return contact


class ClientsView(APIView):
    permission_classes = [ClientsPermission]

    @extend_schema(responses=ClientListSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = client_list_for_organization(
            organization, **client_filters(request.query_params)
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(ClientListSerializer(page, many=True).data)

    @extend_schema(request=ClientCreateSerializer, responses=ClientDetailSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = ClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = _get_contact_or_400(organization, serializer.validated_data["contact_id"])
        result = ClientRegistrationService.register(
            organization=organization,
            contact=contact,
            display_name=serializer.validated_data["display_name"],
            service_plan=serializer.validated_data["service_plan"],
            support_level=serializer.validated_data["support_level"],
            actor=request.user,
            request=request,
            raise_on_duplicate=True,
        )
        client = client_detail_for_organization(organization, result.client.id)
        return success_response(request, ClientDetailSerializer(client).data, status=201)


class ClientDetailView(APIView):
    permission_classes = [ClientsPermission]

    @extend_schema(responses=ClientDetailSerializer)
    def get(self, request, client_id):
        organization = resolve_current_organization(request)
        client = _get_client_or_404(organization, client_id)
        return success_response(request, ClientDetailSerializer(client).data)

    @extend_schema(request=ClientUpdateSerializer, responses=ClientDetailSerializer)
    def patch(self, request, client_id):
        organization = resolve_current_organization(request)
        client = _get_client_or_404(organization, client_id)
        serializer = ClientUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        dirty = []
        for field in UPDATABLE_FIELDS:
            if field in data:
                setattr(client, field, data[field])
                dirty.append(field)
        if dirty:
            client.updated_by_id = request.user.id
            client.save(update_fields=[*dirty, "updated_by_id", "updated_at"])
        if "status" in data:
            change_status(
                client=client,
                to_status=data["status"],
                reason="api_update",
                actor=request.user,
                request=request,
            )
        client = client_detail_for_organization(organization, client.id)
        return success_response(request, ClientDetailSerializer(client).data)


class ClientContactsView(APIView):
    permission_classes = [ClientsPermission]

    @extend_schema(responses=ClientContactSerializer(many=True))
    def get(self, request, client_id):
        organization = resolve_current_organization(request)
        client = _get_client_or_404(organization, client_id)
        return success_response(
            request, ClientContactSerializer(contacts_for_client(client), many=True).data
        )

    @extend_schema(request=ClientContactCreateSerializer, responses=ClientContactSerializer)
    def post(self, request, client_id):
        organization = resolve_current_organization(request)
        client = _get_client_or_404(organization, client_id)
        serializer = ClientContactCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = _get_contact_or_400(organization, serializer.validated_data["contact_id"])
        link = ClientContactService.add_contact(
            client=client,
            contact=contact,
            role=serializer.validated_data["role"],
            is_primary=serializer.validated_data["is_primary"],
            can_request_support=serializer.validated_data["can_request_support"],
            receives_notifications=serializer.validated_data["receives_notifications"],
            actor=request.user,
            request=request,
        )
        return success_response(request, ClientContactSerializer(link).data, status=201)


class ClientServicesView(APIView):
    permission_classes = [ClientsPermission]

    @extend_schema(responses=ClientServiceSerializer(many=True))
    def get(self, request, client_id):
        organization = resolve_current_organization(request)
        client = _get_client_or_404(organization, client_id)
        return success_response(
            request, ClientServiceSerializer(services_for_client(client), many=True).data
        )

    @extend_schema(request=ClientServiceCreateSerializer, responses=ClientServiceSerializer)
    def post(self, request, client_id):
        organization = resolve_current_organization(request)
        client = _get_client_or_404(organization, client_id)
        serializer = ClientServiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = ClientServiceManager.add_service(
            client=client, actor=request.user, request=request, **serializer.validated_data
        )
        return success_response(request, ClientServiceSerializer(service).data, status=201)
