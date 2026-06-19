from crm.prospecting.services.hunter import HunterClient, HunterError


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def test_hunter_domain_search_parses_best_email():
    def fetch(url, params, timeout):
        assert url.endswith("/domain-search")
        assert params["domain"] == "example.com"
        assert params["api_key"] == "k"
        return {
            "data": {
                "emails": [
                    {
                        "value": "info@example.com",
                        "score": 35,
                        "position": "General",
                    },
                    {
                        "value": "ana@example.com",
                        "score": 91,
                        "position": "Owner",
                        "first_name": "Ana",
                        "last_name": "Perez",
                    },
                ]
            }
        }

    result = HunterClient(api_key="k", fetcher=fetch).domain_search("www.example.com")
    assert result["email"] == "ana@example.com"
    assert result["score"] == 91
    assert result["position"] == "Owner"
    assert result["full_name"] == "Ana Perez"


def test_hunter_email_finder_parses_result():
    def fetch(url, params, timeout):
        assert url.endswith("/email-finder")
        assert params["first_name"] == "Ana"
        assert params["last_name"] == "Perez"
        return {
            "data": {
                "email": "ana@example.com",
                "score": 76,
                "position": "Founder",
                "first_name": "Ana",
                "last_name": "Perez",
            }
        }

    result = HunterClient(api_key="k", fetcher=fetch).email_finder("example.com", "Ana", "Perez")
    assert result["email"] == "ana@example.com"
    assert result["score"] == 76
    assert result["position"] == "Founder"


def test_hunter_429_returns_empty_without_raise():
    client = HunterClient(
        api_key="k",
        fetcher=lambda url, params, timeout: _Resp(
            {"errors": [{"details": "rate limit"}]}, status=429
        ),
    )
    assert client.domain_search("example.com") == {}


def test_hunter_empty_input_noops():
    def boom(url, params, timeout):
        raise AssertionError("fetcher should not be called")

    client = HunterClient(api_key="k", fetcher=boom)
    assert client.domain_search("") == {}
    assert HunterClient(api_key="", fetcher=boom).domain_search("example.com") == {}
    assert client.email_finder("example.com") == {}


def test_hunter_error_transient_classification():
    assert HunterError("server", status_code=503).is_transient is True
    assert HunterError("quota", status_code=429).is_transient is False
    assert HunterError("auth", status_code=401).is_transient is False
    assert HunterError("bad", status_code=400).is_transient is False
    assert HunterError("unknown").is_transient is False
