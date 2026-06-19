from django.urls import path

from .views import (
    TaskCancelView,
    TaskCompleteView,
    TaskDetailView,
    TaskReminderView,
    TaskSnoozeView,
    TasksView,
)

urlpatterns = [
    path("", TasksView.as_view(), name="tasks-list"),
    path("<uuid:task_id>/", TaskDetailView.as_view(), name="tasks-detail"),
    path("<uuid:task_id>/complete/", TaskCompleteView.as_view(), name="tasks-complete"),
    path("<uuid:task_id>/snooze/", TaskSnoozeView.as_view(), name="tasks-snooze"),
    path("<uuid:task_id>/cancel/", TaskCancelView.as_view(), name="tasks-cancel"),
    path("<uuid:task_id>/reminders/", TaskReminderView.as_view(), name="tasks-reminders"),
]
