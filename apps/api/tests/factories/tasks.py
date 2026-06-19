import uuid

import factory
from django.utils import timezone

from crm.tasks.domain.enums import TaskReminderStatus, TaskStatus
from crm.tasks.models import Task, TaskReminder


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Task

    organization_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Sequence(lambda n: f"Task {n}")
    status = TaskStatus.PENDING
    due_at = factory.LazyFunction(timezone.now)


class TaskReminderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskReminder

    task = factory.SubFactory(TaskFactory)
    organization_id = factory.SelfAttribute("task.organization_id")
    remind_at = factory.LazyFunction(timezone.now)
    status = TaskReminderStatus.PENDING
