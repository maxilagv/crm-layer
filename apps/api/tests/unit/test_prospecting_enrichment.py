"""Wave 2: the investigator — website analysis, review mining, enrichment persistence."""

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from crm.ai.services.context_builder import _prospect_profile
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.enrichment import (
    ProspectEnrichmentService,
    latest_review_age_days,
    mine_review_themes,
)
from crm.prospecting.services.web_enrichment import WebsiteEnricher
from tests.factories.organizations import OrganizationFactory

_WP_BOOKING_HTML = """
<html><head>
<title>Peluqueria Sur</title>
<meta name="description" content="La mejor peluqueria del barrio">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/wp-content/themes/x/style.css">
</head><body>
<a href="https://calendly.com/peluqueria/turno">Reservar turno</a>
<a href="https://instagram.com/peluqueriasur">Instagram</a>
contacto@peluqueriasur.com
</body></html>
"""


def _fake_fetch(html, status=200):
    def _fetch(url):
        return status, url, html

    return _fetch


def _campaign(org, **kw):
    defaults = {
        "organization_id": org.id,
        "name": "Peluquerias",
        "vertical": "peluquerias",
        "query": "peluquerias en Palermo",
        "min_fit_score": 60,
    }
    defaults.update(kw)
    return ProspectingCampaign.objects.create(**defaults)


def _prospect(org, campaign, **kw):
    defaults = {
        "organization_id": org.id,
        "campaign": campaign,
        "business_name": "Peluqueria Sur",
        "place_id": "p-1",
        "website": "peluqueriasur.com",
    }
    defaults.update(kw)
    return Prospect.objects.create(**defaults)


def test_website_enricher_detects_platform_booking_socials():
    enricher = WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML))
    sig = enricher.enrich("peluqueriasur.com")
    assert sig.reachable is True
    assert sig.https is True
    assert sig.platform == "wordpress"
    assert sig.mobile_friendly is True
    assert sig.has_online_booking is True
    assert sig.title == "Peluqueria Sur"
    assert "instagram" in sig.social_links
    assert "contacto@peluqueriasur.com" in sig.emails


def test_website_enricher_unreachable_never_raises():
    def boom(url):
        raise ConnectionError("dns fail")

    sig = WebsiteEnricher(fetcher=boom).enrich("http://nope.example")
    assert sig.reachable is False
    assert sig.error == "ConnectionError"


def test_website_enricher_empty_website():
    sig = WebsiteEnricher(fetcher=_fake_fetch("")).enrich("")
    assert sig.reachable is False
    assert sig.error == "no_website"


def test_mine_review_themes_counts_complaints():
    reviews = [
        {"text": "Llame mil veces y no atienden el telefono"},
        {"text": "Muy caro y encima tarde una hora"},
        {"text": "Todo bien, volveria"},
    ]
    themes = mine_review_themes(reviews)
    assert themes.get("no_responde") == 1
    assert themes.get("precio_alto") == 1
    assert themes.get("demoras") == 1


def test_latest_review_age_days():
    now = int(timezone.now().timestamp())
    recent = [{"time": now - 3600}]  # 1h ago
    old = [{"time": now - 12 * 86400}]  # 12 days ago
    assert latest_review_age_days(recent) == 0
    assert latest_review_age_days(old) == 12
    assert latest_review_age_days([]) is None


@pytest.mark.django_db
def test_enrichment_service_persists_and_surfaces_in_context():
    org = OrganizationFactory()
    campaign = _campaign(org)
    now = int(timezone.now().timestamp())
    prospect = _prospect(
        org,
        campaign,
        raw_data={
            "reviews": [{"text": "no se puede reservar turno nunca", "time": now - 86400}],
            "editorial_summary": {"overview": "Peluqueria de barrio"},
            "geometry": {"location": {"lat": -34.6, "lng": -58.4}},
            "price_level": 2,
        },
    )

    ProspectEnrichmentService.enrich(
        prospect=prospect, enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML))
    )
    prospect.refresh_from_db()

    assert prospect.website_reachable is True
    assert prospect.website_platform == "wordpress"
    assert prospect.has_online_booking is True
    assert prospect.latest_review_age_days == 1
    assert prospect.enriched_at is not None
    assert prospect.enrichment["review_themes"].get("sin_turnos") == 1
    assert prospect.enrichment["lat"] == -34.6

    # The qualifier/opener context must now see the investigation block.
    profile = _prospect_profile(prospect)
    assert "investigation" in profile
    assert profile["investigation"]["website_platform"] == "wordpress"
    assert profile["investigation"]["review_themes"].get("sin_turnos") == 1


@pytest.mark.django_db
def test_profile_has_no_investigation_before_enrichment():
    org = OrganizationFactory()
    campaign = _campaign(org)
    prospect = _prospect(org, campaign)
    profile = _prospect_profile(prospect)
    assert "investigation" not in profile


class _FakeCustomSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, query):
        self.calls.append(query)
        return self.results


class _FakeHunter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def domain_search(self, domain):
        self.calls.append(domain)
        return self.result


@pytest.mark.django_db
@override_settings(GOOGLE_CSE_DAILY_CAP=10)
def test_enrichment_uses_cse_to_find_missing_website_and_socials():
    cache.clear()
    org = OrganizationFactory()
    campaign = _campaign(org, location_hint="Palermo")
    prospect = _prospect(org, campaign, website="")
    cse = _FakeCustomSearch(
        [
            {
                "title": "Instagram",
                "link": "https://instagram.com/peluqueriasur",
                "snippet": "",
            },
            {
                "title": "Peluqueria Sur",
                "link": "https://peluqueriasur.com",
                "snippet": "Turnos",
            },
        ]
    )

    ProspectEnrichmentService.enrich(
        prospect=prospect,
        enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML)),
        custom_search=cse,
    )
    prospect.refresh_from_db()

    assert cse.calls == ["Peluqueria Sur Palermo"]
    assert prospect.website == "https://peluqueriasur.com"
    assert prospect.website_reachable is True
    custom_search = prospect.enrichment["custom_search"]
    assert custom_search["selected_website"] == "https://peluqueriasur.com"
    assert custom_search["social_links"]["instagram"] == "https://instagram.com/peluqueriasur"


@pytest.mark.django_db
def test_enrichment_does_not_repeat_cse_when_result_already_exists():
    org = OrganizationFactory()
    campaign = _campaign(org)
    prospect = _prospect(
        org,
        campaign,
        website="",
        enrichment={"custom_search": {"query": "old", "results": []}},
    )

    class BoomCSE:
        def search(self, query):
            raise AssertionError("CSE should not be called twice for the same prospect")

    ProspectEnrichmentService.enrich(prospect=prospect, custom_search=BoomCSE(), force=True)
    prospect.refresh_from_db()
    assert prospect.enrichment["custom_search"]["query"] == "old"


@pytest.mark.django_db
@override_settings(GOOGLE_CSE_DAILY_CAP=0)
def test_enrichment_respects_cse_daily_cap_before_calling_client():
    cache.clear()
    org = OrganizationFactory()
    campaign = _campaign(org)
    prospect = _prospect(org, campaign, website="")

    class BoomCSE:
        def search(self, query):
            raise AssertionError("CSE should not be called after the in-app cap is reached")

    ProspectEnrichmentService.enrich(prospect=prospect, custom_search=BoomCSE(), force=True)
    prospect.refresh_from_db()
    assert "custom_search" not in prospect.enrichment


@pytest.mark.django_db
@override_settings(HUNTER_MONTHLY_CAP=10)
def test_enrichment_uses_hunter_to_populate_owner_fields_and_context():
    cache.clear()
    org = OrganizationFactory()
    campaign = _campaign(org)
    prospect = _prospect(org, campaign, website="https://peluqueriasur.com")
    hunter = _FakeHunter(
        {
            "email": "ana@peluqueriasur.com",
            "score": 88,
            "position": "Owner",
            "full_name": "Ana Perez",
        }
    )

    ProspectEnrichmentService.enrich(
        prospect=prospect,
        enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML)),
        hunter=hunter,
    )
    prospect.refresh_from_db()

    assert hunter.calls == ["peluqueriasur.com"]
    assert prospect.owner_name == "Ana Perez"
    assert prospect.owner_email == "ana@peluqueriasur.com"
    assert prospect.owner_email_score == 88
    assert prospect.owner_title == "Owner"
    assert prospect.enrichment["hunter"]["domain"] == "peluqueriasur.com"
    assert _prospect_profile(prospect)["investigation"]["owner_name"] == "Ana Perez"


@pytest.mark.django_db
@override_settings(HUNTER_MONTHLY_CAP=10)
def test_enrichment_caches_hunter_by_domain():
    cache.clear()
    org = OrganizationFactory()
    campaign = _campaign(org)
    first = _prospect(org, campaign, place_id="p-1", website="https://peluqueriasur.com")
    second = _prospect(org, campaign, place_id="p-2", website="https://www.peluqueriasur.com")
    hunter = _FakeHunter(
        {
            "email": "ana@peluqueriasur.com",
            "score": 88,
            "position": "Owner",
            "full_name": "Ana Perez",
        }
    )

    ProspectEnrichmentService.enrich(
        prospect=first,
        enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML)),
        hunter=hunter,
    )
    ProspectEnrichmentService.enrich(
        prospect=second,
        enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML)),
        hunter=hunter,
    )
    second.refresh_from_db()

    assert hunter.calls == ["peluqueriasur.com"]
    assert second.owner_email == "ana@peluqueriasur.com"


@pytest.mark.django_db
def test_enrichment_does_not_repeat_hunter_when_owner_email_exists():
    org = OrganizationFactory()
    campaign = _campaign(org)
    prospect = _prospect(
        org,
        campaign,
        website="https://peluqueriasur.com",
        owner_email="ana@peluqueriasur.com",
    )

    class BoomHunter:
        def domain_search(self, domain):
            raise AssertionError("Hunter should not be called when owner email exists")

    ProspectEnrichmentService.enrich(
        prospect=prospect,
        enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML)),
        hunter=BoomHunter(),
        force=True,
    )
    prospect.refresh_from_db()
    assert prospect.owner_email == "ana@peluqueriasur.com"


@pytest.mark.django_db
@override_settings(HUNTER_MONTHLY_CAP=0)
def test_enrichment_respects_hunter_monthly_cap_before_calling_client():
    cache.clear()
    org = OrganizationFactory()
    campaign = _campaign(org)
    prospect = _prospect(org, campaign, website="https://peluqueriasur.com")

    class BoomHunter:
        def domain_search(self, domain):
            raise AssertionError("Hunter should not be called after the in-app cap is reached")

    ProspectEnrichmentService.enrich(
        prospect=prospect,
        enricher=WebsiteEnricher(fetcher=_fake_fetch(_WP_BOOKING_HTML)),
        hunter=BoomHunter(),
        force=True,
    )
    prospect.refresh_from_db()
    assert prospect.owner_email == ""
    assert "hunter" not in prospect.enrichment
