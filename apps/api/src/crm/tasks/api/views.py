from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization
from crm.tasks.api.serializers import (
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskReminderCreateSerializer,
    TaskReminderSerializer,
    TaskSnoozeSerializer,
    TaskUpdateSerializer,
)
from crm.tasks.selectors.task_detail import task_get_for_organization
from crm.tasks.selectors.task_list import task_list_for_organization
from crm.tasks.services.task_completion import TaskCompletionService
from crm.tasks.services.task_creator import TaskCreator
from crm.tasks.services.task_scheduler import TaskScheduler
from crm.tasks.services.task_updater import TaskUpdater


def _get_task_or_404(organization, task_id):
    task = task_get_for_organization(organization, task_id)
    if task is None:
        raise NotFound("Task not found in current organization")
    return task


class TasksView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: TaskListSerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        due_before = _parse_dt(request.query_params.get("due_before"))
        due_after = _parse_dt(request.query_params.get("due_after"))
        queryset = task_list_for_organization(
            organization,
            status=request.query_params.get("status"),
            priority=request.query_params.get("priority"),
            assigned_to_id=request.query_params.get("assigned_to_id"),
            due_before=due_before,
            due_after=due_after,
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering", "-updated_at"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(TaskListSerializer(page, many=True).data)

    @extend_schema(request=TaskCreateSerializer, responses={201: TaskDetailSerializer})
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = TaskCreateSerializer(data=request.data, context={"organization": organization})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        assigned_to = serializer.context.get("assigned_to")
        task, created = TaskCreator.create_manual(
            organization=organization,
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority"),
            due_at=data.get("due_at"),
            contact_id=data.get("contact_id"),
            lead_id=data.get("lead_id"),
            client_id=data.get("client_id"),
            ticket_id=data.get("ticket_id"),
            conversation_id=data.get("conversation_id"),
            assigned_to=assigned_to,
            actor=request.user,
            request=request,
            metadata=data.get("metadata", {}),
            idempotency_key=data.get("idempotency_key", ""),
        )
        task = task_get_for_organization(organization, task.id)
        return success_response(
            request, TaskDetailSerializer(task).data, status=201 if created else 200
        )


class TaskDetailView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: TaskDetailSerializer})
    def get(self, request, task_id):
        organization = resolve_current_organization(request)
        return success_response(
            request, TaskDetailSerializer(_get_task_or_404(organization, task_id)).data
        )

    @extend_schema(request=TaskUpdateSerializer, responses={200: TaskDetailSerializer})
    def patch(self, request, task_id):
        organization = resolve_current_organization(request)
        task = _get_task_or_404(organization, task_id)
        serializer = TaskUpdateSerializer(
            data=request.data,
            partial=True,
            context={"organization": organization},
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "assigned_to_id" in data:
            data["assigned_to"] = serializer.context.get("assigned_to")
            data.pop("assigned_to_id", None)
        task = TaskUpdater.update(
            organization=organization,
            task=task,
            data=data,
            actor=request.user,
            request=request,
        )
        task = task_get_for_organization(organization, task.id)
        return success_response(request, TaskDetailSerializer(task).data)


class TaskCompleteView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=None, responses={200: TaskDetailSerializer})
    def post(self, request, task_id):
        organization = resolve_current_organization(request)
        task = TaskCompletionService.complete(
            task=_get_task_or_404(organization, task_id),
            actor=request.user,
            request=request,
        )
        return success_response(
            request, TaskDetailSerializer(task_get_for_organization(organization, task.id)).data
        )


class TaskSnoozeView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=TaskSnoozeSerializer, responses={200: TaskDetailSerializer})
    def post(self, request, task_id):
        organization = resolve_current_organization(request)
        task = _get_task_or_404(organization, task_id)
        serializer = TaskSnoozeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskCompletionService.snooze(
            task=task,
            snooze_until=serializer.validated_data["snooze_until"],
            actor=request.user,
            request=request,
        )
        return success_response(
            request, TaskDetailSerializer(task_get_for_organization(organization, task.id)).data
        )


class TaskCancelView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=None, responses={200: TaskDetailSerializer})
    def post(self, request, task_id):
        organization = resolve_current_organization(request)
        task = TaskCompletionService.cancel(
            task=_get_task_or_404(organization, task_id),
            actor=request.user,
            request=request,
        )
        return success_response(
            request, TaskDetailSerializer(task_get_for_organization(organization, task.id)).data
        )


class TaskReminderView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=TaskReminderCreateSerializer, responses={201: TaskReminderSerializer})
    def post(self, request, task_id):
        organization = resolve_current_organization(request)
        task = _get_task_or_404(organization, task_id)
        serializer = TaskReminderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reminder, created = TaskScheduler.schedule_reminder(
            task=task,
            remind_at=serializer.validated_data["remind_at"],
            channel=serializer.validated_data["channel"],
            actor=request.user,
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return success_response(
            request, TaskReminderSerializer(reminder).data, status=201 if created else 200
        )


def _parse_dt(value):
    return parse_datetime(value) if value else None
