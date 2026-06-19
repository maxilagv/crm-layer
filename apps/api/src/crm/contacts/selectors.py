"""Read-side queries for contacts. All are tenant-scoped; mutations live in services."""

import uuid

from django.db.models import Prefetch, Q, QuerySet

from .models import Contact, ContactPhone
from .normalizers import PhoneNormalizationError, normalize_phone


def _primary_first(queryset: QuerySet) -> QuerySet:
    return queryset.order_by("-is_primary", "created_at")


def contact_list_for_organization(
    organization,
    *,
    search: str | None = None,
    type: str | None = None,
    status: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    ordering: str = "-updated_at",
) -> QuerySet[Contact]:
    """Light, tenant-scoped contact list with phones/emails prefetched for previews."""
    queryset = Contact.objects.filter(organization_id=organization.id).prefetch_related(
        Prefetch("phones", queryset=_primary_first(ContactPhone.objects.all())),
        "emails",
    )
    if type:
        queryset = queryset.filter(type=type)
    if status:
        queryset = queryset.filter(status=status)
    if source:
        queryset = queryset.filter(source=source)
    if tag:
        queryset = queryset.filter(tags__slug=tag)
    if search:
        queryset = queryset.filter(
            Q(display_name__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(company_name__icontains=search)
            | Q(phones__phone_e164__icontains=search)
            | Q(emails__normalized_email__icontains=search)
        ).distinct()

    allowed_ordering = {
        "updated_at",
        "-updated_at",
        "created_at",
        "-created_at",
        "display_name",
        "-display_name",
    }
    if ordering not in allowed_ordering:
        ordering = "-updated_at"
    return queryset.order_by(ordering)


def contact_get_for_organization(organization, contact_id: uuid.UUID | str) -> Contact | None:
    return (
        Contact.objects.filter(organization_id=organization.id, id=contact_id)
        .prefetch_related(
            Prefetch("phones", queryset=_primary_first(ContactPhone.objects.all())),
            "emails",
            "tags",
            "company_links__company",
        )
        .first()
    )


def contact_get_by_phone(organization, phone_e164: str) -> Contact | None:
    phone = (
        ContactPhone.objects.filter(organization_id=organization.id, phone_e164=phone_e164)
        .select_related("contact")
        .first()
    )
    return phone.contact if phone else None


def contact_resolve_by_raw_phone(
    organization, raw_phone: str, *, region: str | None = None
) -> Contact | None:
    """Normalize then look up; returns None if the phone is invalid or unknown."""
    try:
        normalized = normalize_phone(raw_phone, region=region)
    except PhoneNormalizationError:
        return None
    return contact_get_by_phone(organization, normalized.e164)


def contact_phones_for_contact(contact) -> QuerySet[ContactPhone]:
    return _primary_first(ContactPhone.objects.filter(contact=contact))


def contact_tags_for_contact(contact):
    from .models import ContactTag

    return ContactTag.objects.filter(contact=contact).order_by("slug")


def contact_notes_visible_to(contact, user) -> QuerySet:
    """Notes for a contact, excluding other users' private notes."""
    return contact.notes.filter(~Q(visibility="private") | Q(author_id=getattr(user, "id", None)))
