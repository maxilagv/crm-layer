from crm.audit.models import (
    AuditAIDecision,
    AuditDataAccessLog,
    AuditExternalRequest,
    AuditLog,
    AuditSecurityEvent,
)


def audit_logs_for_organization(organization):
    return AuditLog.objects.filter(organization_id=organization.id)


def data_access_logs_for_organization(organization):
    return AuditDataAccessLog.objects.filter(organization_id=organization.id)


def security_events_for_organization(organization):
    return AuditSecurityEvent.objects.filter(organization_id=organization.id)


def ai_decisions_for_organization(organization):
    return AuditAIDecision.objects.filter(organization_id=organization.id)


def external_requests_for_organization(organization):
    return AuditExternalRequest.objects.filter(organization_id=organization.id)
