"""Serializers for the contacts API.

List serializers stay light (primary phone/email as flat strings from prefetched
relations — no N+1). Write serializers validate choices and phone shape but
delegate persistence to services. ``organization_id`` and ``metadata`` internals
are never writable from the client.
"""

from rest_framework import serializers

from crm.contacts.constants import (
    ContactSource,
    ContactStatus,
    ContactType,
    NoteVisibility,
)
from crm.contacts.models import (
    Company,
    Contact,
    ContactCompany,
    ContactEmail,
    ContactNote,
    ContactPhone,
    ContactTag,
)


class ContactPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPhone
        fields = ["id", "phone_e164", "country_code", "is_primary", "is_whatsapp", "verified_at"]
        read_only_fields = fields


class ContactEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactEmail
        fields = ["id", "email", "normalized_email", "is_primary", "verified_at"]
        read_only_fields = fields


class ContactTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactTag
        fields = ["id", "name", "slug", "color"]
        read_only_fields = ["id", "slug"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "website", "industry", "size", "country"]
        read_only_fields = ["id"]


class ContactCompanySerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = ContactCompany
        fields = ["id", "company", "role", "title", "is_primary", "started_at", "ended_at"]
        read_only_fields = fields


class ContactNoteSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = ContactNote
        fields = ["id", "body", "visibility", "author", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author(self, obj) -> dict | None:
        if obj.author_id is None:
            return None
        return {"id": str(obj.author_id), "name": getattr(obj.author, "name", "")}


class ContactNoteCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10000)
    visibility = serializers.ChoiceField(
        choices=NoteVisibility.choices, default=NoteVisibility.INTERNAL
    )

    def validate_body(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Note body cannot be empty")
        return value


class ContactTagCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64)
    color = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Tag name cannot be empty")
        return value


class _PrimaryMixin:
    def get_primary_phone(self, obj) -> str | None:
        phones = list(obj.phones.all())
        return phones[0].phone_e164 if phones else None

    def get_primary_email(self, obj) -> str | None:
        primary = [email for email in obj.emails.all() if email.is_primary]
        chosen = primary or list(obj.emails.all())
        return chosen[0].email if chosen else None


class ContactListSerializer(_PrimaryMixin, serializers.ModelSerializer):
    primary_phone = serializers.SerializerMethodField()
    primary_email = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "id",
            "display_name",
            "type",
            "status",
            "source",
            "company_name",
            "language",
            "timezone",
            "summary",
            "primary_phone",
            "primary_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ContactDetailSerializer(_PrimaryMixin, serializers.ModelSerializer):
    phones = ContactPhoneSerializer(many=True, read_only=True)
    emails = ContactEmailSerializer(many=True, read_only=True)
    tags = ContactTagSerializer(many=True, read_only=True)
    companies = ContactCompanySerializer(source="company_links", many=True, read_only=True)
    primary_phone = serializers.SerializerMethodField()
    primary_email = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "id",
            "display_name",
            "first_name",
            "last_name",
            "company_name",
            "type",
            "status",
            "source",
            "language",
            "timezone",
            "avatar_url",
            "summary",
            "metadata",
            "primary_phone",
            "primary_email",
            "phones",
            "emails",
            "tags",
            "companies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class _PhoneInputSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    is_primary = serializers.BooleanField(required=False)
    is_whatsapp = serializers.BooleanField(required=False, default=False)


class _EmailInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    is_primary = serializers.BooleanField(required=False)


class ContactCreateSerializer(serializers.Serializer):
    display_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    first_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    company_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    source = serializers.ChoiceField(choices=ContactSource.choices, default=ContactSource.MANUAL)
    type = serializers.ChoiceField(choices=ContactType.choices, default=ContactType.UNKNOWN)
    status = serializers.ChoiceField(choices=ContactStatus.choices, default=ContactStatus.ACTIVE)
    language = serializers.CharField(max_length=16, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True, default="")
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.DictField(required=False, default=dict)
    phones = _PhoneInputSerializer(many=True, required=False, default=list)
    emails = _EmailInputSerializer(many=True, required=False, default=list)


class ContactUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=255, required=False)
    first_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    company_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=ContactType.choices, required=False)
    status = serializers.ChoiceField(choices=ContactStatus.choices, required=False)
    source = serializers.ChoiceField(choices=ContactSource.choices, required=False)
    language = serializers.CharField(max_length=16, required=False)
    timezone = serializers.CharField(max_length=64, required=False)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(required=False)


class ContactMergeSerializer(serializers.Serializer):
    source_contact_id = serializers.UUIDField()
    target_contact_id = serializers.UUIDField()
    strategy = serializers.ChoiceField(
        choices=["prefer_target", "prefer_source"], default="prefer_target"
    )

    def validate(self, attrs):
        if attrs["source_contact_id"] == attrs["target_contact_id"]:
            raise serializers.ValidationError("source and target must differ")
        return attrs
