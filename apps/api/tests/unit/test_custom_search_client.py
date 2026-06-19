from crm.prospecting.services.custom_search import CustomSearchClient, CustomSearchError


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def test_custom_search_parses_results():
    def fetch(url, params, timeout):
        assert "customsearch" in url
        assert params["key"] == "k"
        assert params["cx"] == "cx"
        assert params["q"] == "peluqueria palermo"
        return {
            "items": [
                {
                    "title": "Peluqueria Sur",
                    "link": "https://peluqueriasur.com",
                    "snippet": "Turnos y color.",
                },
                {"title": "sin link"},
            ]
        }

    result = CustomSearchClient(api_key="k", cx="cx", fetcher=fetch).search("peluqueria palermo")
    assert result == [
        {
            "title": "Peluqueria Sur",
            "link": "https://peluqueriasur.com",
            "snippet": "Turnos y color.",
        }
    ]


def test_custom_search_429_returns_empty_without_raise():
    client = CustomSearchClient(
        api_key="k",
        cx="cx",
        fetcher=lambda url, params, timeout: _Resp(
            {"error": {"message": "daily quota exceeded"}}, status=429
        ),
    )
    assert client.search("x") == []


def test_custom_search_empty_input_noops():
    def boom(url, params, timeout):
        raise AssertionError("fetcher should not be called")

    client = CustomSearchClient(api_key="k", cx="cx", fetcher=boom)
    assert client.search("") == []
    assert CustomSearchClient(api_key="", cx="cx", fetcher=boom).search("x") == []
    assert CustomSearchClient(api_key="k", cx="", fetcher=boom).search("x") == []


def test_custom_search_error_transient_classification():
    assert CustomSearchError("server", status_code=503).is_transient is True
    assert CustomSearchError("quota", status_code=429).is_transient is False
    assert CustomSearchError("auth", status_code=401).is_transient is False
    assert CustomSearchError("bad", status_code=400).is_transient is False
    assert CustomSearchError("unknown").is_transient is False
