import uuid

import factory

from crm.contacts.constants import ContactStatus, ContactType
from crm.contacts.models import (
    Company,
    Contact,
    ContactCompany,
    ContactEmail,
    ContactNote,
    ContactPhone,
)


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    organization_id = factory.LazyFunction(uuid.uuid4)
    display_name = factory.Sequence(lambda n: f"Contact {n}")
    type = ContactType.LEAD
    status = ContactStatus.ACTIVE
    language = "es"
    timezone = "America/Argentina/Buenos_Aires"


class ContactPhoneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactPhone

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    phone_e164 = factory.Sequence(lambda n: f"+54911{n:08d}")
    country_code = "54"
    is_primary = True


class ContactEmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactEmail

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    email = factory.Sequence(lambda n: f"contact-{n}@example.com")
    normalized_email = factory.SelfAttribute("email")
    is_primary = True


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    organization_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Company {n}")


class ContactCompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactCompany

    contact = factory.SubFactory(ContactFactory)
    company = factory.SubFactory(CompanyFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")


class ContactNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactNote

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    body = factory.Sequence(lambda n: f"Note body {n}")
    visibility = "internal"
