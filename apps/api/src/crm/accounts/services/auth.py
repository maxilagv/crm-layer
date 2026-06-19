from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException, Throttled
from rest_framework_simplejwt.tokens import RefreshToken

from crm.audit.services import audit_event_create


class InvalidCredentials(APIException):
    status_code = 401
    default_detail = "Invalid credentials"
    default_code = "authentication_failed"


def _rate_limit_key(*, email: str, ip_address: str) -> str:
    email_digest = salted_hmac("login-rate-limit", email.lower()).hexdigest()
    ip_digest = salted_hmac("login-rate-limit", ip_address or "unknown").hexdigest()
    return f"login-rate-limit:{email_digest}:{ip_digest}"


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


@dataclass(frozen=True)
class LoginResult:
    user: object
    access: str
    refresh: str


def authenticate_user(*, request, email: str, password: str) -> LoginResult:
    """Authenticate with rate limiting and non-enumerating errors."""
    ip_address = _client_ip(request)
    cache_key = _rate_limit_key(email=email, ip_address=ip_address)
    attempts = int(cache.get(cache_key, 0))
    if attempts >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        audit_event_create(
            event_type="login_failed",
            request=request,
            metadata={"email": email.lower(), "reason": "rate_limited"},
        )
        raise Throttled(detail="Invalid credentials")

    user = authenticate(request=request, username=email.lower(), password=password)
    if user is None or not user.is_active:
        cache.set(
            cache_key,
            attempts + 1,
            timeout=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )
        audit_event_create(
            event_type="login_failed",
            actor=user if user and user.is_active else None,
            request=request,
            metadata={"email": email.lower(), "reason": "invalid_credentials"},
        )
        raise InvalidCredentials()

    cache.delete(cache_key)
    user.mark_logged_in()
    refresh = RefreshToken.for_user(user)
    audit_event_create(event_type="login_succeeded", actor=user, request=request)
    return LoginResult(user=user, access=str(refresh.access_token), refresh=str(refresh))


def logout_user(*, request, refresh_token: str) -> None:
    token = RefreshToken(refresh_token)
    token.blacklist()
    audit_event_create(event_type="logout_succeeded", actor=request.user, request=request)
