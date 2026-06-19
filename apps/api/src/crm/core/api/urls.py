from django.urls import path

from .health import HealthView, LiveView, ReadyView, SystemStatusView, VersionView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/live/", LiveView.as_view(), name="health-live"),
    path("health/ready/", ReadyView.as_view(), name="health-ready"),
    path("system/status/", SystemStatusView.as_view(), name="system-status"),
    path("version/", VersionView.as_view(), name="version"),
]
