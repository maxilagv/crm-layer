from crm.documents.domain.enums import DocumentFormat

from .pdf import render_pdf
from .pptx import render_pptx
from .xlsx import render_xlsx

_RENDERERS = {
    DocumentFormat.PDF.value: render_pdf,
    DocumentFormat.XLSX.value: render_xlsx,
    DocumentFormat.PPTX.value: render_pptx,
}


def get_renderer(fmt: str):
    renderer = _RENDERERS.get(fmt)
    if renderer is None:
        raise ValueError(f"Formato de documento no soportado: {fmt}")
    return renderer


__all__ = ["get_renderer", "render_pdf", "render_xlsx", "render_pptx"]
