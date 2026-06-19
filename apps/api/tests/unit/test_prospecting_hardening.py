"""Anti-loop / anti-cost hardening for the Cazador (audit fixes)."""

import pytest
from django.utils import timezone

from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.discovery import _MAX_PAGES, ProspectDiscoveryService
from crm.prospecting.services.enrichment import ProspectEnrichmentService
from crm.prospecting.services.google_places import GooglePlacesError
from crm.prospecting.services.qualification import ProspectQualificationService
from tests.factories.organizations import OrganizationFactory


def test_places_error_transient_classification():
    assert GooglePlacesError("quota", status_code=429).is_transient is False
    assert GooglePlacesError("denied", status_code=403).is_transient is False
    assert GooglePlacesError("bad", status_code=400).is_transient is False
    assert GooglePlacesError("server", status_code=503).is_transient is True
    assert GooglePlacesError("unknown").is_transient is False


class _EndlessPlaces:
    """Always returns a fresh result + a next_page_token — would loop forever w/o the cap."""

    def __init__(self):
        self.search_calls = 0

    def text_search(self, query, *, page_token=None):
        self.search_calls += 1
        pid = f"p{self.search_calls}"
        return {"results": [{"place_id": pid, "name": f"Biz {pid}"}], "next_page_token": "more"}

    def place_details(self, place_id):
        return {}


@pytest.mark.django_db
def test_discovery_stops_at_page_cap():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id, name="C", vertical="gomerias", query="gomerias"
    )
    client = _EndlessPlaces()
    result = ProspectDiscoveryService.discover(campaign=campaign, client=client)
    # The cap bounds Text Search calls (1 quota unit each), no matter how many tokens come back.
    assert client.search_calls == _MAX_PAGES
    assert len(result.created) == _MAX_PAGES


class _BoomEnricher:
    def enrich(self, website):
        raise AssertionError("enricher must not be called when prospect is fresh")


@pytest.mark.django_db
def test_enrichment_skips_when_recently_enriched():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id, name="C", vertical="gomerias", query="gomerias"
    )
    prospect = Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="X",
        place_id="p1",
        website="x.com",
        enriched_at=timezone.now(),
    )
    # Recent enriched_at → returns without touching the website/PageSpeed (no AssertionError).
    ProspectEnrichmentService.enrich(prospect=prospect, enricher=_BoomEnricher())


@pytest.mark.django_db
def test_qualification_skips_when_recently_qualified():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id, name="C", vertical="gomerias", query="gomerias", min_fit_score=60
    )
    prospect = Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="X",
        place_id="p1",
        status="qualified",
        fit_score=80,
        qualified_at=timezone.now(),
    )
    # No AI is configured here; if the guard failed it would hit AIGateway and raise.
    out = ProspectQualificationService.qualify(prospect=prospect)
    assert out.fit_score == 80
    assert out.status == "qualified"
