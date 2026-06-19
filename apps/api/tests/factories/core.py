from datetime import timedelta

import factory
from django.utils import timezone

from crm.core.models import IdempotencyKey, OutboxEvent


class OutboxEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OutboxEvent

    event_type = "test.event.v1"
    payload = factory.Dict({"id": "123"})
    available_at = factory.LazyFunction(timezone.now)


class IdempotencyKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IdempotencyKey

    key = factory.Sequence(lambda n: f"key-{n}")
    scope = "test"
    request_hash = "hash"
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=24))
