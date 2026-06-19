"""Audit domain constants shared by services, API and tests."""

SECURITY_EVENT_TYPES = {
    "login_success",
    "login_succeeded",
    "login_failed",
    "permission_denied",
    "webhook_signature_invalid",
    "cross_organization_access_blocked",
    "secret_exposure_blocked",
    "csrf_failed",
    "rate_limit_exceeded",
    "suspicious_request",
}

SECURITY_SEVERITY_BY_EVENT = {
    "login_success": "info",
    "login_succeeded": "info",
    "login_failed": "low",
    "permission_denied": "medium",
    "webhook_signature_invalid": "high",
    "cross_organization_access_blocked": "high",
    "secret_exposure_blocked": "critical",
    "csrf_failed": "medium",
    "rate_limit_exceeded": "medium",
    "suspicious_request": "high",
}

AUDIT_ACTION_ALIASES = {
    "ai_prompt_version_activated": "prompt_activated",
    "support_ticket_resolved": "ticket_resolved",
    "support_ticket_reopened": "ticket_reopened",
    "support_ticket_updated": "ticket_updated",
    "task_status_changed": "task_status_changed",
    "login_succeeded": "user_login",
    "login_failed": "user_failed_login",
}
