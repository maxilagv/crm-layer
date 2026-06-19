from django.db import models


class AutomationTriggerType(models.TextChoices):
    MESSAGE_RECEIVED = "message_received", "Message received"
    LEAD_SCORE_CHANGED = "lead_score_changed", "Lead score changed"
    LEAD_BECAME_HOT = "lead_became_hot", "Lead became hot"
    TICKET_CREATED = "ticket_created", "Ticket created"
    TASK_DUE = "task_due", "Task due"
    TASK_OVERDUE = "task_overdue", "Task overdue"
    AUDIO_TRANSCRIBED = "audio_transcribed", "Audio transcribed"
    CLIENT_REGISTERED = "client_registered", "Client registered"
    CONVERSATION_PAUSED = "conversation_paused", "Conversation paused"


class AutomationActionType(models.TextChoices):
    SEND_WHATSAPP_MESSAGE = "send_whatsapp_message", "Send WhatsApp message"
    NOTIFY_OWNER = "notify_owner", "Notify owner"
    CREATE_TASK = "create_task", "Create task"
    UPDATE_LEAD_STAGE = "update_lead_stage", "Update lead stage"
    CREATE_TICKET = "create_ticket", "Create ticket"
    PAUSE_AI = "pause_ai", "Pause AI"
    ASSIGN_USER = "assign_user", "Assign user"
    SCHEDULE_FOLLOWUP = "schedule_followup", "Schedule followup"


class AutomationRuleStatus(models.TextChoices):
    ENABLED = "enabled", "Enabled"
    DISABLED = "disabled", "Disabled"


class AutomationRunStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SKIPPED = "skipped", "Skipped"
    SUCCESS = "success", "Success"
    PARTIALLY_FAILED = "partially_failed", "Partially failed"
    FAILED = "failed", "Failed"
    DUPLICATE = "duplicate", "Duplicate"


class AutomationStepStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SKIPPED = "skipped", "Skipped"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    BLOCKED = "blocked", "Blocked"


class AutomationStepType(models.TextChoices):
    CONDITION = "condition", "Condition"
    ACTION = "action", "Action"
