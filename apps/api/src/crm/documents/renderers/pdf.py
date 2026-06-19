"""Branded PDF renderer (reportlab). Pure: (brand, doc_type, payload) -> bytes."""

from functools import partial
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from crm.documents.domain.enums import DOCUMENT_TYPE_LABELS
from crm.documents.domain.payload import format_money

PAGE_W, PAGE_H = A4
BAND_H = 26 * mm


def _hex(value: str, fallback: str) -> colors.Color:
    try:
        return colors.HexColor(value)
    except (ValueError, AttributeError):
        return colors.HexColor(fallback)


def _styles(brand: dict) -> dict:
    text = _hex(brand.get("text_color", "#16161D"), "#16161D")
    muted = colors.HexColor("#6B6B7B")
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocTitle",
            parent=base["Heading1"],
            fontSize=20,
            leading=24,
            textColor=text,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "DocSubtitle",
            parent=base["Normal"],
            fontSize=11,
            textColor=muted,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "DocH2",
            parent=base["Heading2"],
            fontSize=12,
            leading=15,
            textColor=text,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "DocBody",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            textColor=text,
        ),
        "small": ParagraphStyle(
            "DocSmall",
            parent=base["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=muted,
        ),
        "right": ParagraphStyle(
            "DocRight",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            alignment=TA_RIGHT,
            textColor=text,
        ),
        "cell": ParagraphStyle(
            "DocCell",
            parent=base["Normal"],
            fontSize=9.5,
            leading=12,
            textColor=text,
        ),
        "cellr": ParagraphStyle(
            "DocCellR",
            parent=base["Normal"],
            fontSize=9.5,
            leading=12,
            alignment=TA_RIGHT,
            textColor=text,
        ),
        "thead": ParagraphStyle(
            "DocTHead",
            parent=base["Normal"],
            fontSize=9.5,
            leading=12,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "theadr": ParagraphStyle(
            "DocTHeadR",
            parent=base["Normal"],
            fontSize=9.5,
            leading=12,
            textColor=colors.white,
            alignment=TA_RIGHT,
        ),
    }


def _decorate(canvas, doc, *, brand: dict, label: str, number: str) -> None:
    primary = _hex(brand.get("primary_color", "#7C6CFF"), "#7C6CFF")
    canvas.saveState()
    # Top brand band.
    canvas.setFillColor(primary)
    canvas.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, fill=1, stroke=0)

    logo_bytes = brand.get("logo_bytes")
    text_x = 18 * mm
    if logo_bytes:
        try:
            img = ImageReader(BytesIO(logo_bytes))
            iw, ih = img.getSize()
            h = 12 * mm
            w = h * (iw / ih) if ih else h
            canvas.drawImage(
                img,
                18 * mm,
                PAGE_H - BAND_H + (BAND_H - h) / 2,
                width=w,
                height=h,
                mask="auto",
                preserveAspectRatio=True,
            )
            text_x = 18 * mm + w + 6 * mm
        except Exception:  # noqa: BLE001 — a bad logo never breaks the document
            pass

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(text_x, PAGE_H - 14 * mm, (brand.get("business_name") or "")[:48])
    canvas.setFont("Helvetica", 9)
    right = label if not number else f"{label} · {number}"
    canvas.drawRightString(PAGE_W - 18 * mm, PAGE_H - 14 * mm, right)

    # Footer.
    muted = colors.HexColor("#9494A7")
    canvas.setStrokeColor(colors.HexColor("#E4E4EE"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 16 * mm, PAGE_W - 18 * mm, 16 * mm)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 7.5)
    footer_bits = [
        b
        for b in [
            brand.get("business_name"),
            brand.get("tax_id"),
            brand.get("email"),
            brand.get("phone"),
            brand.get("footer_note"),
        ]
        if b
    ]
    canvas.drawString(18 * mm, 11 * mm, "  ·  ".join(footer_bits)[:120])
    canvas.drawRightString(PAGE_W - 18 * mm, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _client_box(payload: dict, st: dict) -> Table:
    c = payload["client"]
    lines = [f"<b>Para:</b> {c['name']}" if c["name"] else "<b>Para:</b> —"]
    extra = "  ·  ".join(b for b in [c["contact"], c["email"], c["phone"]] if b)
    if extra:
        lines.append(extra)
    if c["tax_id"]:
        lines.append(f"CUIT/ID: {c['tax_id']}")
    if c["address"]:
        lines.append(c["address"])
    meta = []
    if payload["valid_until"]:
        meta.append(f"<b>Válido hasta:</b> {payload['valid_until']}")
    left = Paragraph("<br/>".join(lines), st["body"])
    right = Paragraph("<br/>".join(meta), st["right"]) if meta else Paragraph("", st["right"])
    table = Table([[left, right]], colWidths=[110 * mm, 59 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F5F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4EE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _items_table(payload: dict, brand: dict, st: dict) -> Table:
    primary = _hex(brand.get("primary_color", "#7C6CFF"), "#7C6CFF")
    currency = payload["currency"] or brand.get("currency", "")
    head = [
        Paragraph("Detalle", st["thead"]),
        Paragraph("Cant.", st["theadr"]),
        Paragraph("Precio unit.", st["theadr"]),
        Paragraph("Importe", st["theadr"]),
    ]
    rows = [head]
    for it in payload["items"]:
        desc = it["description"] or "—"
        if it["unit"]:
            desc = f"{desc} <font color='#9494A7'>({it['unit']})</font>"
        rows.append(
            [
                Paragraph(desc, st["cell"]),
                Paragraph(f"{it['quantity'].normalize():f}", st["cellr"]),
                Paragraph(format_money(it["unit_price"], currency), st["cellr"]),
                Paragraph(format_money(it["line_total"], currency), st["cellr"]),
            ]
        )
    table = Table(rows, colWidths=[95 * mm, 18 * mm, 28 * mm, 28 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#E4E4EE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFAFC")))
    table.setStyle(TableStyle(style))
    return table


def _totals_table(payload: dict, brand: dict, st: dict) -> Table:
    primary = _hex(brand.get("primary_color", "#7C6CFF"), "#7C6CFF")
    currency = payload["currency"] or brand.get("currency", "")
    data = [
        [
            Paragraph("Subtotal", st["cellr"]),
            Paragraph(format_money(payload["subtotal"], currency), st["cellr"]),
        ],
    ]
    if payload["tax_rate"] and payload["tax"]:
        data.append(
            [
                Paragraph(f"IVA ({payload['tax_rate'].normalize():f}%)", st["cellr"]),
                Paragraph(format_money(payload["tax"], currency), st["cellr"]),
            ]
        )
    total_style = ParagraphStyle(
        "DocTotal",
        parent=st["cellr"],
        fontSize=11,
        textColor=colors.white,
    )
    data.append(
        [
            Paragraph("Total", total_style),
            Paragraph(format_money(payload["total"], currency), total_style),
        ]
    )
    table = Table(data, colWidths=[40 * mm, 33 * mm], hAlign="RIGHT")
    style = [
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, -1), (-1, -1), primary),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#E4E4EE")),
    ]
    table.setStyle(TableStyle(style))
    return table


def render_pdf(brand: dict, doc_type: str, payload: dict) -> bytes:
    buf = BytesIO()
    label = DOCUMENT_TYPE_LABELS.get(doc_type, "Documento")
    st = _styles(brand)
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=BAND_H + 10 * mm,
        bottomMargin=20 * mm,
        title=(payload["title"] or label),
        author=brand.get("business_name", ""),
    )
    story: list = []
    story.append(Paragraph(payload["title"] or label, st["title"]))
    if payload["subtitle"]:
        story.append(Paragraph(payload["subtitle"], st["subtitle"]))
    story.append(
        HRFlowable(
            width="100%", thickness=1.2, color=_hex(brand.get("accent_color", "#22C55E"), "#22C55E")
        )
    )
    story.append(Spacer(1, 8))
    story.append(_client_box(payload, st))

    if payload["intro"]:
        story.append(Spacer(1, 10))
        story.append(Paragraph(payload["intro"].replace("\n", "<br/>"), st["body"]))

    for section in payload["sections"]:
        if section["heading"]:
            story.append(Paragraph(section["heading"], st["h2"]))
        if section["body"]:
            story.append(Paragraph(section["body"].replace("\n", "<br/>"), st["body"]))

    if payload["has_items"]:
        story.append(Spacer(1, 12))
        story.append(_items_table(payload, brand, st))
        story.append(Spacer(1, 6))
        story.append(_totals_table(payload, brand, st))

    if payload["notes"]:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Notas", st["h2"]))
        story.append(Paragraph(payload["notes"].replace("\n", "<br/>"), st["body"]))

    terms = payload["terms"] or brand.get("default_terms", "")
    if terms:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Términos y condiciones", st["h2"]))
        story.append(Paragraph(terms.replace("\n", "<br/>"), st["small"]))

    on_page = partial(_decorate, brand=brand, label=label, number=payload["document_number"])
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
