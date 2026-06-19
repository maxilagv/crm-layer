"""Message text normalization.

``normalize_text`` produces the ``normalized_text`` stored alongside the
original ``body``: control characters removed, whitespace collapsed and
lowercased for consistent search/routing. The original ``body`` is preserved
for display; ``raw_payload`` is never touched here.
"""

import re
import unicodedata

_WS_RUN = re.compile(r"[ \t\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def _strip_control_chars(text: str) -> str:
    # Keep newlines and tabs; drop other control/format characters.
    return "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")


def clean_body(body: str | None) -> str:
    """Light cleanup of the displayable body: normalize newlines, strip control chars."""
    if not body:
        return ""
    text = str(body).replace("\r\n", "\n").replace("\r", "\n")
    text = _strip_control_chars(text)
    return text.strip()


def normalize_text(body: str | None) -> str:
    """Search/routing form: cleaned, whitespace-collapsed, lowercased."""
    text = clean_body(body)
    if not text:
        return ""
    text = _WS_RUN.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip().lower()
