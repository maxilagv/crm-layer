from django.urls import path

from .views import ClientContactsView, ClientDetailView, ClientServicesView, ClientsView

urlpatterns = [
    path("", ClientsView.as_view(), name="clients"),
    path("<uuid:client_id>/", ClientDetailView.as_view(), name="client-detail"),
    path("<uuid:client_id>/contacts/", ClientContactsView.as_view(), name="client-contacts"),
    path("<uuid:client_id>/services/", ClientServicesView.as_view(), name="client-services"),
]
