from crm.core.security.permissions import PermissionCode

ACTION_PERMISSIONS = {
    "send_whatsapp_message": PermissionCode.CONVERSATIONS_REPLY.value,
    "notify_owner": PermissionCode.TASKS_MANAGE.value,
    "create_task": PermissionCode.TASKS_MANAGE.value,
    "update_lead_stage": PermissionCode.LEADS_UPDATE.value,
    "create_ticket": PermissionCode.TICKETS_MANAGE.value,
    "pause_ai": PermissionCode.CONVERSATIONS_TAKEOVER.value,
    "assign_user": PermissionCode.SETTINGS_MANAGE.value,
    "schedule_followup": PermissionCode.LEADS_UPDATE.value,
}
