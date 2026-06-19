import re

from .enums import ObjectionType, SalesIntent

PRICE_PATTERN = re.compile(r"(\$\s?\d+|\d+\s?(usd|d[oó]lares|ars|pesos))", re.IGNORECASE)
GUARANTEE_PATTERN = re.compile(
    r"\b(te\s+garantizo|garantizamos|resultado\s+garantizado|100%\s+seguro)\b",
    re.IGNORECASE,
)
AGGRESSIVE_PATTERN = re.compile(
    r"\b(ten[eé]s que comprar|compr[aá] ahora|[uú]ltima oportunidad|si no contrat[aá]s)\b",
    re.IGNORECASE,
)
SENSITIVE_DATA_PATTERN = re.compile(
    r"\b(contrase[nñ]a|password|tarjeta|c[oó]digo de seguridad|cvv)\b",
    re.IGNORECASE,
)
CONTRACT_CLOSE_PATTERN = re.compile(
    r"\b(firm[aá] el contrato|pag[aá] ahora|enviame el pago|cerramos el contrato)\b",
    re.IGNORECASE,
)
AVAILABILITY_PATTERN = re.compile(
    r"\b(tengo disponibilidad|ma[nñ]ana puedo|hoy puedo|agenda libre)\b",
    re.IGNORECASE,
)
CASE_STUDY_PATTERN = re.compile(
    r"\b(caso de [eé]xito|cliente similar logr[oó]|multiplicamos ventas)\b",
    re.IGNORECASE,
)

PRICE_OBJECTION_PATTERN = re.compile(
    r"\b(caro|precio|presupuesto|cost[oa]|no me da|muy alto)\b", re.IGNORECASE
)
TIME_OBJECTION_PATTERN = re.compile(
    r"\b(no tengo tiempo|despu[eé]s|m[aá]s adelante|ahora no)\b", re.IGNORECASE
)
NOT_INTERESTED_PATTERN = re.compile(
    r"\b(no me interesa|no gracias|dejalo|baja|stop)\b", re.IGNORECASE
)
WANTS_CALL_PATTERN = re.compile(
    r"\b(llamada|reuni[oó]n|meet|hablar|agendar|coordinar)\b", re.IGNORECASE
)
PRICE_QUESTION_PATTERN = re.compile(r"\b(precio|cu[aá]nto sale|cost[oa]|valor)\b", re.IGNORECASE)
PROBLEM_PATTERN = re.compile(
    r"\b(problema|error|necesito|quiero automatizar|pierdo|demora)\b", re.IGNORECASE
)


def detect_objection_type(text: str) -> str | None:
    if NOT_INTERESTED_PATTERN.search(text or ""):
        return ObjectionType.NOT_INTERESTED.value
    if PRICE_OBJECTION_PATTERN.search(text or ""):
        return ObjectionType.PRICE.value
    if TIME_OBJECTION_PATTERN.search(text or ""):
        return ObjectionType.TIME.value
    return None


def classify_intent(text: str) -> str:
    value = text or ""
    objection = detect_objection_type(value)
    if objection == ObjectionType.PRICE.value:
        return SalesIntent.OBJECTING_PRICE.value
    if objection == ObjectionType.TIME.value:
        return SalesIntent.OBJECTING_TIME.value
    if objection == ObjectionType.NOT_INTERESTED.value:
        return SalesIntent.NOT_INTERESTED.value
    if WANTS_CALL_PATTERN.search(value):
        return SalesIntent.WANTS_CALL.value
    if PRICE_QUESTION_PATTERN.search(value):
        return SalesIntent.ASKING_PRICE.value
    if PROBLEM_PATTERN.search(value):
        return SalesIntent.HAS_PROBLEM.value
    return SalesIntent.NEW_INTEREST.value
