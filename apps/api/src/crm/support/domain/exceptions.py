from rest_framework.exceptions import APIException


class SupportError(APIException):
    status_code = 400
    default_code = "support_error"
    default_detail = "Support error"


class DuplicateTicketError(SupportError):
    status_code = 409
    default_code = "duplicate_ticket"
    default_detail = "A ticket already exists for this source message"


class CriticalTicketAIResolveDenied(SupportError):
    status_code = 403
    default_code = "critical_ticket_ai_resolve_denied"
    default_detail = "A critical ticket cannot be resolved by AI alone"


class InvalidTicketTransition(SupportError):
    default_code = "invalid_ticket_transition"
    default_detail = "Invalid ticket transition"
