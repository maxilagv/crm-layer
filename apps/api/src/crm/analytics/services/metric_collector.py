from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from crm.ai.domain.enums import AIRunStatus
from crm.ai.models import AIRun, AIUsageRecord
from crm.analytics.services.time import day_bounds
from crm.automations.domain.enums import AutomationRunStatus
from crm.automations.models import AutomationRun
from crm.conversations.constants import MessageDirection
from crm.conversations.models import Message
from crm.leads.domain.enums import LeadStage, LeadTemperature
from crm.leads.models import Lead
from crm.media.domain.enums import TranscriptionStatus
from crm.media.models import Transcription
from crm.notifications.domain.enums import NotificationDeliveryStatus
from crm.notifications.models import NotificationDelivery
from crm.sales.domain.enums import CallRequestStatus
from crm.sales.models import SalesCallRequest
from crm.support.domain.enums import TicketPriority
from crm.support.models import SupportTicket
from crm.tasks.domain.enums import ACTIVE_TASK_STATUSES, TaskReminderStatus, TaskStatus
from crm.tasks.models import Task, TaskReminder
from crm.whatsapp.domain.enums import OutboundMessageStatus
from crm.whatsapp.models import WhatsAppOutboundMessage


class MetricCollector:
    @staticmethod
    def collect_for_day(*, organization, date) -> dict:
        start, end = day_bounds(date)
        organization_id = organization.id
        resolved_tickets = list(
            SupportTicket.objects.filter(
                organization_id=organization_id,
                resolved_at__gte=start,
                resolved_at__lt=end,
            ).only("created_at", "resolved_at")
        )
        resolution_seconds = [
            (ticket.resolved_at - ticket.created_at).total_seconds()
            for ticket in resolved_tickets
            if ticket.resolved_at
        ]
        ai_cost = AIUsageRecord.objects.filter(
            organization_id=organization_id,
            created_at__gte=start,
            created_at__lt=end,
        ).aggregate(total=Sum("estimated_cost"))["total"] or Decimal("0")
        whatsapp_failures = WhatsAppOutboundMessage.objects.filter(
            organization_id=organization_id,
            created_at__gte=start,
            created_at__lt=end,
            status=OutboundMessageStatus.FAILED.value,
        ).count()
        failed_messages = Message.objects.filter(
            organization_id=organization_id,
            direction=MessageDirection.OUTBOUND,
            status="failed",
            created_at__gte=start,
            created_at__lt=end,
        ).count()
        return {
            "messages_received_total": Message.objects.filter(
                organization_id=organization_id,
                direction=MessageDirection.INBOUND,
                created_at__gte=start,
                created_at__lt=end,
            ).count(),
            "messages_sent_total": Message.objects.filter(
                organization_id=organization_id,
                direction=MessageDirection.OUTBOUND,
                created_at__gte=start,
                created_at__lt=end,
            ).count(),
            "leads_created_total": Lead.objects.filter(
                organization_id=organization_id, created_at__gte=start, created_at__lt=end
            ).count(),
            "hot_leads_total": Lead.objects.filter(
                organization_id=organization_id,
                created_at__lt=end,
            )
            .filter(stage=LeadStage.HOT.value)
            .count()
            + Lead.objects.filter(
                organization_id=organization_id,
                created_at__lt=end,
                temperature__in=[LeadTemperature.HOT.value, LeadTemperature.CRITICAL.value],
            ).count(),
            "calls_requested_total": SalesCallRequest.objects.filter(
                organization_id=organization_id,
                requested_at__gte=start,
                requested_at__lt=end,
            ).count(),
            "calls_scheduled_total": SalesCallRequest.objects.filter(
                organization_id=organization_id,
                status=CallRequestStatus.SCHEDULED.value,
                scheduled_at__gte=start,
                scheduled_at__lt=end,
            ).count(),
            "tickets_created_total": SupportTicket.objects.filter(
                organization_id=organization_id, created_at__gte=start, created_at__lt=end
            ).count(),
            "tickets_resolved_total": len(resolved_tickets),
            "tickets_urgent_total": SupportTicket.objects.filter(
                organization_id=organization_id,
                created_at__gte=start,
                created_at__lt=end,
                priority__in=[TicketPriority.URGENT.value, TicketPriority.CRITICAL.value],
            ).count(),
            "average_resolution_time_seconds": round(
                sum(resolution_seconds) / len(resolution_seconds), 2
            )
            if resolution_seconds
            else 0,
            "tasks_created_total": Task.objects.filter(
                organization_id=organization_id, created_at__gte=start, created_at__lt=end
            ).count(),
            "tasks_completed_total": Task.objects.filter(
                organization_id=organization_id,
                status=TaskStatus.COMPLETED.value,
                completed_at__gte=start,
                completed_at__lt=end,
            ).count(),
            "tasks_overdue_total": Task.objects.filter(
                organization_id=organization_id,
                status__in=ACTIVE_TASK_STATUSES,
                due_at__lt=min(end, timezone.now()),
            ).count(),
            "reminders_sent_total": TaskReminder.objects.filter(
                organization_id=organization_id,
                status=TaskReminderStatus.SENT.value,
                sent_at__gte=start,
                sent_at__lt=end,
            ).count(),
            "notifications_sent_total": NotificationDelivery.objects.filter(
                organization_id=organization_id,
                status=NotificationDeliveryStatus.SENT.value,
                sent_at__gte=start,
                sent_at__lt=end,
            ).count(),
            "notifications_failed_total": NotificationDelivery.objects.filter(
                organization_id=organization_id,
                status=NotificationDeliveryStatus.FAILED.value,
                failed_at__gte=start,
                failed_at__lt=end,
            ).count(),
            "automation_runs_total": AutomationRun.objects.filter(
                organization_id=organization_id,
                created_at__gte=start,
                created_at__lt=end,
            ).count(),
            "automation_failures_total": AutomationRun.objects.filter(
                organization_id=organization_id,
                status__in=[
                    AutomationRunStatus.FAILED.value,
                    AutomationRunStatus.PARTIALLY_FAILED.value,
                ],
                created_at__gte=start,
                created_at__lt=end,
            ).count(),
            "ai_runs_total": AIRun.objects.filter(
                organization_id=organization_id, created_at__gte=start, created_at__lt=end
            ).count(),
            "ai_failures_total": AIRun.objects.filter(
                organization_id=organization_id,
                status=AIRunStatus.FAILED.value,
                created_at__gte=start,
                created_at__lt=end,
            ).count(),
            "ai_cost_total": str(ai_cost),
            "whatsapp_failures_total": whatsapp_failures,
            "failed_messages_total": failed_messages + whatsapp_failures,
            "audio_transcription_failures_total": Transcription.objects.filter(
                organization_id=organization_id,
                status=TranscriptionStatus.FAILED.value,
                created_at__gte=start,
                created_at__lt=end,
            ).count(),
        }
