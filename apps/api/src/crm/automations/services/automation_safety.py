from crm.automations.domain.rules import has_automation_loop


class AutomationSafety:
    has_loop = staticmethod(has_automation_loop)
