from django.urls import path

from .views import (
    ConversationCloseView,
    ConversationDetailView,
    ConversationMessagesView,
    ConversationPauseAIView,
    ConversationReopenView,
    ConversationResumeAIView,
    ConversationSendMessageView,
    ConversationsView,
    ConversationTakeoverView,
)

urlpatterns = [
    path("", ConversationsView.as_view(), name="conversations"),
    path("<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path(
        "<uuid:conversation_id>/messages/",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
    path(
        "<uuid:conversation_id>/send-message/",
        ConversationSendMessageView.as_view(),
        name="conversation-send-message",
    ),
    path(
        "<uuid:conversation_id>/takeover/",
        ConversationTakeoverView.as_view(),
        name="conversation-takeover",
    ),
    path(
        "<uuid:conversation_id>/pause-ai/",
        ConversationPauseAIView.as_view(),
        name="conversation-pause-ai",
    ),
    path(
        "<uuid:conversation_id>/resume-ai/",
        ConversationResumeAIView.as_view(),
        name="conversation-resume-ai",
    ),
    path(
        "<uuid:conversation_id>/close/",
        ConversationCloseView.as_view(),
        name="conversation-close",
    ),
    path(
        "<uuid:conversation_id>/reopen/",
        ConversationReopenView.as_view(),
        name="conversation-reopen",
    ),
]
