"""Deterministic policy data used by SafetyGuard (regexes and keyword sets).

These are intentionally code-level (not DB) so safety behavior is reviewable
in version control. Organization-specific policy (prices, support hours) is
read from ``crm.business_settings`` at evaluation time.
"""

import re

# Requests for credentials in a proposed outbound reply -> always block.
PASSWORD_REQUEST_PATTERNS = [
    re.compile(r"\b(contraseñ|password|clave de acceso|pin de seguridad)\w*\b", re.IGNORECASE),
]

# Absolute guarantees / false promises -> block or revise.
FALSE_PROMISE_PATTERNS = [
    re.compile(
        r"\b(garantizamos|garantizado|resultados? garantizados?|100% (seguro|garantizado)"
        r"|sin ning[uú]n riesgo|te aseguro que (funciona|va a funcionar))\b",
        re.IGNORECASE,
    ),
]

# Price mentions (ARS/USD style). Used to detect unauthorized quoting.
PRICE_PATTERN = re.compile(r"(\$|usd|ars|u\$s)\s?\d[\d.,]*", re.IGNORECASE)

# Legal threats in inbound/customer text -> handoff.
LEGAL_THREAT_KEYWORDS = (
    "abogado",
    "demanda",
    "demandar",
    "denuncia",
    "denunciar",
    "defensa del consumidor",
    "acciones legales",
    "legales",
    "estafa",
)

# Anger signals in inbound text -> handoff.
ANGRY_KEYWORDS = (
    "indignado",
    "furioso",
    "harto",
    "es una vergüenza",
    "una verguenza",
    "pésimo servicio",
    "pesimo servicio",
    "no funciona nada",
    "quiero cancelar todo",
    "los voy a escrachar",
)

# Critical incident signals -> notify owner + handoff.
CRITICAL_FAILURE_KEYWORDS = (
    "producción caída",
    "produccion caida",
    "sistema caído",
    "sistema caido",
    "no podemos operar",
    "perdimos datos",
    "urgente no funciona",
)

# Sensitive operations that require a human -> handoff/notify.
SENSITIVE_OPERATION_KEYWORDS = (
    "reembolso",
    "devolución del dinero",
    "devolucion del dinero",
    "contrato",
    "factura ya pagada",
    "transferencia",
)

# Sensitive data patterns (cards, CBU-like long numbers) for redaction checks.
SENSITIVE_DATA_PATTERNS = [
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),  # card / CBU-like sequences
    re.compile(r"\b\d{2}-\d{8}-\d\b"),  # CUIT/CUIL
]
