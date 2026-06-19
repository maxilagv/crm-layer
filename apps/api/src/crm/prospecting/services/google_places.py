"""Google Places API (New, v1) client for Cazador discovery.

Uses the modern ``places.googleapis.com/v1`` endpoints (Text Search + Place
Details) with API-key auth and field masks. The response is normalized back into
the flat keys the discovery service and enrichment already consume
(``name``, ``formatted_address``, ``website``, ``rating``, ``user_ratings_total``,
``types``, ``photos``, ``reviews``, ``editorial_summary``, ``geometry.location``,
``price_level``) so nothing downstream changes. Key from ``settings.GOOGLE_PLACES_API_KEY``.
"""

from __future__ import annotations

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# Field masks (New API requires them; they cap cost/fields).
_SEARCH_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.types,"
    "places.businessStatus,places.rating,places.userRatingCount,places.websiteUri,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,places.photos,"
    "places.location,nextPageToken"
)
_DETAILS_MASK = (
    "id,displayName,formattedAddress,types,businessStatus,rating,userRatingCount,"
    "websiteUri,nationalPhoneNumber,internationalPhoneNumber,photos,location,priceLevel,"
    "editorialSummary,reviews,regularOpeningHours,googleMapsUri"
)

_PRICE_LEVELS = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


class GooglePlacesError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_transient(self) -> bool:
        """True only for errors worth retrying (timeouts / 5xx). Quota (429) and
        auth (401/403) and bad-request (400) are permanent — retrying burns quota."""
        return self.status_code is not None and self.status_code >= 500


class GooglePlacesClient:
    def __init__(self, *, api_key: str | None = None, session=None, timeout: float = 15.0):
        self.api_key = api_key if api_key is not None else settings.GOOGLE_PLACES_API_KEY
        self.session = session or requests.Session()
        self.timeout = timeout

    def _headers(self, field_mask: str) -> dict:
        if not self.api_key:
            raise GooglePlacesError("GOOGLE_PLACES_API_KEY is not configured")
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

    def _post(self, url: str, body: dict, field_mask: str) -> dict:
        response = self.session.post(
            url, json=body, headers=self._headers(field_mask), timeout=self.timeout
        )
        return self._json_or_raise(response)

    def _get(self, url: str, field_mask: str) -> dict:
        response = self.session.get(url, headers=self._headers(field_mask), timeout=self.timeout)
        return self._json_or_raise(response)

    @staticmethod
    def _json_or_raise(response) -> dict:
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 400:
            message = ""
            if isinstance(data, dict):
                message = (data.get("error") or {}).get("message", "")
            raise GooglePlacesError(
                f"Places API HTTP {response.status_code}: {message}",
                status_code=response.status_code,
            )
        return data or {}

    def text_search(self, query: str, *, page_token: str | None = None) -> dict:
        """Return {'results': [normalized...], 'next_page_token': str | None}."""
        body = {"textQuery": query}
        if page_token:
            body["pageToken"] = page_token
        data = self._post(_SEARCH_URL, body, _SEARCH_MASK)
        results = [_normalize_place(p) for p in (data.get("places") or [])]
        return {"results": results, "next_page_token": data.get("nextPageToken")}

    def place_details(self, place_id: str) -> dict:
        """Return a normalized 'result' dict for a place (website, reviews, geometry, etc.)."""
        url = _DETAILS_URL.format(place_id=place_id)
        data = self._get(url, _DETAILS_MASK)
        return _normalize_place(data) if data else {}


def _normalize_place(p: dict) -> dict:
    """Map a Places API (New) place object onto the flat legacy-shaped keys."""
    if not isinstance(p, dict):
        return {}
    out: dict = {
        "place_id": p.get("id") or "",
        "name": (p.get("displayName") or {}).get("text", ""),
        "formatted_address": p.get("formattedAddress", ""),
        "types": p.get("types") or [],
        "business_status": p.get("businessStatus", ""),
        "website": p.get("websiteUri", ""),
        "international_phone_number": p.get("internationalPhoneNumber", ""),
        "formatted_phone_number": p.get("nationalPhoneNumber", ""),
        "photos": p.get("photos") or [],
        "url": p.get("googleMapsUri", ""),
    }
    if "rating" in p:
        out["rating"] = p.get("rating")
    if "userRatingCount" in p:
        out["user_ratings_total"] = p.get("userRatingCount")
    location = p.get("location") or {}
    if location:
        out["geometry"] = {
            "location": {"lat": location.get("latitude"), "lng": location.get("longitude")}
        }
    price = p.get("priceLevel")
    if price is not None:
        out["price_level"] = _PRICE_LEVELS.get(price, price)
    editorial = (p.get("editorialSummary") or {}).get("text", "")
    if editorial:
        out["editorial_summary"] = {"overview": editorial}
    reviews = p.get("reviews")
    if reviews:
        out["reviews"] = [_normalize_review(r) for r in reviews]
    return out


def _normalize_review(r: dict) -> dict:
    text_field = r.get("text")
    if isinstance(text_field, dict):
        text = text_field.get("text", "")
    elif isinstance(text_field, str):
        text = text_field
    else:
        text = ""
    review = {"text": text, "rating": r.get("rating")}
    published = r.get("publishTime")
    if published:
        parsed = parse_datetime(published)
        if parsed is not None:
            review["time"] = int(parsed.timestamp())
    return review
