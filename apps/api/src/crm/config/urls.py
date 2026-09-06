from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("crm.core.api.urls")),
    path("api/knowledge/", include("crm.knowledge.api.urls")),
    path("api/v1/", include("crm.accounts.api.urls")),
    path("api/v1/organizations/", include("crm.organizations.api.urls")),
    path("api/v1/settings/", include("crm.business_settings.api.urls")),
    path("api/v1/contacts/", include("crm.contacts.api.urls")),
    path("api/v1/conversations/", include("crm.conversations.api.urls")),
    path("api/v1/ai/", include("crm.ai.api.urls")),
    path("api/v1/knowledge/", include("crm.knowledge.api.urls")),
    path("api/v1/", include("crm.whatsapp.api.urls")),
    path("api/v1/leads/", include("crm.leads.api.urls")),
    path("api/v1/sales/", include("crm.sales.api.urls")),
    path("api/v1/tasks/", include("crm.tasks.api.urls")),
    path("api/v1/", include("crm.notifications.api.urls")),
    path("api/v1/automations/", include("crm.automations.api.urls")),
    path("api/v1/media/", include("crm.media.api.urls")),
    path("api/v1/clients/", include("crm.clients.api.urls")),
    path("api/v1/", include("crm.support.api.urls")),
    path("api/v1/image-generations/", include("crm.media.api.image_urls")),
    path("api/v1/documents/", include("crm.documents.api.urls")),
    path("api/v1/prospecting/", include("crm.prospecting.api.urls")),
    path("api/v1/analytics/", include("crm.analytics.api.urls")),
    path("api/v1/audit/", include("crm.audit.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
