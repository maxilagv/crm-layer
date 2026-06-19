import factory

from crm.accounts.models import APIKey, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    name = factory.Faker("name")
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **_kwargs):
        password = extracted or "test-password-123"
        obj.set_password(password)
        if create:
            obj.save(update_fields=["password"])


class APIKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = APIKey

    name = factory.Sequence(lambda n: f"Test key {n}")
    prefix = factory.Sequence(lambda n: f"key{n:08d}"[:12])
    hashed_key = factory.LazyAttribute(lambda obj: APIKey.hash_key(f"raw-{obj.prefix}"))
    scopes = factory.List([])
