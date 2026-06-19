import pytest

from crm.contacts.constants import ContactType
from crm.contacts.exceptions import ContactMergeError, PhoneConflictError
from crm.contacts.normalizers import PhoneNormalizationError, normalize_phone
from crm.contacts.services import (
    ContactMerger,
    ContactResolver,
    add_note,
    add_phone_to_contact,
    create_contact,
)
from crm.core.models import OutboxEvent
from tests.factories.organizations import OrganizationFactory

AR_LANDLINE = "+541143215678"
AR_LANDLINE_LOCAL = "(011) 4321-5678"
AR_MOBILE = "+5491158123456"


def test_normalize_phone_accepts_flexible_inputs() -> None:
    assert normalize_phone("11 4321-5678").e164 == AR_LANDLINE
    assert normalize_phone(AR_LANDLINE_LOCAL).e164 == AR_LANDLINE
    assert normalize_phone(AR_LANDLINE).e164 == AR_LANDLINE


def test_normalize_phone_rejects_invalid() -> None:
    with pytest.raises(PhoneNormalizationError):
        normalize_phone("not a phone")
    with pytest.raises(PhoneNormalizationError):
        normalize_phone("")


@pytest.mark.django_db
def test_contact_created() -> None:
    org = OrganizationFactory()
    contact = create_contact(
        organization=org, actor=None, display_name="Juan", phones=[{"phone": AR_LANDLINE}]
    )
    assert contact.organization_id == org.id
    assert contact.display_name == "Juan"
    assert contact.phones.count() == 1
    phone = contact.phones.first()
    assert phone.phone_e164 == AR_LANDLINE
    assert phone.is_primary is True


@pytest.mark.django_db
def test_contact_phone_normalized() -> None:
    org = OrganizationFactory()
    contact = create_contact(organization=org, actor=None, phones=[{"phone": AR_LANDLINE_LOCAL}])
    assert contact.phones.first().phone_e164 == AR_LANDLINE


@pytest.mark.django_db
def test_duplicate_phone_resolves_existing_contact() -> None:
    org = OrganizationFactory()
    first = ContactResolver.resolve_by_phone(organization=org, raw_phone=AR_LANDLINE)
    second = ContactResolver.resolve_by_phone(organization=org, raw_phone="11 4321-5678")
    assert first.created is True
    assert second.created is False
    assert second.matched_by == "phone"
    assert second.contact.id == first.contact.id


@pytest.mark.django_db
def test_same_phone_allowed_in_different_organizations() -> None:
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    r_a = ContactResolver.resolve_by_phone(organization=org_a, raw_phone=AR_LANDLINE)
    r_b = ContactResolver.resolve_by_phone(organization=org_b, raw_phone=AR_LANDLINE)
    assert r_a.created and r_b.created
    assert r_a.contact.id != r_b.contact.id


@pytest.mark.django_db
def test_resolver_does_not_create_when_create_false() -> None:
    org = OrganizationFactory()
    result = ContactResolver.resolve_by_phone(organization=org, raw_phone=AR_LANDLINE, create=False)
    assert result.contact is None
    assert result.created is False


@pytest.mark.django_db
def test_single_primary_phone_per_contact() -> None:
    org = OrganizationFactory()
    contact = create_contact(organization=org, actor=None, phones=[{"phone": AR_LANDLINE}])
    add_phone_to_contact(contact=contact, raw_phone=AR_MOBILE, is_primary=True)
    primaries = contact.phones.filter(is_primary=True)
    assert primaries.count() == 1
    assert primaries.first().phone_e164 == AR_MOBILE


@pytest.mark.django_db
def test_create_contact_phone_conflict() -> None:
    org = OrganizationFactory()
    create_contact(organization=org, actor=None, phones=[{"phone": AR_LANDLINE}])
    with pytest.raises(PhoneConflictError):
        create_contact(organization=org, actor=None, phones=[{"phone": "11 4321-5678"}])


@pytest.mark.django_db
def test_contact_created_emits_outbox_event() -> None:
    org = OrganizationFactory()
    create_contact(organization=org, actor=None, phones=[{"phone": AR_LANDLINE}])
    assert OutboxEvent.objects.filter(
        event_type="contact.created.v1", organization_id=org.id
    ).exists()


@pytest.mark.django_db
def test_merge_moves_relations_and_archives_source() -> None:
    org = OrganizationFactory()
    target = create_contact(
        organization=org, actor=None, display_name="Target", phones=[{"phone": AR_LANDLINE}]
    )
    source = create_contact(
        organization=org, actor=None, display_name="Source", phones=[{"phone": AR_MOBILE}]
    )
    add_note(contact=source, author=None, body="important", visibility="internal")

    merged = ContactMerger.merge(organization=org, source=source, target=target)

    assert merged.id == target.id
    assert target.phones.count() == 2
    assert target.notes.count() == 1
    source.refresh_from_db()
    assert source.deleted_at is not None


@pytest.mark.django_db
def test_merge_cross_tenant_fails() -> None:
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    contact_a = create_contact(organization=org_a, actor=None, display_name="A")
    contact_b = create_contact(organization=org_b, actor=None, display_name="B")
    with pytest.raises(ContactMergeError):
        ContactMerger.merge(organization=org_a, source=contact_b, target=contact_a)


@pytest.mark.django_db
def test_classifier_marks_blocked() -> None:
    from crm.contacts.constants import ContactStatus
    from crm.contacts.services import ContactClassifier

    org = OrganizationFactory()
    contact = create_contact(
        organization=org, actor=None, display_name="Blocked", status=ContactStatus.BLOCKED
    )
    assert ContactClassifier.classify(contact) == ContactType.BLOCKED.value
