"""Apollo.io client for B2B prospect discovery and enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field

import requests
from django.conf import settings

from .quotas import consume_daily_and_monthly

_BASE_URL = "https://api.apollo.io/v1"
_TIMEOUT = 20.0
_MAX_PAGES = 5
_PER_PAGE = 25


class ApolloError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_transient(self) -> bool:
        return self.status_code is not None and self.status_code >= 500


@dataclass(frozen=True)
class ApolloOrganizationResult:
    apollo_id: str = ""
    name: str = ""
    website: str = ""
    phone: str = ""
    industry: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    linkedin_url: str = ""
    raw: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "apollo_id": self.apollo_id,
            "name": self.name,
            "website": self.website,
            "phone": self.phone,
            "industry": self.industry,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "linkedin_url": self.linkedin_url,
            "raw": self.raw,
        }


@dataclass(frozen=True)
class ApolloPersonResult:
    apollo_id: str = ""
    name: str = ""
    title: str = ""
    email: str = ""
    organization_id: str = ""
    organization_name: str = ""
    raw: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "apollo_id": self.apollo_id,
            "name": self.name,
            "title": self.title,
            "email": self.email,
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "raw": self.raw,
        }


class ApolloClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        fetcher=None,
        timeout: float = _TIMEOUT,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "APOLLO_API_KEY", "")
        self._fetch = fetcher or self._default_fetch
        self.timeout = timeout

    def _default_fetch(self, url: str, payload: dict, timeout: float) -> dict:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
                "X-Api-Key": self.api_key,
            },
            timeout=timeout,
        )
        return _json_or_raise(response)

    def organization_search(
        self,
        *,
        query: str = "",
        location: str = "",
        industry: str = "",
        max_pages: int = _MAX_PAGES,
        per_page: int = _PER_PAGE,
        max_results: int | None = None,
    ) -> list[dict]:
        query = (query or "").strip()
        location = (location or "").strip()
        industry = (industry or "").strip()
        if not self.api_key or not (query or location or industry):
            return []

        payload = _base_payload(
            query=query,
            location=location,
            industry=industry,
            per_page=per_page,
        )
        return self._paged(
            endpoint="/organizations/search",
            payload=payload,
            parser=_parse_organizations,
            max_pages=max_pages,
            max_results=max_results,
        )

    def mixed_people_search(
        self,
        *,
        query: str = "",
        location: str = "",
        titles: list[str] | None = None,
        max_pages: int = _MAX_PAGES,
        per_page: int = _PER_PAGE,
        max_results: int | None = None,
    ) -> list[dict]:
        query = (query or "").strip()
        location = (location or "").strip()
        titles = [title.strip() for title in (titles or []) if title.strip()]
        if not self.api_key or not (query or location or titles):
            return []

        payload = {"page": 1, "per_page": per_page}
        if query:
            payload["q_keywords"] = query
        if location:
            payload["person_locations"] = [location]
        if titles:
            payload["person_titles"] = titles
        return self._paged(
            endpoint="/mixed_people/search",
            payload=payload,
            parser=_parse_people,
            max_pages=max_pages,
            max_results=max_results,
        )

    def _paged(
        self,
        *,
        endpoint: str,
        payload: dict,
        parser,
        max_pages: int,
        max_results: int | None,
    ) -> list[dict]:
        results: list[dict] = []
        pages = max(1, min(int(max_pages or 1), _MAX_PAGES))
        for page in range(1, pages + 1):
            if max_results is not None and len(results) >= max_results:
                break
            if not consume_daily_and_monthly(
                "apollo",
                getattr(settings, "APOLLO_DAILY_CAP", 50),
                getattr(settings, "APOLLO_MONTHLY_CAP", 500),
            ):
                break
            payload["page"] = page
            try:
                data = _coerce_payload(self._fetch(f"{_BASE_URL}{endpoint}", payload, self.timeout))
            except ApolloError as exc:
                if exc.is_transient:
                    raise
                break
            except Exception:  # noqa: BLE001 - malformed/network responses degrade to no results
                break

            page_results = parser(data)
            if max_results is not None:
                remaining = max_results - len(results)
                page_results = page_results[:remaining]
            results.extend(item.as_dict() for item in page_results)
            if not _has_next_page(data, page):
                break
        return results


def _base_payload(*, query: str, location: str, industry: str, per_page: int) -> dict:
    payload = {"page": 1, "per_page": per_page}
    if query:
        payload["q_keywords"] = query
    if location:
        payload["organization_locations"] = [location]
    if industry:
        payload["organization_industry_tag_ids"] = [industry]
    return payload


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
            message = str(data.get("error") or data.get("message") or "")
        raise ApolloError(
            f"Apollo HTTP {response.status_code}: {message}",
            status_code=response.status_code,
        )
    return data or {}


def _parse_organizations(data: dict) -> list[ApolloOrganizationResult]:
    rows = (data or {}).get("organizations") or (data or {}).get("accounts") or []
    results: list[ApolloOrganizationResult] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        org = ApolloOrganizationResult(
            apollo_id=str(row.get("id") or "").strip(),
            name=str(row.get("name") or "").strip(),
            website=str(row.get("website_url") or row.get("website") or "").strip(),
            phone=str(row.get("phone") or row.get("primary_phone") or "").strip(),
            industry=str(row.get("industry") or "").strip(),
            city=str(row.get("city") or "").strip(),
            state=str(row.get("state") or "").strip(),
            country=str(row.get("country") or "").strip(),
            linkedin_url=str(row.get("linkedin_url") or "").strip(),
            raw=row,
        )
        if org.apollo_id and org.name:
            results.append(org)
    return results


def _parse_people(data: dict) -> list[ApolloPersonResult]:
    rows = (data or {}).get("people") or (data or {}).get("contacts") or []
    results: list[ApolloPersonResult] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        org = row.get("organization") if isinstance(row.get("organization"), dict) else {}
        person = ApolloPersonResult(
            apollo_id=str(row.get("id") or "").strip(),
            name=str(row.get("name") or "").strip(),
            title=str(row.get("title") or "").strip(),
            email=str(row.get("email") or "").strip(),
            organization_id=str(row.get("organization_id") or org.get("id") or "").strip(),
            organization_name=str(org.get("name") or row.get("organization_name") or "").strip(),
            raw=row,
        )
        if person.apollo_id:
            results.append(person)
    return results


def _has_next_page(data: dict, current_page: int) -> bool:
    pagination = (data or {}).get("pagination") or {}
    total_pages = pagination.get("total_pages")
    if isinstance(total_pages, int):
        return current_page < total_pages
    next_page = pagination.get("next_page")
    if isinstance(next_page, int):
        return next_page > current_page
    return False
