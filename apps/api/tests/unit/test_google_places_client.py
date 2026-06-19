"""Google Places API (New) client: normalizes v1 responses to the legacy-shaped keys."""

from crm.prospecting.services.google_places import GooglePlacesClient, GooglePlacesError

_SEARCH_JSON = {
    "places": [
        {
            "id": "PLACE1",
            "displayName": {"text": "Gomeria Sur"},
            "formattedAddress": "Av Siempre Viva 123",
            "types": ["car_repair", "point_of_interest"],
            "rating": 4.6,
            "userRatingCount": 90,
            "websiteUri": "https://gomeriasur.com",
            "nationalPhoneNumber": "011 4444-5555",
            "photos": [{"name": "a"}, {"name": "b"}],
            "location": {"latitude": -34.6, "longitude": -58.4},
        }
    ],
    "nextPageToken": "TOK2",
}

_DETAILS_JSON = {
    "id": "PLACE1",
    "displayName": {"text": "Gomeria Sur"},
    "websiteUri": "https://gomeriasur.com",
    "priceLevel": "PRICE_LEVEL_MODERATE",
    "editorialSummary": {"text": "Gomeria de barrio"},
    "location": {"latitude": -34.6, "longitude": -58.4},
    "reviews": [
        {
            "text": {"text": "no atienden el telefono"},
            "rating": 2,
            "publishTime": "2026-06-01T12:00:00Z",
        },
    ],
}


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


class _Session:
    def __init__(self, post=None, get=None):
        self._post = post
        self._get = get

    def post(self, url, json=None, headers=None, timeout=None):
        return self._post

    def get(self, url, headers=None, timeout=None):
        return self._get


def test_text_search_normalizes_new_api():
    client = GooglePlacesClient(api_key="k", session=_Session(post=_Resp(_SEARCH_JSON)))
    out = client.text_search("gomerias")
    assert out["next_page_token"] == "TOK2"
    place = out["results"][0]
    assert place["place_id"] == "PLACE1"
    assert place["name"] == "Gomeria Sur"
    assert place["formatted_address"] == "Av Siempre Viva 123"
    assert place["website"] == "https://gomeriasur.com"
    assert place["rating"] == 4.6
    assert place["user_ratings_total"] == 90
    assert len(place["photos"]) == 2
    assert place["geometry"]["location"]["lat"] == -34.6


def test_place_details_normalizes_reviews_and_extras():
    client = GooglePlacesClient(api_key="k", session=_Session(get=_Resp(_DETAILS_JSON)))
    d = client.place_details("PLACE1")
    assert d["price_level"] == 2  # PRICE_LEVEL_MODERATE -> 2
    assert d["editorial_summary"]["overview"] == "Gomeria de barrio"
    review = d["reviews"][0]
    assert review["text"] == "no atienden el telefono"
    assert isinstance(review["time"], int)  # publishTime -> epoch seconds


def test_http_error_raises():
    client = GooglePlacesClient(
        api_key="k",
        session=_Session(post=_Resp({"error": {"message": "bad"}}, status=400)),
    )
    try:
        client.text_search("x")
        raise AssertionError("expected GooglePlacesError")
    except GooglePlacesError as exc:
        assert "bad" in str(exc)


def test_missing_key_raises():
    client = GooglePlacesClient(api_key="", session=_Session(post=_Resp(_SEARCH_JSON)))
    try:
        client.text_search("x")
        raise AssertionError("expected GooglePlacesError")
    except GooglePlacesError as exc:
        assert "GOOGLE_PLACES_API_KEY" in str(exc)
