import pytest
from django.core.cache import cache
from django.test import override_settings

from crm.prospecting.services.apollo import ApolloClient, ApolloError


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


@override_settings(APOLLO_DAILY_CAP=10, APOLLO_MONTHLY_CAP=10)
def test_apollo_organization_search_parses_and_caps_pages():
    cache.clear()
    calls = []

    def fetch(url, payload, timeout):
        calls.append(payload.copy())
        page = payload["page"]
        return {
            "organizations": [
                {
                    "id": f"org-{page}",
                    "name": f"Empresa {page}",
                    "website_url": f"https://empresa{page}.com",
                    "industry": "software",
                    "city": "Buenos Aires",
                    "country": "Argentina",
                }
            ],
            "pagination": {"total_pages": 3},
        }

    result = ApolloClient(api_key="k", fetcher=fetch).organization_search(
        query="software",
        location="Buenos Aires",
        max_pages=2,
    )
    assert [item["apollo_id"] for item in result] == ["org-1", "org-2"]
    assert [call["page"] for call in calls] == [1, 2]


@override_settings(APOLLO_DAILY_CAP=10, APOLLO_MONTHLY_CAP=10)
def test_apollo_mixed_people_search_parses_people():
    cache.clear()

    def fetch(url, payload, timeout):
        assert url.endswith("/mixed_people/search")
        assert payload["person_titles"] == ["Owner"]
        return {
            "people": [
                {
                    "id": "person-1",
                    "name": "Ana Perez",
                    "title": "Owner",
                    "email": "ana@example.com",
                    "organization": {"id": "org-1", "name": "Acme"},
                }
            ],
            "pagination": {"total_pages": 1},
        }

    result = ApolloClient(api_key="k", fetcher=fetch).mixed_people_search(titles=["Owner"])
    assert result[0]["apollo_id"] == "person-1"
    assert result[0]["organization_id"] == "org-1"


@override_settings(APOLLO_DAILY_CAP=10, APOLLO_MONTHLY_CAP=10)
def test_apollo_429_returns_empty_without_raise():
    cache.clear()
    client = ApolloClient(
        api_key="k",
        fetcher=lambda url, payload, timeout: _Resp({"error": "rate limit"}, status=429),
    )
    assert client.organization_search(query="software") == []


@override_settings(APOLLO_DAILY_CAP=10, APOLLO_MONTHLY_CAP=10)
def test_apollo_402_returns_empty_without_raise():
    cache.clear()
    client = ApolloClient(
        api_key="k",
        fetcher=lambda url, payload, timeout: _Resp({"error": "payment required"}, status=402),
    )
    assert client.organization_search(query="software") == []


def test_apollo_empty_input_noops():
    def boom(url, payload, timeout):
        raise AssertionError("fetcher should not be called")

    client = ApolloClient(api_key="k", fetcher=boom)
    assert client.organization_search() == []
    assert ApolloClient(api_key="", fetcher=boom).organization_search(query="software") == []
    assert client.mixed_people_search() == []


@override_settings(APOLLO_DAILY_CAP=10, APOLLO_MONTHLY_CAP=10)
def test_apollo_transient_5xx_raises_for_task_retry():
    cache.clear()
    client = ApolloClient(
        api_key="k",
        fetcher=lambda url, payload, timeout: _Resp({"error": "server"}, status=503),
    )
    with pytest.raises(ApolloError) as exc:
        client.organization_search(query="software")
    assert exc.value.is_transient is True


def test_apollo_error_transient_classification():
    assert ApolloError("server", status_code=503).is_transient is True
    assert ApolloError("quota", status_code=429).is_transient is False
    assert ApolloError("payment", status_code=402).is_transient is False
    assert ApolloError("auth", status_code=401).is_transient is False
    assert ApolloError("bad", status_code=400).is_transient is False
    assert ApolloError("unknown").is_transient is False
