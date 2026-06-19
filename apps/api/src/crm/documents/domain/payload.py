"""Document payload: one normalized spec rendered into PDF / Excel / PPTX.

The API/agent provide a JSON-safe ``raw`` payload (strings/numbers); we store
that verbatim and normalize at render time into Decimals + computed totals.
Renderers consume the normalized dict and never touch the DB.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

_CENTS = Decimal("0.01")


def to_decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def format_money(amount: Decimal, currency: str = "") -> str:
    """AR-style money: thousands with '.', decimals with ','."""
    q = amount.quantize(_CENTS)
    s = f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{currency} {s}".strip()


def _str(value: Any) -> str:
    return str(value).strip() if value not in (None,) else ""


def normalize_payload(raw: dict | None) -> dict:
    raw = raw or {}

    items = []
    for it in raw.get("items") or []:
        qty = to_decimal(it.get("quantity", 1), "1")
        price = to_decimal(it.get("unit_price", 0))
        items.append(
            {
                "description": _str(it.get("description", "")),
                "quantity": qty,
                "unit": _str(it.get("unit", "")),
                "unit_price": price,
                "line_total": (qty * price).quantize(_CENTS),
            }
        )

    subtotal = sum((i["line_total"] for i in items), Decimal("0")).quantize(_CENTS)
    tax_rate = to_decimal(raw.get("tax_rate", 0))
    tax = (subtotal * tax_rate / Decimal("100")).quantize(_CENTS)
    total = (subtotal + tax).quantize(_CENTS)

    sections = [
        {"heading": _str(s.get("heading", "")), "body": _str(s.get("body", ""))}
        for s in (raw.get("sections") or [])
        if _str(s.get("heading", "")) or _str(s.get("body", ""))
    ]

    client = raw.get("client") or {}
    meta = raw.get("meta") or {}

    return {
        "title": _str(raw.get("title", "")),
        "subtitle": _str(raw.get("subtitle", "")),
        "client": {
            "name": _str(client.get("name", "")),
            "contact": _str(client.get("contact", "")),
            "email": _str(client.get("email", "")),
            "phone": _str(client.get("phone", "")),
            "tax_id": _str(client.get("tax_id", "")),
            "address": _str(client.get("address", "")),
        },
        "intro": _str(raw.get("intro", "")),
        "sections": sections,
        "items": items,
        "currency": _str(raw.get("currency", "")),
        "tax_rate": tax_rate,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "has_items": bool(items),
        "notes": _str(raw.get("notes", "")),
        "terms": _str(raw.get("terms", "")),
        "valid_until": _str(raw.get("valid_until", "")),
        "document_number": _str(meta.get("document_number", "")),
    }
