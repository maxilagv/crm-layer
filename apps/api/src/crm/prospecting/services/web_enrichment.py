"""Website intelligence for the Cazador "private investigator".

Fetches a prospect's website (if any) and extracts a structured footprint: is it
reachable, is it modern (https, mobile), what platform, does it have online
booking or e-commerce, and any emails / social links on the page. Network access
is isolated behind an injectable ``fetcher`` so tests run without HTTP.

Everything is best-effort: any failure degrades to ``reachable: False`` and never
raises to the caller. The qualifier/opener then reason over what we found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests

_TIMEOUT = 8.0
_MAX_BYTES = 600_000  # don't slurp huge pages
_UA = "Mozilla/5.0 (compatible; CazadorBot/1.0; +https://crm.local)"

# Platform fingerprints: substring (lowercased) -> platform label.
_PLATFORM_MARKERS: tuple[tuple[str, str], ...] = (
    ("wp-content", "wordpress"),
    ("wp-json", "wordpress"),
    ("/wp-includes/", "wordpress"),
    ("cdn.shopify.com", "shopify"),
    ("shopify", "shopify"),
    ("tiendanube", "tiendanube"),
    ("nuvemshop", "tiendanube"),
    ("wix.com", "wix"),
    ("_wixcss", "wix"),
    ("squarespace", "squarespace"),
    ("webflow", "webflow"),
    ("woocommerce", "woocommerce"),
    ("mercadolibre", "mercadolibre"),
    ("wordpress", "wordpress"),
)

# Online-booking signals (links or copy).
_BOOKING_MARKERS = (
    "calendly.com",
    "fresha.com",
    "booksy",
    "turnos online",
    "reservar turno",
    "reserva tu turno",
    "sacar turno",
    "agenda tu",
    "agendar",
    "reservar ahora",
    "book now",
    "/reservas",
    "/turnos",
)

# E-commerce signals.
_ECOMMERCE_MARKERS = (
    "agregar al carrito",
    "añadir al carrito",
    "anadir al carrito",
    "add to cart",
    "/carrito",
    "/cart",
    "checkout",
    "comprar ahora",
    "tienda online",
    "woocommerce",
    "snipcart",
    "mercadopago",
)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_VIEWPORT_RE = re.compile(r'<meta[^>]+name=["\']viewport["\']', re.IGNORECASE)
_INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.\-/]+", re.IGNORECASE)
_FACEBOOK_RE = re.compile(r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9_.\-/]+", re.IGNORECASE)
_WHATSAPP_RE = re.compile(
    r"https?://(?:wa\.me|api\.whatsapp\.com)/[A-Za-z0-9_?=&.\-/]+", re.IGNORECASE
)


@dataclass
class WebsiteSignals:
    reachable: bool = False
    https: bool = False
    status: int | None = None
    final_url: str = ""
    platform: str = ""
    mobile_friendly: bool = False
    has_online_booking: bool = False
    has_ecommerce: bool = False
    title: str = ""
    meta_description: str = ""
    emails: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "reachable": self.reachable,
            "https": self.https,
            "status": self.status,
            "final_url": self.final_url,
            "platform": self.platform,
            "mobile_friendly": self.mobile_friendly,
            "has_online_booking": self.has_online_booking,
            "has_ecommerce": self.has_ecommerce,
            "title": self.title,
            "meta_description": self.meta_description,
            "emails": self.emails,
            "social_links": self.social_links,
            "error": self.error,
        }


def _default_fetcher(url: str) -> tuple[int, str, str]:
    """Return (status_code, final_url, html). Raises on network errors."""
    resp = requests.get(
        url,
        timeout=_TIMEOUT,
        allow_redirects=True,
        headers={"User-Agent": _UA, "Accept-Language": "es-AR,es;q=0.9"},
        stream=True,
    )
    # Read at most _MAX_BYTES of text.
    content = resp.raw.read(_MAX_BYTES, decode_content=True) or b""
    resp.close()
    encoding = resp.encoding or "utf-8"
    try:
        html = content.decode(encoding, errors="replace")
    except (LookupError, TypeError):
        html = content.decode("utf-8", errors="replace")
    return resp.status_code, str(resp.url), html


def _norm_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw


def _first(pattern: re.Pattern, text: str) -> str:
    m = pattern.search(text)
    if not m:
        return ""
    return (m.group(1) if m.lastindex else m.group(0)).strip()


class WebsiteEnricher:
    def __init__(self, fetcher=None):
        self._fetch = fetcher or _default_fetcher

    def enrich(self, website: str) -> WebsiteSignals:
        url = _norm_url(website)
        if not url:
            return WebsiteSignals(reachable=False, error="no_website")
        try:
            status, final_url, html = self._fetch(url)
        except Exception as exc:  # noqa: BLE001 — any network failure = unreachable, never raise
            return WebsiteSignals(reachable=False, error=type(exc).__name__)

        reachable = bool(status and status < 400)
        signals = WebsiteSignals(
            reachable=reachable,
            status=status,
            final_url=final_url or url,
            https=(final_url or url).lower().startswith("https://"),
        )
        if not reachable or not html:
            return signals

        lowered = html.lower()
        signals.title = _strip_tags(_first(_TITLE_RE, html))[:200]
        signals.meta_description = _strip_tags(_first(_META_DESC_RE, html))[:300]
        signals.mobile_friendly = bool(_VIEWPORT_RE.search(html))
        signals.platform = _detect_platform(lowered)
        signals.has_online_booking = any(m in lowered for m in _BOOKING_MARKERS)
        signals.has_ecommerce = any(m in lowered for m in _ECOMMERCE_MARKERS)
        signals.emails = _dedup(_EMAIL_RE.findall(html))[:5]
        signals.social_links = _social_links(html)
        return signals


def _detect_platform(lowered_html: str) -> str:
    for marker, label in _PLATFORM_MARKERS:
        if marker in lowered_html:
            return label
    return ""


def _social_links(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    ig = _INSTAGRAM_RE.search(html)
    fb = _FACEBOOK_RE.search(html)
    wa = _WHATSAPP_RE.search(html)
    if ig:
        out["instagram"] = ig.group(0)
    if fb:
        out["facebook"] = fb.group(0)
    if wa:
        out["whatsapp"] = wa.group(0)
    return out


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        low = it.lower()
        if low not in seen:
            seen.add(low)
            out.append(it)
    return out


def domain_of(website: str) -> str:
    try:
        return urlparse(_norm_url(website)).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""
