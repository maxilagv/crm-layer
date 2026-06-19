"""Cazador 14.2: Google Places discovery service (fake client, no real HTTP)."""

import pytest
from django.core.cache import cache
from django.test import override_settings

from crm.prospecting.domain.enums import CampaignSource
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.apollo import ApolloClient
from crm.prospecting.services.discovery import ProspectDiscoveryService
from tests.factories.organizations import OrganizationFactory


class FakePlaces:
    def __init__(self, results, details=None):
        self._results = results
        self._details = details or {}
        self.detail_calls = 0

    def text_search(self, query, *, page_token=None):
        return {"results": self._results, "next_page_token": None}

    def place_details(self, place_id):
        self.detail_calls += 1
        return self._details.get(place_id, {})


@pytest.mark.django_db
def test_discovery_creates_enriches_and_dedups():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id,
        name="Gomerías",
        query="gomerías en Palermo",
        location_hint="Palermo",
    )
    results = [
        {
            "place_id": "p1",
            "name": "Gomería Uno",
            "formatted_address": "Calle 1",
            "rating": 4.2,
            "user_ratings_total": 10,
            "types": ["car_repair"],
        },
        {
            "place_id": "p2",
            "name": "Gomería Dos",
            "formatted_address": "Calle 2",
            "types": ["car_repair"],
        },
    ]
    details = {
        "p1": {
            "website": "https://uno.com",
            "international_phone_number": "+54 11 1111-1111",
            "photos": [{}, {}],
        },
        "p2": {"international_phone_number": "+54 11 2222-2222"},  # no website → a signal
    }
    client = FakePlaces(results, details)

    result = ProspectDiscoveryService.discover(campaign=campaign, client=client)
    assert len(result.created) == 2

    p1 = Prospect.objects.get(organization_id=org.id, place_id="p1")
    assert p1.website == "https://uno.com"
    assert p1.photos_count == 2
    assert p1.phone == "+54 11 1111-1111"
    assert p1.reviews_count == 10

    p2 = Prospect.objects.get(organization_id=org.id, place_id="p2")
    assert p2.website == ""  # "no website" is a key qualification signal

    campaign.refresh_from_db()
    assert campaign.discovered_count == 2
    assert campaign.last_run_at is not None

    # Second run dedups by place_id — nothing new.
    again = ProspectDiscoveryService.discover(campaign=campaign, client=client)
    assert len(again.created) == 0
    assert again.skipped == 2
    assert Prospect.objects.filter(organization_id=org.id, campaign=campaign).count() == 2


@pytest.mark.django_db
def test_discovery_without_enrich_skips_details():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(organization_id=org.id, name="x", query="q")
    client = FakePlaces([{"place_id": "p1", "name": "Uno"}])
    result = ProspectDiscoveryService.discover(campaign=campaign, client=client, enrich=False)
    assert len(result.created) == 1
    assert client.detail_calls == 0


class FakeApollo:
    def __init__(self, organizations):
        self.organizations = organizations
        self.calls = []

    def organization_search(self, **kwargs):
        self.calls.append(kwargs)
        return self.organizations


@pytest.mark.django_db
def test_apollo_discovery_creates_and_dedups_by_external_id():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id,
        name="Software",
        vertical="software",
        query="software factories",
        location_hint="Buenos Aires",
        source=CampaignSource.APOLLO.value,
        daily_cap=2,
    )
    client = FakeApollo(
        [
            {
                "apollo_id": "apollo-1",
                "name": "Acme Software",
                "website": "https://acme.example",
                "industry": "software",
                "city": "Buenos Aires",
                "country": "Argentina",
                "raw": {"id": "apollo-1"},
            },
            {
                "apollo_id": "apollo-2",
                "name": "Beta Dev",
                "website": "https://beta.example",
                "industry": "software",
            },
        ]
    )

    result = ProspectDiscoveryService.discover(campaign=campaign, client=client, max_results=10)
    assert len(result.created) == 2
    assert client.calls[0]["max_results"] == 2  # campaign daily_cap bounds Apollo credits

    prospect = Prospect.objects.get(organization_id=org.id, external_id="apollo-1")
    assert prospect.place_id == ""
    assert prospect.external_source == CampaignSource.APOLLO.value
    assert prospect.business_name == "Acme Software"
    assert prospect.website == "https://acme.example"
    assert prospect.raw_data["apollo"]["id"] == "apollo-1"

    again = ProspectDiscoveryService.discover(campaign=campaign, client=client)
    assert len(again.created) == 0
    assert again.skipped == 2


@pytest.mark.django_db
@override_settings(APOLLO_DAILY_CAP=0, APOLLO_MONTHLY_CAP=10)
def test_apollo_discovery_respects_daily_cap_before_fetching():
    cache.clear()
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id,
        name="Software",
        query="software",
        source=CampaignSource.APOLLO.value,
    )

    def boom(url, payload, timeout):
        raise AssertionError("Apollo should not be called after the daily cap is reached")

    client = ApolloClient(api_key="k", fetcher=boom)
    result = ProspectDiscoveryService.discover(campaign=campaign, client=client)
    assert result.created == []
    assert Prospect.objects.filter(organization_id=org.id, campaign=campaign).count() == 0


@pytest.mark.django_db
@override_settings(APOLLO_DAILY_CAP=10, APOLLO_MONTHLY_CAP=0)
def test_apollo_discovery_respects_monthly_cap_before_fetching():
    cache.clear()
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id,
        name="Software",
        query="software",
        source=CampaignSource.APOLLO.value,
    )

    def boom(url, payload, timeout):
        raise AssertionError("Apollo should not be called after the monthly cap is reached")

    client = ApolloClient(api_key="k", fetcher=boom)
    result = ProspectDiscoveryService.discover(campaign=campaign, client=client)
    assert result.created == []
