from django.urls import path

from .views import KnowledgeDocumentsView, KnowledgeSourcesView

urlpatterns = [
    path("documents/", KnowledgeDocumentsView.as_view(), name="knowledge-documents"),
    path("sources/", KnowledgeSourcesView.as_view(), name="knowledge-sources"),
]
