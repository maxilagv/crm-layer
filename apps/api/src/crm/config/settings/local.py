"""Local development settings.

Loads the repository ``.env`` as a convenience before importing base settings.
Other environments never depend on a ``.env`` file existing.
"""

from pathlib import Path

from dotenv import load_dotenv

# apps/api/src/crm/config/settings/local.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
load_dotenv(REPO_ROOT / ".env")

from .base import *  # noqa: E402,F403
from .base import env, env_bool  # noqa: E402

APP_ENV = "local"
DEBUG = env_bool("DEBUG", True)

# Development-only fallback so the project boots without configuration.
SECRET_KEY = env("SECRET_KEY") or "insecure-local-development-key"

CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS or ["http://localhost:3000"]  # noqa: F405
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS or ["http://localhost:3000"]  # noqa: F405
