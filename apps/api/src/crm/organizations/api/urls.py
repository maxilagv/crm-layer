from django.urls import path

from .views import CurrentOrganizationView

urlpatterns = [
    path("current/", CurrentOrganizationView.as_view(), name="organization-current"),
]
