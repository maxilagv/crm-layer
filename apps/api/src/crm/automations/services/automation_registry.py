from crm.automations.domain.enums import AutomationActionType, AutomationTriggerType


class AutomationRegistry:
    triggers = AutomationTriggerType.values
    actions = AutomationActionType.values
