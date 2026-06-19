"""Phone and email normalization.

Phones are canonicalized to E.164 with ``phonenumbers`` before they are ever
persisted; ``phone_e164`` is the single source of truth and the deduplication
key. The default region (used when the input has no ``+`` country prefix) is
read from ``settings.CONTACTS_DEFAULT_PHONE_REGION`` and defaults to ``"AR"``;
it can be overridden per call.
"""

from dataclasses import dataclass

import phonenumbers
from django.conf import settings

DEFAULT_PHONE_REGION = "AR"


class PhoneNormalizationError(ValueError):
    """Raised when a raw phone number cannot be parsed/validated to E.164."""


@dataclass(frozen=True)
class NormalizedPhone:
    e164: str
    country_code: str  # numeric calling code, e.g. "54"
    region: str | None  # ISO region, e.g. "AR"


def default_region() -> str:
    return getattr(settings, "CONTACTS_DEFAULT_PHONE_REGION", DEFAULT_PHONE_REGION)


def normalize_phone(raw: str, *, region: str | None = None) -> NormalizedPhone:
    """Parse a flexible phone input into canonical E.164.

    Accepts ``+54911...``, ``11 1234-5678``, ``(011) 1234-5678`` etc. Raises
    :class:`PhoneNormalizationError` for empty, unparsable or invalid numbers.
    """
    if raw is None or not str(raw).strip():
        raise PhoneNormalizationError("Phone number is empty")

    region = region or default_region()
    try:
        parsed = phonenumbers.parse(str(raw), region)
    except phonenumbers.NumberParseException as exc:
        raise PhoneNormalizationError(f"Could not parse phone number: {exc}") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise PhoneNormalizationError("Phone number is not valid")

    return NormalizedPhone(
        e164=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        country_code=str(parsed.country_code),
        region=phonenumbers.region_code_for_number(parsed),
    )


def normalize_email(raw: str) -> str:
    """Return a canonical, case-insensitive form of an email for dedup.

    Lowercases and trims; does not apply provider-specific aliasing so that the
    stored ``email`` and ``normalized_email`` stay predictable.
    """
    if raw is None or not str(raw).strip():
        raise ValueError("Email is empty")
    return str(raw).strip().lower()
