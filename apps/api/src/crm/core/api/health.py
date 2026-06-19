"""Health and version endpoints.

- ``/api/health/``       simple aggregate, no dependency calls;
- ``/api/health/live/``  process is alive, never touches DB/Redis;
- ``/api/health/ready/`` real readiness: queries PostgreSQL and Redis with a
  short timeout and returns 503 when a critical dependency is down;
- ``/api/version/``      version/commit/build metadata from the environment.
"""

import logging

import redis
from django.conf import settings
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from crm.core.observability.health import SystemStatusBuilder
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode

from .responses import error_response, success_response

logger = logging.getLogger(__name__)


def _check_database() -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return {"status": "ok"}


def _redis_client():
    if settings.HEALTHCHECK_USE_FAKE_REDIS:
        import fakeredis

        return fakeredis.FakeRedis()
    return redis.Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=settings.HEALTHCHECK_REDIS_TIMEOUT_SECONDS,
        socket_timeout=settings.HEALTHCHECK_REDIS_TIMEOUT_SECONDS,
    )


def _check_redis() -> dict[str, str]:
    client = _redis_client()
    if not client.ping():
        raise RuntimeError("Redis ping failed")
    return {"status": "ok"}


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiResponse(description="API health summary")})
    def get(self, request):
        return success_response(
            request,
            {
                "status": "ok",
                "service": settings.SERVICE_NAME,
                "environment": settings.APP_ENV,
            },
        )


class LiveView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiResponse(description="Django process is alive")})
    def get(self, request):
        return success_response(request, {"status": "ok"})


class ReadyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Critical dependencies are ready"),
            503: OpenApiResponse(description="One or more critical dependencies are down"),
        }
    )
    def get(self, request):
        checks: dict[str, dict[str, str]] = {}
        status_code = 200

        for name, check in {"database": _check_database, "redis": _check_redis}.items():
            try:
                checks[name] = check()
            except Exception as exc:
                logger.warning(
                    "Readiness check failed",
                    extra={
                        "event": "health.ready.failed",
                        "metadata": {"dependency": name, "error": str(exc)},
                    },
                )
                # Never leak connection details/secrets in the response body.
                checks[name] = {"status": "error", "message": f"{name} unavailable"}
                status_code = 503

        payload = {"status": "ok" if status_code == 200 else "error", "checks": checks}
        if status_code == 200:
            return success_response(request, payload)
        return error_response(
            request,
            code="service_unavailable",
            message="One or more critical dependencies are unavailable",
            details=payload,
            status=status_code,
        )


class VersionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiResponse(description="Application version metadata")})
    def get(self, request):
        return success_response(
            request,
            {
                "version": settings.APP_VERSION,
                "commit": settings.GIT_COMMIT,
                "build_date": settings.BUILD_DATE,
                "environment": settings.APP_ENV,
            },
        )


class SystemStatusView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.AUDIT_VIEW.value

    @extend_schema(responses={200: OpenApiResponse(description="Operational system status")})
    def get(self, request):
        return success_response(request, SystemStatusBuilder.build())
