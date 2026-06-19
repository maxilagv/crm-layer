"""Write-side operations for contacts.

Mutations live here (not in views/models). Every mutation that changes business
state also records a :class:`ContactEvent` and, where relevant, an outbox event
(in the same transaction) and an audit entry for human actions.
"""

import uuid
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event

from .constants import (
    EVENT_CONTACT_CREATED,
    EVENT_CONTACT_UPDATED,
    ContactSource,
    ContactStatus,
    ContactType,
)
from .exceptions import Conflict, ContactMergeError, PhoneConflictError
from .models import (
    Contact,
    ContactEmail,
    ContactEvent,
    ContactNote,
    ContactPhone,
    ContactTag,
)
from .normalizers import normalize_email, normalize_phone

# Fields a PATCH is allowed to change (organization_id is never mutable).
UPDATABLE_CONTACT_FIELDS = (
    "display_name",
    "first_name",
    "last_name",
    "company_name",
    "type",
    "status",
    "language",
    "timezone",
    "avatar_url",
    "summary",
    "source",
)


def derive_display_name(
    *, first_name: str = "", last_name: str = "", company_name: str = "", fallback: str = ""
) -> str:
    full = f"{first_name} {last_name}".strip()
    return full or company_name.strip() or fallback.strip() or "Contacto sin nombre"


def _actor_id(actor) -> uuid.UUID | None:
    return getattr(actor, "id", None)


def _emit_event(event_type: str, *, organization_id, data: dict, request=None) -> None:
    """Persist a versioned internal event via the outbox (same transaction)."""
    create_outbox_event(
        event_type=event_type,
        organization_id=organization_id,
        payload={
            "event_type": event_type,
            "organization_id": str(organization_id),
            "data": data,
            "metadata": {"request_id": getattr(request, "request_id", None)},
        },
    )


def _record_contact_event(contact: Contact, event_type: str, payload: dict) -> ContactEvent:
    return ContactEvent.objects.create(
        organization_id=contact.organization_id,
        contact=contact,
        event_type=event_type,
        payload=payload,
        occurred_at=timezone.now(),
    )


# --- phones / emails -------------------------------------------------------


def _set_primary_phone(contact: Contact, keep_id: uuid.UUID) -> None:
    ContactPhone.objects.filter(contact=contact, is_primary=True).exclude(id=keep_id).update(
        is_primary=False
    )


@transaction.atomic
def add_phone_to_contact(
    *,
    contact: Contact,
    raw_phone: str,
    region: str | None = None,
    is_primary: bool | None = None,
    is_whatsapp: bool = False,
    verified_at=None,
) -> ContactPhone:
    """Normalize to E.164 and attach. First phone becomes primary by default.

    Enforces a single primary phone per contact inside the transaction. Raises
    :class:`PhoneConflictError` if the number already exists in the organization.
    """
    normalized = normalize_phone(raw_phone, region=region)
    has_existing = contact.phones.exists()
    make_primary = (not has_existing) if is_primary is None else is_primary

    try:
        phone = ContactPhone.objects.create(
            organization_id=contact.organization_id,
            contact=contact,
            phone_e164=normalized.e164,
            country_code=normalized.country_code,
            is_primary=make_primary,
            is_whatsapp=is_whatsapp,
            verified_at=verified_at,
        )
    except IntegrityError as exc:
        raise PhoneConflictError() from exc

    if make_primary:
        _set_primary_phone(contact, keep_id=phone.id)
    return phone


@transaction.atomic
def add_email_to_contact(
    *,
    contact: Contact,
    raw_email: str,
    is_primary: bool | None = None,
    verified_at=None,
) -> ContactEmail:
    normalized = normalize_email(raw_email)
    has_existing = contact.emails.exists()
    make_primary = (not has_existing) if is_primary is None else is_primary
    try:
        email = ContactEmail.objects.create(
            organization_id=contact.organization_id,
            contact=contact,
            email=raw_email.strip(),
            normalized_email=normalized,
            is_primary=make_primary,
            verified_at=verified_at,
        )
    except IntegrityError as exc:
        raise Conflict(detail="Email already belongs to another contact") from exc
    if make_primary:
        ContactEmail.objects.filter(contact=contact, is_primary=True).exclude(id=email.id).update(
            is_primary=False
        )
    return email


# --- contact CRUD ----------------------------------------------------------


@transaction.atomic
def create_contact(
    *,
    organization,
    actor=None,
    request=None,
    display_name: str = "",
    first_name: str = "",
    last_name: str = "",
    company_name: str = "",
    source: str = ContactSource.MANUAL,
    type: str = ContactType.UNKNOWN,
    status: str = ContactStatus.ACTIVE,
    language: str | None = None,
    timezone_name: str | None = None,
    avatar_url: str = "",
    summary: str = "",
    metadata: dict | None = None,
    phones: list[dict] | None = None,
    emails: list[dict] | None = None,
    region: str | None = None,
) -> Contact:
    """Create a contact with optional phones/emails. Phone numbers are normalized
    and checked for conflicts up front so the operation never partially commits."""
    phones = phones or []
    emails = emails or []

    # Normalize + conflict-check phones before any write.
    prepared_phones = []
    for spec in phones:
        normalized = normalize_phone(spec["phone"], region=region)
        if ContactPhone.objects.filter(
            organization_id=organization.id, phone_e164=normalized.e164
        ).exists():
            raise PhoneConflictError()
        prepared_phones.append((normalized, spec))

    display = display_name or derive_display_name(
        first_name=first_name,
        last_name=last_name,
        company_name=company_name,
        fallback=prepared_phones[0][0].e164 if prepared_phones else "",
    )

    contact = Contact.objects.create(
        organization_id=organization.id,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
        display_name=display,
        first_name=first_name,
        last_name=last_name,
        company_name=company_name,
        source=source,
        type=type,
        status=status,
        language=language or organization.default_language,
        timezone=timezone_name or organization.default_timezone,
        avatar_url=avatar_url,
        summary=summary,
        metadata=metadata or {},
    )

    for index, (normalized, spec) in enumerate(prepared_phones):
        is_primary = spec.get("is_primary", index == 0)
        phone = ContactPhone.objects.create(
            organization_id=organization.id,
            contact=contact,
            phone_e164=normalized.e164,
            country_code=normalized.country_code,
            is_primary=is_primary,
            is_whatsapp=spec.get("is_whatsapp", False),
        )
        if is_primary:
            _set_primary_phone(contact, keep_id=phone.id)

    for index, spec in enumerate(emails):
        add_email_to_contact(
            contact=contact,
            raw_email=spec["email"],
            is_primary=spec.get("is_primary", index == 0),
        )

    _record_contact_event(contact, EVENT_CONTACT_CREATED, {"source": source, "type": type})
    _emit_event(
        EVENT_CONTACT_CREATED,
        organization_id=organization.id,
        data={"contact_id": str(contact.id), "type": type, "source": source},
        request=request,
    )
    if actor is not None:
        audit_event_create(
            event_type="contact_created",
            actor=actor,
            organization=organization,
            request=request,
            resource_type="contacts_contact",
            resource_id=str(contact.id),
        )
    return contact


@transaction.atomic
def update_contact(*, contact: Contact, actor=None, request=None, data: dict) -> Contact:
    changes: dict[str, dict] = {}
    for field in UPDATABLE_CONTACT_FIELDS:
        if field not in data:
            continue
        new_value = data[field]
        old_value = getattr(contact, field)
        if old_value != new_value:
            changes[field] = {"before": old_value, "after": new_value}
            setattr(contact, field, new_value)

    if "metadata" in data and isinstance(data["metadata"], dict):
        merged = {**(contact.metadata or {}), **data["metadata"]}
        if merged != contact.metadata:
            changes["metadata"] = {"before": contact.metadata, "after": merged}
            contact.metadata = merged

    if not changes:
        return contact

    contact.updated_by_id = _actor_id(actor)
    contact.save()

    _record_contact_event(contact, EVENT_CONTACT_UPDATED, {"fields": sorted(changes)})
    _emit_event(
        EVENT_CONTACT_UPDATED,
        organization_id=contact.organization_id,
        data={"contact_id": str(contact.id), "fields": sorted(changes)},
        request=request,
    )
    if actor is not None:
        audit_event_create(
            event_type="contact_updated",
            actor=actor,
            organization=_org_stub(contact.organization_id),
            request=request,
            resource_type="contacts_contact",
            resource_id=str(contact.id),
            changes=changes,
        )
    return contact


@transaction.atomic
def soft_delete_contact(*, contact: Contact, actor=None, request=None) -> None:
    contact.soft_delete()
    _record_contact_event(contact, "contact.deleted.v1", {})
    if actor is not None:
        audit_event_create(
            event_type="contact_deleted",
            actor=actor,
            organization=_org_stub(contact.organization_id),
            request=request,
            resource_type="contacts_contact",
            resource_id=str(contact.id),
        )


# --- notes / tags ----------------------------------------------------------


@transaction.atomic
def add_note(
    *, contact: Contact, author=None, body: str, visibility: str, request=None
) -> ContactNote:
    note = ContactNote.objects.create(
        organization_id=contact.organization_id,
        contact=contact,
        author=author,
        body=body,
        visibility=visibility,
        created_by_id=_actor_id(author),
    )
    return note


@transaction.atomic
def add_tag(*, contact: Contact, name: str, color: str = "", actor=None) -> ContactTag:
    slug = slugify(name)
    tag, _created = ContactTag.objects.get_or_create(
        organization_id=contact.organization_id,
        contact=contact,
        slug=slug,
        defaults={"name": name.strip(), "color": color, "created_by_id": _actor_id(actor)},
    )
    return tag


# --- services --------------------------------------------------------------


@dataclass(frozen=True)
class ResolveResult:
    contact: Contact | None
    created: bool
    matched_by: str | None
    phone: ContactPhone | None


class ContactResolver:
    """Resolve a contact by phone deterministically; optionally create one."""

    @staticmethod
    def resolve_by_phone(
        *,
        organization,
        raw_phone: str,
        region: str | None = None,
        create: bool = True,
        contact_type: str = ContactType.UNKNOWN,
        source: str = ContactSource.WHATSAPP,
        is_whatsapp: bool = True,
        request=None,
    ) -> ResolveResult:
        normalized = normalize_phone(raw_phone, region=region)
        existing = (
            ContactPhone.objects.filter(organization_id=organization.id, phone_e164=normalized.e164)
            .select_related("contact")
            .first()
        )
        if existing is not None:
            return ResolveResult(
                contact=existing.contact, created=False, matched_by="phone", phone=existing
            )
        if not create:
            return ResolveResult(contact=None, created=False, matched_by=None, phone=None)

        try:
            with transaction.atomic():
                contact = Contact.objects.create(
                    organization_id=organization.id,
                    display_name=normalized.e164,
                    source=source,
                    type=contact_type,
                    language=organization.default_language,
                    timezone=organization.default_timezone,
                )
                phone = ContactPhone.objects.create(
                    organization_id=organization.id,
                    contact=contact,
                    phone_e164=normalized.e164,
                    country_code=normalized.country_code,
                    is_primary=True,
                    is_whatsapp=is_whatsapp,
                )
                _record_contact_event(contact, EVENT_CONTACT_CREATED, {"source": source})
                _emit_event(
                    EVENT_CONTACT_CREATED,
                    organization_id=organization.id,
                    data={"contact_id": str(contact.id), "matched_by": "phone", "created": True},
                    request=request,
                )
        except IntegrityError:
            # Concurrent creation of the same number; recover the winner.
            existing = (
                ContactPhone.objects.filter(
                    organization_id=organization.id, phone_e164=normalized.e164
                )
                .select_related("contact")
                .first()
            )
            return ResolveResult(
                contact=existing.contact if existing else None,
                created=False,
                matched_by="phone",
                phone=existing,
            )
        return ResolveResult(contact=contact, created=True, matched_by="phone", phone=phone)


class ContactClassifier:
    """Rule-based contact classification (no AI in this phase)."""

    @staticmethod
    def classify(contact: Contact) -> str:
        if contact.status == ContactStatus.BLOCKED or contact.type == ContactType.BLOCKED:
            return ContactType.BLOCKED.value
        # Placeholder for future rules/AI; manual classification is authoritative.
        return contact.type


class ContactMerger:
    """Merge a duplicate source contact into a target, preserving all data."""

    RELATION_ATTRS = ("phones", "emails", "notes", "tags", "events", "company_links")

    @staticmethod
    @transaction.atomic
    def merge(
        *,
        organization,
        source: Contact,
        target: Contact,
        strategy: str = "prefer_target",
        actor=None,
        request=None,
    ) -> Contact:
        if source.id == target.id:
            raise ContactMergeError(detail="Cannot merge a contact into itself")
        if not (source.organization_id == target.organization_id == organization.id):
            raise ContactMergeError(detail="Cross-tenant merge is not allowed")

        from crm.conversations.models import (  # local import avoids app-load cycle
            Conversation,
            ConversationMemory,
            Message,
        )

        # Phones/emails have org-unique values, so they never collide across contacts.
        source.phones.update(contact=target, is_primary=False)
        source.emails.update(contact=target, is_primary=False)
        source.notes.update(contact=target)
        source.events.update(contact=target)

        # Tags/company links can collide on the target's unique key: drop dupes.
        target_slugs = set(target.tags.values_list("slug", flat=True))
        for tag in source.tags.all():
            if tag.slug in target_slugs:
                tag.delete()
            else:
                tag.contact = target
                tag.save(update_fields=["contact", "updated_at"])
        target_company_ids = set(target.company_links.values_list("company_id", flat=True))
        for link in source.company_links.all():
            if link.company_id in target_company_ids:
                link.delete()
            else:
                link.contact = target
                link.save(update_fields=["contact", "updated_at"])

        Conversation.objects.filter(contact=source).update(contact=target)
        Message.objects.filter(contact=source).update(contact=target)
        ConversationMemory.objects.filter(contact=source).update(contact=target)

        if strategy == "prefer_source":
            for field in ("first_name", "last_name", "company_name", "summary", "avatar_url"):
                value = getattr(source, field)
                if value:
                    setattr(target, field, value)
            target.save()

        source.status = ContactStatus.ARCHIVED
        source.save(update_fields=["status", "updated_at"])
        source.soft_delete()

        _record_contact_event(target, "contact.merged.v1", {"source_contact_id": str(source.id)})
        _emit_event(
            EVENT_CONTACT_UPDATED,
            organization_id=organization.id,
            data={"contact_id": str(target.id), "merged_from": str(source.id)},
            request=request,
        )
        if actor is not None:
            audit_event_create(
                event_type="contact_merged",
                actor=actor,
                organization=organization,
                request=request,
                resource_type="contacts_contact",
                resource_id=str(target.id),
                metadata={"source_contact_id": str(source.id), "strategy": strategy},
            )
        target.refresh_from_db()
        return target


def _org_stub(organization_id):
    """Lightweight object carrying ``.id`` for audit calls that only need the id."""

    class _Org:
        id = organization_id

    return _Org()
