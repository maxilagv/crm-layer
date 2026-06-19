"""Hunter.io client for best-effort decision-maker email enrichment."""

from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings

_BASE_URL = "https://api.hunter.io/v2"
_TIMEOUT = 12.0


class HunterError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_transient(self) -> bool:
        return self.status_code is not None and self.status_code >= 500


@dataclass(frozen=True)
class HunterEmailResult:
    email: str = ""
    score: int | None = None
    position: str = ""
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    source: str = ""

    def as_dict(self) -> dict:
        return {
            "email": self.email,
            "score": self.score,
            "position": self.position,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "source": self.source,
        }


class HunterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        fetcher=None,
        timeout: float = _TIMEOUT,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "HUNTER_API_KEY", "")
        self._fetch = fetcher or self._default_fetch
        self.timeout = timeout

    def _default_fetch(self, url: str, params: dict, timeout: float) -> dict:
        response = requests.get(url, params=params, timeout=timeout)
        return _json_or_raise(response)

    def domain_search(self, domain: str) -> dict:
        domain = _clean_domain(domain)
        if not domain or not self.api_key:
            return {}
        params = {"domain": domain, "api_key": self.api_key, "limit": 10}
        try:
            payload = self._fetch(f"{_BASE_URL}/domain-search", params, self.timeout)
            data = _coerce_payload(payload)
        except Exception:  # noqa: BLE001 - Hunter enrichment must never block the caller
            return {}
        return _parse_domain_search(data)

    def email_finder(self, domain: str, first_name: str = "", last_name: str = "") -> dict:
        domain = _clean_domain(domain)
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not domain or not self.api_key or not (first_name or last_name):
            return {}
        params = {
            "domain": domain,
            "api_key": self.api_key,
            "first_name": first_name,
            "last_name": last_name,
        }
        try:
            payload = self._fetch(f"{_BASE_URL}/email-finder", params, self.timeout)
            data = _coerce_payload(payload)
        except Exception:  # noqa: BLE001 - Hunter enrichment must never block the caller
            return {}
        return _parse_email_finder(data)


def _clean_domain(domain: str) -> str:
    return (domain or "").strip().lower().removeprefix("www.")


def _coerce_payload(payload) -> dict:
    if hasattr(payload, "status_code"):
        return _json_or_raise(payload)
    return payload if isinstance(payload, dict) else {}


def _json_or_raise(response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code >= 400:
        message = ""
        if isinstance(data, dict):
            errors = data.get("errors")
            error = data.get("error")
            if isinstance(errors, list) and errors:
                first_error = errors[0]
                if isinstance(first_error, dict):
                    message = first_error.get("details") or first_error.get("message") or ""
            elif isinstance(error, dict):
                message = error.get("details") or error.get("message") or ""
            elif isinstance(error, str):
                message = error
        raise HunterError(
            f"Hunter HTTP {response.status_code}: {message}",
            status_code=response.status_code,
        )
    return data or {}


def _parse_domain_search(data: dict) -> dict:
    emails = ((data or {}).get("data") or {}).get("emails") or []
    candidates = [_parse_email_item(item, source="domain_search") for item in emails]
    candidates = [candidate for candidate in candidates if candidate.email]
    if not candidates:
        return {}
    candidates.sort(key=lambda candidate: candidate.score or 0, reverse=True)
    return candidates[0].as_dict()


def _parse_email_finder(data: dict) -> dict:
    item = (data or {}).get("data") or {}
    result = HunterEmailResult(
        email=str(item.get("email") or "").strip(),
        score=_score(item.get("score")),
        position=str(item.get("position") or "").strip(),
        first_name=str(item.get("first_name") or "").strip(),
        last_name=str(item.get("last_name") or "").strip(),
        full_name=str(item.get("full_name") or "").strip(),
        source="email_finder",
    )
    return result.as_dict() if result.email else {}


def _parse_email_item(item: dict, *, source: str) -> HunterEmailResult:
    if not isinstance(item, dict):
        return HunterEmailResult()
    first_name = str(item.get("first_name") or "").strip()
    last_name = str(item.get("last_name") or "").strip()
    full_name = str(item.get("full_name") or "").strip()
    if not full_name:
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()
    return HunterEmailResult(
        email=str(item.get("value") or item.get("email") or "").strip(),
        score=_score(item.get("score")),
        position=str(item.get("position") or "").strip(),
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        source=source,
    )


def _score(value) -> int | None:
    if value is None:
        return None
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return None
