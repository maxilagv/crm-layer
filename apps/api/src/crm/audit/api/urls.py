from django.urls import path

from .views import (
    AuditAIDecisionsView,
    AuditDataAccessLogsView,
    AuditExternalRequestsView,
    AuditLogsView,
    AuditSecurityEventsView,
)

urlpatterns = [
    path("logs/", AuditLogsView.as_view(), name="audit-logs"),
    path("data-access/", AuditDataAccessLogsView.as_view(), name="audit-data-access"),
    path("security-events/", AuditSecurityEventsView.as_view(), name="audit-security-events"),
    path("ai-decisions/", AuditAIDecisionsView.as_view(), name="audit-ai-decisions"),
    path("external-requests/", AuditExternalRequestsView.as_view(), name="audit-external-requests"),
]
