"""Signed token helpers for local private downloads.

The token encodes the media asset id and is time-limited via Django's
TimestampSigner. The storage_key is NEVER placed in the URL; the internal
download view resolves it from the asset after verifying the token.
"""

from django.core import signing

_SALT = "crm.media.signed-download"


class SignedURLError(Exception):
    pass


def sign_asset(asset_id) -> str:
    return signing.TimestampSigner(salt=_SALT).sign(str(asset_id))


def unsign_asset(token: str, *, max_age: int) -> str:
    try:
        return signing.TimestampSigner(salt=_SALT).unsign(token, max_age=max_age)
    except signing.SignatureExpired as exc:
        raise SignedURLError("Signed URL expired") from exc
    except signing.BadSignature as exc:
        raise SignedURLError("Invalid signed URL") from exc
