"""Staging settings: as close to production as possible, smoke-test friendly."""

from ._deployed import *  # noqa: F403

APP_ENV = "staging"

# Short HSTS without preload so a staging misconfiguration is recoverable.
SECURE_HSTS_SECONDS = 60 * 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
