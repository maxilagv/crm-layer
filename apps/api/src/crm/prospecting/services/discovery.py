"""ProspectDiscoveryService: turn a campaign query into deduplicated Prospects."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from crm.prospecting.domain.enums import CampaignSource, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign

from .apollo import ApolloClient
from .google_places import GooglePlacesClient, GooglePlacesError

# Hard cap on Text Search pages per discovery run. Each page == 1 SearchText call
# (quota). The New API rarely returns more than ~3 pages; this stops a runaway loop
# from paginating forever when every result is a dedup hit and `created` never grows.
_MAX_PAGES = 5


@dataclass(frozen=True)
class DiscoveryResult:
    created: list[Prospect]
    skipped: int  # already existed (dedup) or concurrent insert


def _phone(merged: dict) -> str:
    return (
        merged.get("international_phone_number") or merged.get("formatted_phone_number") or ""
    ).strip()


def _prospect_fields(place: dict, details: dict) -> dict:
    merged = {**place, **{k: v for k, v in details.items() if v}}
    return {
        "business_name": (merged.get("name") or "")[:255],
        "category": ", ".join((merged.get("types") or [])[:3])[:255],
        "address": (merged.get("formatted_address") or "")[:500],
        "phone": _phone(merged)[:64],
        "website": (merged.get("website") or "")[:500],
        "rating": merged.get("rating"),
        "reviews_count": int(merged.get("user_ratings_total") or 0),
        "photos_count": len(merged.get("photos") or []),
        "raw_data": merged,
    }


def _apollo_prospect_fields(org: dict) -> dict:
    address = ", ".join(
        part
        for part in [
            org.get("city") or "",
            org.get("state") or "",
            org.get("country") or "",
        ]
        if part
    )
    raw = org.get("raw") if isinstance(org.get("raw"), dict) else org
    return {
        "business_name": (org.get("name") or "")[:255],
        "category": (org.get("industry") or "")[:255],
        "address": address[:500],
        "phone": (org.get("phone") or "")[:64],
        "website": (org.get("website") or "")[:500],
        "raw_data": {"apollo": raw},
    }


class ProspectDiscoveryService:
    @staticmethod
    def discover(
        *,
        campaign: ProspectingCampaign,
        client: GooglePlacesClient | ApolloClient | None = None,
        max_results: int = 60,
        enrich: bool = True,
    ) -> DiscoveryResult:
        if campaign.source == CampaignSource.APOLLO:
            return ProspectDiscoveryService._discover_apollo(
                campaign=campaign,
                client=client,
                max_results=max_results,
            )

        client = client or GooglePlacesClient()
        query = campaign.query
        if campaign.location_hint and campaign.location_hint.lower() not in query.lower():
            query = f"{query} {campaign.location_hint}"

        existing = set(
            Prospect.objects.filter(
                organization_id=campaign.organization_id,
                campaign=campaign,
                deleted_at__isnull=True,
            )
            .exclude(place_id="")
            .values_list("place_id", flat=True)
        )

        created: list[Prospect] = []
        skipped = 0
        seen: set[str] = set()
        page_token: str | None = None
        first = True
        pages = 0

        while len(created) < max_results and pages < _MAX_PAGES:
            pages += 1
            if first:
                page = client.text_search(query)
                first = False
            else:
                try:
                    page = client.text_search(query, page_token=page_token)
                except GooglePlacesError:
                    break  # subsequent-page token may be invalid/expired; keep page 1

            for place in page.get("results", []):
                place_id = place.get("place_id") or ""
                if not place_id or place_id in seen:
                    continue
                seen.add(place_id)
                if place_id in existing:
                    skipped += 1
                    continue
                details = client.place_details(place_id) if enrich else {}
                prospect = ProspectDiscoveryService._create(
                    campaign, place_id, _prospect_fields(place, details)
                )
                if prospect is None:
                    skipped += 1
                else:
                    created.append(prospect)
                if len(created) >= max_results:
                    break

            page_token = page.get("next_page_token")
            if not page_token:
                break

        ProspectingCampaign.objects.filter(id=campaign.id).update(
            discovered_count=models.F("discovered_count") + len(created),
            last_run_at=timezone.now(),
        )
        return DiscoveryResult(created=created, skipped=skipped)

    @staticmethod
    def _discover_apollo(
        *,
        campaign: ProspectingCampaign,
        client: ApolloClient | None = None,
        max_results: int = 60,
    ) -> DiscoveryResult:
        client = client or ApolloClient()
        max_results = min(max_results, int(campaign.daily_cap or max_results))
        existing = set(
            Prospect.objects.filter(
                organization_id=campaign.organization_id,
                campaign=campaign,
                external_source=CampaignSource.APOLLO.value,
                deleted_at__isnull=True,
            )
            .exclude(external_id="")
            .values_list("external_id", flat=True)
        )

        organizations = client.organization_search(
            query=campaign.query,
            location=campaign.location_hint,
            industry=campaign.vertical,
            max_pages=_MAX_PAGES,
            max_results=max_results,
        )

        created: list[Prospect] = []
        skipped = 0
        seen: set[str] = set()
        for org in organizations:
            external_id = str((org or {}).get("apollo_id") or "").strip()
            if not external_id or external_id in seen:
                continue
            seen.add(external_id)
            if external_id in existing:
                skipped += 1
                continue
            prospect = ProspectDiscoveryService._create(
                campaign,
                "",
                _apollo_prospect_fields(org),
                external_source=CampaignSource.APOLLO.value,
                external_id=external_id,
            )
            if prospect is None:
                skipped += 1
            else:
                created.append(prospect)
            if len(created) >= max_results:
                break

        ProspectingCampaign.objects.filter(id=campaign.id).update(
            discovered_count=models.F("discovered_count") + len(created),
            last_run_at=timezone.now(),
        )
        return DiscoveryResult(created=created, skipped=skipped)

    @staticmethod
    @transaction.atomic
    def _create(
        campaign: ProspectingCampaign,
        place_id: str,
        fields: dict,
        *,
        external_source: str = "",
        external_id: str = "",
    ) -> Prospect | None:
        try:
            prospect = Prospect.objects.create(
                organization_id=campaign.organization_id,
                campaign=campaign,
                place_id=place_id,
                external_source=external_source,
                external_id=external_id,
                status=ProspectStatus.DISCOVERED.value,
                **fields,
            )
        except IntegrityError:
            return None  # concurrent insert hit the unique constraint
        # Investigate + auto-qualify the freshly discovered prospect once the row commits.
        transaction.on_commit(lambda pid=str(prospect.id): _enqueue_enrichment(pid))
        return prospect


def _enqueue_enrichment(prospect_id: str) -> None:
    try:
        from crm.prospecting.tasks import enrich_prospect

        # Enrichment chains qualification on success (then_qualify=True by default).
        enrich_prospect.delay(prospect_id=prospect_id)
    except Exception:  # noqa: BLE001 — best-effort; discovery must not fail
        pass
