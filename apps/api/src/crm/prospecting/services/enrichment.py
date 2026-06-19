"""ProspectEnrichmentService: the investigator step between discovery and qualification.

Takes a freshly discovered prospect and deepens its footprint with signal the bare
Google Places row never had: an analysis of its website (if any), themes mined from
its review texts, and the extra Places fields (editorial summary, price level, geo).
Persists everything onto the typed columns + the ``enrichment`` JSON blob so the
qualifier and the opener can reason over real evidence instead of guessing.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from crm.prospecting.models import Prospect

from .custom_search import CustomSearchClient
from .hunter import HunterClient
from .pagespeed import PageSpeedClient
from .quotas import consume_daily, consume_monthly
from .web_enrichment import WebsiteEnricher, WebsiteSignals, domain_of

logger = logging.getLogger(__name__)

# Spanish review complaint themes: theme tag -> trigger substrings (accent-insensitive).
_REVIEW_THEMES: dict[str, tuple[str, ...]] = {
    "no_responde": ("no atienden", "no contestan", "no responden", "nunca atienden", "no atiende"),
    "demoras": ("demor", "tard", "lento", "lentos", "mucha espera", "hacer cola"),
    "precio_alto": ("caro", "carisimo", "muy caros", "precios altos", "un robo", "carero"),
    "mala_atencion": ("mala atencion", "maltrato", "destrato", "mal trato", "pesima atencion"),
    "sin_turnos": ("no se puede reservar", "sin turnos", "no dan turno", "conseguir turno"),
    "calidad": ("mal trabajo", "quedo mal", "tuve que volver", "no lo solucionaron", "chapuza"),
}


# Don't re-investigate (website fetch + PageSpeed + Places review parse) a prospect
# that was enriched within this window. Protects the PageSpeed/Places quota on retries
# or re-runs; pass force=True for an explicit manual refresh.
_ENRICH_TTL_HOURS = 168  # 7 days
_HUNTER_DOMAIN_CACHE_PREFIX = "prospecting:hunter:domain:"
_CACHE_MISS = object()

_SOCIAL_DOMAINS = {
    "instagram.com": "instagram",
    "facebook.com": "facebook",
}
_BLOCKED_WEBSITE_DOMAINS = (
    "google.",
    "g.page",
    "maps.",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "yelp.",
    "tripadvisor.",
    "foursquare.",
    "waze.com",
    "paginasamarillas",
)


def _normalize(text: str) -> str:
    text = "".join(
        c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", text.lower()).strip()


def mine_review_themes(reviews) -> dict[str, int]:
    """Count recurring complaint themes across Places review bodies."""
    counts: dict[str, int] = {}
    for r in reviews or []:
        body = _normalize(r.get("text", "") if isinstance(r, dict) else str(r))
        if not body:
            continue
        for theme, triggers in _REVIEW_THEMES.items():
            if any(t in body for t in triggers):
                counts[theme] = counts.get(theme, 0) + 1
    return counts


def latest_review_age_days(reviews) -> int | None:
    """Age (days) of the most recent review. Places reviews carry epoch-seconds 'time'."""
    times = [
        int(r["time"])
        for r in (reviews or [])
        if isinstance(r, dict) and str(r.get("time", "")).strip()
    ]
    if not times:
        return None
    age = (timezone.now().timestamp() - max(times)) / 86400.0
    return max(0, int(age))


class ProspectEnrichmentService:
    @staticmethod
    def enrich(
        *,
        prospect: Prospect,
        enricher: WebsiteEnricher | None = None,
        pagespeed: PageSpeedClient | None = None,
        custom_search: CustomSearchClient | None = None,
        hunter: HunterClient | None = None,
        force: bool = False,
    ) -> Prospect:
        # Skip if recently investigated (protects PageSpeed/Places quota on retries/re-runs).
        if not force and prospect.enriched_at is not None:
            age_hours = (timezone.now() - prospect.enriched_at).total_seconds() / 3600
            if age_hours < _ENRICH_TTL_HOURS:
                return prospect

        existing_enrichment = prospect.enrichment if isinstance(prospect.enrichment, dict) else {}
        custom_search_result = _maybe_custom_search(
            prospect=prospect,
            existing_enrichment=existing_enrichment,
            client=custom_search,
        )
        if custom_search_result and custom_search_result.get("selected_website"):
            prospect.website = str(custom_search_result["selected_website"])[:500]

        enricher = enricher or WebsiteEnricher()
        if prospect.website:
            web = enricher.enrich(prospect.website)
        else:
            web = WebsiteSignals(reachable=False, error="no_website")

        # PageSpeed only when the site loads and a key/client is available (it's a slow call).
        pagespeed_result = {"score": None, "lcp_ms": None}
        if prospect.website and web.reachable:
            client = pagespeed or (
                PageSpeedClient() if getattr(settings, "PAGESPEED_API_KEY", "") else None
            )
            if client is not None:
                pagespeed_result = client.analyze(prospect.website, strategy="mobile")

        hunter_result = _maybe_hunter(
            prospect=prospect,
            existing_enrichment=existing_enrichment,
            client=hunter,
        )
        _apply_hunter_result(prospect, hunter_result)

        raw = prospect.raw_data or {}
        reviews = raw.get("reviews") or []
        themes = mine_review_themes(reviews)
        age = latest_review_age_days(reviews)

        editorial = ""
        es = raw.get("editorial_summary")
        if isinstance(es, dict):
            editorial = (es.get("overview") or "")[:500]

        geometry = raw.get("geometry") or {}
        loc = geometry.get("location") if isinstance(geometry, dict) else {}
        lat = loc.get("lat") if isinstance(loc, dict) else None
        lng = loc.get("lng") if isinstance(loc, dict) else None

        enrichment = {
            **existing_enrichment,
            **web.as_dict(),
            "review_themes": themes,
            "editorial_summary": editorial,
            "price_level": raw.get("price_level"),
            "lat": lat,
            "lng": lng,
            "pagespeed": pagespeed_result,
        }
        if custom_search_result is not None:
            enrichment["custom_search"] = custom_search_result
        if hunter_result is not None:
            enrichment["hunter"] = hunter_result

        prospect.website_reachable = web.reachable if prospect.website else None
        prospect.website_platform = web.platform or ""
        prospect.has_online_booking = web.has_online_booking if web.reachable else None
        prospect.latest_review_age_days = age
        prospect.pagespeed_score = pagespeed_result.get("score")
        prospect.enrichment = enrichment
        prospect.enriched_at = timezone.now()
        update_fields = [
            "website",
            "website_reachable",
            "website_platform",
            "has_online_booking",
            "latest_review_age_days",
            "pagespeed_score",
            "owner_name",
            "owner_email",
            "owner_email_score",
            "owner_title",
            "enrichment",
            "enriched_at",
            "updated_at",
        ]
        prospect.save(update_fields=update_fields)
        return prospect


def _maybe_custom_search(
    *,
    prospect: Prospect,
    existing_enrichment: dict,
    client: CustomSearchClient | None,
) -> dict | None:
    if prospect.website or existing_enrichment.get("custom_search"):
        return None
    if client is None and not (
        getattr(settings, "GOOGLE_CSE_API_KEY", "") and getattr(settings, "GOOGLE_CSE_CX", "")
    ):
        return None

    query = _custom_search_query(prospect)
    if not query:
        return None
    if not consume_daily("cse", getattr(settings, "GOOGLE_CSE_DAILY_CAP", 90)):
        return None

    client = client or CustomSearchClient()
    results = client.search(query)
    selected = _select_custom_search_result(results)
    return {
        "query": query,
        "results": results[:5],
        "selected_website": selected["website"],
        "social_links": selected["social_links"],
    }


def _custom_search_query(prospect: Prospect) -> str:
    location = prospect.campaign.location_hint or prospect.address
    return " ".join(part for part in [prospect.business_name, location] if part).strip()


def _select_custom_search_result(results: list[dict]) -> dict:
    selected_website = ""
    social_links: dict[str, str] = {}
    for result in results or []:
        link = str((result or {}).get("link") or "").strip()
        if not link:
            continue
        social = _social_kind(link)
        if social and social not in social_links:
            social_links[social] = link
            continue
        if not selected_website and _is_plausible_website(link):
            selected_website = link
    return {"website": selected_website, "social_links": social_links}


def _social_kind(link: str) -> str:
    domain = _link_domain(link)
    for social_domain, kind in _SOCIAL_DOMAINS.items():
        if domain == social_domain or domain.endswith(f".{social_domain}"):
            return kind
    return ""


def _is_plausible_website(link: str) -> bool:
    domain = _link_domain(link)
    if not domain:
        return False
    if _social_kind(link):
        return False
    return not any(blocked in domain for blocked in _BLOCKED_WEBSITE_DOMAINS)


def _link_domain(link: str) -> str:
    try:
        parsed = urlparse(link if "://" in link else f"https://{link}")
    except ValueError:
        return ""
    return (parsed.netloc or "").lower().removeprefix("www.")


def _maybe_hunter(
    *,
    prospect: Prospect,
    existing_enrichment: dict,
    client: HunterClient | None,
) -> dict | None:
    if prospect.owner_email or existing_enrichment.get("hunter"):
        return None
    if client is None and not getattr(settings, "HUNTER_API_KEY", ""):
        return None

    domain = domain_of(prospect.website)
    if not domain:
        return None

    cache_key = f"{_HUNTER_DOMAIN_CACHE_PREFIX}{domain}"
    cached = cache.get(cache_key, _CACHE_MISS)
    if cached is not _CACHE_MISS:
        return cached if isinstance(cached, dict) else {}

    if not consume_monthly("hunter", getattr(settings, "HUNTER_MONTHLY_CAP", 40)):
        return None

    client = client or HunterClient()
    result = client.domain_search(domain)
    hunter_data = {"domain": domain, **(result or {})}
    cache.set(cache_key, hunter_data, timeout=None)
    return hunter_data


def _apply_hunter_result(prospect: Prospect, hunter_result: dict | None) -> None:
    if not hunter_result:
        return
    email = str(hunter_result.get("email") or "").strip()
    if email:
        prospect.owner_email = email[:254]
    name = str(hunter_result.get("full_name") or "").strip()
    if not name:
        first = str(hunter_result.get("first_name") or "").strip()
        last = str(hunter_result.get("last_name") or "").strip()
        name = " ".join(part for part in [first, last] if part).strip()
    if name:
        prospect.owner_name = name[:255]
    title = str(hunter_result.get("position") or "").strip()
    if title:
        prospect.owner_title = title[:255]
    score = hunter_result.get("score")
    if score is not None:
        try:
            prospect.owner_email_score = max(0, min(100, int(score)))
        except (TypeError, ValueError):
            logger.info(
                "Ignoring malformed Hunter score",
                extra={
                    "event": "prospecting.hunter_malformed_score",
                    "metadata": {"prospect_id": str(prospect.id)},
                },
            )
