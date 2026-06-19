from django.urls import path

from .views import NotificationPreferencesView, NotificationReadView, NotificationsView

urlpatterns = [
    path("notifications/", NotificationsView.as_view(), name="notifications-list"),
    path(
        "notifications/<uuid:notification_id>/read/",
        NotificationReadView.as_view(),
        name="notifications-read",
    ),
    path(
        "notification-preferences/",
        NotificationPreferencesView.as_view(),
        name="notification-preferences",
    ),
]
