"""Google Custom Search client for best-effort site/social discovery."""

from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings

_URL = "https://www.googleapis.com/customsearch/v1"
_TIMEOUT = 10.0


class CustomSearchError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_transient(self) -> bool:
        return self.status_code is not None and self.status_code >= 500


@dataclass(frozen=True)
class CustomSearchResult:
    title: str = ""
    link: str = ""
    snippet: str = ""

    def as_dict(self) -> dict:
        return {"title": self.title, "link": self.link, "snippet": self.snippet}


class CustomSearchClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        cx: str | None = None,
        fetcher=None,
        timeout: float = _TIMEOUT,
    ):
        self.api_key = (
            api_key if api_key is not None else getattr(settings, "GOOGLE_CSE_API_KEY", "")
        )
        self.cx = cx if cx is not None else getattr(settings, "GOOGLE_CSE_CX", "")
        self._fetch = fetcher or self._default_fetch
        self.timeout = timeout

    def _default_fetch(self, url: str, params: dict, timeout: float) -> dict:
        response = requests.get(url, params=params, timeout=timeout)
        return _json_or_raise(response)

    def search(self, query: str) -> list[dict]:
        query = (query or "").strip()
        if not query or not self.api_key or not self.cx:
            return []

        params = {"key": self.api_key, "cx": self.cx, "q": query}
        try:
            payload = self._fetch(_URL, params, self.timeout)
            data = _coerce_payload(payload)
        except Exception:  # noqa: BLE001 - external search is best-effort enrichment
            return []
        return [result.as_dict() for result in _parse_results(data)]


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
            message = (data.get("error") or {}).get("message", "")
        raise CustomSearchError(
            f"Custom Search HTTP {response.status_code}: {message}",
            status_code=response.status_code,
        )
    return data or {}


def _parse_results(data: dict) -> list[CustomSearchResult]:
    results: list[CustomSearchResult] = []
    for item in (data or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        link = str(item.get("link") or "").strip()
        if not link:
            continue
        results.append(
            CustomSearchResult(
                title=str(item.get("title") or "").strip()[:300],
                link=link[:1000],
                snippet=str(item.get("snippet") or "").strip()[:500],
            )
        )
    return results
