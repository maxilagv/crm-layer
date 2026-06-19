"""Render a branded sample of every document format to disk so you can eyeball quality.

Uses the organization's real Brand Kit when a DB/org is available; otherwise falls
back to a sample brand. Writes a Propuesta (PDF), un Presupuesto (XLSX) y una
Presentación (PPTX) a la carpeta indicada.

    python manage.py documents_sample --out ./muestras
    python manage.py documents_sample --organization-id <uuid> --out ~/Desktop/muestras
"""

import os
from pathlib import Path

from django.core.management.base import BaseCommand

from crm.documents.domain.enums import EXT_BY_FORMAT
from crm.documents.domain.payload import normalize_payload
from crm.documents.renderers import get_renderer

# Realistic payload for a software development studio.
SAMPLE_PAYLOAD = {
    "title": "Propuesta de desarrollo — Plataforma de turnos",
    "subtitle": "App web + backend + soporte para ACME SRL",
    "client": {
        "name": "ACME SRL",
        "contact": "Juan Pérez",
        "email": "juan@acme.com",
        "tax_id": "30-71234567-9",
    },
    "intro": (
        "Gracias por la oportunidad de trabajar juntos. A continuación detallamos el "
        "alcance propuesto, el cronograma y la inversión para la primera etapa del "
        "proyecto. Quedamos a disposición para ajustar lo que necesiten."
    ),
    "sections": [
        {
            "heading": "Alcance",
            "body": (
                "• Backend a medida (Django/DRF) con API documentada.\n"
                "• App web responsive con panel de administración.\n"
                "• Integración de notificaciones por WhatsApp.\n"
                "• Puesta en producción y monitoreo."
            ),
        },
        {
            "heading": "Cronograma",
            "body": (
                "Etapa 1 (semanas 1-3): diseño técnico y backend.\n"
                "Etapa 2 (semanas 4-6): app web e integraciones.\n"
                "Etapa 3 (semana 7): QA, deploy y capacitación."
            ),
        },
        {
            "heading": "Por qué nosotros",
            "body": (
                "Estudio de desarrollo de software con foco en producto. Entregamos "
                "código mantenible, con tests y documentación, y acompañamos la "
                "operación después del lanzamiento."
            ),
        },
    ],
    "items": [
        {
            "description": "Desarrollo backend a medida (API + base de datos)",
            "quantity": 1,
            "unit_price": "1500000",
            "unit": "proyecto",
        },
        {
            "description": "App web responsive + panel de administración",
            "quantity": 1,
            "unit_price": "1200000",
            "unit": "proyecto",
        },
        {
            "description": "Integración de notificaciones WhatsApp",
            "quantity": 1,
            "unit_price": "350000",
        },
        {
            "description": "Soporte y mantenimiento mensual",
            "quantity": 3,
            "unit_price": "180000",
            "unit": "mes",
        },
    ],
    "currency": "ARS",
    "tax_rate": "21",
    "terms": "50% para iniciar, 25% al cierre de la etapa 2 y 25% contra entrega final.",
    "valid_until": "2026-07-15",
    "meta": {"document_number": "P-0001"},
}

SAMPLE_BRAND = {
    "business_name": "Mi Estudio",
    "legal_name": "Mi Estudio de Software SRL",
    "tax_id": "30-11111111-9",
    "email": "hola@miestudio.com",
    "phone": "+54 11 5555-5555",
    "website": "miestudio.com",
    "address": "Av. Siempreviva 742, CABA",
    "primary_color": "#7C6CFF",
    "accent_color": "#22C55E",
    "text_color": "#16161D",
    "currency": "ARS",
    "default_terms": "Condiciones generales según contrato marco.",
    "footer_note": "Gracias por confiar en nosotros.",
    "logo_bytes": None,
}

# (doc_type, format) pairs to render — one of each format.
TARGETS = [("proposal", "pdf"), ("quote", "xlsx"), ("deck", "pptx")]


class Command(BaseCommand):
    help = "Renderiza una muestra branded de PDF/Excel/PowerPoint a una carpeta."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)
        parser.add_argument(
            "--out",
            default="./muestras-documentos",
            help="Carpeta de salida (se crea si no existe).",
        )

    def _resolve_brand(self, organization_id) -> dict:
        """Use the org's real Brand Kit when possible; otherwise a sample brand."""
        try:
            from crm.documents.services.brand_kit import BrandKitService
            from crm.organizations.models import Organization

            if organization_id:
                organization = Organization.objects.filter(id=organization_id).first()
            else:
                organization = Organization.objects.order_by("created_at").first()
            if organization is None:
                self.stdout.write("Sin organización: uso marca de ejemplo.")
                return SAMPLE_BRAND
            kit = BrandKitService.get_or_create(organization)
            self.stdout.write(self.style.SUCCESS(f"Usando Brand Kit de '{organization.slug}'."))
            return BrandKitService.as_render_dict(kit)
        except Exception as exc:  # noqa: BLE001 — DB puede no estar disponible
            self.stdout.write(f"No pude leer el Brand Kit ({exc}). Uso marca de ejemplo.")
            return SAMPLE_BRAND

    def handle(self, *args, **options):
        out_dir = Path(os.path.expanduser(options["out"])).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        brand = self._resolve_brand(options["organization_id"])
        payload = normalize_payload(SAMPLE_PAYLOAD)

        written = []
        for doc_type, fmt in TARGETS:
            renderer = get_renderer(fmt)
            data = renderer(brand, doc_type, payload)
            path = out_dir / f"muestra-{doc_type}.{EXT_BY_FORMAT[fmt]}"
            path.write_bytes(data)
            written.append((path, len(data)))

        self.stdout.write("")
        for path, size in written:
            self.stdout.write(f"  [OK] {path}  ({size:,} bytes)")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Listo. Abrí los archivos en: {out_dir}"))
