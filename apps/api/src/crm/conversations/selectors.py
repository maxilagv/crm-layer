"""Read-side queries for conversations and messages (tenant-scoped, N+1-free)."""

import uuid

from django.db.models import F, OuterRef, Prefetch, Q, QuerySet, Subquery

from crm.contacts.models import ContactPhone

from .models import Conversation, Message


def conversation_list_for_inbox(
    organization,
    *,
    status: str | None = None,
    mode: str | None = None,
    channel: str | None = None,
    assigned_user_id: str | None = None,
    contact_id: str | None = None,
    ai_enabled: bool | None = None,
    search: str | None = None,
) -> QuerySet[Conversation]:
    """Inbox list: contact + assigned_user joined, last-message preview annotated
    via correlated subqueries, primary phone prefetched — one query, no N+1."""
    latest = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at")
    queryset = (
        Conversation.objects.filter(organization_id=organization.id)
        .select_related("contact", "assigned_user")
        .prefetch_related(
            Prefetch(
                "contact__phones",
                queryset=ContactPhone.objects.order_by("-is_primary", "created_at"),
            )
        )
        .annotate(
            last_message_id=Subquery(latest.values("id")[:1]),
            last_message_body=Subquery(latest.values("body")[:1]),
            last_message_direction=Subquery(latest.values("direction")[:1]),
            last_message_type=Subquery(latest.values("message_type")[:1]),
            last_message_status=Subquery(latest.values("status")[:1]),
            last_message_created_at=Subquery(latest.values("created_at")[:1]),
        )
    )

    if status:
        queryset = queryset.filter(status=status)
    if mode:
        queryset = queryset.filter(mode=mode)
    if channel:
        queryset = queryset.filter(channel=channel)
    if assigned_user_id:
        queryset = queryset.filter(assigned_user_id=assigned_user_id)
    if contact_id:
        queryset = queryset.filter(contact_id=contact_id)
    if ai_enabled is not None:
        queryset = queryset.filter(ai_enabled=ai_enabled)
    if search:
        queryset = queryset.filter(
            Q(contact__display_name__icontains=search)
            | Q(contact__phones__phone_e164__icontains=search)
        ).distinct()

    return queryset.order_by(F("last_message_at").desc(nulls_last=True), "-updated_at")


def conversation_get_for_organization(
    organization, conversation_id: uuid.UUID | str
) -> Conversation | None:
    return (
        Conversation.objects.filter(organization_id=organization.id, id=conversation_id)
        .select_related("contact", "assigned_user")
        .prefetch_related(
            Prefetch(
                "contact__phones",
                queryset=ContactPhone.objects.order_by("-is_primary", "created_at"),
            )
        )
        .first()
    )


def messages_for_conversation(conversation) -> QuerySet[Message]:
    return conversation.messages.prefetch_related("attachments").order_by("created_at")


def conversation_last_message(conversation) -> Message | None:
    return conversation.messages.order_by("-created_at").first()
