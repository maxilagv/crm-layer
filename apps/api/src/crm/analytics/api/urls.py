from django.urls import path

from .views import (
    AlertDefinitionsView,
    AlertEventsView,
    AnalyticsAICostsView,
    AnalyticsConversationsView,
    AnalyticsDashboardView,
    AnalyticsFunnelView,
    AnalyticsLeadsView,
    AnalyticsTasksView,
    AnalyticsTicketsView,
    AnalyticsWhatsAppView,
)

urlpatterns = [
    path("dashboard/", AnalyticsDashboardView.as_view(), name="analytics-dashboard"),
    path("leads/", AnalyticsLeadsView.as_view(), name="analytics-leads"),
    path("conversations/", AnalyticsConversationsView.as_view(), name="analytics-conversations"),
    path("tasks/", AnalyticsTasksView.as_view(), name="analytics-tasks"),
    path("tickets/", AnalyticsTicketsView.as_view(), name="analytics-tickets"),
    path("ai-costs/", AnalyticsAICostsView.as_view(), name="analytics-ai-costs"),
    path("whatsapp/", AnalyticsWhatsAppView.as_view(), name="analytics-whatsapp"),
    path("funnel/", AnalyticsFunnelView.as_view(), name="analytics-funnel"),
    path("alerts/definitions/", AlertDefinitionsView.as_view(), name="analytics-alert-definitions"),
    path("alerts/events/", AlertEventsView.as_view(), name="analytics-alert-events"),
]
