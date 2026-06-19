from django.urls import path

from .views import (
    AIBehaviorPolicyView,
    BusinessProfileView,
    NotificationPolicyView,
    SalesPolicyView,
    SupportPolicyView,
    WhatsAppPolicyView,
)

urlpatterns = [
    path("business-profile/", BusinessProfileView.as_view(), name="settings-business-profile"),
    path("sales-policy/", SalesPolicyView.as_view(), name="settings-sales-policy"),
    path("support-policy/", SupportPolicyView.as_view(), name="settings-support-policy"),
    path("ai-policy/", AIBehaviorPolicyView.as_view(), name="settings-ai-policy"),
    path(
        "notification-policy/",
        NotificationPolicyView.as_view(),
        name="settings-notification-policy",
    ),
    path("whatsapp-policy/", WhatsAppPolicyView.as_view(), name="settings-whatsapp-policy"),
]
