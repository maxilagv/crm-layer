"""Thin contact views: parse/validate input, delegate to services/selectors, envelope output."""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.contacts.normalizers import PhoneNormalizationError
from crm.contacts.permissions import (
    ContactDetailPermission,
    ContactsCollectionPermission,
    ContactWritePermission,
)
from crm.contacts.selectors import (
    contact_get_for_organization,
    contact_list_for_organization,
    contact_tags_for_contact,
)
from crm.contacts.services import (
    ContactMerger,
    add_note,
    add_tag,
    create_contact,
    soft_delete_contact,
    update_contact,
)
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.organizations.selectors.organizations import resolve_current_organization

from .serializers import (
    ContactCreateSerializer,
    ContactDetailSerializer,
    ContactListSerializer,
    ContactMergeSerializer,
    ContactNoteCreateSerializer,
    ContactNoteSerializer,
    ContactTagCreateSerializer,
    ContactTagSerializer,
    ContactUpdateSerializer,
)


def _get_contact_or_404(organization, contact_id):
    contact = contact_get_for_organization(organization, contact_id)
    if contact is None:
        raise NotFound("Contact not found in current organization")
    return contact


class ContactsView(APIView):
    permission_classes = [ContactsCollectionPermission]

    @extend_schema(responses=ContactListSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = contact_list_for_organization(
            organization,
            search=request.query_params.get("search"),
            type=request.query_params.get("type"),
            status=request.query_params.get("status"),
            source=request.query_params.get("source"),
            tag=request.query_params.get("tag"),
            ordering=request.query_params.get("ordering", "-updated_at"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = ContactListSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(request=ContactCreateSerializer, responses=ContactDetailSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = ContactCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            contact = create_contact(
                organization=organization,
                actor=request.user,
                request=request,
                display_name=payload["display_name"],
                first_name=payload["first_name"],
                last_name=payload["last_name"],
                company_name=payload["company_name"],
                source=payload["source"],
                type=payload["type"],
                status=payload["status"],
                language=payload.get("language") or None,
                timezone_name=payload.get("timezone") or None,
                avatar_url=payload["avatar_url"],
                summary=payload["summary"],
                metadata=payload["metadata"],
                phones=payload["phones"],
                emails=payload["emails"],
            )
        except PhoneNormalizationError as exc:
            raise ValidationError({"phones": [str(exc)]}) from exc

        contact = contact_get_for_organization(organization, contact.id)
        return success_response(request, ContactDetailSerializer(contact).data, status=201)


class ContactDetailView(APIView):
    permission_classes = [ContactDetailPermission]

    @extend_schema(responses=ContactDetailSerializer)
    def get(self, request, contact_id):
        organization = resolve_current_organization(request)
        contact = _get_contact_or_404(organization, contact_id)
        return success_response(request, ContactDetailSerializer(contact).data)

    @extend_schema(request=ContactUpdateSerializer, responses=ContactDetailSerializer)
    def patch(self, request, contact_id):
        organization = resolve_current_organization(request)
        contact = _get_contact_or_404(organization, contact_id)
        serializer = ContactUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_contact(
            contact=contact, actor=request.user, request=request, data=serializer.validated_data
        )
        contact = contact_get_for_organization(organization, contact.id)
        return success_response(request, ContactDetailSerializer(contact).data)

    @extend_schema(request=None, responses=None)
    def delete(self, request, contact_id):
        organization = resolve_current_organization(request)
        contact = _get_contact_or_404(organization, contact_id)
        soft_delete_contact(contact=contact, actor=request.user, request=request)
        return success_response(request, {"status": "deleted", "id": str(contact.id)})


@extend_schema(request=ContactNoteCreateSerializer, responses=ContactNoteSerializer)
class ContactNotesView(APIView):
    permission_classes = [ContactWritePermission]

    def post(self, request, contact_id):
        organization = resolve_current_organization(request)
        contact = _get_contact_or_404(organization, contact_id)
        serializer = ContactNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = add_note(
            contact=contact,
            author=request.user,
            body=serializer.validated_data["body"],
            visibility=serializer.validated_data["visibility"],
            request=request,
        )
        return success_response(request, ContactNoteSerializer(note).data, status=201)


@extend_schema(request=ContactTagCreateSerializer, responses=ContactTagSerializer(many=True))
class ContactTagsView(APIView):
    permission_classes = [ContactWritePermission]

    def post(self, request, contact_id):
        organization = resolve_current_organization(request)
        contact = _get_contact_or_404(organization, contact_id)
        serializer = ContactTagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        add_tag(
            contact=contact,
            name=serializer.validated_data["name"],
            color=serializer.validated_data["color"],
            actor=request.user,
        )
        tags = contact_tags_for_contact(contact)
        return success_response(request, ContactTagSerializer(tags, many=True).data, status=201)


@extend_schema(request=ContactMergeSerializer, responses=ContactDetailSerializer)
class ContactMergeView(APIView):
    permission_classes = [ContactWritePermission]

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = ContactMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = _get_contact_or_404(organization, serializer.validated_data["source_contact_id"])
        target = _get_contact_or_404(organization, serializer.validated_data["target_contact_id"])
        merged = ContactMerger.merge(
            organization=organization,
            source=source,
            target=target,
            strategy=serializer.validated_data["strategy"],
            actor=request.user,
            request=request,
        )
        merged = contact_get_for_organization(organization, merged.id)
        return success_response(request, ContactDetailSerializer(merged).data)
