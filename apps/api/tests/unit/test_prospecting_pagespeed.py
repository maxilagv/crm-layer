"""PageSpeed Insights: the investigator's website-performance signal."""

import pytest

from crm.ai.services.context_builder import _prospect_profile
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.enrichment import ProspectEnrichmentService
from crm.prospecting.services.pagespeed import PageSpeedClient
from crm.prospecting.services.web_enrichment import WebsiteEnricher
from tests.factories.organizations import OrganizationFactory

_LIGHTHOUSE = {
    "lighthouseResult": {
        "categories": {"performance": {"score": 0.32}},
        "audits": {"largest-contentful-paint": {"numericValue": 8200.0}},
    }
}


def _fake_ps(payload=_LIGHTHOUSE):
    return PageSpeedClient(api_key="k", fetcher=lambda url, strategy: payload)


def test_pagespeed_parses_score_and_lcp():
    res = _fake_ps().analyze("midominio.com")
    assert res["score"] == 32
    assert res["lcp_ms"] == 8200
    assert res["strategy"] == "mobile"
    assert res["error"] == ""


def test_pagespeed_unreachable_never_raises():
    def boom(url, strategy):
        raise TimeoutError("slow")

    res = PageSpeedClient(api_key="k", fetcher=boom).analyze("midominio.com")
    assert res["score"] is None
    assert res["error"] == "TimeoutError"


def test_pagespeed_empty_website():
    res = _fake_ps().analyze("")
    assert res["score"] is None
    assert res["error"] == "no_website"


@pytest.mark.django_db
def test_enrichment_persists_pagespeed_and_surfaces_it():
    org = OrganizationFactory()
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id, name="C", vertical="gomerias", query="gomerias"
    )
    prospect = Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Gomeria Sur",
        place_id="p-1",
        website="gomeriasur.com",
    )
    html = '<html><head><meta name="viewport" content="x"></head><body>ok</body></html>'

    ProspectEnrichmentService.enrich(
        prospect=prospect,
        enricher=WebsiteEnricher(fetcher=lambda url: (200, url, html)),
        pagespeed=_fake_ps(),
    )
    prospect.refresh_from_db()

    assert prospect.pagespeed_score == 32
    assert prospect.enrichment["pagespeed"]["lcp_ms"] == 8200
    # The qualifier/opener context sees the slow-site signal.
    profile = _prospect_profile(prospect)
    assert profile["investigation"]["pagespeed_score"] == 32
