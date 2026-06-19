from django.urls import path

from .views import (
    ContactDetailView,
    ContactMergeView,
    ContactNotesView,
    ContactsView,
    ContactTagsView,
)

urlpatterns = [
    path("", ContactsView.as_view(), name="contacts"),
    path("merge/", ContactMergeView.as_view(), name="contacts-merge"),
    path("<uuid:contact_id>/", ContactDetailView.as_view(), name="contact-detail"),
    path("<uuid:contact_id>/notes/", ContactNotesView.as_view(), name="contact-notes"),
    path("<uuid:contact_id>/tags/", ContactTagsView.as_view(), name="contact-tags"),
]
