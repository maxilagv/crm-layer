"""Google PageSpeed Insights client — the investigator's killer signal.

A slow, heavy website on mobile is the single most concrete, undeniable pain to
sell digital professionalization ("tu web tarda 9s en cargar en el celular y el
40% se va antes de verla"). We pull the Lighthouse performance score (0-100) and
the LCP for the prospect's site. Network access is behind an injectable fetcher so
tests run without HTTP, and any failure degrades to ``score=None`` (never raises).
"""

from __future__ import annotations

import requests
from django.conf import settings

_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
_TIMEOUT = 30.0


class PageSpeedClient:
    def __init__(self, *, api_key: str | None = None, fetcher=None, timeout: float = _TIMEOUT):
        if api_key is None:
            api_key = getattr(settings, "PAGESPEED_API_KEY", "")
        self.api_key = api_key
        self._fetch = fetcher or self._default_fetch
        self.timeout = timeout

    def _default_fetch(self, url: str, strategy: str) -> dict:
        params = {"url": url, "strategy": strategy, "category": "performance"}
        if self.api_key:
            params["key"] = self.api_key
        response = requests.get(_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def analyze(self, website: str, *, strategy: str = "mobile") -> dict:
        """Return {'score': 0-100|None, 'lcp_ms': int|None, 'strategy': str, 'error': str}."""
        url = (website or "").strip()
        if not url:
            return {"score": None, "lcp_ms": None, "strategy": strategy, "error": "no_website"}
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            data = self._fetch(url, strategy)
        except Exception as exc:  # noqa: BLE001 — best-effort signal, never raise to the caller
            return {
                "score": None,
                "lcp_ms": None,
                "strategy": strategy,
                "error": type(exc).__name__,
            }
        return _parse(data, strategy)


def _parse(data: dict, strategy: str) -> dict:
    result = {"score": None, "lcp_ms": None, "strategy": strategy, "error": ""}
    lighthouse = (data or {}).get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    perf = categories.get("performance") or {}
    raw_score = perf.get("score")
    if isinstance(raw_score, (int, float)):
        result["score"] = round(float(raw_score) * 100)
    audits = lighthouse.get("audits") or {}
    lcp = (audits.get("largest-contentful-paint") or {}).get("numericValue")
    if isinstance(lcp, (int, float)):
        result["lcp_ms"] = int(lcp)
    if result["score"] is None:
        result["error"] = "no_performance_score"
    return result
