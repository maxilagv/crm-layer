import hashlib
import hmac

from django.conf import settings


class WebhookVerificationError(Exception):
    """Safe webhook verification failure."""


def verify_token_matches(token: str | None) -> bool:
    expected = settings.WHATSAPP_VERIFY_TOKEN
    if not expected or token is None:
        return False
    return hmac.compare_digest(str(token), str(expected))


def validate_signature(*, raw_body: bytes, signature_header: str | None) -> bool:
    app_secret = settings.WHATSAPP_APP_SECRET
    if not app_secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = (
        "sha256="
        + hmac.new(
            app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(signature_header, expected)


def truncate_signature(signature_header: str | None) -> str:
    if not signature_header:
        return ""
    return signature_header[:24]
