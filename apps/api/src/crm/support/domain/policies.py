"""Deterministic triage keyword rules (reviewable in version control).

Organization-specific overrides (urgent_keywords, critical_ticket_rules) are
read from ``business_settings.SupportPolicy`` at triage time.
"""

from .enums import TicketCategory, TicketPriority

# category -> keyword substrings (lowercased, accent-insensitive matching done in code)
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    TicketCategory.ACCESS.value: (
        "no puedo acceder",
        "no puedo entrar",
        "login",
        "iniciar sesion",
        "contrasena",
        "password",
        "no me deja entrar",
        "bloqueado",
    ),
    TicketCategory.BILLING.value: (
        "pago",
        "factura",
        "cobro",
        "facturacion",
        "tarjeta",
        "suscripcion",
        "reembolso",
    ),
    TicketCategory.PERFORMANCE.value: (
        "lento",
        "demora",
        "performance",
        "se cuelga",
        "tarda mucho",
        "rendimiento",
    ),
    TicketCategory.INTEGRATION.value: (
        "integracion",
        "api",
        "webhook",
        "whatsapp",
        "conexion",
        "sincroniza",
    ),
    TicketCategory.DATA_ISSUE.value: (
        "datos incorrectos",
        "se borraron",
        "perdimos datos",
        "informacion mal",
    ),
    TicketCategory.BUG.value: (
        "error",
        "falla",
        "bug",
        "no funciona",
        "se rompe",
    ),
}

# Phrases that escalate to urgent/critical regardless of category.
URGENT_KEYWORDS = (
    "caido",
    "no funciona nada",
    "produccion",
    "clientes no pueden",
    "no podemos operar",
    "urgente",
    "sistema caido",
    "todo roto",
)
CRITICAL_KEYWORDS = (
    "produccion caida",
    "perdimos datos",
    "fuga de datos",
    "no podemos facturar",
    "todos los clientes",
    "sistema completamente caido",
)

# Support levels (from clients) that elevate priority by one step.
ELEVATING_SUPPORT_LEVELS = {"priority", "vip", "internal"}


def default_priority() -> str:
    return TicketPriority.MEDIUM.value
